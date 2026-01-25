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
            'fapiPublic': 'https://fapi.xt.com', # Убираем /fapi/v1 чтобы ccxt сам добавил
            'fapiPrivate': 'https://fapi.xt.com',
        }
        self.urls['test'] = self.urls['api']
        self.id = 'xt'
        
        # Удаляем sapi, так как XT его не поддерживает
        if 'sapi' in self.urls.get('api', {}):
            del self.urls['api']['sapi']
        
        # Переопределяем методы API для XT
        self.api = {
            'fapiPublic': {
                'get': [
                    'exchangeInfo',
                    'klines',
                    'ticker/24hr',
                    'depth',
                ],
            },
            'fapiPrivate': {
                'get': [
                    'balance',
                    'account',
                ],
            },
        }
        
        self.has['fetchMarkets'] = True
        self.has['fetchCurrencies'] = False
        self.options['sandboxMode'] = False
        self.markets = {}

    def set_sandbox_mode(self, enabled):
        """Жестко отключаем sandbox, так как у XT его нет"""
        self.sandboxMode = False
        if 'options' not in self.options:
            self.options = {}
        self.options['sandboxMode'] = False
        return self.urls

    def fetch_markets(self, params={}):
        """Получает список рынков с XT.com через V4 API (более надежно)"""
        try:
            import requests
            # Используем V4 API для списка рынков, так как fapi/v1/exchangeInfo часто пустой
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
        
        # Fallback если не нашли в списке
        base, quote = symbol.split('/') if '/' in symbol else (symbol[:-4], 'usdt')
        symbol_id = f"{base.lower()}_{quote.lower()}"
        return {
            'id': symbol_id,
            'symbol': symbol,
            'base': base.upper(),
            'quote': quote.upper(),
            'active': True,
            'type': 'future',
        }

class XTClient:
    """Клиент для работы с биржей XT.com без сторонних fallback-ов"""
    
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
            self.executor = ThreadPoolExecutor(max_workers=5)
        except Exception as e:
            print(f"ERROR: Не удалось создать клиент XT.com: {e}")
            raise
    
    async def _run_in_executor(self, func, *args, **kwargs):
        """Запуск синхронной функции ccxt в executor-е"""
        try:
            task = asyncio.current_task()
            loop = task.get_loop() if task else asyncio.get_event_loop()
        except (RuntimeError, AttributeError):
            loop = asyncio.get_event_loop()
        
        if loop.is_closed():
            raise RuntimeError("Event loop is closed")
        
        if kwargs:
            return await loop.run_in_executor(self.executor, lambda: func(*args, **kwargs))
        else:
            return await loop.run_in_executor(self.executor, lambda: func(*args))
        
    async def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        """Получение OHLCV данных напрямую с XT.com"""
        try:
            if not self.exchange.markets:
                await self._run_in_executor(self.exchange.fetch_markets)
            
            # XT V1 Klines API (Binance clone)
            ohlcv = await self._run_in_executor(
                self.exchange.fetch_ohlcv,
                symbol,
                timeframe,
                None,
                limit
            )
            
            if ohlcv and len(ohlcv) > 0:
                df = pd.DataFrame(
                    ohlcv,
                    columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                )
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                return df
            
            return pd.DataFrame()
        except Exception as e:
            return pd.DataFrame()
    
    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Получение текущей цены с XT.com"""
        try:
            ticker = await self._run_in_executor(self.exchange.fetch_ticker, symbol)
            return ticker if ticker and ticker.get('last') else None
        except Exception:
            return None
    
    async def get_all_futures_symbols(self) -> List[str]:
        """Получение списка всех фьючерсных пар XT.com"""
        try:
            markets = await self._run_in_executor(self.exchange.fetch_markets)
            return [m['symbol'] for m in markets if m.get('quote') == 'USDT']
        except Exception as e:
            logger.error(f"Error getting symbols from XT: {e}")
            return []
    
    def close(self):
        """Закрытие соединения"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
        self.exchange = None
