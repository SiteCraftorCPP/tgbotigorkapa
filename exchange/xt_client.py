import os
import ccxt
import pandas as pd
import asyncio
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor
import config
from utils.logger import logger

class XTExchange(ccxt.binance):
    """Кастомный класс для работы с XT.com через ccxt API (Futures V1)"""
    
    def __init__(self, config=None):
        if config is None:
            config = {}
        if 'options' not in config:
            config['options'] = {}
        config['options']['defaultType'] = 'future'
        
        super().__init__(config)
        
        # XT фьючерсы используют v1 API
        self.urls['api'] = {
            'public': 'https://fapi.xt.com/fapi/v1',
            'private': 'https://fapi.xt.com/fapi/v1',
            'fapiPublic': 'https://fapi.xt.com/fapi/v1',
            'fapiPrivate': 'https://fapi.xt.com/fapi/v1',
        }
        self.urls['test'] = self.urls['api']
        self.id = 'xt'
        
        if 'sapi' in self.urls.get('api', {}):
            del self.urls['api']['sapi']
        
        self.has['fetchMarkets'] = True
        self.has['fetchCurrencies'] = False
        self.options['sandboxMode'] = False
        self.markets = {}

    def set_sandbox_mode(self, enabled):
        self.sandboxMode = False
        return self.urls

    def fetch_markets(self, params={}):
        """Получает список рынков с XT.com через V4 API (более надежно)"""
        try:
            import requests
            url = "https://fapi.xt.com/future/market/v1/public/symbol/list"
            resp = requests.get(url, timeout=15)
            data = resp.json()
            
            if data.get('returnCode') != 0:
                return []
                
            symbols = data.get('result', [])
            result = []
            for s in symbols:
                if s.get('quoteCurrency') != 'usdt':
                    continue
                
                base = s.get('baseCurrency', '').upper()
                quote = 'USDT'
                symbol = f"{base}/{quote}"
                
                result.append({
                    'id': s.get('symbol'),
                    'symbol': symbol,
                    'base': base,
                    'quote': quote,
                    'baseId': base.lower(),
                    'quoteId': 'usdt',
                    'active': s.get('state') == 'TRADING',
                    'type': 'future',
                    'linear': True,
                    'inverse': False,
                    'spot': False,
                    'swap': True,
                    'future': True,
                    'option': False,
                    'margin': False,
                    'contract': True,
                    'contractSize': float(s.get('contractSize', 1.0)),
                    'precision': {
                        'amount': int(s.get('quantityPrecision', 8)),
                        'price': int(s.get('pricePrecision', 8)),
                    },
                    'limits': {
                        'amount': {
                            'min': float(s.get('minQty', 0)) if s.get('minQty') else None,
                            'max': None,
                        },
                        'price': {
                            'min': float(s.get('minPrice', 0)) if s.get('minPrice') else None,
                            'max': None,
                        },
                    },
                    'info': s,
                })
            return result
        except Exception as e:
            logger.error(f"Error fetching markets from XT: {e}")
            return []

    def market(self, symbol):
        """Определяет параметры рынка для символа"""
        if self.markets and symbol in self.markets:
            return self.markets[symbol]
        
        if not self.markets:
            try:
                markets = self.fetch_markets()
                if markets:
                    self.markets = {m['symbol']: m for m in markets}
            except Exception:
                pass
        
        if self.markets and symbol in self.markets:
            return self.markets[symbol]
        
        base, quote = symbol.split('/') if '/' in symbol else (symbol[:-4], 'usdt')
        symbol_id = f"{base.lower()}_{quote.lower()}"
        return {
            'id': symbol_id,
            'symbol': symbol,
            'base': base.upper(),
            'quote': quote.upper(),
            'active': True,
            'type': 'future',
            'linear': True,
            'inverse': False,
            'spot': False,
            'swap': True,
            'future': True,
            'option': False,
            'margin': False,
            'contract': True,
        }

    def fetch_ohlcv(self, symbol, timeframe='1m', since=None, limit=None, params={}):
        """Полная замена fetch_ohlcv с использованием V4 API для XT"""
        market = self.market(symbol)
        
        # XT Futures V4 Klines API
        # GET https://fapi.xt.com/future/market/v1/public/q/kline?symbol=btc_usdt&interval=1m&limit=500
        url = "https://fapi.xt.com/future/market/v1/public/q/kline"
        
        # Маппинг таймфреймов ccxt -> XT V4
        tf_map = {
            '1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '1h', '2h': '2h', '4h': '4h', '6h': '6h', '8h': '8h', '12h': '12h',
            '1d': '1d', '3d': '3d', '1w': '1w'
        }
        
        request_params = {
            'symbol': market['id'],
            'interval': tf_map.get(timeframe, timeframe),
        }
        if limit is not None:
            request_params['limit'] = limit
            
        import requests
        try:
            resp = requests.get(url, params=request_params, timeout=10)
            data = resp.json()
            
            if data.get('returnCode') == 0:
                # XT V4 возвращает список объектов: [{"t":ts,"o":open,"h":high,"l":low,"c":close,"v":vol}, ...]
                klines = data.get('result', [])
                if not isinstance(klines, list):
                    return []
                
                # Формируем стандартный ccxt-формат: [timestamp, open, high, low, close, volume]
                formatted = []
                for k in klines:
                    formatted.append([
                        int(k.get('t')),
                        float(k.get('o')),
                        float(k.get('h')),
                        float(k.get('l')),
                        float(k.get('c')),
                        float(k.get('v'))
                    ])
                return formatted
            else:
                logger.error(f"XT V4 Klines API error for {symbol}: {data}")
                return []
        except Exception as e:
            logger.error(f"XT V4 Klines request failed for {symbol}: {e}")
            return []

class XTClient:
    """Клиент для работы с биржей XT.com"""
    
    def __init__(self):
        """Инициализация клиента XT.com"""
        try:
            exchange_config = {
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',
                    'sandboxMode': False,
                },
            }
            
            if config.XT_API_KEY and config.XT_API_SECRET:
                exchange_config['apiKey'] = config.XT_API_KEY
                exchange_config['secret'] = config.XT_API_SECRET
            
            self.exchange = XTExchange(exchange_config)
            self.executor = ThreadPoolExecutor(max_workers=10)
        except Exception as e:
            logger.error(f"ERROR: Не удалось создать клиент XT.com: {e}")
            raise
    
    async def _run_in_executor(self, func, *args):
        """Запуск синхронной функции ccxt в executor-е"""
        try:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(self.executor, func, *args)
        except Exception as e:
            import traceback
            logger.error(f"Executor critical error: {type(e).__name__}: {e}")
            logger.error(traceback.format_exc())
            return None
        
    async def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        """Получение OHLCV данных напрямую с XT.com"""
        try:
            if not self.exchange.markets:
                await self._run_in_executor(self.exchange.fetch_markets)
            
            ohlcv = await self._run_in_executor(
                self.exchange.fetch_ohlcv,
                symbol,
                timeframe,
                None,
                limit
            )
            
            if ohlcv and isinstance(ohlcv, list) and len(ohlcv) > 0:
                df = pd.DataFrame(
                    ohlcv,
                    columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                )
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = df[col].astype(float)
                return df
            
            return pd.DataFrame()
        except Exception as e:
            return pd.DataFrame()
    
    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Получение текущей цены с XT.com"""
        try:
            ticker = await self._run_in_executor(self.exchange.fetch_ticker, symbol)
            return ticker if ticker and isinstance(ticker, dict) and ticker.get('last') else None
        except Exception:
            return None
    
    async def get_all_futures_symbols(self) -> List[str]:
        """Получение списка всех фьючерсных пар XT.com"""
        try:
            markets = await self._run_in_executor(self.exchange.fetch_markets)
            if markets and isinstance(markets, list):
                return [m['symbol'] for m in markets if m.get('quote') == 'USDT']
            return []
        except Exception as e:
            logger.error(f"Error getting symbols from XT: {e}")
            return []
    
    def close(self):
        """Закрытие соединения"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
        self.exchange = None
