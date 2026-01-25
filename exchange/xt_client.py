import os
import pandas as pd
import asyncio
import httpx
import time
from typing import List, Dict, Optional
import config
from utils.logger import logger

class XTClient:
    """
    Полностью асинхронный клиент для XT.com API (Futures V4).
    Использует httpx для неблокирующих запросов.
    """
    
    def __init__(self):
        self.base_url = "https://fapi.xt.com"
        self.api_key = config.XT_API_KEY
        self.api_secret = config.XT_API_SECRET
        # Используем один клиент для всех запросов
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(10.0, read=15.0),
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=20)
        )

    async def _request(self, method: str, path: str, params: Dict = None) -> Dict:
        """Асинхронный HTTP запрос к XT.com"""
        try:
            response = await self.client.request(method, path, params=params)
            data = response.json()
            if data.get('returnCode') != 0:
                return {}
            return data
        except Exception as e:
            logger.debug(f"XT Request failed {path}: {e}")
            return {}

    async def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        """Асинхронное получение свечей"""
        symbol_id = symbol.replace('/', '_').lower()
        
        tf_map = {
            '1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '1h', '2h': '2h', '4h': '4h', '6h': '6h', '8h': '8h', '12h': '12h',
            '1d': '1d', '3d': '3d', '1w': '1w'
        }
        
        path = "/future/market/v1/public/q/kline"
        params = {
            'symbol': symbol_id,
            'interval': tf_map.get(timeframe, timeframe),
            'limit': limit
        }
        
        data = await self._request('GET', path, params)
        result = data.get('result', [])
        
        if not result or not isinstance(result, list):
            return pd.DataFrame()
            
        try:
            df = pd.DataFrame(result)
            df = df.rename(columns={'t': 'timestamp', 'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'})
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            df.set_index('timestamp', inplace=True)
            return df
        except Exception:
            return pd.DataFrame()

    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Асинхронное получение цены"""
        symbol_id = symbol.replace('/', '_').lower()
        path = "/future/market/v1/public/q/tickers"
        params = {'symbol': symbol_id}
        
        data = await self._request('GET', path, params)
        result = data.get('result', [])
        
        if result and isinstance(result, list):
            t = result[0]
            return {
                'symbol': symbol,
                'last': float(t.get('c', 0)),
                'volume': float(t.get('v', 0))
            }
        return None

    async def get_all_futures_symbols(self) -> List[str]:
        """Асинхронное получение всех пар"""
        path = "/future/market/v1/public/symbol/list"
        data = await self._request('GET', path)
        symbols = data.get('result', [])
        
        pairs = []
        for s in symbols:
            if s.get('quoteCurrency') == 'usdt' and s.get('state') == 'TRADING':
                base = s.get('baseCurrency', '').upper()
                pairs.append(f"{base}/USDT")
        return pairs

    async def close(self):
        """Закрытие клиента"""
        await self.client.aclose()
