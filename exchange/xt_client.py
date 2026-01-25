import os
import pandas as pd
import asyncio
import requests
import time
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor
import config
from utils.logger import logger

class XTClient:
    """
    Чистый клиент для XT.com API (Futures V4).
    Никаких клонов Binance, только прямые запросы к XT.
    """
    
    def __init__(self):
        self.base_url = "https://fapi.xt.com"
        self.api_key = config.XT_API_KEY
        self.api_secret = config.XT_API_SECRET
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.markets_cache = {}

    async def _request(self, method: str, path: str, params: Dict = None) -> Dict:
        """Прямой HTTP запрос к XT.com"""
        url = f"{self.base_url}{path}"
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                self.executor, 
                lambda: requests.request(method, url, params=params, timeout=10)
            )
            data = response.json()
            if data.get('returnCode') != 0:
                logger.debug(f"XT API Error {path}: {data}")
                return {}
            return data
        except Exception as e:
            logger.error(f"XT Request failed {path}: {e}")
            return {}

    async def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        """Получение свечей через чистый XT Futures V4 API"""
        # Превращаем BTC/USDT в btc_usdt
        symbol_id = symbol.replace('/', '_').lower()
        
        # Маппинг таймфреймов для XT
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
            # XT V4: [{"t":123,"o":"1.1","h":"1.2","l":"1.0","c":"1.15","v":"100"}, ...]
            df = pd.DataFrame(result)
            df = df.rename(columns={
                't': 'timestamp',
                'o': 'open',
                'h': 'high',
                'l': 'low',
                'c': 'close',
                'v': 'volume'
            })
            
            # Приведение типов
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
                
            df.set_index('timestamp', inplace=True)
            return df
        except Exception as e:
            logger.error(f"Error parsing XT OHLCV for {symbol}: {e}")
            return pd.DataFrame()

    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Получение цены через чистый XT API"""
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
                'volume': float(t.get('v', 0)),
                'high': float(t.get('h', 0)),
                'low': float(t.get('l', 0))
            }
        return None

    async def get_all_futures_symbols(self) -> List[str]:
        """Получение всех пар через чистый XT API"""
        path = "/future/market/v1/public/symbol/list"
        data = await self._request('GET', path)
        symbols = data.get('result', [])
        
        pairs = []
        for s in symbols:
            if s.get('quoteCurrency') == 'usdt' and s.get('state') == 'TRADING':
                base = s.get('baseCurrency', '').upper()
                pairs.append(f"{base}/USDT")
        return pairs

    def close(self):
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
