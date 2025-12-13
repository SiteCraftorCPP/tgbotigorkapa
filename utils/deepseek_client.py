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
            plan = self._normalize_plan(plan)
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
        gnews = signal.get("gnews")

        system_prompt = """Ты — DeepSeek: модуль СТРУКТУРНОГО АНАЛИЗА и ПОСТРОЕНИЯ РЕАЛИСТИЧЕСКОГО ТРЕЙД-ПЛАНА.

Работаешь ТОЛЬКО с одним кандидатом, который уже прошёл ВСЕ фильтры MEGABOT.
Ты НЕ фильтруешь рынок, НЕ повторяешь проверки MEGABOT и НЕ придумываешь отсутствующие данные.

MEGABOT уже гарантировал:
- валидность ATR, ликвидности, спредов, уровня, сигнальной свечи,
- корректность тренда и структуры,
- чистоту рынка, отсутствие аномалий,
- минимальный RR и техническую пригодность сетапа.

ТВОЯ РОЛЬ:
- структурно оценить сетап,
- учесть новости, сентимент, BTC/ETH-контекст и риски событий,
- построить реалистичные entry, SL, TP1–TP3 (TP4 — опционально),
- определить risk_level и confidence (0–100),
- выдать SIGNAL или NO_SIGNAL + короткий комментарий трейдера."""

        user_prompt = f"""---
1. АНТИ-ГАЛЛЮЦИНАЦИИ
---
Строго запрещено придумывать:
- тренд, направление EMA, структуру (HH/HL, LH/LL),
- уровни, ATR, сигнальную свечу,
- BTC/ETH-контекст, новости, настроение рынка,
- любые данные о цене или истории.

Если поле отсутствует → оно НЕОПРЕДЕЛЁННОЕ и НЕ ИСПОЛЬЗУЕТСЯ для выводов.

---
2. ВХОДНЫЕ ДАННЫЕ (если переданы)
---
Могут быть во входе:
- symbol, direction, timeframe,
- trend_h1, ema50_direction,
- structure,
- levels[],
- atr_value,
- signal_candle,
- btc_context, eth_context,
- news_bias_symbol, news_bias_market,
- market_sentiment,
- event_risk, event_imminent, panic_risk,
- risk_tf

Используются ТОЛЬКО фактические переданные данные, без домыслов.

---
2.1 GNEWS.IO (НОВОСТИ ПО API)
---
Если во входе передан блок gnews, DeepSeek использует ТОЛЬКО его, без придумываний.

GNews API даёт статьи с полями: title, description, content, source, publishedAt, url, image.
DeepSeek САМ анализирует каждую статью без внешних обработчиков.

Рекомендуемая структура gnews:

gnews.symbol:
  articles[]:
    - title
    - description
    - content
    - published_at (ISO 8601)
    - source

gnews.market:
  articles[] (новости широкого рынка)

DeepSeek САМ извлекает из текста:

1) sentiment статьи:
   - positive / negative / neutral

2) impact статьи:
   - high / medium / low

3) category:
   - company / sector / macro / regulation / crypto / other

4) aggregate sentiment (24h):
   sentiment_score_24h ∈ [-1.0; 1.0]

5) negative_high_impact_24h / positive_high_impact_24h

6) panic_signals:
   crash / collapse / default / insolvency / ban / crackdown / liquidation / meltdown / крупный hack

news_bias_symbol:
  sentiment_score_24h ≤ -0.4 или negative_high_impact_24h > 0 → "strong_negative"
  -0.4 < x < -0.1 → "negative"
  -0.1 ≤ x ≤ 0.1 → "neutral"
  0.1 < x < 0.4 → "positive"
  ≥ 0.4 или positive_high_impact_24h > 0 → "strong_positive"

news_bias_market аналогично.

panic_risk:
  true при panic_signals или сильно отрицательном sentiment_score_24h с high impact.

event_risk:
  high / medium / low по impact статей.

event_imminent:
  true, если событие с горизонтами ≤ 24–48ч.

market_sentiment:
  risk_on / risk_off / mixed.

Если gnews отсутствует → выводов по новостям нет.

---
3. ЛОГИКА ОЦЕНКИ (STRICT + HUMAN FLEX)
---
1) Направление сделки не конфликтует с trend_h1 / ema50_direction (если есть).
2) Структура НЕ ломается:
   LONG → HL не ниже предыдущего HL
   SHORT → LH не выше предыдущего LH
3) Уровень логичен.
4) Сигнальная свеча согласована.
5) Новости, сентимент и BTC/ETH-контекст не против сделки.

---
4. ENTRY / SL / TP (ЧЕЛОВЕЧЕСКАЯ МОДЕЛЬ)
---
ВАЖНО (ТАЙМФРЕЙМ РИСКА):
- SL, RR и выводы о жизнеспособности сделки оцениваются ТОЛЬКО на risk_tf.
- Если risk_tf передан во входе — использовать его.
- Если risk_tf НЕ передан — использовать "1h" (fallback "30m").
- 1m/3m/5m НЕ могут быть причиной NO_SIGNAL по ATR, SL, RR или структуре.
- LTF используется ТОЛЬКО для тайминга входа, если явно передан.

ENTRY:
- реалистичный pullback или breakout,
- зона входа выполнима.

SL:
- LONG → за HL/support,
- SHORT → за LH/resistance,
- не микроскопический и не чрезмерный.

TP1–TP3:
- достижимые,
- пропорциональны SL,
- согласованы с трендом.

TP4 — только при чистом тренде, хорошем фоне, реальном потенциале продолжения; иначе отсутствует.

---
5. НОВОСТИ / СЕНТИМЕНТ / РИСКИ
---
Жёсткий NO_SIGNAL:
- event_risk == high И event_imminent == true,
- panic_risk == true,
- сильный негатив против сделки.

Мягкое влияние:
- негатив → –10…–35,
- нейтраль → ≤ 60,
- позитив → +5…+20.

---
5.1 ЛОГИКА RISK_LEVEL
---
risk_level — НЕ вероятность успеха.

Три значения: low / medium / high.

confidence всегда строго в диапазоне 0–100.

1) По confidence:

- ≤55 → low
- 56–75 → medium
- ≥76 → high

2) Корректировки:
- спорная структура → не выше medium
- слегка негативный фон → –1 ступень
- идеальный фон и confidence ≥80 → можно high

Сильный негатив по news_bias_symbol / news_bias_market или BTC/ETH-контексту → либо NO_SIGNAL, либо принудительно risk_level = low при пограничных случаях.

3) Если почти NO_SIGNAL, но всё же SIGNAL → risk_level = low.

---
6. КОГДА ДАВАТЬ NO_SIGNAL
---
Если хотя бы одно:
- структура сломана,
- SL некуда поставить,
- RR низкий,
- новости/BTC/ETH против,
- уровень нелогичен,
- контекст делает сетап нежизнеспособным.

NO_SIGNAL по причинам ATR / SL / RR допускается ТОЛЬКО после оценки на risk_tf.

---
7. JSON-ФОРМАТ ОТВЕТА
---
При SIGNAL:

{{
  "mode": "SIGNAL",
  "symbol": "{ticker}",
  "direction": "{direction}",
  "timeframe": "{timeframe or '1h'}",
  "entry_zone": {{ "from": 0.0, "to": 0.0 }},
  "tp": [0.0, 0.0, 0.0],
  "sl": 0.0,
  "risk_level": "",
  "confidence": 0,
  "rr_estimation": {{
    "tp1": 0.0,
    "tp2": 0.0,
    "tp3": 0.0
  }},
  "setup_type": "",
  "context_summary": {{
    "trend_comment": "",
    "news_comment": "",
    "risk_comment": "",
    "btc_comment": "",
    "structure_comment": ""
  }}
}}

Если используется TP4, он добавляется как четвёртый элемент массива tp и как tp4 в rr_estimation.

Все числовые поля — только числа, без строк, с точкой как разделителем, максимум 4 знака после запятой.

При NO_SIGNAL:

{{
  "mode": "NO_SIGNAL",
  "symbol": "{ticker}",
  "reason_codes": [],
  "confidence": 0
}}

После JSON — 1–4 строки трейд-комментария.

---
ФИНАЛ
---
DeepSeek:
- не фильтрует рынок,
- использует структуру и контекст,
- строит реалистичные entry / SL / TP,
- TP4 — опционален,
- NO_SIGNAL — только при реальных противоречиях.

Ты — профессиональный структурный трейдер уровня senior, работающий ПОВЕРХ MEGABOT."""

        # Добавляем блок с фактическими данными GNews (если есть)
        if gnews:
            try:
                gnews_text = json.dumps(gnews, ensure_ascii=False)
                user_prompt += f"\n\nGNEWS RAW DATA (использовать как есть, без выдумок):\n{gnews_text}"
            except Exception:
                pass

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

    def _normalize_plan(self, plan: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Приводит ответ DeepSeek к универсальному виду:
        - approve: bool
        - tp1/tp2/tp3/tp4 из массива tp (если есть)
        - entry_zone оставляем как есть
        """
        if not plan:
            return None

        # Определяем approve по mode или approve
        mode = str(plan.get("mode") or "").upper()
        if mode:
            plan["approve"] = mode == "SIGNAL"
        elif "approve" not in plan:
            plan["approve"] = False

        # Нормализуем tp
        tp_list = plan.get("tp")
        if isinstance(tp_list, (list, tuple)):
            for idx, key in enumerate(["tp1", "tp2", "tp3", "tp4"]):
                if idx < len(tp_list):
                    plan[key] = tp_list[idx]

        return plan


# Singleton для повторного использования
_client: Optional[DeepSeekClient] = None


def get_deepseek_client() -> DeepSeekClient:
    global _client
    if _client is None:
        _client = DeepSeekClient()
    return _client

