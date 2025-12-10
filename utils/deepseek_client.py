import asyncio
import json
import re
from typing import Any, Dict, Optional

import httpx

import config
from utils.logger import log_error, log_info


class DeepSeekClient:
    """
    Простая обёртка для DeepSeek chat/completions.
    Поддерживает раунд-робин по списку ключей и отключённый timeout (по требованию).
    """

    def __init__(self):
        self._keys = config.DEEPSEEK_API_KEYS or []
        self._model = config.DEEPSEEK_MODEL or "deepseek-chat"
        self._base_url = (config.DEEPSEEK_API_BASE or "https://api.deepseek.com").rstrip("/")
        self._index = 0

    def _next_key(self) -> str:
        if not self._keys:
            raise RuntimeError("DEEPSEEK_API_KEYS is empty. Add keys to .env.")
        key = self._keys[self._index]
        self._index = (self._index + 1) % len(self._keys)
        return key

    async def analyze_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Отправляет сигнал на анализ. Возвращает dict:
        {
          'approved': bool,
          'plan': {...parsed json...} or None,
          'raw': original text,
          'error': optional str
        }
        """
        try:
            key = self._next_key()
        except RuntimeError as e:
            return {"approved": False, "plan": None, "raw": "", "error": str(e)}

        payload = self._build_payload(signal)
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=None) as client:
                resp = await client.post(
                    f"{self._base_url}/v1/chat/completions",
                    json=payload,
                    headers=headers,
                )
            if resp.status_code >= 300:
                msg = f"DeepSeek HTTP {resp.status_code}: {resp.text[:400]}"
                log_error(msg, "deepseek_http")
                return {"approved": False, "plan": None, "raw": resp.text, "error": msg}

            data = resp.json()
            content = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            plan = self._extract_json(content)
            approved = bool(plan.get("approve")) if plan else False
            return {"approved": approved, "plan": plan, "raw": content, "error": None}
        except Exception as e:
            msg = f"DeepSeek request failed: {e}"
            log_error(msg, "deepseek_request")
            return {"approved": False, "plan": None, "raw": "", "error": msg}

    def _build_payload(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Готовит messages для Chat Completions.
        Просим вернуть ТОЛЬКО JSON с ключами:
        approve (bool), entry_zone ({from,to} или number), sl, tp1, tp2, tp3,
        tp4 (optional), confidence (0-100 или 0-1), risk_level (low/medium/high),
        setup_type (string), context_summary (trend_comment, news_comment,
        btc_comment, risk_comment), reason (short text).
        """
        ticker = signal.get("ticker")
        direction = signal.get("direction")
        timeframe = signal.get("timeframe")
        entry = signal.get("entry_price")
        stop = signal.get("stop_loss")
        tp1 = signal.get("take_profit_1")
        tp2 = signal.get("take_profit_2")
        tp3 = signal.get("take_profit_3")
        leverage = signal.get("leverage")
        spread = signal.get("spread_percent")
        volume_24h = signal.get("volume_24h")
        atr = signal.get("atr_value")
        analysis = signal.get("analysis", {})

        system_prompt = (
            "Ты — DeepSeek: модуль структурного анализа и построения реалистичного трейд‑плана "
            "поверх MEGABOT. MEGABOT уже проверил ATR, ликвидность, спреды, уровни, сигнальную свечу, "
            "тренд и структуру. Ты НЕ фильтруешь рынок и НЕ дублируешь проверки MEGABOT. "
            "Уровни entry/SL/TP MEGABOT не задаёт — ты строишь их сам; любые переданные черновые уровни "
            "можешь полностью игнорировать и заменить. Строго избегай галлюцинаций и используй только "
            "переданные данные. Отвечай ТОЛЬКО одним JSON‑объектом без markdown и комментариев."
        )

        user_prompt = f"""
ТЫ — DeepSeek, структурный трейдер уровня senior, работающий ПОВЕРХ MEGABOT.
MEGABOT уже гарантировал валидность сетапа (ATR, ликвидность, спреды, уровень, сигнальная свеча,
тренд и структура, минимальный RR и отсутствие аномалий).

ТВОЯ РОЛЬ:
- структурно оценить сетап,
- учесть новости/сентимент/BTC‑контекст и риски событий,
- самостоятельно построить реалистичные entry, SL, TP1–TP3 (TP4 строго опционален) без опоры на черновые уровни,
- определить risk_level и confidence (0–100),
- выдать SIGNAL (approve=true) или NO_SIGNAL (approve=false) с кратким комментарием reason.

АНТИ‑ГАЛЛЮЦИНАЦИИ:
- нельзя придумывать тренд, направление EMA, структуру (HH/HL, LH/LL),
- нельзя придумывать уровни, ATR, сигнальную свечу, BTC/ETH‑контекст, новости, настроение рынка,
- если поле отсутствует во входных данных/analysis → оно НЕОПРЕДЕЛЁННО и НЕ используется.

СТРУКТУРНАЯ ОЦЕНКА:
1) Направление сделки не должно явно конфликтовать с трендом/структурой из входных данных (если есть).
2) SL:
   - LONG → за HL или значимый support;
   - SHORT → за LH или значимый resistance;
   - SL не должен быть микроскопическим и не должен быть бессмысленно глубоким.
3) TP1–TP3:
   - достижимые и логичные,
   - пропорциональны размеру SL,
   - согласованы с трендом, волатильностью и расположением уровней,
   - строятся как у опытного трейдера, а не как жёсткая формула.
4) TP4:
   - добавляй ТОЛЬКО если тренд выраженный, структура чистая и контекст не негативный;
   - если условий нет → TP4 вообще не указывай.

RISK_LEVEL и CONFIDENCE:
- confidence: 0–100 (можно дробные, они будут округлены).
- базово: confidence ≤55 → risk_level="low"; 56–75 → "medium"; ≥76 → "high".
- если структура неполная/спорная — risk_level НЕ ВЫШЕ "medium".
- если BTC/ETH‑контекст или новости ближе к нейтральным/слегка негативным — понижай риск на одну ступень.
- если условия тянут на NO_SIGNAL, но сделка допустима как пограничная — risk_level="low".

КОГДА ДАВАТЬ NO_SIGNAL (approve=false):
- структура явно сломана и конфликтует с трендом,
- SL нельзя поставить корректно по структуре,
- RR слишком низкий для адекватной сделки,
- новости/сентимент или BTC/ETH‑контекст явно против сигнала,
- уровень во входных данных нелогичен как зона входа,
- внешний контекст делает сетап нежизнеспособным.

ФОРМАТ ОТВЕТА — СТРОГО ТОЛЬКО ОДИН JSON‑ОБЪЕКТ:
- Поля:
  approve (bool),
  entry_zone (число или объект с полями from/to),
  sl (число),
  tp1, tp2, tp3 (числа), tp4 (число, опционален),
  confidence (0–100),
  risk_level ("low"|"medium"|"high"),
  setup_type (строка, краткое описание сетапа),
  context_summary (объект с полями trend_comment, news_comment, btc_comment, risk_comment),
  reason (очень краткий комментарий трейдера, почему approve true/false).

Входные данные сигнала:
- ticker: {ticker}
- direction: {direction}
- timeframe: {timeframe}
- leverage: {leverage}
- volume_24h: {volume_24h}
- spread_percent: {spread}
- atr_value: {atr}
- analysis: {json.dumps(analysis, default=str)}
- legacy_levels (черновик, можно игнорировать и заменить полностью):
  entry={entry}, stop={stop}, tp1={tp1}, tp2={tp2}, tp3={tp3}

Правила:
- Не придумывай данные, которых нет.
- Если сетап неприемлем → approve=false и reason с кратким объяснением.
- Числа оставляй числами (float), проценты тоже в виде чисел.
- Строго НИКАКОГО текста вне одного JSON‑объекта.
"""

        return {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 800,
        }

    def _extract_json(self, content: str) -> Optional[Dict[str, Any]]:
        """Пытается найти и распарсить первый JSON в тексте."""
        if not content:
            return None
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Fallback: искать первый {...}
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except Exception:
            return None


# Singleton для повторного использования
_client: Optional[DeepSeekClient] = None


def get_deepseek_client() -> DeepSeekClient:
    global _client
    if _client is None:
        _client = DeepSeekClient()
    return _client

