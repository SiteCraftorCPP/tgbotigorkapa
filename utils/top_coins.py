"""
Сервис для автоматического получения топ монет по бирже XT (по объёму USDT).
"""
import asyncio
import httpx
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
    
    EXCLUDED_BASES = {'USDT', 'USDC', 'BUSD', 'USDS', 'BSC-USD', 'DAI', 'FDUSD', 'TUSD'}

    FALLBACK_TOP_100 = [
        "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT", "AVAX/USDT", "DOGE/USDT", "DOT/USDT", "LINK/USDT",
        "MATIC/USDT", "SHIB/USDT", "LTC/USDT", "BCH/USDT", "NEAR/USDT", "UNI/USDT", "ICP/USDT", "APT/USDT", "TIA/USDT", "OP/USDT",
        "ARB/USDT", "INJ/USDT", "SUI/USDT", "SEI/USDT", "FIL/USDT", "ETC/USDT", "XLM/USDT", "ATOM/USDT", "VET/USDT", "IMX/USDT"
    ]
    
    @classmethod
    async def fetch_top_coins(cls, limit: int = 100, force_refresh: bool = False) -> List[str]:
        if not force_refresh and cls._is_cache_valid():
            return cls._cache['coins'][:limit]
        
        try:
            coins = await cls._fetch_from_xt(limit=limit)
            if not coins:
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
        """Получить топ пар через httpx (асинхронно)"""
        url = "https://fapi.xt.com/future/market/v1/public/q/tickers"
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(url)
                response = resp.json()
                
                if response.get('returnCode') != 0:
                    return []
                    
                tickers = response.get('result', [])
                pairs_with_vol = []
                
                for t in tickers:
                    symbol_id = t.get('s', '')
                    if not symbol_id.endswith('_usdt'): continue
                    
                    base = symbol_id.split('_')[0].upper()
                    if base in cls.EXCLUDED_BASES: continue
                        
                    pair = f"{base}/USDT"
                    vol = float(t.get('v', 0)) * float(t.get('c', 0))
                    if vol > 0:
                        pairs_with_vol.append((pair, vol))
                
                pairs_with_vol.sort(key=lambda x: x[1], reverse=True)
                candidates = [p for p, _ in pairs_with_vol[:max(limit, int(limit * 1.2))]]
                
                # Валидация
                from exchange.xt_client import XTClient
                xt = XTClient()
                semaphore = asyncio.Semaphore(20)
                
                async def validate(p):
                    async with semaphore:
                        df = await xt.get_ohlcv(p, '1h', limit=1)
                        return p if df is not None and not df.empty else None

                results = await asyncio.gather(*(validate(p) for p in candidates))
                await xt.close()
                return [p for p in results if p][:limit]
                
            except Exception as e:
                logger.error(f"Failed to fetch from XT V4: {e}")
                return []
    
    @classmethod
    def _is_cache_valid(cls) -> bool:
        if not cls._cache['coins'] or not cls._cache['last_update']: return False
        return datetime.utcnow() - cls._cache['last_update'] < cls._cache['update_interval']

async def update_trading_pairs_auto(limit: int = 300) -> bool:
    from database.config_manager import ConfigManager
    try:
        top_pairs = await TopCoinsService.fetch_top_coins(limit=limit, force_refresh=True)
        if not top_pairs: return False
        return ConfigManager.set_trading_pairs(top_pairs)
    except Exception as e:
        logger.error(f"Error in auto-update: {e}")
        return False
