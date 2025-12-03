"""
Сервис для автоматического получения топ монет по капитализации
Использует CoinGecko API (бесплатный, без ключа)
"""
import aiohttp
import asyncio
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from utils.logger import logger


class TopCoinsService:
    """Сервис для получения топ монет по рыночной капитализации"""
    
    # CoinGecko API (бесплатный)
    COINGECKO_API = "https://api.coingecko.com/api/v3"
    
    # Кэш для уменьшения запросов
    _cache: Dict = {
        'coins': [],
        'last_update': None,
        'update_interval': timedelta(hours=1)  # Обновлять раз в час
    }
    
    # Монеты которые нужно исключить (стейблкоины, wrapped токены и т.д.)
    EXCLUDED_SYMBOLS = {
        'USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'USDP', 'USDD', 'GUSD', 'FRAX',
        'WBTC', 'WETH', 'STETH', 'WSTETH', 'CBETH', 'RETH',  # Wrapped/staked
        'UST', 'USTC',  # Мёртвые стейблы
        'USDE', 'FDUSD', 'PYUSD', 'USDG', 'RLUSD', 'USD0', 'USDAI', 'FRXUSD', 'USDF', 'AUSD', 'DUSD',  # Новые стейблы
        'PAXG', 'XAUT',  # Gold-backed
    }
    
    # Маппинг символов CoinGecko -> биржевые символы
    SYMBOL_MAP = {
        'miota': 'IOTA',
        'xrp': 'XRP',
    }
    
    @classmethod
    def _get_top_coins_limit(cls) -> int:
        """Получить лимит топ монет из настроек фильтров"""
        try:
            from analysis.market_filters import MarketFilters
            return MarketFilters.TOP_COINS_LIMIT
        except:
            return 200  # Дефолтное значение если не удалось загрузить
    
    @classmethod
    async def fetch_top_coins(cls, limit: int = 100, force_refresh: bool = False) -> List[str]:
        """
        Получить список топ монет по капитализации
        
        Args:
            limit: количество монет (макс 250)
            force_refresh: принудительное обновление кэша
            
        Returns:
            Список символов в формате ['BTC/USDT', 'ETH/USDT', ...]
        """
        # Проверяем кэш
        if not force_refresh and cls._is_cache_valid():
            logger.debug(f"Using cached top coins ({len(cls._cache['coins'])} coins)")
            return cls._cache['coins'][:limit]
        
        try:
            coins = await cls._fetch_from_coingecko(limit + 50)  # Запрашиваем больше из-за фильтрации
            
            if coins:
                cls._cache['coins'] = coins
                cls._cache['last_update'] = datetime.utcnow()
                logger.info(f"✅ Updated top coins list: {len(coins)} coins")
                return coins[:limit]
            
        except Exception as e:
            logger.error(f"Error fetching top coins: {e}")
        
        # Если ошибка - возвращаем кэш или дефолтный список
        if cls._cache['coins']:
            logger.warning("Using cached coins due to API error")
            return cls._cache['coins'][:limit]
        
        return cls._get_default_coins()[:limit]
    
    @classmethod
    async def _fetch_from_coingecko(cls, limit: int) -> List[str]:
        """Получить монеты с CoinGecko API"""
        url = f"{cls.COINGECKO_API}/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': min(limit, 250),
            'page': 1,
            'sparkline': 'false'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    return cls._process_coingecko_data(data)
                elif response.status == 429:
                    logger.warning("CoinGecko rate limit hit, using cache")
                    return []
                else:
                    logger.error(f"CoinGecko API error: {response.status}")
                    return []
    
    @classmethod
    def _process_coingecko_data(cls, data: List[Dict]) -> List[str]:
        """Обработать данные CoinGecko и вернуть список пар"""
        pairs = []
        
        for coin in data:
            symbol = coin.get('symbol', '').upper()
            
            # Применяем маппинг
            symbol = cls.SYMBOL_MAP.get(symbol.lower(), symbol)
            
            # Пропускаем исключённые
            if symbol in cls.EXCLUDED_SYMBOLS:
                continue
            
            # Пропускаем невалидные
            if not symbol or len(symbol) < 2 or len(symbol) > 10:
                continue
            
            # Формируем торговую пару
            pair = f"{symbol}/USDT"
            
            # Пропускаем дубликаты и USDT/USDT
            if pair not in pairs and symbol != 'USDT':
                pairs.append(pair)
        
        return pairs
    
    @classmethod
    def _is_cache_valid(cls) -> bool:
        """Проверить валидность кэша"""
        if not cls._cache['coins'] or not cls._cache['last_update']:
            return False
        
        age = datetime.utcnow() - cls._cache['last_update']
        return age < cls._cache['update_interval']
    
    @classmethod
    def _get_default_coins(cls) -> List[str]:
        """Дефолтный список если API недоступен"""
        return [
            'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'XRP/USDT', 'SOL/USDT',
            'ADA/USDT', 'DOGE/USDT', 'TRX/USDT', 'AVAX/USDT', 'LINK/USDT',
            'DOT/USDT', 'MATIC/USDT', 'SHIB/USDT', 'LTC/USDT', 'BCH/USDT',
            'ATOM/USDT', 'UNI/USDT', 'XLM/USDT', 'ETC/USDT', 'FIL/USDT',
            'APT/USDT', 'NEAR/USDT', 'ICP/USDT', 'HBAR/USDT', 'VET/USDT',
            'ALGO/USDT', 'FTM/USDT', 'SAND/USDT', 'MANA/USDT', 'XTZ/USDT',
        ]
    
    @classmethod
    def get_cache_info(cls) -> Dict:
        """Получить информацию о кэше"""
        return {
            'coins_count': len(cls._cache['coins']),
            'last_update': cls._cache['last_update'],
            'is_valid': cls._is_cache_valid(),
            'next_update': cls._cache['last_update'] + cls._cache['update_interval'] if cls._cache['last_update'] else None
        }
    
    @classmethod
    async def get_coin_info(cls, symbol: str) -> Optional[Dict]:
        """Получить информацию о конкретной монете"""
        if not cls._cache['coins']:
            await cls.fetch_top_coins()
        
        # Ищем в кэше
        pair = f"{symbol.upper()}/USDT"
        if pair in cls._cache['coins']:
            rank = cls._cache['coins'].index(pair) + 1
            return {
                'symbol': symbol.upper(),
                'pair': pair,
                'rank': rank,
                # Используем значение из настроек фильтров (динамически)
                'in_top_limit': rank <= cls._get_top_coins_limit()
            }
        
        return None


async def update_trading_pairs_auto(limit: int = 100) -> bool:
    """
    Автоматически обновить торговые пары на топ монеты
    Фильтрует пары, которые не торгуются на XT.com
    
    Returns:
        True если обновление прошло успешно
    """
    from database.config_manager import ConfigManager
    from exchange.xt_client import XTClient
    
    try:
        # Получаем топ монеты
        top_pairs = await TopCoinsService.fetch_top_coins(limit=limit + 50)  # Берем больше для фильтрации
        
        if not top_pairs:
            logger.error("Failed to fetch top coins - empty list")
            return False
        
        # Получаем список доступных пар на XT.com
        logger.info(f"🔍 Проверка {len(top_pairs)} пар на доступность на XT.com...")
        client = XTClient()
        
        # Загружаем markets для получения списка доступных пар
        try:
            await client._run_in_executor(client.exchange.load_markets)
            available_markets = set(client.exchange.markets.keys())
        except Exception as e:
            logger.warning(f"Не удалось загрузить markets: {e}, используем проверку через get_ohlcv")
            available_markets = None
        
        valid_pairs = []
        
        # Фильтруем пары
        for pair in top_pairs:
            try:
                if available_markets is not None:
                    # Быстрая проверка через markets
                    if pair in available_markets:
                        valid_pairs.append(pair)
                        if len(valid_pairs) >= limit:
                            break
                else:
                    # Медленная проверка через get_ohlcv (fallback)
                    df = await client.get_ohlcv(pair, '1m', limit=1)
                    if df is not None and not df.empty:
                        valid_pairs.append(pair)
                        if len(valid_pairs) >= limit:
                            break
            except Exception:
                # Пара не торгуется на XT.com - пропускаем
                continue
        
        if not valid_pairs:
            logger.error("No valid trading pairs found on XT.com")
            return False
        
        # Сохраняем в БД
        success = ConfigManager.set_trading_pairs(valid_pairs)
        
        if success:
            filtered_count = len(top_pairs) - len(valid_pairs)
            logger.info(f"✅ Auto-updated trading pairs: {len(valid_pairs)} pairs (проверено {len(top_pairs)}, отфильтровано {filtered_count})")
            return True
        else:
            logger.error("Failed to save trading pairs to database")
            return False
            
    except Exception as e:
        logger.error(f"Error in auto-update trading pairs: {e}")
        return False

