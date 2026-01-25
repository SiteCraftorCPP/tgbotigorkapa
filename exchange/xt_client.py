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
        self.urls['test'] = self.urls.get('api', self.urls)
        return self.urls

    def fetch_currencies(self, params={}):
        return {}
    
    def fetch_markets(self, params={}):
        """Получает список рынков с XT.com"""
        try:
            # Вызываем напрямую через эндпоинт v1
            response = self.fapiPublicGetExchangeInfo(params)
            
            # Обработка формата XT.com {"code": 0, "msg": "success", "data": {"symbols": [...]}}
            data = response.get('data', {})
            symbols = data.get('symbols', [])
            
            if not symbols:
                if isinstance(data, list):
                    symbols = data
                elif isinstance(response, list):
                    symbols = response
            
            result = []
            for s in symbols:
                id = s.get('symbol')
                baseId = s.get('baseAsset', '').upper()
                quoteId = s.get('quoteAsset', '').upper()
                base = self.safe_currency_code(baseId)
                quote = self.safe_currency_code(quoteId)
                symbol = f"{base}/{quote}"
                
                result.append({
                    'id': id,
                    'symbol': symbol,
                    'base': base,
                    'quote': quote,
                    'baseId': baseId,
                    'quoteId': quoteId,
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
                    'expiry': None,
                    'expiryDatetime': None,
                    'settle': quote,
                    'settleId': quoteId,
                    'precision': {
                        'amount': int(s.get('quantityPrecision', 8)),
                        'price': int(s.get('pricePrecision', 8)),
                    },
                    'limits': {
                        'amount': {
                            'min': float(s.get('minQty', 0)) if s.get('minQty') else None,
                            'max': float(s.get('maxQty', 0)) if s.get('maxQty') else None,
                        },
                        'price': {
                            'min': float(s.get('minPrice', 0)) if s.get('minPrice') else None,
                            'max': float(s.get('maxPrice', 0)) if s.get('maxPrice') else None,
                        },
                        'cost': {'min': None, 'max': None},
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
                    self.markets = {m['symbol']: m for m in (markets.values() if isinstance(markets, dict) else markets) if 'symbol' in m}
            except Exception:
                pass
        
        if self.markets and symbol in self.markets:
            return self.markets[symbol]
        
        # Формат для XT.com Futures V1: btc_usdt (нижний регистр)
        base, quote = symbol.split('/') if '/' in symbol else (symbol[:-4], 'usdt')
        symbol_id = f"{base.lower()}_{quote.lower()}"
        
        market_data = {
            'id': symbol_id,
            'symbol': symbol,
            'base': base.upper(),
            'quote': quote.upper(),
            'baseId': base.lower(),
            'quoteId': quote.lower(),
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
            'contractSize': 1.0,
            'expiry': None,
            'expiryDatetime': None,
            'settle': quote.upper(),
            'settleId': quote.lower(),
            'precision': {
                'amount': 8,
                'price': 8,
            },
            'limits': {
                'amount': {'min': None, 'max': None},
                'price': {'min': None, 'max': None},
                'cost': {'min': None, 'max': None},
            },
            'info': {},
        }
        
        if not hasattr(self, 'markets') or self.markets is None:
            self.markets = {}
        self.markets[symbol] = market_data
        
        return market_data

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
            try:
                self.exchange.set_sandbox_mode(False)
            except Exception as e:
                logger.warning(f"XTClient: failed to disable sandbox mode: {e}")
            
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
                await self._run_in_executor(self.exchange.load_markets)
            
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
            error_str = str(e).lower()
            if 'does not have market symbol' not in error_str and '400' not in error_str:
                logger.warning(f"XT API OHLCV unavailable for {symbol}: {e}")
            return pd.DataFrame()
    
    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Получение текущей цены с XT.com"""
        try:
            if not self.exchange.markets:
                await self._run_in_executor(self.exchange.load_markets)
            
            ticker = await self._run_in_executor(self.exchange.fetch_ticker, symbol)
            if ticker and ticker.get('last'):
                return ticker
            return None
        except Exception:
            return None
    
    async def get_funding_rate(self, symbol: str) -> Optional[float]:
        """Получение ставки финансирования с XT.com"""
        try:
            funding = await self._run_in_executor(self.exchange.fetch_funding_rate, symbol)
            if funding and 'fundingRate' in funding:
                return funding.get('fundingRate', 0)
            return None
        except:
            return None
    
    async def get_open_interest(self, symbol: str) -> Optional[float]:
        """Получение открытого интереса с XT.com"""
        try:
            oi = await self._run_in_executor(self.exchange.fetch_open_interest, symbol)
            if oi and 'openInterest' in oi:
                return oi.get('openInterest', 0)
            return None
        except:
            return None
    
    async def get_orderbook(self, symbol: str, limit: int = 20) -> Optional[Dict]:
        """Получение стакана заявок с XT.com"""
        try:
            if limit < 5: limit = 5
            if not self.exchange.markets:
                await self._run_in_executor(self.exchange.load_markets)
            
            orderbook = await self._run_in_executor(self.exchange.fetch_order_book, symbol, limit)
            if orderbook and orderbook.get('bids') and orderbook.get('asks'):
                return orderbook
            return None
        except Exception:
            return None
    
    async def get_all_futures_symbols(self) -> List[str]:
        """Получение списка всех фьючерсных пар XT.com"""
        try:
            markets = await self._run_in_executor(self.exchange.load_markets)
            futures = [
                symbol for symbol, market in markets.items()
                if market.get('future') and market.get('quote') == 'USDT'
            ]
            return futures
        except Exception as e:
            logger.error(f"Error getting symbols from XT: {e}")
            return []
    
    async def get_account_balance(self) -> Optional[Dict]:
        """Получение баланса аккаунта XT.com"""
        try:
            balance = await self._run_in_executor(self.exchange.fetch_balance)
            return balance
        except Exception as e:
            logger.error(f"Error getting balance from XT: {e}")
            return None
    
    def close(self):
        """Закрытие соединения"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
        self.exchange = None
