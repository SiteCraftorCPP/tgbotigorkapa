import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import httpx

import config
from utils.logger import logger


class GNewsClient:
    """
    Простая обёртка над GNews API для получения новостей по символу и рынку.
    Возвращает структуру, совместимую с промптом DeepSeek.
    """

    BASE_URL = "https://gnews.io/api/v4/search"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.GNEWS_API_KEY

    async def fetch(self, symbol: str) -> Optional[Dict]:
        """
        Получить новости по конкретному символу и по рынку в целом.
        Ограничиваем до 10 статей на символ и 10 по рынку, чтобы не раздувать промпт.
        """
        if not self.api_key:
            logger.info("[GNEWS] API key not set, skipping news fetch")
            return None

        try:
            symbol_query = f"{symbol} crypto"
            market_query = "crypto OR bitcoin OR ethereum"
            date_from = (datetime.utcnow() - timedelta(days=2)).isoformat(timespec="seconds") + "Z"

            async with httpx.AsyncClient(timeout=10) as client:
                symbol_articles = await self._fetch_query(client, symbol_query, date_from)
                market_articles = await self._fetch_query(client, market_query, date_from)

            result = {
                "symbol": {"articles": symbol_articles},
                "market": {"articles": market_articles},
            }
            logger.info(f"[GNEWS] Fetched news: symbol={len(symbol_articles)}, market={len(market_articles)}")
            return result
        except Exception as e:
            logger.warning(f"[GNEWS] Failed to fetch news: {e}")
            return None

    async def _fetch_query(self, client: httpx.AsyncClient, query: str, date_from: str) -> List[Dict]:
        params = {
            "q": query,
            "lang": "en",
            "max": 10,
            "sortby": "publishedAt",
            "from": date_from,
            "token": self.api_key,
        }
        resp = await client.get(self.BASE_URL, params=params)
        resp.raise_for_status()
        data = resp.json() or {}
        articles = data.get("articles", []) or []
        parsed: List[Dict] = []
        for a in articles[:10]:
            parsed.append(
                {
                    "title": a.get("title"),
                    "description": a.get("description"),
                    "content": a.get("content"),
                    "published_at": a.get("publishedAt") or a.get("published_at"),
                    "source": (a.get("source") or {}).get("name") if isinstance(a.get("source"), dict) else a.get("source"),
                    "url": a.get("url"),
                    "image": a.get("image"),
                }
            )
        return parsed


async def fetch_gnews(symbol: str) -> Optional[Dict]:
    """Хелпер для быстрого получения новостей."""
    client = GNewsClient()
    return await client.fetch(symbol)

