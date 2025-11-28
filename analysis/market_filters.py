"""
Market filters for signal generation
Strict criteria for HIGH-QUALITY signals
"""

import pandas as pd
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
from exchange.xt_client import XTClient
from ta.trend import EMAIndicator, ADXIndicator


class MarketFilters:
    """
    Market filters according to technical requirements
    """
    
    # === FILTER CONSTANTS ===
    
    # 1. Top-200 by market cap
    TOP_COINS_LIMIT = 200
    
    # 2. Futures volume
    MIN_FUTURES_VOLUME_USDT = 2_500_000  # ≥ 2,500,000 USDT
    
    # 3. Spread
    MAX_SPREAD_PERCENT = 0.35  # ≤ 0.35%
    
    # 4. Liquidity
    MIN_LIQUIDITY_USDT = 80_000  # ≥ 80,000 USDT
    LIQUIDITY_PRICE_RANGE = 0.003  # within 0.3% of price
    
    # 5. ATR volatility filter
    ATR_MIN_PERCENT = 0.10  # ≥ 0.10%
    ATR_MAX_PERCENT = 6.0   # ≤ 6.0%
    
    # 6. Gap filter (Open→Close)
    MAX_GAP_PERCENT = 2.5  # ≤ 2.5% разрыв Open→Close
    
    # 7. Anomaly candle 5m
    ANOMALY_CANDLE_PERCENT = 3.0  # > 3%
    ANOMALY_CANDLE_PAUSE_MINUTES = 15  # pause 15 min for candle anomaly
    
    # 8. Anomaly volume
    ANOMALY_VOLUME_RATIO = 2.5  # > 250% of average
    ANOMALY_VOLUME_PAUSE_MINUTES = 10  # pause 10 min for volume anomaly
    
    # 9. Gaps (Open→Close) legacy
    GAP_TIMEFRAMES = ['5m', '15m']  # forbidden on 5m/15m
    GAP_THRESHOLD = 0.008  # 0.8% considered a gap
    
    # 10. Pair cooldown
    PAIR_COOLDOWN_MINUTES = 30  # minimum 30 min since last signal
    
    # 11. BTC trend filter
    BTC_ADX_MIN = 20  # ADX BTC ≥ 20
    
    # === NEW FILTERS ===
    
    # 12. BTC Volatility Guard
    BTC_VOLATILITY_THRESHOLD = 2.5  # > 2.5% за 5 мин
    BTC_VOLATILITY_PAUSE_MINUTES = 5  # пауза 5 минут
    
    # 13. Anti-Pump Filter
    ANTI_PUMP_THRESHOLD = 10.0  # > ±10% за 30 минут
    ANTI_PUMP_LOOKBACK_CANDLES = 6  # 30 минут на 5m = 6 свечей
    
    # 14. Time Guard
    TIME_GUARD_MINUTES = 3  # первые 3 минуты каждого часа
    
    # 15. Time Session Filter (ОТКЛЮЧЕН - слишком строгий)
    FORBIDDEN_HOURS_START = 25  # Отключено (25 > 24, никогда не сработает)
    FORBIDDEN_HOURS_END = -1    # Отключено
    
    # Storage for paused coins
    _paused_coins = {}  # {ticker: pause_until_timestamp}
    
    # Storage for last signal times per pair
    _last_signal_times = {}  # {ticker: datetime}
    
    # Storage for BTC volatility pause
    _btc_pause_until = None
    
    @staticmethod
    async def check_all_filters(ticker: str, timeframe: str, df: pd.DataFrame, 
                                client: XTClient, direction: str = None) -> Dict:
        """
        Check all market filters
        
        Returns:
            {
                'passed': bool,
                'reason': str,
                'volume_24h': float,
                'spread': float,
                'liquidity': float
            }
        """
        
        result = {
            'passed': False,
            'reason': '',
            'volume_24h': None,
            'spread': None,
            'liquidity': None
        }
        
        # 0. Check anomaly pause
        if MarketFilters._is_paused(ticker):
            remaining = MarketFilters._get_pause_remaining(ticker)
            result['reason'] = f"Coin on pause ({remaining} min remaining)"
            return result
        
        # === NEW: Time Session Filter (23:00 - 05:00 UTC) ===
        if not MarketFilters.check_time_session():
            current_hour = datetime.utcnow().hour
            result['reason'] = f"Forbidden trading session (current: {current_hour}:00 UTC, forbidden: 23:00-05:00)"
            return result
        
        # === NEW: Time Guard (first 5 min of each hour) ===
        if not MarketFilters.check_time_guard():
            current_minute = datetime.utcnow().minute
            result['reason'] = f"Time guard active (minute {current_minute} < {MarketFilters.TIME_GUARD_MINUTES})"
            return result
        
        # === NEW: BTC Volatility Guard ===
        btc_guard = await MarketFilters.check_btc_volatility_guard(client)
        if not btc_guard['passed']:
            result['reason'] = btc_guard['reason']
            return result
        
        # 1. Pair cooldown - 30 min since last signal
        cooldown_passed, cooldown_remaining = MarketFilters.check_pair_cooldown(ticker)
        if not cooldown_passed:
            result['reason'] = f"Pair cooldown active ({cooldown_remaining} min remaining)"
            return result
        
        # 2. Top-300 by market cap
        is_top_300 = await MarketFilters.check_top_300(ticker)
        if not is_top_300:
            result['reason'] = "Not in TOP-300 by market cap"
            return result
        
        # 3. Futures volume ≥ 2,500,000 USDT
        volume_24h = await MarketFilters.check_futures_volume(ticker, client)
        if volume_24h is None or volume_24h < MarketFilters.MIN_FUTURES_VOLUME_USDT:
            vol_str = f"{volume_24h:,.0f}" if volume_24h else "0"
            result['reason'] = f"Volume {vol_str} < {MarketFilters.MIN_FUTURES_VOLUME_USDT:,.0f} USDT"
            return result
        result['volume_24h'] = volume_24h
        
        # 4. Spread ≤ 0.35%
        spread = await MarketFilters.check_spread(ticker, client)
        if spread is None:
            result['reason'] = "Failed to get spread"
            return result
        if spread > MarketFilters.MAX_SPREAD_PERCENT:
            result['reason'] = f"Spread {spread:.3f}% > {MarketFilters.MAX_SPREAD_PERCENT}%"
            return result
        result['spread'] = spread
        
        # 5. Liquidity ≥ 120,000 USDT within 0.3% of price
        liquidity = await MarketFilters.check_liquidity(ticker, client)
        if liquidity is None or liquidity < MarketFilters.MIN_LIQUIDITY_USDT:
            liq_str = f"{liquidity:,.0f}" if liquidity else "0"
            result['reason'] = f"Liquidity {liq_str} < {MarketFilters.MIN_LIQUIDITY_USDT:,.0f} USDT"
            return result
        result['liquidity'] = liquidity
        
        # 6. ATR volatility filter: 0.20% ≤ ATR% ≤ 6.0%
        atr_check = MarketFilters.check_atr_volatility(df)
        if not atr_check['passed']:
            result['reason'] = atr_check['reason']
            return result
        result['atr_percent'] = atr_check['atr_percent']
        
        # 7. Gap filter: нет разрыва Open→Close > 1.5%
        gap_check = MarketFilters.check_open_close_gap(df)
        if not gap_check['passed']:
            result['reason'] = gap_check['reason']
            return result
        
        # === NEW: Anti-Pump Filter (movement > ±7% in 30 min) ===
        anti_pump = MarketFilters.check_anti_pump(df, ticker, timeframe)
        if not anti_pump['passed']:
            result['reason'] = anti_pump['reason']
            return result
        
        # 8. BTC trend filter (for altcoins)
        if direction and ticker not in ['BTC/USDT', 'BTCUSDT']:
            btc_trend_ok = await MarketFilters.check_btc_trend_filter(direction, client)
            if not btc_trend_ok['passed']:
                result['reason'] = btc_trend_ok['reason']
                return result
        
        # 9. Anomaly candle 5m > 3% → pause 15 min
        if timeframe in ['5m', '1m']:
            has_anomaly_candle = MarketFilters.check_anomaly_candle(df, ticker)
            if has_anomaly_candle:
                result['reason'] = "Anomaly candle > 3% (15 min pause)"
                return result
        
        # 10. Anomaly volume > 250% of average → pause 10 min
        has_anomaly_volume = MarketFilters.check_anomaly_volume(df, ticker)
        if has_anomaly_volume:
            result['reason'] = "Anomaly volume > 250% (10 min pause)"
            return result
        
        # 11. Gaps forbidden on 5m/15m (legacy check)
        if timeframe in MarketFilters.GAP_TIMEFRAMES:
            has_gap = MarketFilters.check_gaps(df)
            if has_gap:
                result['reason'] = f"Gap detected on {timeframe}"
                return result
        
        # All filters passed
        result['passed'] = True
        result['reason'] = "All filters passed"
        return result
    
    # ========================================================================
    # NEW FILTERS
    # ========================================================================
    
    @staticmethod
    def check_time_session() -> bool:
        """
        Time Session Filter: не торгуем с 23:00 до 05:00 UTC
        
        Returns:
            True - если можно торговать
            False - если запрещено
        """
        current_hour = datetime.utcnow().hour
        
        # Запрещённые часы: 23, 0, 1, 2, 3, 4
        if current_hour >= MarketFilters.FORBIDDEN_HOURS_START or current_hour < MarketFilters.FORBIDDEN_HOURS_END:
            return False
        
        return True
    
    @staticmethod
    def check_time_guard() -> bool:
        """
        Time Guard: не входим в первые 5 минут каждого часа
        
        Returns:
            True - если можно торговать
            False - если запрещено
        """
        current_minute = datetime.utcnow().minute
        
        if current_minute < MarketFilters.TIME_GUARD_MINUTES:
            return False
        
        return True
    
    @staticmethod
    async def check_btc_volatility_guard(client: XTClient) -> Dict:
        """
        BTC Volatility Guard: при движении BTC > 1.5% за 5 минут — пауза 10 минут
        Использует кэш для оптимизации при 200+ парах
        
        Returns:
            {'passed': bool, 'reason': str}
        """
        from utils.cache import btc_cache
        
        result = {
            'passed': False,
            'reason': ''
        }
        
        # Проверяем, не активна ли пауза
        if MarketFilters._btc_pause_until and datetime.utcnow() < MarketFilters._btc_pause_until:
            remaining = (MarketFilters._btc_pause_until - datetime.utcnow()).total_seconds() / 60
            result['reason'] = f"BTC volatility pause active ({int(remaining)} min remaining)"
            return result
        
        try:
            # Получаем данные BTC из кэша (или загружаем если устарели)
            btc_df = await btc_cache.get_btc_ohlcv_1m(client)
            
            if btc_df is None or btc_df.empty or len(btc_df) < 5:
                result['passed'] = True
                result['reason'] = "BTC data unavailable, filter skipped"
                return result
            
            # Берём последние 5 минут
            recent_5min = btc_df.tail(5)
            
            # Цена 5 минут назад и текущая
            price_5min_ago = recent_5min.iloc[0]['open']
            current_price = recent_5min.iloc[-1]['close']
            
            if price_5min_ago == 0:
                result['passed'] = True
                return result
            
            # Изменение в процентах
            change_percent = abs((current_price - price_5min_ago) / price_5min_ago) * 100
            
            if change_percent > MarketFilters.BTC_VOLATILITY_THRESHOLD:
                # Устанавливаем паузу на 5 минут
                MarketFilters._btc_pause_until = datetime.utcnow() + timedelta(minutes=MarketFilters.BTC_VOLATILITY_PAUSE_MINUTES)
                result['reason'] = f"BTC moved {change_percent:.2f}% in 5 min > {MarketFilters.BTC_VOLATILITY_THRESHOLD}% ({MarketFilters.BTC_VOLATILITY_PAUSE_MINUTES} min pause set)"
                return result
            
            result['passed'] = True
            return result
            
        except Exception as e:
            # При ошибке пропускаем фильтр
            result['passed'] = True
            result['reason'] = f"BTC volatility check error: {str(e)}, filter skipped"
            return result
    
    @staticmethod
    def check_anti_pump(df: pd.DataFrame, ticker: str, timeframe: str) -> Dict:
        """
        Anti-Pump Filter: избегать монет с движением > ±7% за последние 30 минут
        
        Адаптивно работает для всех таймфреймов:
        - 1m: 30 свечей
        - 5m: 6 свечей
        - 15m: 2 свечи
        - 1h: 1 свеча (30 минут)
        - 4h: 1 свеча (но это 4 часа, не 30 минут - пропускаем)
        
        Returns:
            {'passed': bool, 'reason': str}
        """
        result = {
            'passed': False,
            'reason': ''
        }
        
        # Определяем количество свечей для 30 минут в зависимости от таймфрейма
        timeframe_minutes = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '1h': 60,
            '4h': 240,
            '1d': 1440
        }
        
        tf_minutes = timeframe_minutes.get(timeframe, 5)
        
        # Для таймфреймов >= 1h проверяем только последнюю свечу (может быть больше 30 минут)
        if tf_minutes >= 60:
            lookback_candles = 1
        else:
            # Для меньших таймфреймов: 30 минут / длительность свечи
            lookback_candles = max(1, int(30 / tf_minutes))
        
        if df.empty or len(df) < lookback_candles:
            result['passed'] = True
            return result
        
        # Берём последние N свечей (30 минут)
        recent = df.tail(lookback_candles)
        
        # Цена N свечей назад и текущая
        price_30min_ago = recent.iloc[0]['open']
        current_price = recent.iloc[-1]['close']
        
        if price_30min_ago == 0:
            result['passed'] = True
            return result
        
        # Изменение в процентах
        change_percent = ((current_price - price_30min_ago) / price_30min_ago) * 100
        
        if abs(change_percent) > MarketFilters.ANTI_PUMP_THRESHOLD:
            direction = "pump" if change_percent > 0 else "dump"
            actual_minutes = lookback_candles * tf_minutes
            result['reason'] = f"Anti-{direction} filter: {ticker} moved {change_percent:+.2f}% in {actual_minutes} min > ±{MarketFilters.ANTI_PUMP_THRESHOLD}%"
            return result
        
        result['passed'] = True
        return result
    
    # ========================================================================
    # INDIVIDUAL FILTER CHECKS
    # ========================================================================
    
    @staticmethod
    async def check_top_300(ticker: str) -> bool:
        """
        Check if coin is in TOP-300 by market cap
        
        Использует текущий список торговых пар из ConfigManager
        Если монета в списке торговых пар - значит она в топ-300
        """
        from database.config_manager import ConfigManager
        
        # Получаем текущий список торговых пар (автоматически обновляется из CoinGecko)
        trading_pairs = ConfigManager.get_trading_pairs()
        
        # Если монета есть в списке торговых пар - значит она в топ-300
        if ticker in trading_pairs:
            return True
        
        # Также проверяем через TopCoinsService (если доступен)
        try:
            from utils.top_coins import TopCoinsService
            coin_info = await TopCoinsService.get_coin_info(ticker.replace('/USDT', ''))
            if coin_info and coin_info.get('rank', 999) <= MarketFilters.TOP_COINS_LIMIT:
                return True
        except:
            pass  # Если сервис недоступен, используем только проверку по списку
        
        # Если монеты нет в списке - считаем что она не в топ-300
        return False
    
    @staticmethod
    async def check_futures_volume(ticker: str, client: XTClient) -> Optional[float]:
        """
        Check futures volume ≥ 2,500,000 USDT
        """
        try:
            ticker_data = await client.get_ticker(ticker)
            
            if not ticker_data:
                return None
            
            # Get 24h volume in USDT
            # quoteVolume - volume in quote currency (USDT)
            volume_usdt = ticker_data.get('quoteVolume')
            
            if volume_usdt is None:
                # Try to calculate: baseVolume * last price
                base_volume = ticker_data.get('baseVolume')
                last_price = ticker_data.get('last')
                
                if base_volume and last_price:
                    volume_usdt = float(base_volume) * float(last_price)
            
            return float(volume_usdt) if volume_usdt else None
            
        except Exception as e:
            print(f"[ERROR] Volume check error for {ticker}: {e}")
            return None
    
    @staticmethod
    async def check_spread(ticker: str, client: XTClient) -> Optional[float]:
        """
        Check spread ≤ 0.35%
        
        Spread = (ask - bid) / bid * 100%
        """
        try:
            ticker_data = await client.get_ticker(ticker)
            
            if not ticker_data:
                return None
            
            bid = ticker_data.get('bid')
            ask = ticker_data.get('ask')
            
            if not bid or not ask:
                # Try to get from orderbook (minimum 5 levels for Binance)
                orderbook = await client.get_orderbook(ticker, limit=5)
                if orderbook and orderbook.get('bids') and orderbook.get('asks'):
                    bid = float(orderbook['bids'][0][0])
                    ask = float(orderbook['asks'][0][0])
            
            if bid and ask:
                bid = float(bid)
                ask = float(ask)
                spread_percent = (ask - bid) / bid * 100
                return spread_percent
            
            return None
            
        except Exception as e:
            print(f"[ERROR] Spread check error for {ticker}: {e}")
            return None
    
    @staticmethod
    async def check_liquidity(ticker: str, client: XTClient) -> Optional[float]:
        """
        Check liquidity ≥ 120,000 USDT within 0.3% of price
        
        Liquidity = sum of (bid_volume + ask_volume) in USDT 
        for orders within ±0.3% of current price
        """
        try:
            # Get current price
            ticker_data = await client.get_ticker(ticker)
            if not ticker_data or not ticker_data.get('last'):
                return None
            
            current_price = float(ticker_data['last'])
            
            # Get orderbook (50 levels depth)
            orderbook = await client.get_orderbook(ticker, limit=50)
            if not orderbook:
                return None
            
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            # Price range ±0.3%
            price_range = current_price * MarketFilters.LIQUIDITY_PRICE_RANGE
            min_price = current_price - price_range
            max_price = current_price + price_range
            
            # Calculate liquidity in USDT
            liquidity_usdt = 0
            
            # Bids (buyers) - below current price
            for price, volume in bids:
                price = float(price)
                volume = float(volume)
                
                if price >= min_price:  # Within 0.3% of current price
                    liquidity_usdt += price * volume
            
            # Asks (sellers) - above current price
            for price, volume in asks:
                price = float(price)
                volume = float(volume)
                
                if price <= max_price:  # Within 0.3% of current price
                    liquidity_usdt += price * volume
            
            return liquidity_usdt
            
        except Exception as e:
            print(f"[ERROR] Liquidity check error for {ticker}: {e}")
            return None
    
    @staticmethod
    def check_anomaly_candle(df: pd.DataFrame, ticker: str) -> bool:
        """
        Check for anomaly candle 5m > 3%
        If detected → sets 15 min pause
        
        Returns:
            True - if anomaly candle detected (filter NOT passed)
            False - if OK (filter passed)
        """
        if df.empty or len(df) < 2:
            return False
        
        # Check last 3 candles
        recent_candles = df.tail(3)
        
        for idx, row in recent_candles.iterrows():
            open_price = row['open']
            close_price = row['close']
            
            if open_price == 0:
                continue
            
            # Candle size in percent
            candle_size = abs(close_price - open_price) / open_price * 100
            
            if candle_size > MarketFilters.ANOMALY_CANDLE_PERCENT:
                # Anomaly candle detected - set pause 15 min
                MarketFilters._set_pause(ticker, MarketFilters.ANOMALY_CANDLE_PAUSE_MINUTES)
                print(f"[ANOMALY] Anomaly candle {ticker}: {candle_size:.2f}% > {MarketFilters.ANOMALY_CANDLE_PERCENT}% ({MarketFilters.ANOMALY_CANDLE_PAUSE_MINUTES} min pause)")
                return True
        
        return False
    
    @staticmethod
    def check_anomaly_volume(df: pd.DataFrame, ticker: str) -> bool:
        """
        Check for anomaly volume > 250% of average
        If detected → sets 10 min pause
        
        Returns:
            True - if anomaly volume (filter NOT passed)
            False - if OK (filter passed)
        """
        if df.empty or len(df) < 20:
            return False
        
        # Average volume for last 20 candles (excluding last)
        avg_volume = df['volume'].iloc[-21:-1].mean()
        
        if avg_volume == 0:
            return False
        
        # Check last 3 candles
        recent_candles = df.tail(3)
        
        for idx, row in recent_candles.iterrows():
            current_volume = row['volume']
            volume_ratio = current_volume / avg_volume
            
            if volume_ratio > MarketFilters.ANOMALY_VOLUME_RATIO:
                # Anomaly volume detected - set pause 10 min
                MarketFilters._set_pause(ticker, MarketFilters.ANOMALY_VOLUME_PAUSE_MINUTES)
                print(f"[ANOMALY] Anomaly volume {ticker}: {volume_ratio:.1f}x > {MarketFilters.ANOMALY_VOLUME_RATIO}x ({MarketFilters.ANOMALY_VOLUME_PAUSE_MINUTES} min pause)")
                return True
        
        return False
    
    @staticmethod
    def check_gaps(df: pd.DataFrame) -> bool:
        """
        Check for gaps on 5m/15m
        Gap = difference between previous candle's close and current candle's open
        
        Returns:
            True - if gap detected (filter NOT passed)
            False - if no gaps (filter passed)
        """
        if df.empty or len(df) < 2:
            return False
        
        # Check last 5 candles for gaps
        recent_candles = df.tail(6)
        
        for i in range(1, len(recent_candles)):
            prev_close = recent_candles.iloc[i-1]['close']
            current_open = recent_candles.iloc[i]['open']
            
            if prev_close == 0:
                continue
            
            # Gap size in percent
            gap_size = abs(current_open - prev_close) / prev_close
            
            if gap_size > MarketFilters.GAP_THRESHOLD:
                print(f"[GAP] Gap detected: {gap_size*100:.2f}%")
                return True
        
        return False
    
    # ========================================================================
    # VOLATILITY AND GAP CHECKS
    # ========================================================================
    
    @staticmethod
    def check_pair_cooldown(ticker: str) -> Tuple[bool, int]:
        """
        Check pair cooldown - at least 30 min since last signal
        
        Returns:
            (passed: bool, remaining_minutes: int)
        """
        if ticker not in MarketFilters._last_signal_times:
            return True, 0
        
        last_signal = MarketFilters._last_signal_times[ticker]
        cooldown_end = last_signal + timedelta(minutes=MarketFilters.PAIR_COOLDOWN_MINUTES)
        
        if datetime.utcnow() >= cooldown_end:
            # Cooldown expired - remove from storage
            del MarketFilters._last_signal_times[ticker]
            return True, 0
        
        # Cooldown still active
        remaining = (cooldown_end - datetime.utcnow()).total_seconds() / 60
        return False, int(remaining)
    
    @staticmethod
    def record_signal_time(ticker: str):
        """Record the time when a signal was generated for a pair"""
        MarketFilters._last_signal_times[ticker] = datetime.utcnow()
    
    @staticmethod
    def check_atr_volatility(df: pd.DataFrame) -> Dict:
        """
        ATR volatility filter
        ATR % = ATR(14) / Price × 100
        Condition: 0.20% ≤ ATR% ≤ 6.0%
        
        Returns:
            {'passed': bool, 'reason': str, 'atr_percent': float}
        """
        result = {
            'passed': False,
            'reason': '',
            'atr_percent': None
        }
        
        if df.empty or len(df) < 14:
            result['reason'] = "Not enough data for ATR calculation"
            return result
        
        # Calculate ATR (14 period)
        from ta.volatility import AverageTrueRange
        
        atr_indicator = AverageTrueRange(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            window=14
        )
        
        atr = atr_indicator.average_true_range().iloc[-1]
        current_price = df.iloc[-1]['close']
        
        if current_price == 0:
            result['reason'] = "Invalid price (zero)"
            return result
        
        # ATR % = ATR / Price × 100
        atr_percent = (atr / current_price) * 100
        result['atr_percent'] = atr_percent
        
        if atr_percent < MarketFilters.ATR_MIN_PERCENT:
            result['reason'] = f"ATR% {atr_percent:.2f}% < {MarketFilters.ATR_MIN_PERCENT}% (dead market)"
            return result
        
        if atr_percent > MarketFilters.ATR_MAX_PERCENT:
            result['reason'] = f"ATR% {atr_percent:.2f}% > {MarketFilters.ATR_MAX_PERCENT}% (too high volatility)"
            return result
        
        result['passed'] = True
        return result
    
    @staticmethod
    def check_open_close_gap(df: pd.DataFrame) -> Dict:
        """
        Проверка разрыва Open→Close > 1.5%
        
        Returns:
            {'passed': bool, 'reason': str}
        """
        result = {
            'passed': False,
            'reason': ''
        }
        
        if df.empty or len(df) < 1:
            result['reason'] = "Not enough data for gap check"
            return result
        
        # Проверяем последнюю свечу
        last = df.iloc[-1]
        open_price = last['open']
        close_price = last['close']
        
        if open_price == 0:
            result['reason'] = "Invalid open price (zero)"
            return result
        
        # Разрыв в процентах
        gap_percent = abs(close_price - open_price) / open_price * 100
        
        if gap_percent > MarketFilters.MAX_GAP_PERCENT:
            result['reason'] = f"Open→Close gap {gap_percent:.2f}% > {MarketFilters.MAX_GAP_PERCENT}%"
            return result
        
        result['passed'] = True
        return result
    
    @staticmethod
    async def check_btc_trend_filter(direction: str, client: XTClient) -> Dict:
        """
        BTC Trend Filter
        Использует кэш для оптимизации при 200+ парах
        
        For LONG:
        - BTC price > EMA200 (1H)
        - EMA50 > EMA200 (1H)
        - ADX BTC ≥ 20
        
        For SHORT:
        - BTC price < EMA200 (1H)
        - EMA50 < EMA200 (1H)
        - ADX BTC ≥ 20
        
        Returns:
            {'passed': bool, 'reason': str}
        """
        from utils.cache import btc_cache
        
        result = {
            'passed': False,
            'reason': ''
        }
        
        try:
            # Get BTC 1H data from cache
            btc_df = await btc_cache.get_btc_ohlcv_1h(client)
            
            if btc_df is None or btc_df.empty or len(btc_df) < 200:
                # If we can't get BTC data, allow signal (don't block)
                result['passed'] = True
                result['reason'] = "BTC data unavailable, filter skipped"
                return result
            
            # Calculate EMA50 and EMA200
            ema50 = EMAIndicator(close=btc_df['close'], window=50).ema_indicator()
            ema200 = EMAIndicator(close=btc_df['close'], window=200).ema_indicator()
            
            # Calculate ADX
            adx_indicator = ADXIndicator(
                high=btc_df['high'],
                low=btc_df['low'],
                close=btc_df['close'],
                window=14
            )
            adx = adx_indicator.adx()
            
            # Get latest values
            btc_price = btc_df.iloc[-1]['close']
            btc_ema50 = ema50.iloc[-1]
            btc_ema200 = ema200.iloc[-1]
            btc_adx = adx.iloc[-1]
            
            # Check ADX first
            if btc_adx < MarketFilters.BTC_ADX_MIN:
                result['reason'] = f"BTC ADX {btc_adx:.1f} < {MarketFilters.BTC_ADX_MIN} (weak trend)"
                return result
            
            if direction == 'LONG':
                # For LONG: BTC > EMA200 and EMA50 > EMA200
                if btc_price <= btc_ema200:
                    result['reason'] = f"BTC price ${btc_price:.0f} below EMA200 ${btc_ema200:.0f} (bearish)"
                    return result
                
                if btc_ema50 <= btc_ema200:
                    result['reason'] = f"BTC EMA50 below EMA200 (bearish trend)"
                    return result
            
            else:  # SHORT
                # For SHORT: BTC < EMA200 and EMA50 < EMA200
                if btc_price >= btc_ema200:
                    result['reason'] = f"BTC price ${btc_price:.0f} above EMA200 ${btc_ema200:.0f} (bullish)"
                    return result
                
                if btc_ema50 >= btc_ema200:
                    result['reason'] = f"BTC EMA50 above EMA200 (bullish trend)"
                    return result
            
            result['passed'] = True
            result['reason'] = "BTC trend filter passed"
            return result
            
        except Exception as e:
            # On error, allow signal (don't block)
            print(f"[ERROR] BTC trend filter error: {e}")
            result['passed'] = True
            result['reason'] = f"BTC filter error: {str(e)}, filter skipped"
            return result
    
    # ========================================================================
    # PAUSE MANAGEMENT
    # ========================================================================
    
    @staticmethod
    def _set_pause(ticker: str, minutes: int = 15):
        """Set pause for a coin for specified minutes"""
        pause_until = datetime.utcnow() + timedelta(minutes=minutes)
        MarketFilters._paused_coins[ticker] = pause_until
    
    @staticmethod
    def _is_paused(ticker: str) -> bool:
        """Check if a coin is on pause"""
        if ticker not in MarketFilters._paused_coins:
            return False
        
        pause_until = MarketFilters._paused_coins[ticker]
        
        if datetime.utcnow() >= pause_until:
            # Pause expired - remove
            del MarketFilters._paused_coins[ticker]
            return False
        
        return True
    
    @staticmethod
    def _get_pause_remaining(ticker: str) -> int:
        """Get remaining pause time in minutes"""
        if ticker not in MarketFilters._paused_coins:
            return 0
        
        pause_until = MarketFilters._paused_coins[ticker]
        remaining = (pause_until - datetime.utcnow()).total_seconds() / 60
        
        return int(remaining) if remaining > 0 else 0
    
    @staticmethod
    def get_paused_coins() -> Dict[str, int]:
        """Get list of paused coins with remaining time"""
        result = {}
        
        for ticker, pause_until in list(MarketFilters._paused_coins.items()):
            remaining = MarketFilters._get_pause_remaining(ticker)
            
            if remaining > 0:
                result[ticker] = remaining
            else:
                # Pause expired - remove
                del MarketFilters._paused_coins[ticker]
        
        return result
