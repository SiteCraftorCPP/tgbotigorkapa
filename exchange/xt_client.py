import ccxt
import pandas as pd
from typing import List, Dict, Optional
import config
import asyncio
from datetime import datetime

class XTClient:
    """Клиент для работы с биржей XT.com"""
    
    def __init__(self):
        self.exchange = ccxt.xt({
            'apiKey': config.XT_API_KEY,
            'secret': config.XT_API_SECRET,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',
            }
        })
        
    async def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        """Получение OHLCV данных"""
        try:
            ohlcv = await asyncio.to_thread(
                self.exchange.fetch_ohlcv,
                symbol,
                timeframe,
                limit=limit
            )
            
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
        except Exception as e:
            print(f"❌ Ошибка получения OHLCV для {symbol}: {e}")
            return pd.DataFrame()
    
    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Получение текущей цены"""
        try:
            ticker = await asyncio.to_thread(self.exchange.fetch_ticker, symbol)
            return ticker
        except Exception as e:
            print(f"❌ Ошибка получения тикера {symbol}: {e}")
            return None
    
    async def get_funding_rate(self, symbol: str) -> Optional[float]:
        """Получение ставки финансирования"""
        try:
            funding = await asyncio.to_thread(
                self.exchange.fetch_funding_rate,
                symbol
            )
            return funding.get('fundingRate', 0)
        except Exception as e:
            print(f"⚠️ Funding rate недоступен для {symbol}: {e}")
            return None
    
    async def get_open_interest(self, symbol: str) -> Optional[float]:
        """Получение открытого интереса"""
        try:
            oi = await asyncio.to_thread(
                self.exchange.fetch_open_interest,
                symbol
            )
            return oi.get('openInterest', 0)
        except Exception as e:
            print(f"⚠️ Open Interest недоступен для {symbol}: {e}")
            return None
    
    async def get_orderbook(self, symbol: str, limit: int = 20) -> Optional[Dict]:
        """Получение стакана заявок"""
        try:
            orderbook = await asyncio.to_thread(
                self.exchange.fetch_order_book,
                symbol,
                limit
            )
            return orderbook
        except Exception as e:
            print(f"⚠️ Orderbook недоступен для {symbol}: {e}")
            return None
    
    async def get_all_futures_symbols(self) -> List[str]:
        """Получение списка всех фьючерсных пар"""
        try:
            markets = await asyncio.to_thread(self.exchange.load_markets)
            futures = [
                symbol for symbol, market in markets.items()
                if market.get('future') and market.get('quote') == 'USDT'
            ]
            return futures
        except Exception as e:
            print(f"❌ Ошибка получения списка символов: {e}")
            return []
    
    async def get_account_balance(self) -> Optional[Dict]:
        """Получение баланса аккаунта"""
        try:
            balance = await asyncio.to_thread(self.exchange.fetch_balance)
            return balance
        except Exception as e:
            print(f"❌ Ошибка получения баланса: {e}")
            return None
    
    def close(self):
        """Закрытие соединения"""
        if self.exchange:
            self.exchange.close()

