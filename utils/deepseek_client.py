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
            "Ты — профессиональный структурный трейдер уровня senior. "
            "Ты не фильтруешь рынок и не дублируешь MEGABOT. "
            "Используешь структуру, новости и контекст. "
            "Ставишь реалистичные entry/SL/TP. TP4 — строго опционален. "
            "NO_SIGNAL только при реальных противоречиях. "
            "Возвращай ТОЛЬКО JSON (без markdown, без комментариев)."
        )

        user_prompt = f"""
ФИНАЛ. DeepSeek:
- не фильтрует рынок,
- не дублирует MEGABOT,
- работает как опытный трейдер,
- использует структуру, новости и контекст,
- ставит реалистичные entry / SL / TP,
- TP4 — строго опционален,
- NO_SIGNAL — только при реальных противоречиях.

Верни ТОЛЬКО JSON с ключами:
approve (bool), entry_zone ({{from,to}} или число), sl, tp1, tp2, tp3, tp4 (optional),
confidence (0..100 или 0..1), risk_level ("low"|"medium"|"high"),
setup_type (строка), context_summary: {{trend_comment, news_comment, btc_comment, risk_comment}},
reason (коротко).

Входные данные сигнала:
- ticker: {ticker}
- direction: {direction}
- timeframe: {timeframe}
- leverage: {leverage}
- entry: {entry}
- stop: {stop}
- tp1: {tp1}
- tp2: {tp2}
- tp3: {tp3}
- volume_24h: {volume_24h}
- spread_percent: {spread}
- atr_value: {atr}
- analysis: {json.dumps(analysis, default=str)}

Правила:
- Не придумывай данные, которых нет.
- Если есть реальные противоречия — approve=false и reason.
- Числа оставляй числами (float).
- Без markdown и текста вне JSON.
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

