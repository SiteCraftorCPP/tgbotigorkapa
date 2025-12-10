import os
import ccxt
import pandas as pd
from typing import List, Dict, Optional
import config
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import requests
from utils.logger import logger

class XTExchange(ccxt.binance):
    """Кастомный класс для работы с XT.com через ccxt API"""
    
    def __init__(self, config=None):
        # Инициализируем как binance, но с настройками для XT.com
        if config is None:
            config = {}
        # Убеждаемся, что defaultType установлен
        if 'options' not in config:
            config['options'] = {}
        config['options']['defaultType'] = 'future'
        
        super().__init__(config)
        
        # Переопределяем базовые URL
        self.urls['api'] = {
            'public': 'https://fapi.xt.com/fapi/v1',
            'private': 'https://fapi.xt.com/fapi/v1',
        }
        # Во избежание ошибок sandbox/testnet — задаем test такие же, как prod
        self.urls['test'] = self.urls['api']
        self.id = 'xt'
        
        # Убираем testnet URLs
        if 'test' in self.urls:
            del self.urls['test']
        
        # Убираем sapi URLs - они не поддерживаются XT.com
        if 'sapi' in self.urls.get('api', {}):
            del self.urls['api']['sapi']
        
        # Отключаем использование sapi endpoints
        # Переопределяем методы, которые используют sapi
        self.has['fetchMarkets'] = True
        self.has['fetchCurrencies'] = False  # Отключаем загрузку валют через sapi
        # Явно выключаем sandboxMode на уровне опций
        if 'options' not in self.options:
            self.options = {}
        self.options['sandboxMode'] = False
        
        # Отключаем автоматическую загрузку markets при инициализации
        # Markets будут загружаться по требованию
        self.markets = {}

    # XT не имеет sandbox/testnet URL. Жёстко блокируем включение sandboxMode,
    # чтобы ccxt не пытался переключиться и не бросал исключение.
    def set_sandbox_mode(self, enabled):
        # Игнорируем запрос на включение sandbox, оставляем продовые URL
        self.sandboxMode = False
        if 'options' not in self.options:
            self.options = {}
        self.options['sandboxMode'] = False
        self.urls['test'] = self.urls.get('api', self.urls)
        return self.urls
    
    def public_get_klines(self, params={}):
        """Переопределяем public_get_klines для использования правильного эндпоинта XT.com"""
        # XT.com API возвращает только документацию для публичных эндпоинтов
        # Используем Binance публичный API как fallback для получения исторических данных
        # Это временное решение до настройки реального XT.com API
        
        try:
            # Используем Binance публичный API для фьючерсов
            binance_fapi = "https://fapi.binance.com/fapi/v1/klines"
            
            request_params = {
                'symbol': params.get('symbol', '').replace('/', ''),
                'interval': params.get('interval', '1h'),
            }
            if 'limit' in params:
                request_params['limit'] = params['limit']
            if 'startTime' in params:
                request_params['startTime'] = params['startTime']
            if 'endTime' in params:
                request_params['endTime'] = params['endTime']
            
            response = requests.get(binance_fapi, params=request_params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, list) and len(data) > 0:
                return data
            else:
                raise Exception(f"Пустой ответ от Binance API для {request_params.get('symbol')}")
                
        except Exception as e:
            raise Exception(f"Ошибка получения klines через Binance fallback: {str(e)}")
    
    def public_get_ticker_24hr(self, params={}):
        """Переопределяем public_get_ticker_24hr для использования правильного эндпоинта XT.com"""
        # Используем Binance API как fallback
        try:
            request_params = {}
            if 'symbol' in params:
                request_params['symbol'] = params['symbol'].replace('/', '')
            
            # Используем Binance публичный API для фьючерсов
            binance_fapi = "https://fapi.binance.com/fapi/v1/ticker/24hr"
            response = requests.get(binance_fapi, params=request_params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return data
        except requests.RequestException as e:
            raise Exception(f"HTTP ошибка при запросе ticker: {str(e)}")
        except Exception as e:
            error_msg = f"Ошибка в public_get_ticker_24hr: {str(e)}"
            raise Exception(error_msg)
    
    def public_get_depth(self, params={}):
        """Переопределяем public_get_depth для использования правильного эндпоинта XT.com"""
        # Используем Binance API как fallback
        try:
            request_params = {'symbol': params.get('symbol', '').replace('/', '')}
            if 'limit' in params:
                request_params['limit'] = params['limit']
            
            # Используем Binance публичный API для фьючерсов
            binance_fapi = "https://fapi.binance.com/fapi/v1/depth"
            response = requests.get(binance_fapi, params=request_params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return data
        except requests.RequestException as e:
            raise Exception(f"HTTP ошибка при запросе depth: {str(e)}")
        except Exception as e:
            error_msg = f"Ошибка в public_get_depth: {str(e)}"
            raise Exception(error_msg)
    
    def fetch_currencies(self, params={}):
        """Переопределяем fetch_currencies, чтобы не использовать sapi"""
        # Возвращаем пустой словарь валют, так как sapi недоступен
        # Валюты будут определяться из markets
        return {}
    
    def market(self, symbol):
        """Переопределяем market для работы без загруженных markets"""
        # Если markets загружены и символ есть, возвращаем его
        if self.markets and symbol in self.markets:
            return self.markets[symbol]
        
        # Пробуем загрузить markets, если они не загружены
        if not self.markets:
            try:
                markets = self.fetch_markets()
                if markets:
                    self.markets = {}
                    for m in markets.values() if isinstance(markets, dict) else markets:
                        if isinstance(m, dict) and 'symbol' in m:
                            self.markets[m['symbol']] = m
            except Exception:
                pass
        
        # Если символ есть в markets после загрузки, возвращаем его
        if self.markets and symbol in self.markets:
            return self.markets[symbol]
        
        # Создаем простой market из символа, если его нет
        # Формат для XT.com: BTC/USDT -> BTCUSDT
        symbol_id = symbol.replace('/', '')
        base, quote = symbol.split('/') if '/' in symbol else (symbol[:-4], 'USDT')
        market_data = {
            'id': symbol_id,
            'symbol': symbol,
            'base': base,
            'quote': quote,
            'baseId': base,
            'quoteId': quote,
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
            'settle': quote,
            'settleId': quote,
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
        
        # Сохраняем в markets для повторного использования
        if not hasattr(self, 'markets') or self.markets is None:
            self.markets = {}
        self.markets[symbol] = market_data
        
        return market_data
    
    def fetch_markets(self, params={}):
        """Переопределяем для использования правильного эндпоинта"""
        try:
            # Используем публичный эндпоинт для получения списка рынков
            response = self.public_get_exchangeinfo(params)
            if 'symbols' in response:
                markets = self.parse_markets(response['symbols'])
                return markets
            else:
                # Если формат ответа другой, пробуем другой подход
                return []
        except Exception as e:
            # Если не удалось загрузить рынки, возвращаем пустой список
            # Рынки будут загружаться по требованию
            return []
    
    def fetch_ohlcv(self, symbol, timeframe='1m', since=None, limit=None, params={}):
        """Переопределяем fetch_ohlcv для правильной работы с XT.com"""
        try:
            market = self.market(symbol)
            symbol_id = market['id']
            interval = self.timeframes[timeframe] if timeframe in self.timeframes else timeframe
            request_params = {
                'symbol': symbol_id,
                'interval': interval,
            }
            if limit is not None:
                request_params['limit'] = limit
            if since is not None:
                request_params['startTime'] = since
            
            # Объединяем с дополнительными параметрами
            request_params = self.extend(request_params, params)
            
            # Используем публичный метод без подписи
            response = self.public_get_klines(request_params)
            
            # Обрабатываем ответ XT.com (может быть в формате {"code": 0, "data": [...]})
            if isinstance(response, dict):
                if 'code' in response:
                    if response.get('code') != 0:
                        msg = response.get('msg', 'Unknown error')
                        raise Exception(f"API вернул ошибку {response.get('code')}: {msg}")
                    response = response.get('data', [])
                elif 'data' in response:
                    response = response['data']
            
            if not response or len(response) == 0:
                raise Exception(f"Пустой ответ от API для {symbol} (symbol_id={symbol_id})")
            
            return self.parse_ohlcvs(response, market, timeframe, since, limit)
        except Exception as e:
            error_msg = str(e)
            # Добавляем больше информации об ошибке
            if "HTTP" in error_msg or "GET" in error_msg or "POST" in error_msg:
                error_msg = f"HTTP ошибка при запросе {symbol} (symbol_id={symbol_id}): {error_msg}"
            raise Exception(f"Ошибка fetch_ohlcv для {symbol}: {error_msg}")
    
    def fetch_ticker(self, symbol, params={}):
        """Переопределяем fetch_ticker для правильной работы с XT.com"""
        try:
            market = self.market(symbol)
            symbol_id = market['id']
            request_params = {'symbol': symbol_id}
            request_params = self.extend(request_params, params)
            
            # Используем публичный метод без подписи
            response = self.public_get_ticker_24hr(request_params)
            
            # Обрабатываем ответ XT.com (может быть в формате {"code": 0, "data": {...}})
            if isinstance(response, dict):
                if 'code' in response:
                    if response.get('code') != 0:
                        msg = response.get('msg', 'Unknown error')
                        raise Exception(f"API вернул ошибку {response.get('code')}: {msg}")
                    response = response.get('data', response)
                elif 'data' in response:
                    response = response['data']
            
            if not response:
                raise Exception(f"Пустой ответ от API для {symbol} (symbol_id={symbol_id})")
            
            return self.parse_ticker(response, market)
        except Exception as e:
            error_msg = str(e)
            if "HTTP" in error_msg or "GET" in error_msg or "POST" in error_msg:
                error_msg = f"HTTP ошибка при запросе {symbol} (symbol_id={symbol_id}): {error_msg}"
            raise Exception(f"Ошибка fetch_ticker для {symbol}: {error_msg}")
    
    def fetch_order_book(self, symbol, limit=None, params={}):
        """Переопределяем fetch_order_book для правильной работы с XT.com"""
        try:
            market = self.market(symbol)
            symbol_id = market['id']
            request_params = {'symbol': symbol_id}
            if limit is not None:
                request_params['limit'] = limit
            request_params = self.extend(request_params, params)
            
            # Используем публичный метод без подписи
            response = self.public_get_depth(request_params)
            
            # Обрабатываем ответ XT.com (может быть в формате {"code": 0, "data": {...}})
            if isinstance(response, dict):
                if 'code' in response:
                    if response.get('code') != 0:
                        msg = response.get('msg', 'Unknown error')
                        raise Exception(f"API вернул ошибку {response.get('code')}: {msg}")
                    response = response.get('data', response)
                elif 'data' in response:
                    response = response['data']
            
            if not response:
                raise Exception(f"Пустой ответ от API для {symbol} (symbol_id={symbol_id})")
            
            orderbook = self.parse_order_book(response, symbol)
            return orderbook
        except Exception as e:
            error_msg = str(e)
            if "HTTP" in error_msg or "GET" in error_msg or "POST" in error_msg:
                error_msg = f"HTTP ошибка при запросе {symbol} (symbol_id={symbol_id}): {error_msg}"
            raise Exception(f"Ошибка fetch_order_book для {symbol}: {error_msg}")

class XTClient:
    """Клиент для работы с биржей XT.com"""
    
    def __init__(self, use_binance_fallback=True):
        """
        Инициализация клиента XT.com
        use_binance_fallback: Если True, использует Binance API как fallback для публичных данных
        """
        self.use_binance_fallback = use_binance_fallback
        # Используем кастомный класс XTExchange для работы с XT.com через API
        try:
            exchange_config = {
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',
                    'sandboxMode': False,
                },
            }
            
            # Добавляем API ключи только если они есть (для приватных запросов)
            if config.XT_API_KEY and config.XT_API_SECRET:
                exchange_config['apiKey'] = config.XT_API_KEY
                exchange_config['secret'] = config.XT_API_SECRET
            
            self.exchange = XTExchange(exchange_config)
            # Явно отключаем sandbox/testnet режим, чтобы не дергать несуществующие testnet URLs
            try:
                if hasattr(self.exchange, "set_sandbox_mode"):
                    self.exchange.set_sandbox_mode(False)
            except Exception as e:
                logger.warning(f"XTClient: failed to disable sandbox mode: {e}")
            
            # Если используем Binance fallback, инициализируем Binance exchange для публичных данных
            if self.use_binance_fallback:
                try:
                    import ccxt
                    self.binance_exchange = ccxt.binance({
                        'enableRateLimit': True,
                        'options': {
                            'defaultType': 'future',
                            'sandboxMode': False,
                        },
                    })
                    # Загружаем markets для Binance
                    self.binance_exchange.load_markets()
                    try:
                        if hasattr(self.binance_exchange, "set_sandbox_mode"):
                            self.binance_exchange.set_sandbox_mode(False)
                    except Exception as e:
                        logger.warning(f"Binance fallback: failed to disable sandbox mode: {e}")
                except Exception as e:
                    print(f"WARN: Не удалось инициализировать Binance fallback: {e}")
                    self.binance_exchange = None
            else:
                self.binance_exchange = None
            
            # Загружаем рынки для правильной работы с символами
            # Не загружаем при инициализации - будет загружено по требованию
            # Это избегает проблем с event loop
            # Executor для Python 3.7 совместимости
            self.executor = ThreadPoolExecutor(max_workers=5)
            # Сохраняем ссылку на event loop (будет установлена при первом использовании)
            self._event_loop = None
        except Exception as e:
            print(f"ERROR: Не удалось создать клиент XT.com: {e}")
            raise
    
    
    async def _run_in_executor(self, func, *args, **kwargs):
        """Запуск синхронной функции в executor (для Python 3.7)"""
        # Получаем текущий event loop через текущую задачу (наиболее надежный способ)
        try:
            # Пытаемся получить loop через текущую задачу
            task = asyncio.current_task()
            if task:
                loop = task.get_loop()
            else:
                # Если нет текущей задачи, используем get_event_loop()
                loop = asyncio.get_event_loop()
        except (RuntimeError, AttributeError):
            # Fallback на get_event_loop()
            loop = asyncio.get_event_loop()
        
        # Проверяем, что loop не закрыт
        if loop.is_closed():
            raise RuntimeError("Event loop is closed")
        
        if kwargs:
            return await loop.run_in_executor(self.executor, lambda: func(*args, **kwargs))
        else:
            return await loop.run_in_executor(self.executor, lambda: func(*args))
        
    async def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        """Получение OHLCV данных"""
        try:
            # Сначала пробуем получить данные через XT.com
            try:
                # Убеждаемся, что рынки загружены
                if not self.exchange.markets:
                    await self._run_in_executor(self.exchange.load_markets)
                
                # Вызываем fetch_ohlcv через API ccxt
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
            except Exception as xt_error:
                # Если XT.com не работает и включен fallback, используем Binance
                if self.use_binance_fallback and self.binance_exchange:
                    try:
                        ohlcv = await self._run_in_executor(
                            self.binance_exchange.fetch_ohlcv,
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
                            print(f"INFO: Использован Binance fallback для {symbol} {timeframe}")
                            return df
                    except Exception as binance_error:
                        # Тихая обработка - пара недоступна на Binance
                        # Не логируем каждую ошибку, чтобы не засорять логи
                        pass
                
                # Если оба метода не сработали, возвращаем пустой DataFrame
                # Логируем только если это не известная проблема (символ не найден)
                error_str = str(xt_error).lower()
                if 'does not have market symbol' not in error_str and '400' not in error_str:
                    # Только нестандартные ошибки логируем
                    from utils.logger import log_warning
                    log_warning(f"OHLCV unavailable for {symbol}: {xt_error}")
            
            return pd.DataFrame()
        except Exception as e:
            # Тихая обработка ошибок для недоступных пар
            return pd.DataFrame()
    
    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Получение текущей цены"""
        try:
            # Сначала пробуем получить данные через XT.com
            try:
                # Убеждаемся, что рынки загружены
                if not self.exchange.markets:
                    await self._run_in_executor(self.exchange.load_markets)
                
                ticker = await self._run_in_executor(self.exchange.fetch_ticker, symbol)
                if ticker and ticker.get('last'):
                    # Если отсутствуют bid/ask, попробуем получить их из orderbook
                    if (not ticker.get('bid') or not ticker.get('ask')) and self.use_binance_fallback:
                        try:
                            orderbook = await self.get_orderbook(symbol, 1)
                            if orderbook and orderbook.get('bids') and orderbook.get('asks'):
                                if not ticker.get('bid'):
                                    ticker['bid'] = float(orderbook['bids'][0][0])
                                if not ticker.get('ask'):
                                    ticker['ask'] = float(orderbook['asks'][0][0])
                        except:
                            pass  # Если не удалось получить orderbook, просто возвращаем ticker как есть
                    
                    return ticker
            except Exception as xt_error:
                # Если XT.com не работает и включен fallback, используем Binance
                if self.use_binance_fallback and self.binance_exchange:
                    try:
                        ticker = await self._run_in_executor(self.binance_exchange.fetch_ticker, symbol)
                        if ticker and ticker.get('last'):
                            print(f"INFO: Использован Binance fallback для ticker {symbol}")
                            return ticker
                    except Exception as binance_error:
                        print(f"Ошибка получения ticker через Binance fallback для {symbol}: {binance_error}")
                
                print(f"Ошибка получения тикера {symbol} через XT.com: {xt_error}")
            
            return None
        except Exception as e:
            print(f"Ошибка получения тикера {symbol}: {e}")
            return None
    
    async def get_funding_rate(self, symbol: str) -> Optional[float]:
        """Получение ставки финансирования"""
        try:
            # Сначала пробуем через XT.com
            try:
                funding = await self._run_in_executor(
                    self.exchange.fetch_funding_rate,
                    symbol
                )
                if funding and 'fundingRate' in funding:
                    return funding.get('fundingRate', 0)
            except:
                pass
            
            # Если XT.com не работает и включен fallback, используем Binance
            if self.use_binance_fallback and self.binance_exchange:
                try:
                    funding = await self._run_in_executor(
                        self.binance_exchange.fetch_funding_rate,
                        symbol
                    )
                    if funding and 'fundingRate' in funding:
                        return funding.get('fundingRate', 0)
                except Exception as e:
                    pass
            
            return None
        except Exception as e:
            # Funding rate не критичен, просто возвращаем None
            return None
    
    async def get_open_interest(self, symbol: str) -> Optional[float]:
        """Получение открытого интереса"""
        try:
            # Сначала пробуем через XT.com
            try:
                oi = await self._run_in_executor(
                    self.exchange.fetch_open_interest,
                    symbol
                )
                if oi and 'openInterest' in oi:
                    return oi.get('openInterest', 0)
            except:
                pass
            
            # Если XT.com не работает и включен fallback, используем Binance
            if self.use_binance_fallback and self.binance_exchange:
                try:
                    oi = await self._run_in_executor(
                        self.binance_exchange.fetch_open_interest,
                        symbol
                    )
                    if oi and 'openInterest' in oi:
                        return oi.get('openInterest', 0)
                except Exception as e:
                    pass
            
            return None
        except Exception as e:
            # Open Interest не критичен, просто возвращаем None
            return None
    
    async def get_orderbook(self, symbol: str, limit: int = 20) -> Optional[Dict]:
        """Получение стакана заявок"""
        try:
            # Binance API требует минимум 5 уровней
            if limit < 5:
                limit = 5
            
            # Сначала пробуем получить данные через XT.com
            try:
                # Убеждаемся, что рынки загружены
                if not self.exchange.markets:
                    await self._run_in_executor(self.exchange.load_markets)
                
                orderbook = await self._run_in_executor(
                    self.exchange.fetch_order_book,
                    symbol,
                    limit
                )
                if orderbook and orderbook.get('bids') and orderbook.get('asks'):
                    return orderbook
            except Exception as xt_error:
                # Если XT.com не работает и включен fallback, используем Binance
                if self.use_binance_fallback and self.binance_exchange:
                    try:
                        orderbook = await self._run_in_executor(
                            self.binance_exchange.fetch_order_book,
                            symbol,
                            limit
                        )
                        if orderbook and orderbook.get('bids') and orderbook.get('asks'):
                            print(f"INFO: Использован Binance fallback для orderbook {symbol}")
                            return orderbook
                    except Exception as binance_error:
                        print(f"Ошибка получения orderbook через Binance fallback для {symbol}: {binance_error}")
                
                print(f"Orderbook недоступен для {symbol} через XT.com: {xt_error}")
            
            return None
        except Exception as e:
            print(f"Orderbook недоступен для {symbol}: {e}")
            return None
    
    async def get_all_futures_symbols(self) -> List[str]:
        """Получение списка всех фьючерсных пар"""
        try:
            markets = await self._run_in_executor(self.exchange.load_markets)
            futures = [
                symbol for symbol, market in markets.items()
                if market.get('future') and market.get('quote') == 'USDT'
            ]
            return futures
        except Exception as e:
            print(f"[ERROR] Ошибка получения списка символов: {e}")
            return []
    
    async def get_account_balance(self) -> Optional[Dict]:
        """Получение баланса аккаунта"""
        try:
            balance = await self._run_in_executor(self.exchange.fetch_balance)
            return balance
        except Exception as e:
            print(f"[ERROR] Ошибка получения баланса: {e}")
            return None
    
    def close(self):
        """Закрытие соединения"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
        # ccxt.binance не имеет метода close(), просто очищаем ссылку
        if hasattr(self, 'exchange'):
            self.exchange = None
        if hasattr(self, 'binance_exchange'):
            self.binance_exchange = None

