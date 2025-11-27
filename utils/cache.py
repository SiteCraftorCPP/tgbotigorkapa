"""
Система кэширования для оптимизации API запросов
Особенно полезно при обработке 200+ торговых пар
"""

import asyncio
import time
from typing import Optional, Dict, Any
from datetime import datetime


class DataCache:
    """Кэш для рыночных данных с TTL"""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str, ttl: int = 60) -> Optional[Any]:
        """
        Получить данные из кэша
        
        Args:
            key: Ключ кэша
            ttl: Время жизни в секундах
            
        Returns:
            Данные или None если кэш устарел/отсутствует
        """
        async with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            if time.time() - entry['timestamp'] > ttl:
                # Кэш устарел
                del self._cache[key]
                return None
            
            return entry['data']
    
    async def set(self, key: str, data: Any):
        """Сохранить данные в кэш"""
        async with self._lock:
            self._cache[key] = {
                'data': data,
                'timestamp': time.time()
            }
    
    async def clear(self):
        """Очистить весь кэш"""
        async with self._lock:
            self._cache.clear()
    
    async def clear_expired(self, ttl: int = 60):
        """Удалить устаревшие записи"""
        async with self._lock:
            now = time.time()
            expired_keys = [
                key for key, entry in self._cache.items()
                if now - entry['timestamp'] > ttl
            ]
            for key in expired_keys:
                del self._cache[key]


class BTCDataCache:
    """
    Специализированный кэш для данных BTC
    Используется для фильтров BTC Volatility Guard и BTC Trend Filter
    """
    
    def __init__(self):
        self._btc_ohlcv_1m: Optional[Any] = None
        self._btc_ohlcv_1h: Optional[Any] = None
        self._btc_ticker: Optional[Dict] = None
        
        self._btc_ohlcv_1m_time: float = 0
        self._btc_ohlcv_1h_time: float = 0
        self._btc_ticker_time: float = 0
        
        self._lock = asyncio.Lock()
    
    # TTL для разных типов данных
    TTL_OHLCV_1M = 30   # 30 секунд для 1m данных
    TTL_OHLCV_1H = 300  # 5 минут для 1h данных
    TTL_TICKER = 10     # 10 секунд для тикера
    
    async def get_btc_ohlcv_1m(self, client) -> Optional[Any]:
        """Получить BTC OHLCV 1m с кэшированием"""
        async with self._lock:
            now = time.time()
            
            if self._btc_ohlcv_1m is not None and (now - self._btc_ohlcv_1m_time) < self.TTL_OHLCV_1M:
                return self._btc_ohlcv_1m
            
            # Загружаем свежие данные
            try:
                data = await client.get_ohlcv('BTC/USDT', '1m', limit=10)
                if data is not None and not data.empty:
                    self._btc_ohlcv_1m = data
                    self._btc_ohlcv_1m_time = now
                return self._btc_ohlcv_1m
            except Exception as e:
                print(f"[CACHE] Error loading BTC 1m data: {e}")
                return self._btc_ohlcv_1m  # Возвращаем старые данные
    
    async def get_btc_ohlcv_1h(self, client) -> Optional[Any]:
        """Получить BTC OHLCV 1h с кэшированием"""
        async with self._lock:
            now = time.time()
            
            if self._btc_ohlcv_1h is not None and (now - self._btc_ohlcv_1h_time) < self.TTL_OHLCV_1H:
                return self._btc_ohlcv_1h
            
            # Загружаем свежие данные
            try:
                data = await client.get_ohlcv('BTC/USDT', '1h', limit=250)
                if data is not None and not data.empty:
                    self._btc_ohlcv_1h = data
                    self._btc_ohlcv_1h_time = now
                return self._btc_ohlcv_1h
            except Exception as e:
                print(f"[CACHE] Error loading BTC 1h data: {e}")
                return self._btc_ohlcv_1h
    
    async def get_btc_ticker(self, client) -> Optional[Dict]:
        """Получить BTC тикер с кэшированием"""
        async with self._lock:
            now = time.time()
            
            if self._btc_ticker is not None and (now - self._btc_ticker_time) < self.TTL_TICKER:
                return self._btc_ticker
            
            # Загружаем свежие данные
            try:
                data = await client.get_ticker('BTC/USDT')
                if data is not None:
                    self._btc_ticker = data
                    self._btc_ticker_time = now
                return self._btc_ticker
            except Exception as e:
                print(f"[CACHE] Error loading BTC ticker: {e}")
                return self._btc_ticker


# Глобальные экземпляры кэша
data_cache = DataCache()
btc_cache = BTCDataCache()


class RateLimiter:
    """
    Rate limiter для API запросов
    Ограничивает количество одновременных запросов
    """
    
    def __init__(self, max_concurrent: int = 30, requests_per_second: float = 20):
        """
        Args:
            max_concurrent: Максимум одновременных запросов
            requests_per_second: Максимум запросов в секунду
        """
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._min_interval = 1.0 / requests_per_second
        self._last_request_time = 0
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Получить разрешение на запрос"""
        await self._semaphore.acquire()
        
        async with self._lock:
            now = time.time()
            elapsed = now - self._last_request_time
            
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            
            self._last_request_time = time.time()
    
    def release(self):
        """Освободить разрешение"""
        self._semaphore.release()
    
    async def __aenter__(self):
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.release()


# Глобальный rate limiter
api_rate_limiter = RateLimiter(max_concurrent=30, requests_per_second=20)

