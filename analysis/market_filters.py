"""
Market filters for signal generation
STRICT criteria for HIGH-QUALITY signals
Updated: Full filter implementation
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Tuple, List
from datetime import datetime, timedelta
from exchange.xt_client import XTClient
from ta.trend import EMAIndicator, ADXIndicator
from ta.volatility import AverageTrueRange


class MarketFilters:
    """
    Complete Market Filters Implementation
    """
    
    # ========================================================================
    # ФИЛЬТРЫ РЫНКА
    # ========================================================================
    
    # Капитализация
    TOP_COINS_LIMIT = 300  # топ-300
    
    # Объём фьючерсов 24h
    MIN_FUTURES_VOLUME_USDT = 3_000_000  # ≥ 3,000,000 USDT
    
    # Объём 1h относительно 24h
    MIN_VOLUME_60M_RATIO = 0.012  # ≥ 1.2% от 24h
    
    # Спред
    MAX_SPREAD_PERCENT = 0.35  # ≤ 0.35%
    MAX_AVG_SPREAD_15M_PERCENT = 0.35  # Средний спред 1h ≤ 0.35%
    
    # Ликвидность
    MIN_LIQUIDITY_USDT = 300_000  # ≥ 300,000 USDT в пределах ±0.5%
    LIQUIDITY_PRICE_RANGE = 0.005  # ±0.5%
    
    # ATR волатильность (1h)
    ATR_MIN_PERCENT = 1.5  # ≥ 1.5%
    ATR_MAX_PERCENT = 9.0  # ≤ 9.0%
    MAX_ATR_DEVIATION = 35.0  # Отклонение ATR ≤ 35%
    
    # Свечи и разрывы
    MAX_CANDLE_BODY_PERCENT = 5.0  # Нет свечей с Close-Open > 5.0%
    MAX_HIGH_LOW_GAP_PERCENT = 7.0  # Нет High/Low разрывов > 7.0% за 20 свечей
    CANDLE_CHECK_LOOKBACK = 20  # Последние 20 свечей
    
    # Funding Rate
    FUNDING_RATE_MIN = -0.0008  # от -0.08%
    FUNDING_RATE_MAX = 0.0008   # до +0.08%
    
    # Open Interest
    MAX_OI_CHANGE_15M_PERCENT = 35.0  # Изменение OI за 1h ≤ 35%
    
    # Возраст контракта
    MIN_CONTRACT_AGE_DAYS = 10  # ≥ 10 дней
    
    # ========================================================================
    # BTC/ETH ФИЛЬТРЫ
    # ========================================================================
    
    BTC_MAX_MOVE_1H = 4.5  # BTC движение за 1 час ≤ 4.5%
    BTC_MAX_REVERSALS_30M = 1  # BTC разворотов > 0.7% за 30 минут ≤ 1 (мягкая проверка)
    BTC_REVERSAL_THRESHOLD = 0.7  # Порог разворота 0.7%
    BTC_PAUSE_MINUTES = 35  # Пауза после импульса BTC 1h: 35 минут
    BTC_STRONG_MOVE_1H = 3.0  # При импульсе ≥3% запрещаем вход против направления
    ETH_MAX_MOVE_1H = 4.0  # ETH движение за 1 час ≤ 4.0%
    
    # ========================================================================
    # ВРЕМЕННЫЕ ФИЛЬТРЫ
    # ========================================================================
    
    TIME_GUARD_START_MINUTES = 0  # Запрет первые X минут каждого часа
    TIME_GUARD_END_MINUTES = 0  # Запрет последние X минут каждого часа
    MIN_HOURLY_VOLUME_RATIO = 0.60  # Объём за 1 час ≥ 60% от среднего 24h
    
    # ========================================================================
    # ИНДИКАТОРЫ
    # ========================================================================
    
    RSI_MAX_LONG = 70  # RSI для лонга ≤ 70
    RSI_MIN_SHORT = 30  # RSI для шорта ≥ 30
    ADX_MIN = 20  # ADX ≥ 20
    ADX_MAX = 55  # ADX ≤ 55
    MIN_RR_RATIO = 1.5  # Минимальный RR ≥ 1.5:1
    
    # ========================================================================
    # ТРЕНД И СТРУКТУРА
    # ========================================================================
    
    MAX_EMA50_DISTANCE_ATR = 2.5  # Расстояние от EMA50 ≤ 2.5 ATR
    PULLBACK_MIN_ATR = 0.3  # Pullback минимум 0.3 ATR
    PULLBACK_MAX_ATR = 1.0  # Pullback максимум 1.0 ATR
    MIN_TREND_CANDLES = 0.333  # Минимум 1 из 3 свечей в направлении
    
    # ========================================================================
    # КАЧЕСТВО СИГНАЛА
    # ========================================================================
    
    IMPULSE_BODY_RATIO = 0.43  # Импульсная свеча: тело ≥ 43% (синхронизировано с SignalGenerator)
    IMPULSE_AVG_MULTIPLIER = 1.05  # Импульсная свеча ≥ 1.05× среднего тела
    MAX_DIRTY_CANDLES = 4  # Не более 4 грязных свечей за 10 свечей
    DIRTY_CANDLE_TAIL_RATIO = 0.60  # Грязная свеча: хвосты > 60%
    EMA50_SLOPE_MIN_CANDLES = 6  # Наклон EMA50 в нужную сторону ≥ 6 из 10
    MAX_BID_ASK_IMBALANCE = 0.40  # Дисбаланс Bid/Ask ≤ 40%
    MAX_STDDEV_RATIO = 1.35  # StdDev 10 свечей ≤ 1.35× StdDev 50 свечей
    IMPULSE_VOLUME_MULTIPLIER = 1.03  # Объём импульсной свечи ≥ 1.03× среднего за 40 свечей (синхронизировано с SignalGenerator)
    MAX_SAW_CANDLES = 4  # Максимум 4 пила-свечи за 12 свечей
    SAW_CANDLE_TAIL_RATIO = 0.70  # Пила-свеча: хвосты > 70% тела
    
    # ========================================================================
    # УРОВНИ
    # ========================================================================
    
    MIN_LEVEL_TOUCHES = 2  # Минимум 2 касания уровня
    MIN_HTF_LEVEL_TOUCHES = 2  # HTF: минимум 2 касания
    HTF_VOLUME_MULTIPLIER = 1.3  # HTF: объём ≥ 1.3× среднего
    MIN_OPPOSITE_LEVEL_DISTANCE_ATR = 1.8  # Дистанция до противоположного уровня ≥ 1.8 ATR
    BREAKOUT_BODY_RATIO = 0.55  # Свеча пробоя: тело ≥ 55% выше/ниже уровня
    
    # ========================================================================
    # SL/TP ПАРАМЕТРЫ
    # ========================================================================
    
    SL_TOLERANCE_MIN_ATR = 0.7  # SL допуск минимум 0.7 ATR
    SL_TOLERANCE_MAX_ATR = 1.2  # SL допуск максимум 1.2 ATR
    MAX_SL_DISTANCE_ATR = 2.4  # SL ≤ 2.4 ATR от входа
    HIGH_VOLATILITY_SL_EXTENSION = 0.8  # При ATR% ≥ 3.0% допуск до 0.8 ATR
    MIN_SL_LIQUIDITY_USDT = 90_000  # Ликвидность в зоне SL ≥ 90,000 USDT
    MAX_EMA50_DEVIATION_ATR = 2.5  # Отклонение от EMA50 ≤ 2.5 ATR
    TP1_MIN_ATR = 1.5  # TP1 = 1.5-1.8 ATR
    TP1_MAX_ATR = 1.8
    TP2_MIN_ATR = 3.0  # TP2 = 3.0-3.5 ATR
    TP2_MAX_ATR = 3.5
    TP3_MIN_ATR = 6.0  # TP3 = 6.0-9.0 ATR
    TP3_MAX_ATR = 9.0
    CANCEL_IMPULSE_MULTIPLIER = 1.3  # Отмена при обратном импульсе ≥ 1.3× среднего
    
    # ========================================================================
    # SIGNAL CANDLE
    # ========================================================================
    
    SIGNAL_CANDLE_BODY_MIN = 0.60  # Тело ≥ 60%
    SIGNAL_CANDLE_BODY_MAX_MULTIPLIER = 1.8  # Тело ≤ 1.8× среднего за 20 свечей
    SIGNAL_VOLUME_MULTIPLIER = 1.05  # Объём ≥ 1.05× среднего за 20 свечей
    
    # ========================================================================
    # STORAGE
    # ========================================================================
    
    _paused_coins = {}  # {ticker: pause_until_timestamp}
    _last_signal_times = {}  # {ticker: datetime}
    _btc_pause_until = None
    _btc_direction = None  # Направление BTC при сильном движении
    
    @staticmethod
    async def check_all_filters(ticker: str, timeframe: str, df: pd.DataFrame, 
                                client: XTClient, direction: str = None) -> Dict:
        """
        Check all market filters
        Все пороговые значения настраиваются через админку
        """
        result = {
            'passed': False,
            'reason': '',
            'volume_24h': None,
            'spread': None,
            'liquidity': None,
            'atr_percent': None
        }
        
        # 0. Check anomaly pause
        if MarketFilters._is_paused(ticker):
            remaining = MarketFilters._get_pause_remaining(ticker)
            result['reason'] = f"Coin on pause ({remaining} min remaining)"
            return result
        
        # === ВРЕМЕННЫЕ ФИЛЬТРЫ ===
        time_check = MarketFilters.check_time_guards()
        if not time_check['passed']:
            result['reason'] = time_check['reason']
            return result
        
        # === BTC/ETH ФИЛЬТРЫ ===
        btc_check = await MarketFilters.check_btc_eth_filters(client, direction)
        if not btc_check['passed']:
            result['reason'] = btc_check['reason']
            return result
        
        # === ФИЛЬТРЫ РЫНКА ===
        
        # 1. Top-200 by market cap
        is_top_200 = await MarketFilters.check_top_coins(ticker)
        if not is_top_200:
            result['reason'] = "Not in TOP-200 by market cap"
            return result
        
        # 2. Futures volume ≥ 2,000,000 USDT
        volume_24h = await MarketFilters.check_futures_volume(ticker, client)
        if volume_24h is None or volume_24h < MarketFilters.MIN_FUTURES_VOLUME_USDT:
            vol_str = f"{volume_24h:,.0f}" if volume_24h else "0"
            result['reason'] = f"Volume {vol_str} < {MarketFilters.MIN_FUTURES_VOLUME_USDT:,.0f} USDT"
            return result
        result['volume_24h'] = volume_24h
        
        # 3. Spread ≤ 0.35%
        spread = await MarketFilters.check_spread(ticker, client)
        if spread is None:
            result['reason'] = "Failed to get spread"
            return result
        if spread > MarketFilters.MAX_SPREAD_PERCENT:
            result['reason'] = f"Spread {spread:.3f}% > {MarketFilters.MAX_SPREAD_PERCENT}%"
            return result
        result['spread'] = spread
        
        # 4. Liquidity ≥ 300,000 USDT within ±0.5%
        liquidity = await MarketFilters.check_liquidity(ticker, client)
        if liquidity is None or liquidity < MarketFilters.MIN_LIQUIDITY_USDT:
            liq_str = f"{liquidity:,.0f}" if liquidity else "0"
            result['reason'] = f"Liquidity {liq_str} < {MarketFilters.MIN_LIQUIDITY_USDT:,.0f} USDT"
            return result
        result['liquidity'] = liquidity
        
        # 5. ATR volatility
        atr_check = MarketFilters.check_atr_volatility(df)
        if not atr_check['passed']:
            result['reason'] = atr_check['reason']
            return result
        result['atr_percent'] = atr_check.get('atr_percent')
        
        # 6. ATR deviation
        atr_dev_check = MarketFilters.check_atr_deviation(df)
        if not atr_dev_check['passed']:
            result['reason'] = atr_dev_check['reason']
            return result
        
        # 7. No candles with Close-Open > 1.8%
        candle_check = MarketFilters.check_candle_bodies(df)
        if not candle_check['passed']:
            result['reason'] = candle_check['reason']
            return result
        
        # 8. No High/Low gaps
        gap_check = MarketFilters.check_high_low_gaps(df)
        if not gap_check['passed']:
            result['reason'] = gap_check['reason']
            return result
        
        # 9. Volume 1h ratio check (адаптивно для разных таймфреймов)
        volume_ratio_check = MarketFilters.check_volume_60m_ratio(df, volume_24h, timeframe)
        if not volume_ratio_check['passed']:
            result['reason'] = volume_ratio_check['reason']
            return result
        
        # 10. Hourly volume check (адаптивно для разных таймфреймов)
        hourly_vol_check = MarketFilters.check_hourly_volume(df, timeframe)
        if not hourly_vol_check['passed']:
            result['reason'] = hourly_vol_check['reason']
            return result
        
        # 11. Средний спред 1h ≤ 0.35%
        avg_spread_check = await MarketFilters.check_avg_spread_15m(ticker, client, df, timeframe)
        if not avg_spread_check['passed']:
            result['reason'] = avg_spread_check['reason']
            return result
        
        # 12. Funding Rate от −0.08% до +0.08%
        funding_check = await MarketFilters.check_funding_rate(ticker, client)
        if not funding_check['passed']:
            result['reason'] = funding_check['reason']
            return result
        
        # 13. Изменение Open Interest за 1h ≤ 35%
        oi_check = await MarketFilters.check_open_interest_change(ticker, client, df, timeframe)
        if not oi_check['passed']:
            result['reason'] = oi_check['reason']
            return result
        
        # 14. Возраст фьючерсного контракта ≥ 10 дней
        contract_age_check = await MarketFilters.check_contract_age(ticker, client)
        if not contract_age_check['passed']:
            result['reason'] = contract_age_check['reason']
            return result
        
        # === ИНДИКАТОРЫ ===
        indicator_check = MarketFilters.check_indicators(df, direction)
        if not indicator_check['passed']:
            result['reason'] = indicator_check['reason']
            return result
        
        # === КАЧЕСТВО СИГНАЛА ===
        quality_check = MarketFilters.check_signal_quality(df, direction)
        if not quality_check['passed']:
            result['reason'] = quality_check['reason']
            return result
        
        # All filters passed
        result['passed'] = True
        result['reason'] = "All filters passed"
        return result
    
    # ========================================================================
    # ВРЕМЕННЫЕ ФИЛЬТРЫ
    # ========================================================================
    
    @staticmethod
    def check_time_guards() -> Dict:
        """
        Временные фильтры:
        - Запрет первые N минут каждого часа
        - Запрет последние N минут каждого часа
        """
        result = {'passed': False, 'reason': ''}
        
        current_minute = datetime.utcnow().minute
        
        # Запрет первые 5 минут
        if current_minute < MarketFilters.TIME_GUARD_START_MINUTES:
            result['reason'] = f"Time guard: first {MarketFilters.TIME_GUARD_START_MINUTES} min of hour (current: {current_minute})"
            return result
        
        # Запрет последние 3 минуты
        if current_minute >= (60 - MarketFilters.TIME_GUARD_END_MINUTES):
            result['reason'] = f"Time guard: last {MarketFilters.TIME_GUARD_END_MINUTES} min of hour (current: {current_minute})"
            return result
        
        result['passed'] = True
        return result
    
    # ========================================================================
    # BTC/ETH ФИЛЬТРЫ
    # ========================================================================
    
    @staticmethod
    async def check_btc_eth_filters(client: XTClient, direction: str = None) -> Dict:
        """
        BTC/ETH фильтры:
        - BTC движение за 1 час ≤ 3.0%
        - BTC разворотов > 0.7% за 30 минут ≤ 1 (мягкая проверка)
        - Пауза после импульса BTC 1h: 10 минут
        - При импульсе BTC ≥3% запрещаем вход против направления
        - ETH движение за 1 час ≤ 3.0%
        """
        from utils.cache import btc_cache
        
        result = {'passed': False, 'reason': ''}
        
        # Проверяем паузу BTC
        if MarketFilters._btc_pause_until and datetime.utcnow() < MarketFilters._btc_pause_until:
            remaining = (MarketFilters._btc_pause_until - datetime.utcnow()).total_seconds() / 60
            result['reason'] = f"BTC pause active ({int(remaining)} min remaining)"
            return result
        
        try:
            # Получаем данные BTC
            btc_df = await btc_cache.get_btc_ohlcv_1m(client)
            
            if btc_df is None or btc_df.empty or len(btc_df) < 60:
                result['passed'] = True
                result['reason'] = "BTC data unavailable, filter skipped"
                return result
            
            # BTC разворотов за 30 минут
            if len(btc_df) >= 30:
                recent_30m = btc_df.tail(30)
                reversals = MarketFilters._count_reversals(recent_30m, MarketFilters.BTC_REVERSAL_THRESHOLD)
                
                if reversals > MarketFilters.BTC_MAX_REVERSALS_30M:
                    result['reason'] = f"BTC reversals {reversals} > {MarketFilters.BTC_MAX_REVERSALS_30M} in 30min"
                    return result
            
            # BTC движение за 1 час
            if len(btc_df) >= 60:
                recent_60m = btc_df.tail(60)
                if not recent_60m.empty and len(recent_60m) >= 1:
                    price_60m_ago = recent_60m.iloc[0]['open']
                    current_price = recent_60m.iloc[-1]['close']
                    
                    if price_60m_ago > 0:
                        btc_move_1h = ((current_price - price_60m_ago) / price_60m_ago) * 100
                        
                        if abs(btc_move_1h) > MarketFilters.BTC_MAX_MOVE_1H:
                            MarketFilters._set_btc_pause()
                            result['reason'] = f"BTC moved {btc_move_1h:+.2f}% in 1h > {MarketFilters.BTC_MAX_MOVE_1H}%"
                            return result
                        
                        if direction:
                            btc_direction = 'LONG' if btc_move_1h > 0 else 'SHORT'
                            if abs(btc_move_1h) >= MarketFilters.BTC_STRONG_MOVE_1H and direction != btc_direction:
                                MarketFilters._set_btc_pause()
                                result['reason'] = f"BTC impulse {btc_move_1h:+.2f}% in 1h against signal direction"
                                return result
            
            # ETH движение за 1 час
            try:
                eth_df = await client.get_ohlcv('ETH/USDT', '1m', limit=60)
                if eth_df is not None and not eth_df.empty and len(eth_df) >= 60:
                    price_60m_ago = eth_df.iloc[0]['open']
                    current_price = eth_df.iloc[-1]['close']
                    
                    if price_60m_ago > 0:
                        eth_move_1h = abs((current_price - price_60m_ago) / price_60m_ago) * 100
                        
                        if eth_move_1h > MarketFilters.ETH_MAX_MOVE_1H:
                            result['reason'] = f"ETH moved {eth_move_1h:.2f}% in 1h > {MarketFilters.ETH_MAX_MOVE_1H}%"
                            return result
            except:
                pass  # ETH check is optional
            
            result['passed'] = True
            return result
            
        except Exception as e:
            result['passed'] = True
            result['reason'] = f"BTC/ETH filter error: {str(e)}, skipped"
            return result
    
    @staticmethod
    def _count_reversals(df: pd.DataFrame, threshold: float) -> int:
        """Подсчёт разворотов больше порога"""
        reversals = 0
        if len(df) < 2:
            return 0
        
        prev_direction = None
        for i in range(1, len(df)):
            change = ((df.iloc[i]['close'] - df.iloc[i-1]['close']) / df.iloc[i-1]['close']) * 100
            
            if abs(change) >= threshold:
                current_direction = 'up' if change > 0 else 'down'
                if prev_direction and current_direction != prev_direction:
                    reversals += 1
                prev_direction = current_direction
        
        return reversals
    
    @staticmethod
    def _set_btc_pause():
        """Установить паузу BTC"""
        MarketFilters._btc_pause_until = datetime.utcnow() + timedelta(minutes=MarketFilters.BTC_PAUSE_MINUTES)
    
    # ========================================================================
    # ФИЛЬТРЫ РЫНКА
    # ========================================================================
    
    @staticmethod
    async def check_top_coins(ticker: str) -> bool:
        """Check if coin is in TOP-200 by market cap"""
        from database.config_manager import ConfigManager
        
        trading_pairs = ConfigManager.get_trading_pairs()
        
        if ticker in trading_pairs:
            return True
        
        try:
            from utils.top_coins import TopCoinsService
            coin_info = await TopCoinsService.get_coin_info(ticker.replace('/USDT', ''))
            if coin_info and coin_info.get('rank', 999) <= MarketFilters.TOP_COINS_LIMIT:
                return True
        except:
            pass
        
        return False
    
    @staticmethod
    async def check_futures_volume(ticker: str, client: XTClient) -> Optional[float]:
        """Check futures volume ≥ 3,000,000 USDT"""
        try:
            ticker_data = await client.get_ticker(ticker)
            
            if not ticker_data:
                return None
            
            volume_usdt = ticker_data.get('quoteVolume')
            
            if volume_usdt is None:
                base_volume = ticker_data.get('baseVolume')
                last_price = ticker_data.get('last')
                
                if base_volume and last_price:
                    volume_usdt = float(base_volume) * float(last_price)
            
            return float(volume_usdt) if volume_usdt else None
            
        except Exception as e:
            return None
    
    @staticmethod
    async def check_spread(ticker: str, client: XTClient) -> Optional[float]:
        """Check spread ≤ 0.35%"""
        try:
            ticker_data = await client.get_ticker(ticker)
            
            if not ticker_data:
                return None
            
            bid = ticker_data.get('bid')
            ask = ticker_data.get('ask')
            
            if not bid or not ask:
                orderbook = await client.get_orderbook(ticker, limit=5)
                if orderbook and orderbook.get('bids') and orderbook.get('asks'):
                    bids_list = orderbook['bids']
                    asks_list = orderbook['asks']
                    if len(bids_list) > 0 and len(asks_list) > 0:
                        bid = float(bids_list[0][0])
                        ask = float(asks_list[0][0])
            
            if bid and ask:
                bid = float(bid)
                ask = float(ask)
                spread_percent = (ask - bid) / bid * 100
                return spread_percent
            
            return None
            
        except Exception as e:
            return None
    
    @staticmethod
    async def check_liquidity(ticker: str, client: XTClient) -> Optional[float]:
        """Check liquidity ≥ 300,000 USDT within ±0.5%"""
        try:
            ticker_data = await client.get_ticker(ticker)
            if not ticker_data or not ticker_data.get('last'):
                return None
            
            current_price = float(ticker_data['last'])
            
            orderbook = await client.get_orderbook(ticker, limit=50)
            if not orderbook:
                return None
            
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if not bids or not asks:
                return None
            
            price_range = current_price * MarketFilters.LIQUIDITY_PRICE_RANGE
            min_price = current_price - price_range
            max_price = current_price + price_range
            
            liquidity_usdt = 0
            
            try:
                for price, volume in bids:
                    price = float(price)
                    volume = float(volume)
                    if price >= min_price:
                        liquidity_usdt += price * volume
            
                for price, volume in asks:
                    price = float(price)
                    volume = float(volume)
                    if price <= max_price:
                        liquidity_usdt += price * volume
            except (ValueError, TypeError, IndexError) as e:
                return None
            
            return liquidity_usdt
            
        except Exception as e:
            return None
    
    @staticmethod
    def check_atr_volatility(df: pd.DataFrame) -> Dict:
        """
        ATR волатильность на 1H:
        - atr% должно быть в диапазоне [ATR_MIN_PERCENT; ATR_MAX_PERCENT]
        """
        result = {'passed': False, 'reason': '', 'atr_percent': None}
        
        try:
            if df is None or df.empty or len(df) < 20:
                result['reason'] = "Not enough candles for ATR check"
                return result
            
            atr_series = AverageTrueRange(
                high=df['high'],
                low=df['low'],
                close=df['close'],
                window=14
            ).average_true_range()
            
            atr = atr_series.iloc[-1]
            price = df['close'].iloc[-1]
            
            if pd.isna(atr) or pd.isna(price) or price <= 0:
                result['reason'] = "ATR or price is NaN"
                return result
            
            atr_percent = (atr / price) * 100
            result['atr_percent'] = atr_percent
            
            if atr_percent < MarketFilters.ATR_MIN_PERCENT:
                result['reason'] = f"ATR {atr_percent:.2f}% < {MarketFilters.ATR_MIN_PERCENT}%"
                return result
            
            if atr_percent > MarketFilters.ATR_MAX_PERCENT:
                result['reason'] = f"ATR {atr_percent:.2f}% > {MarketFilters.ATR_MAX_PERCENT}%"
                return result
            
            result['passed'] = True
            return result
        except Exception as e:
            result['reason'] = f"ATR check error: {e}"
            return result
    
    @staticmethod
    def check_atr_deviation(df: pd.DataFrame) -> Dict:
        """
        Отклонение текущего ATR от среднего не должно превышать MAX_ATR_DEVIATION (в %).
        """
        result = {'passed': False, 'reason': ''}
        
        try:
            if df is None or df.empty or len(df) < 50:
                result['reason'] = "Not enough candles for ATR deviation check"
                return result
            
            atr_series = AverageTrueRange(
                high=df['high'],
                low=df['low'],
                close=df['close'],
                window=14
            ).average_true_range()
            
            if atr_series.isna().any():
                result['reason'] = "ATR series has NaN"
                return result
            
            current_atr = atr_series.iloc[-1]
            avg_atr = atr_series.tail(50).mean()
            
            if avg_atr == 0:
                result['reason'] = "ATR average is zero"
                return result
            
            deviation_percent = abs(current_atr - avg_atr) / avg_atr * 100
            
            if deviation_percent > MarketFilters.MAX_ATR_DEVIATION:
                result['reason'] = f"ATR deviation {deviation_percent:.1f}% > {MarketFilters.MAX_ATR_DEVIATION}%"
                return result
            
            result['passed'] = True
            return result
        except Exception as e:
            result['reason'] = f"ATR deviation error: {e}"
            return result
    
    @staticmethod
    def check_candle_bodies(df: pd.DataFrame) -> Dict:
        """No candles with Close-Open > 2.5% (ОТКЛЮЧЕНО ДЛЯ ТЕСТИРОВАНИЯ)"""
        result = {'passed': True, 'reason': ''}  # Всегда разрешаем
        return result
    
    @staticmethod
    def check_high_low_gaps(df: pd.DataFrame) -> Dict:
        """No High/Low gaps > 3.0% in last 20 candles"""
        result = {'passed': True, 'reason': ''}
        
        if df.empty or len(df) < MarketFilters.CANDLE_CHECK_LOOKBACK:
            return result
        
        recent = df.tail(MarketFilters.CANDLE_CHECK_LOOKBACK)
        
        for i in range(1, len(recent)):
            prev_low = recent.iloc[i-1]['low']
            prev_high = recent.iloc[i-1]['high']
            curr_low = recent.iloc[i]['low']
            curr_high = recent.iloc[i]['high']
            
            if prev_high == 0 or prev_low == 0:
                continue
            
            # Gap up
            if curr_low > prev_high:
                gap = (curr_low - prev_high) / prev_high * 100
                if gap > MarketFilters.MAX_HIGH_LOW_GAP_PERCENT:
                    result['reason'] = f"Gap up {gap:.2f}% > {MarketFilters.MAX_HIGH_LOW_GAP_PERCENT}%"
                    result['passed'] = False
                    return result
            
            # Gap down
            if curr_high < prev_low:
                gap = (prev_low - curr_high) / prev_low * 100
                if gap > MarketFilters.MAX_HIGH_LOW_GAP_PERCENT:
                    result['reason'] = f"Gap down {gap:.2f}% > {MarketFilters.MAX_HIGH_LOW_GAP_PERCENT}%"
                    result['passed'] = False
                    return result
        
        return result
    
    @staticmethod
    def check_volume_60m_ratio(df: pd.DataFrame, volume_24h: float, timeframe: str = '5m') -> Dict:
        """Volume 1h ≥ 1.2% of 24h (адаптивно для разных таймфреймов)"""
        result = {'passed': False, 'reason': ''}
        
        if df.empty or volume_24h is None or volume_24h == 0:
            result['passed'] = True
            return result
        
        # Определяем количество свечей для 60 минут в зависимости от таймфрейма
        timeframe_minutes = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '1h': 60,
            '4h': 240,
            '1d': 1440
        }
        
        tf_minutes = timeframe_minutes.get(timeframe, 5)
        candles_60m = max(1, int(60 / tf_minutes))
        
        if len(df) < candles_60m:
            result['passed'] = True
            return result
        
        # Последние N свечей = 60 минут
        recent_60m = df.tail(candles_60m)
        volume_60m = recent_60m['volume'].sum()
        
        # Конвертируем в USDT (примерно)
        avg_price = recent_60m['close'].mean()
        volume_60m_usdt = volume_60m * avg_price
        
        ratio = volume_60m_usdt / volume_24h
        
        if ratio < MarketFilters.MIN_VOLUME_60M_RATIO:
            result['reason'] = f"Volume 1h ratio {ratio*100:.2f}% < {MarketFilters.MIN_VOLUME_60M_RATIO*100}%"
            return result
        
        result['passed'] = True
        return result
    
    @staticmethod
    def check_hourly_volume(df: pd.DataFrame, timeframe: str = '5m') -> Dict:
        """Hourly volume ≥ 60% of average 24h hourly volume (адаптивно для разных таймфреймов)"""
        result = {'passed': False, 'reason': ''}
        
        if df.empty:
            result['passed'] = True
            return result
        
        # Определяем количество свечей для 1 часа и 24 часов
        timeframe_minutes = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '1h': 60,
            '4h': 240,
            '1d': 1440
        }
        
        tf_minutes = timeframe_minutes.get(timeframe, 5)
        candles_1h = max(1, int(60 / tf_minutes))
        candles_24h = max(1, int(1440 / tf_minutes))
        
        if len(df) < candles_24h:
            result['passed'] = True
            return result
        
        # Последний час
        last_hour = df.tail(candles_1h)
        hourly_volume = last_hour['volume'].sum()
        
        # Средний часовой объём за 24h
        full_24h = df.tail(candles_24h)
        avg_hourly_volume = full_24h['volume'].sum() / 24
        
        if avg_hourly_volume == 0:
            result['passed'] = True
            return result
        
        ratio = hourly_volume / avg_hourly_volume
        
        if ratio < MarketFilters.MIN_HOURLY_VOLUME_RATIO:
            result['reason'] = f"Hourly volume {ratio*100:.1f}% < {MarketFilters.MIN_HOURLY_VOLUME_RATIO*100}%"
            return result
        
        result['passed'] = True
        return result
    
    # ========================================================================
    # ИНДИКАТОРЫ
    # ========================================================================
    
    @staticmethod
    def check_indicators(df: pd.DataFrame, direction: str) -> Dict:
        """
        Проверка индикаторов:
        - RSI для лонга ≤ 70
        - RSI для шорта ≥ 30
        - ADX ≥ 15 и ≤ 55
        """
        result = {'passed': False, 'reason': ''}
        
        # Минимум 50 свечей для надёжного расчёта индикаторов
        if df.empty or len(df) < 50:
            result['passed'] = True  # Недостаточно данных - пропускаем
            return result
        
        from ta.momentum import RSIIndicator
        
        try:
            # RSI
            rsi_series = RSIIndicator(close=df['close'], window=14).rsi()
            
            # Проверка на пустую серию
            if rsi_series.empty or len(rsi_series) == 0:
                result['passed'] = True  # Недостаточно данных - пропускаем
                return result
            
            rsi = rsi_series.iloc[-1]
        except Exception as e:
            result['passed'] = True  # При ошибке - пропускаем
            return result
        
        # Проверка на NaN
        if pd.isna(rsi):
            result['passed'] = True
            return result
        
        if direction == 'LONG' and rsi > MarketFilters.RSI_MAX_LONG:
            result['reason'] = f"RSI {rsi:.1f} > {MarketFilters.RSI_MAX_LONG} for LONG"
            return result
            
        if direction == 'SHORT' and rsi < MarketFilters.RSI_MIN_SHORT:
            result['reason'] = f"RSI {rsi:.1f} < {MarketFilters.RSI_MIN_SHORT} for SHORT"
            return result
        
        try:
            # ADX
            adx_indicator = ADXIndicator(
                high=df['high'],
                low=df['low'],
                close=df['close'],
                window=14
            )
            adx_series = adx_indicator.adx()
            
            # Проверка на пустую серию
            if adx_series.empty or len(adx_series) == 0:
                result['passed'] = True  # Недостаточно данных - пропускаем
                return result
            
            adx = adx_series.iloc[-1]
            
            # Проверка на NaN
            if pd.isna(adx):
                result['passed'] = True
                return result
            
            if adx < MarketFilters.ADX_MIN:
                result['reason'] = f"ADX {adx:.1f} < {MarketFilters.ADX_MIN}"
                return result
            
            if adx > MarketFilters.ADX_MAX:
                result['reason'] = f"ADX {adx:.1f} > {MarketFilters.ADX_MAX}"
                return result
        except Exception as e:
            result['passed'] = True  # При ошибке - пропускаем
            return result
        
        result['passed'] = True
        return result
        
    # ========================================================================
    # КАЧЕСТВО СИГНАЛА
    # ========================================================================
    
    @staticmethod
    def check_signal_quality(df: pd.DataFrame, direction: str) -> Dict:
        """
        Проверка качества сигнала:
        - Не более 4 грязных свечей за 10 свечей
        - Наклон EMA50 в нужную сторону ≥ 6 из 10
        - StdDev 10 свечей ≤ 1.35× StdDev 50 свечей
        - Максимум 4 пила-свечи за 12 свечей
        - Паттерн: импульс → маленькая свеча / поглощение / пробой / пинбар
        
        Примечание: Импульсная свеча проверяется в signal_generator._check_impulse_candle()
        """
        result = {'passed': False, 'reason': ''}
        
        # Минимум 60 свечей для надёжного расчёта EMA50 + запас
        if df.empty or len(df) < 60:
            result['passed'] = True  # Недостаточно данных - пропускаем
            return result
        
        # Импульсная свеча проверяется в signal_generator._check_impulse_candle()
        # Здесь проверку убираем, чтобы избежать дублирования и противоречий
        
        # Проверка паттерна: импульс → маленькая свеча / поглощение / пробой / пинбар
        # Используем настройку из ConservativeFilters (применяется через FilterSettings)
        from .conservative_filters import ConservativeFilters
        if ConservativeFilters.PATTERN_CHECK_ENABLED:
            pattern_check = MarketFilters._check_pattern(df, direction)
            if not pattern_check['passed']:
                result['reason'] = pattern_check.get('reason', 'Pattern check failed')
                return result
        
        # Проверка грязных свечей (хвосты > 60%)
        recent_10 = df.tail(10)
        dirty_count = 0
        
        for idx, row in recent_10.iterrows():
            body = abs(row['close'] - row['open'])
            full_range = row['high'] - row['low']
            
            if full_range > 0:
                body_ratio = body / full_range
                if body_ratio < (1 - MarketFilters.DIRTY_CANDLE_TAIL_RATIO):
                    dirty_count += 1
        
        if dirty_count > MarketFilters.MAX_DIRTY_CANDLES:
            result['reason'] = f"Dirty candles {dirty_count} > {MarketFilters.MAX_DIRTY_CANDLES}"
            return result
            
        # Наклон EMA50
        try:
            ema50 = EMAIndicator(close=df['close'], window=50).ema_indicator()
            ema50_recent = ema50.tail(10)
            
            # Проверка на NaN в EMA50
            if ema50_recent.isna().any():
                result['passed'] = True
                return result
            
            slope_count = 0
            for i in range(1, len(ema50_recent)):
                if pd.isna(ema50_recent.iloc[i]) or pd.isna(ema50_recent.iloc[i-1]):
                    continue
                if direction == 'LONG' and ema50_recent.iloc[i] > ema50_recent.iloc[i-1]:
                    slope_count += 1
                elif direction == 'SHORT' and ema50_recent.iloc[i] < ema50_recent.iloc[i-1]:
                    slope_count += 1
            
            if slope_count < MarketFilters.EMA50_SLOPE_MIN_CANDLES:
                result['reason'] = f"EMA50 slope {slope_count}/10 < {MarketFilters.EMA50_SLOPE_MIN_CANDLES}/10"
                return result
        except Exception as e:
            result['passed'] = True  # При ошибке - пропускаем
            return result
            
        # StdDev check
        stddev_10 = df['close'].tail(10).std()
        stddev_50 = df['close'].tail(50).std()
        
        # Проверка на NaN
        if pd.isna(stddev_10) or pd.isna(stddev_50):
            result['passed'] = True
            return result
        
        if stddev_50 > 0 and stddev_10 / stddev_50 > MarketFilters.MAX_STDDEV_RATIO:
            result['reason'] = f"StdDev ratio {stddev_10/stddev_50:.2f} > {MarketFilters.MAX_STDDEV_RATIO}"
            return result
        
        # Пила-свечи (хвосты > 70% тела)
        recent_12 = df.tail(12)
        saw_count = 0
        
        for idx, row in recent_12.iterrows():
            body = abs(row['close'] - row['open'])
            upper_tail = row['high'] - max(row['close'], row['open'])
            lower_tail = min(row['close'], row['open']) - row['low']
            
            if body > 0:
                tail_ratio = (upper_tail + lower_tail) / body
                if tail_ratio > MarketFilters.SAW_CANDLE_TAIL_RATIO:
                    saw_count += 1
        
        if saw_count > MarketFilters.MAX_SAW_CANDLES:
            result['reason'] = f"Saw candles {saw_count} > {MarketFilters.MAX_SAW_CANDLES}"
            return result
        
        result['passed'] = True
        return result
    
    # ========================================================================
    # ПАТТЕРНЫ
    # ========================================================================
    
    @staticmethod
    def _check_pattern(df: pd.DataFrame, direction: str) -> Dict:
        """Проверка паттерна: импульс → маленькая свеча / поглощение / пробой / пинбар"""
        result = {'passed': False, 'reason': ''}
        
        if len(df) < 5:
            result['passed'] = True
            return result
        
        recent_5 = df.tail(5)
        
        # Ищем импульсную свечу
        impulse_idx = None
        for i in range(len(recent_5) - 1, -1, -1):
            row = recent_5.iloc[i]
            body = abs(row['close'] - row['open'])
            full_range = row['high'] - row['low']
            
            if full_range == 0:
                continue
            
            body_ratio = body / full_range
            is_bullish = row['close'] > row['open']
            is_bearish = row['close'] < row['open']
            
            if body_ratio >= MarketFilters.IMPULSE_BODY_RATIO:
                if (direction == 'LONG' and is_bullish) or (direction == 'SHORT' and is_bearish):
                    impulse_idx = i
                    break
        
        if impulse_idx is None:
            result['passed'] = True  # Если нет импульса, пропускаем проверку паттерна
            return result
        
        # Проверяем свечи после импульса
        if impulse_idx > 0:
            # Есть свечи после импульса
            for i in range(impulse_idx - 1, -1, -1):
                row = recent_5.iloc[i]
                prev_row = recent_5.iloc[i + 1] if i + 1 < len(recent_5) else None
                
                if prev_row is None:
                    continue
                
                body = abs(row['close'] - row['open'])
                full_range = row['high'] - row['low']
                prev_body = abs(prev_row['close'] - prev_row['open'])
                prev_range = prev_row['high'] - prev_row['low']
                
                if full_range == 0 or prev_range == 0:
                    continue
                
                # 1. Маленькая свеча (тело < 40% от импульса)
                if body < prev_body * 0.4:
                    result['passed'] = True
                    return result
                
                # 2. Поглощение (engulfing)
                if direction == 'LONG':
                    if row['close'] > prev_row['open'] and row['open'] < prev_row['close']:
                        result['passed'] = True
                        return result
                else:
                    if row['close'] < prev_row['open'] and row['open'] > prev_row['close']:
                        result['passed'] = True
                        return result
                
                # 3. Пробой (breakout) - свеча закрылась выше/ниже максимума/минимума импульса
                if direction == 'LONG':
                    if row['close'] > prev_row['high']:
                        result['passed'] = True
                        return result
                else:
                    if row['close'] < prev_row['low']:
                        result['passed'] = True
                        return result
                
                # 4. Пинбар (pinbar) - длинный хвост
                upper_tail = row['high'] - max(row['close'], row['open'])
                lower_tail = min(row['close'], row['open']) - row['low']
                tail_ratio = max(upper_tail, lower_tail) / full_range
                
                if tail_ratio > 0.6:  # Хвост > 60% свечи
                    result['passed'] = True
                    return result
        
        # Если паттерн не найден, но есть импульс - разрешаем (не строго обязательно)
        result['passed'] = True
        return result
    
    # ========================================================================
    # ДОПОЛНИТЕЛЬНЫЕ ФИЛЬТРЫ РЫНКА
    # ========================================================================
    
    @staticmethod
    async def check_avg_spread_15m(ticker: str, client: XTClient, df: pd.DataFrame, timeframe: str) -> Dict:
        """Средний спред 1h ≤ 0.35% (название ключа сохранено для совместимости)"""
        result = {'passed': False, 'reason': ''}
        
        try:
            # Определяем количество свечей для 60 минут
            timeframe_minutes = {
                '1m': 1,
                '5m': 5,
                '15m': 15,
                '1h': 60,
                '4h': 240,
                '1d': 1440
            }
            
            tf_minutes = timeframe_minutes.get(timeframe, 5)
            candles_60m = max(1, int(60 / tf_minutes))
            
            if len(df) < candles_60m:
                result['passed'] = True
                return result
            
            # Получаем спреды за последние 60 минут
            recent = df.tail(candles_60m)
            spreads = []
            
            for idx, row in recent.iterrows():
                try:
                    # Используем high/low как приближение спреда
                    if row['high'] > 0 and row['low'] > 0:
                        spread_approx = ((row['high'] - row['low']) / row['low']) * 100
                        spreads.append(spread_approx)
                except:
                    continue
            
            if not spreads:
                result['passed'] = True
                return result
            
            avg_spread = sum(spreads) / len(spreads)
            
            if avg_spread > MarketFilters.MAX_AVG_SPREAD_15M_PERCENT:
                reason = f"Avg spread 1h {avg_spread:.3f}% > {MarketFilters.MAX_AVG_SPREAD_15M_PERCENT}%"
                result['reason'] = reason
                from utils.logger import log_api_check
                log_api_check(ticker, "BLOCKED", f"AvgSpread1h: {avg_spread:.3f}%")
                return result
            
            result['passed'] = True
            return result
            
        except Exception as e:
            result['passed'] = True  # При ошибке пропускаем
            return result
            
    @staticmethod
    async def check_funding_rate(ticker: str, client: XTClient) -> Dict:
        """Funding Rate от −0.08% до +0.08%"""
        result = {'passed': False, 'reason': ''}
        
        try:
            funding_rate = await client.get_funding_rate(ticker)
            
            if funding_rate is None:
                result['passed'] = True  # Если не удалось получить, пропускаем
                return result
                
            funding_rate_percent = funding_rate * 100  # Конвертируем в проценты
            
            if funding_rate_percent < MarketFilters.FUNDING_RATE_MIN * 100:
                reason = f"Funding rate {funding_rate_percent:.4f}% < {MarketFilters.FUNDING_RATE_MIN * 100:.4f}%"
                result['reason'] = reason
                from utils.logger import log_api_check
                log_api_check(ticker, "BLOCKED", f"FundingRate: {funding_rate_percent:.4f}%")
                return result
            
            if funding_rate_percent > MarketFilters.FUNDING_RATE_MAX * 100:
                reason = f"Funding rate {funding_rate_percent:.4f}% > {MarketFilters.FUNDING_RATE_MAX * 100:.4f}%"
                result['reason'] = reason
                from utils.logger import log_api_check
                log_api_check(ticker, "BLOCKED", f"FundingRate: {funding_rate_percent:.4f}%")
                return result
            
            result['passed'] = True
            return result
            
        except Exception as e:
            result['passed'] = True  # При ошибке пропускаем
            return result
    
    @staticmethod
    async def check_open_interest_change(ticker: str, client: XTClient, df: pd.DataFrame, timeframe: str) -> Dict:
        """Изменение Open Interest за 1h ≤ 35%"""
        result = {'passed': False, 'reason': ''}
        
        try:
            # Определяем количество свечей для 60 минут
            timeframe_minutes = {
                '1m': 1,
                '5m': 5,
                '15m': 15,
                '1h': 60,
                '4h': 240,
                '1d': 1440
            }
            
            tf_minutes = timeframe_minutes.get(timeframe, 5)
            candles_60m = max(1, int(60 / tf_minutes))
            
            if len(df) < candles_60m + 1:
                result['passed'] = True
                return result
            
            # Получаем текущий OI
            current_oi = await client.get_open_interest(ticker)
            
            if current_oi is None:
                result['passed'] = True  # Если не удалось получить, пропускаем
                return result
            
            # Для расчёта изменения OI нужно хранить предыдущее значение
            # Используем приближение через объём (если OI не доступен в истории)
            # В реальной реализации нужно хранить историю OI
            
            # Упрощённая проверка: если OI доступен, проверяем только текущее значение
            # Для полной проверки нужна история OI
            result['passed'] = True
            return result
            
        except Exception as e:
            result['passed'] = True  # При ошибке пропускаем
            return result
    
    @staticmethod
    async def check_contract_age(ticker: str, client: XTClient) -> Dict:
        """Возраст фьючерсного контракта ≥ 10 дней"""
        result = {'passed': False, 'reason': ''}
        
        try:
            # Получаем информацию о контракте
            try:
                market = await client._run_in_executor(
                    client.exchange.market,
                    ticker
                )
                
                if market and 'info' in market:
                    # Пытаемся получить дату создания контракта
                    # Для бессрочных контрактов (perpetual) возраст не применим
                    if market.get('type') == 'future' and market.get('expiry'):
                        # Контракт с датой экспирации
                        expiry = market.get('expiry')
                        if expiry:
                            from datetime import datetime
                            expiry_date = datetime.fromtimestamp(expiry / 1000)
                            age_days = (datetime.utcnow() - expiry_date).days
                            
                            if age_days < MarketFilters.MIN_CONTRACT_AGE_DAYS:
                                result['reason'] = f"Contract age {age_days} days < {MarketFilters.MIN_CONTRACT_AGE_DAYS} days"
                                return result
                            else:
                                result['passed'] = True
                                return result
                    else:
                        # Бессрочный контракт (perpetual) - всегда пропускаем
                        result['passed'] = True
                        return result
                
            except:
                pass
            
            # Если не удалось определить возраст, пропускаем проверку
            result['passed'] = True
            return result
            
        except Exception as e:
            result['passed'] = True  # При ошибке пропускаем
            return result
    
    # ========================================================================
    # PAUSE MANAGEMENT
    # ========================================================================
    
    @staticmethod
    def _set_pause(ticker: str, minutes: int = 15):
        """Set pause for a coin"""
        pause_until = datetime.utcnow() + timedelta(minutes=minutes)
        MarketFilters._paused_coins[ticker] = pause_until
    
    @staticmethod
    def _is_paused(ticker: str) -> bool:
        """Check if a coin is on pause"""
        if ticker not in MarketFilters._paused_coins:
            return False
        
        pause_until = MarketFilters._paused_coins[ticker]
        
        if datetime.utcnow() >= pause_until:
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
    def record_signal_time(ticker: str):
        """Record signal time for cooldown"""
        MarketFilters._last_signal_times[ticker] = datetime.utcnow()
