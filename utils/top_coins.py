"""
Сервис для автоматического получения топ монет по бирже XT (по объёму USDT).
Без CoinGecko. Берём только реально торгуемые пары USDT на XT.
"""
import asyncio
from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta
from utils.logger import logger


class TopCoinsService:
    """Сервис для получения топ монет по объёму на XT"""
    
    # Кэш для уменьшения запросов
    _cache: Dict = {
        'coins': [],
        'last_update': None,
        'update_interval': timedelta(minutes=30)  # Обновлять раз в 30 минут
    }
    
    @classmethod
    def _get_top_coins_limit(cls) -> int:
        """Получить лимит топ монет из настроек фильтров"""
        try:
            from analysis.market_filters import MarketFilters
            return MarketFilters.TOP_COINS_LIMIT
        except:
            return 200
    
    @classmethod
    async def fetch_top_coins(cls, limit: int = 100, force_refresh: bool = False) -> List[str]:
        """
        Получить список топ монет по объёму на XT (USDT пары).
        """
        if not force_refresh and cls._is_cache_valid():
            logger.debug(f"Using cached top coins ({len(cls._cache['coins'])} coins)")
            return cls._cache['coins'][:limit]
        
        try:
            coins = await cls._fetch_from_xt(limit=limit)
            if coins:
                cls._cache['coins'] = coins
                cls._cache['last_update'] = datetime.utcnow()
                logger.info(f"✅ Updated top coins list from XT: {len(coins)} coins")
                return coins[:limit]
        except Exception as e:
            logger.error(f"Error fetching top coins from XT: {e}")
        
        if cls._cache['coins']:
            logger.warning("Using cached coins due to XT fetch error")
            return cls._cache['coins'][:limit]
        
        # В крайних случаях — возвращаем то, что сохранено в конфиге (чтобы не подмешивать левое)
        try:
            from database.config_manager import ConfigManager
            saved = ConfigManager.get_trading_pairs()
            if saved:
                logger.warning("Fallback to saved trading_pairs from DB")
                return saved[:limit]
        except Exception:
            pass
        
        return []
    
    @classmethod
    async def _fetch_from_xt(cls, limit: int) -> List[str]:
        """
        Получить топ пар по объёму USDT с XT.
        Используем fetch_tickers для объёмов, фильтруем только USDT, активные рынки.
        ВАЛИДАЦИЯ: проверяем что пары реально торгуются (есть OHLCV данные).
        """
        from exchange.xt_client import XTClient
        
        client = XTClient()
        
        # Загружаем markets
        await client._run_in_executor(client.exchange.load_markets)
        markets = client.exchange.markets or {}
        
        # Получаем тикеры (может быть тяжёлый запрос, но нужен для объёмов)
        tickers = await client._run_in_executor(client.exchange.fetch_tickers)
        
        pairs: List[Tuple[str, float]] = []
        
        for symbol, ticker in tickers.items():
            # Фильтруем только USDT пары
            if not symbol.endswith('/USDT'):
                continue
            
            # Проверяем market активность
            market = markets.get(symbol)
            if not market or market.get('active') is False:
                continue
            
            # Берём объём в quote, если нет — пытаемся из baseVolume * last
            vol = ticker.get('quoteVolume')
            if vol is None:
                base_vol = ticker.get('baseVolume')
                last = ticker.get('last') or 0
                vol = (base_vol * last) if base_vol and last else 0
            
            if vol is None:
                vol = 0
            
            pairs.append((symbol, float(vol)))
        
        # Сортируем по объёму убыв.
        pairs.sort(key=lambda x: x[1], reverse=True)
        
        # ВАЛИДАЦИЯ: проверяем что пары реально торгуются (есть данные OHLCV)
        # Берём топ (limit * 1.5) для валидации, так как часть может не пройти проверку
        candidates = [p for p, _ in pairs[:int(limit * 1.5)]]
        validated_pairs = []
        
        logger.info(f"🔍 Validating {len(candidates)} top pairs from XT (checking OHLCV availability)...")
        
        for pair in candidates:
            try:
                # Быстрая проверка - запрашиваем 1 свечу
                df = await client.get_ohlcv(pair, '1m', limit=1)
                if df is not None and not df.empty:
                    validated_pairs.append(pair)
                    if len(validated_pairs) >= limit:
                        break
                else:
                    logger.warning(f"⚠️ Pair {pair} from XT tickers has no OHLCV data - skipping")
            except Exception as e:
                logger.warning(f"⚠️ Pair {pair} validation failed: {e} - skipping")
                continue
        
        if len(validated_pairs) < limit:
            logger.warning(f"⚠️ Only {len(validated_pairs)}/{limit} pairs passed validation. Some XT tickers may not have OHLCV data.")
        
        return validated_pairs
    
    @classmethod
    def _is_cache_valid(cls) -> bool:
        if not cls._cache['coins'] or not cls._cache['last_update']:
            return False
        age = datetime.utcnow() - cls._cache['last_update']
        return age < cls._cache['update_interval']
    
    @classmethod
    def get_cache_info(cls) -> Dict:
        return {
            'coins_count': len(cls._cache['coins']),
            'last_update': cls._cache['last_update'],
            'is_valid': cls._is_cache_valid(),
            'next_update': cls._cache['last_update'] + cls._cache['update_interval'] if cls._cache['last_update'] else None
        }
    
    @classmethod
    async def get_coin_info(cls, symbol: str) -> Optional[Dict]:
        if not cls._cache['coins']:
            await cls.fetch_top_coins()
        
        pair = f"{symbol.upper()}/USDT"
        if pair in cls._cache['coins']:
            rank = cls._cache['coins'].index(pair) + 1
            return {
                'symbol': symbol.upper(),
                'pair': pair,
                'rank': rank,
                'in_top_limit': rank <= cls._get_top_coins_limit()
            }
        return None


async def update_trading_pairs_auto(limit: int = 100) -> bool:
    """
    Автоматически обновить торговые пары на топ монеты XT (по объёму USDT).
    """
    from database.config_manager import ConfigManager
    
    try:
        top_pairs = await TopCoinsService.fetch_top_coins(limit=limit, force_refresh=True)
        
        if not top_pairs:
            logger.error("Failed to fetch top coins from XT - empty list")
            return False
        
        # Сохраняем в БД
        success = ConfigManager.set_trading_pairs(top_pairs[:limit])
        
        if success:
            logger.info(f"✅ Auto-updated trading pairs from XT: {len(top_pairs[:limit])} pairs")
            return True
        else:
            logger.error("Failed to save trading pairs to database")
            return False
            
    except Exception as e:
        logger.error(f"Error in auto-update trading pairs (XT): {e}")
        return False

