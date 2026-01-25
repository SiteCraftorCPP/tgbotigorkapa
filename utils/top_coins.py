"""
Сервис для автоматического получения топ монет по бирже XT (по объёму USDT).
"""
import asyncio
import requests
from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta
from utils.logger import logger

class TopCoinsService:
    """Сервис для получения топ монет по объёму на XT"""
    
    _cache: Dict = {
        'coins': [],
        'last_update': None,
        'update_interval': timedelta(minutes=30)
    }
    
    EXCLUDED_BASES = {
        'USDT', 'USDC', 'BUSD', 'USDS', 'BSC-USD', 'DAI', 'FDUSD', 'TUSD'
    }

    # Хардкод список топ-100 на случай полного отказа API
    FALLBACK_TOP_100 = [
        "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT", "AVAX/USDT", "DOGE/USDT", "DOT/USDT", "LINK/USDT",
        "MATIC/USDT", "SHIB/USDT", "LTC/USDT", "BCH/USDT", "NEAR/USDT", "UNI/USDT", "ICP/USDT", "APT/USDT", "TIA/USDT", "OP/USDT",
        "ARB/USDT", "INJ/USDT", "SUI/USDT", "SEI/USDT", "FIL/USDT", "ETC/USDT", "XLM/USDT", "ATOM/USDT", "VET/USDT", "IMX/USDT",
        "TRX/USDT", "HBAR/USDT", "GRT/USDT", "RUNE/USDT", "STX/USDT", "EGLD/USDT", "THETA/USDT", "ALGO/USDT", "FLOW/USDT", "DYDX/USDT",
        "KAS/USDT", "FET/USDT", "AGIX/USDT", "ORDI/USDT", "WLD/USDT", "GALA/USDT", "SAND/USDT", "MANA/USDT", "AXS/USDT", "APE/USDT",
        "ROSE/USDT", "AAVE/USDT", "SNX/USDT", "MKR/USDT", "CRV/USDT", "RNDR/USDT", "JUP/USDT", "PYTH/USDT", "BEAM/USDT", "STRK/USDT",
        "ZETA/USDT", "MANTA/USDT", "ALT/USDT", "ENS/USDT", "LDO/USDT", "PENDLE/USDT", "MINA/USDT", "FTM/USDT", "BLUR/USDT", "MEME/USDT",
        "BONK/USDT", "PEPE/USDT", "FLOKI/USDT", "WOO/USDT", "GMT/USDT", "MASK/USDT", "OCEAN/USDT", "ANKR/USDT", "SKL/USDT", "LRC/USDT",
        "KNC/USDT", "1INCH/USDT", "SUSHI/USDT", "BAL/USDT", "YFI/USDT", "COMP/USDT", "GLMR/USDT", "ASTR/USDT", "GMX/USDT", "MAGIC/USDT",
        "ID/USDT", "HOOK/USDT", "EDU/USDT", "ARKM/USDT", "CYBER/USDT", "MAV/USDT", "GAL/USDT", "XRD/USDT", "QNT/USDT", "XMR/USDT"
    ]
    
    @classmethod
    async def fetch_top_coins(cls, limit: int = 100, force_refresh: bool = False) -> List[str]:
        if not force_refresh and cls._is_cache_valid():
            return cls._cache['coins'][:limit]
        
        try:
            coins = await cls._fetch_from_xt(limit=limit)
            if not coins:
                logger.warning("XT API returned no coins, using fallback list")
                coins = cls.FALLBACK_TOP_100
                
            if coins:
                cls._cache['coins'] = coins
                cls._cache['last_update'] = datetime.utcnow()
                return coins[:limit]
        except Exception as e:
            logger.error(f"Error fetching top coins: {e}")
        
        return cls._cache['coins'][:limit] if cls._cache['coins'] else cls.FALLBACK_TOP_100[:limit]
    
    @classmethod
    async def _fetch_from_xt(cls, limit: int) -> List[str]:
        """
        Получить топ пар по объёму напрямую через V4 API
        """
        try:
            # Получаем тикеры всех фьючерсов через V4 API (самый надежный способ для объемов)
            url = "https://fapi.xt.com/future/market/v1/public/q/tickers"
            response = requests.get(url, timeout=15).json()
            
            if response.get('returnCode') != 0:
                logger.error(f"XT API Tickers Error: {response}")
                return []
                
            tickers = response.get('result', [])
            pairs_with_vol = []
            
            for t in tickers:
                symbol_id = t.get('s', '')
                if not symbol_id.endswith('_usdt'):
                    continue
                
                # Конвертируем btc_usdt в BTC/USDT
                base = symbol_id.split('_')[0].upper()
                if base in cls.EXCLUDED_BASES:
                    continue
                    
                pair = f"{base}/USDT"
                vol = float(t.get('v', 0)) * float(t.get('c', 0)) # v (volume) * c (close price) = usdt volume
                
                if vol > 0:
                    pairs_with_vol.append((pair, vol))
            
            # Сортируем по объему
            pairs_with_vol.sort(key=lambda x: x[1], reverse=True)
            
            # Берем кандидатов (чуть больше чем лимит, чтобы отсеять невалидные)
            candidates = [p for p, _ in pairs_with_vol[:max(limit, int(limit * 1.5))]]
            logger.info(f"🔍 Validating {len(candidates)} top pairs from XT (checking OHLCV availability)...")
            
            from exchange.xt_client import XTClient
            client = XTClient()
            
            # Параллельная валидация
            semaphore = asyncio.Semaphore(15)
            
            async def validate_pair(pair: str):
                async with semaphore:
                    try:
                        # Пробуем получить 1 свечу за 1 час
                        df = await client.get_ohlcv(pair, '1h', limit=1)
                        if df is not None and not df.empty:
                            return pair
                    except:
                        pass
                    return None

            results = await asyncio.gather(*(validate_pair(p) for p in candidates))
            validated_pairs = [p for p in results if p][:limit]
            
            logger.info(f"✅ Successfully fetched and validated {len(validated_pairs)} top pairs from XT")
            return validated_pairs
            
        except Exception as e:
            logger.error(f"Failed to fetch from XT V4: {e}")
            return []
    
    @classmethod
    def _is_cache_valid(cls) -> bool:
        if not cls._cache['coins'] or not cls._cache['last_update']:
            return False
        return datetime.utcnow() - cls._cache['last_update'] < cls._cache['update_interval']

    @classmethod
    def get_cache_info(cls) -> Dict:
        return {
            'coins_count': len(cls._cache['coins']),
            'last_update': cls._cache['last_update'],
            'is_valid': cls._is_cache_valid(),
            'next_update': cls._cache['last_update'] + cls._cache['update_interval'] if cls._cache['last_update'] else None
        }

async def update_trading_pairs_auto(limit: int = 300) -> bool:
    from database.config_manager import ConfigManager
    try:
        top_pairs = await TopCoinsService.fetch_top_coins(limit=limit, force_refresh=True)
        if not top_pairs:
            logger.error("Failed to fetch top pairs for auto-update")
            return False
        
        # Ограничиваем список ровно тем, что просил юзер (или лимитом)
        top_pairs = top_pairs[:limit]
        success = ConfigManager.set_trading_pairs(top_pairs)
        if success:
            logger.info(f"✅ Trading pairs auto-updated to top {len(top_pairs)} coins")
            return True
        return False
    except Exception as e:
        logger.error(f"Error in auto-update: {e}")
        return False
