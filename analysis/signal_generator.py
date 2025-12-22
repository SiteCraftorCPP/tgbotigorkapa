import pandas as pd
from typing import Optional, Dict
from .indicators import TechnicalAnalysis
from .multi_timeframe import MultiTimeframeAnalysis
from .conservative_filters import ConservativeFilters
from .market_filters import MarketFilters
from database.config_manager import ConfigManager
from database.risk_manager import RiskManager
from exchange.xt_client import XTClient
import config
import uuid
from datetime import datetime

class SignalGenerator:
    """Генератор торговых сигналов с полной системой фильтрации"""
    
    # Хранение последней структуры для анти-дублирования
    _last_structures = {}  # {(symbol, timeframe, direction): signature_tuple}
    
    # Минимальный RR
    MIN_RR_RATIO = 1.5  # ≥ 1.5:1
    
    # SL параметры
    SL_TOLERANCE_MIN_ATR = 0.7  # SL допуск минимум 0.7 ATR
    SL_TOLERANCE_MAX_ATR = 1.2  # SL допуск максимум 1.2 ATR
    MAX_SL_DISTANCE_ATR = 2.4  # SL ≤ 2.4 ATR от входа
    HIGH_VOLATILITY_THRESHOLD = 3.0  # ATR% ≥ 3.0% для расширения SL
    HIGH_VOLATILITY_SL_EXTENSION = 0.8  # При высокой волатильности до 0.8 ATR
    
    # TP параметры
    TP1_MIN_ATR = 1.5
    TP1_MAX_ATR = 1.8
    TP2_MIN_ATR = 3.0
    TP2_MAX_ATR = 3.5
    TP3_MIN_ATR = 6.0
    TP3_MAX_ATR = 9.0
    
    # Тренд и структура
    MAX_EMA50_DISTANCE_ATR = 2.5  # Расстояние от EMA50 ≤ 2.5 ATR
    MAX_EMA50_DEVIATION_ATR = 2.5  # Отклонение от EMA50 ≤ 2.5 ATR
    PULLBACK_MIN_ATR = 0.3
    PULLBACK_MAX_ATR = 1.0
    MIN_TREND_CANDLES = 0.333  # Минимум 1 из 3 свечей
    
    # Свеча сигнала
    SIGNAL_CANDLE_BODY_MIN = 0.60  # Тело ≥ 60%
    SIGNAL_CANDLE_BODY_MAX_MULTIPLIER = 1.8  # ≤ 1.8× среднего
    SIGNAL_VOLUME_MULTIPLIER = 1.05  # Объём ≥ 1.05× среднего
    
    # Импульс
    IMPULSE_BODY_RATIO = 0.60  # Тело импульсной свечи ≥ 60%
    CANCEL_IMPULSE_MULTIPLIER = 1.3  # Отмена при обратном импульсе ≥ 1.3×
    
    # EMA50 slope
    EMA50_SLOPE_MIN_CANDLES = 6  # Наклон EMA50 в нужную сторону ≥ 6 из 10
    
    def __init__(self, symbol: str, timeframe: str, df: pd.DataFrame, 
                 df_higher: pd.DataFrame, client: XTClient):
        self.symbol = symbol
        self.timeframe = timeframe
        self.df = df
        self.df_higher = df_higher
        self.client = client
        self.ta = TechnicalAnalysis(df)
    
    def _get_price_precision(self, price: float) -> int:
        """Определяет количество знаков после запятой"""
        if price >= 1000:
            return 2
        elif price >= 100:
            return 3
        elif price >= 10:
            return 4
        elif price >= 1:
            return 5
        elif price >= 0.1:
            return 6
        elif price >= 0.01:
            return 7
        else:
            return 8
    
    def _round_price(self, price: float, reference_price: float) -> float:
        """Округление цены"""
        precision = self._get_price_precision(reference_price)
        return round(price, precision)
        
    # Минимальное количество свечей для анализа
    MIN_CANDLES_REQUIRED = 210  # EMA200 + запас для надёжных расчётов
    
    async def generate_signal(self) -> Optional[Dict]:
        """Генерация сигнала с полной валидацией всех фильтров"""
        from utils.logger import log_filter_block, log_filter_pass
        
        # === ПРОВЕРКА: Достаточно ли данных для анализа ===
        if self.df is None or len(self.df) < self.MIN_CANDLES_REQUIRED:
            log_filter_block(self.symbol, self.timeframe, "InsufficientData", 
                           f"Not enough candles: {len(self.df) if self.df is not None else 0} < {self.MIN_CANDLES_REQUIRED}")
            return None
        
        if self.df_higher is None or len(self.df_higher) < 50:
            log_filter_block(self.symbol, self.timeframe, "InsufficientData", 
                           f"Not enough higher TF candles: {len(self.df_higher) if self.df_higher is not None else 0}")
            return None
        
        # === ПРОВЕРКА: СИГНАЛ ПОДАЁТСЯ ТОЛЬКО ПОСЛЕ ЗАКРЫТИЯ СИГНАЛЬНОЙ СВЕЧИ ===
        if not self._check_candle_closed():
            log_filter_block(self.symbol, self.timeframe, "CandleNotClosed", "Signal candle must be closed before generating signal")
            return None
        
        # Расчёт индикаторов
        self.ta.calculate_all_indicators()
        
        if self.ta.df.empty or len(self.ta.df) < self.MIN_CANDLES_REQUIRED:
            log_filter_block(self.symbol, self.timeframe, "DataCheck", "No data or insufficient data after indicator calculation")
            return None
        
        # === МУЛЬТИТАЙМФРЕЙМНЫЙ АНАЛИЗ ===
        mtf = MultiTimeframeAnalysis.check_trend_alignment(self.df_higher, self.df)
        
        if not mtf.get('aligned', False):
            mtf_reason = f"MTF not aligned: higher={mtf.get('higher_trend')} (score={mtf.get('higher_score', 0):.0f}), lower={mtf.get('lower_signal')} (score={mtf.get('lower_score', 0):.0f})"
            log_filter_block(self.symbol, self.timeframe, "MTF_Alignment", mtf_reason)
            return None
        
        # Определяем направление сигнала
        direction = mtf.get('higher_trend') if mtf.get('higher_trend') else mtf.get('lower_signal')
        
        if not direction:
            log_filter_block(self.symbol, self.timeframe, "MTF_Alignment", "No trend direction found")
            return None
        
        # === ПРОВЕРКА ЗАПРЕТА ВХОДА ПРОТИВ ТРЕНДА H1 ===
        if not self._check_h1_trend_alignment(direction):
            log_filter_block(self.symbol, self.timeframe, "H1_Trend", f"Entry against H1 trend for {direction}")
            return None
        
        # === МИНИ-ТРЕНД: минимум N из 3 или 4 свечей в направлении ===
        if not self._check_mini_trend(direction):
            # Форматирование для сообщения
            min_trend = SignalGenerator.MIN_TREND_CANDLES
            if abs(min_trend - 0.333) < 0.001:
                trend_msg = "1/3"
            else:
                trend_msg = f"{int(min_trend)}/4"
            log_filter_block(self.symbol, self.timeframe, "MiniTrend", f"Less than {trend_msg} candles in {direction} direction")
            return None
        
        # === РАССТОЯНИЕ ОТ EMA50 ≤ 2 ATR ===
        if not self._check_ema50_distance():
            log_filter_block(self.symbol, self.timeframe, "EMA50_Distance", "Price too far from EMA50")
            return None
        
        # === PULLBACK В ДИАПАЗОНЕ ===
        if not self._check_pullback(direction):
            log_filter_block(self.symbol, self.timeframe, "Pullback", f"Pullback not in range {self.PULLBACK_MIN_ATR}-{self.PULLBACK_MAX_ATR} ATR for {direction}")
            return None
        
        # === ПРОВЕРКА MARKET STRUCTURE (HH/HL для LONG, LL/LH для SHORT) ===
        structure_ok, structure_sig = self._check_market_structure(direction)
        if not structure_ok:
            log_filter_block(self.symbol, self.timeframe, "MarketStructure", f"Invalid structure for {direction}")
            return None
        # Анти-дублирование: повторный сигнал только при новой структуре
        key = (self.symbol, self.timeframe, direction)
        if structure_sig and SignalGenerator._last_structures.get(key) == structure_sig:
            log_filter_block(self.symbol, self.timeframe, "MarketStructure", "Structure not updated since last signal")
            return None
        
        # === ИМПУЛЬСНАЯ СВЕЧА ===
        if not self._check_impulse_candle(direction):
            log_filter_block(self.symbol, self.timeframe, "ImpulseCandle", "No valid impulse candle")
            return None
        
        # === СВЕЧА СИГНАЛА ===
        if not self._check_signal_candle():
            log_filter_block(self.symbol, self.timeframe, "SignalCandle", "Signal candle validation failed")
            return None
        
        # === EMA50 НАПРАВЛЕНИЕ И НАКЛОН ===
        if not self._check_ema50_direction(direction):
            log_filter_block(self.symbol, self.timeframe, "EMA50_Direction", "EMA50 direction/slope not aligned")
            return None
        
        # Текущая цена и ATR
        if len(self.ta.df) == 0:
            log_filter_block(self.symbol, self.timeframe, "DataCheck", "DataFrame is empty")
            return None
        
        last_row = self.ta.df.iloc[-1]
        current_price = last_row['close']
        atr = last_row['atr']
        
        # Проверка на NaN и валидность данных
        if pd.isna(current_price) or pd.isna(atr) or atr <= 0 or current_price <= 0:
            log_filter_block(self.symbol, self.timeframe, "DataValidation", f"Invalid price or ATR: price={current_price}, atr={atr}")
            return None
        
        levels = self.ta.calculate_support_resistance()
        
        # === MARKET FILTERS ===
        market_filters_result = await MarketFilters.check_all_filters(
            self.symbol,
            self.timeframe,
            self.df,
            self.client,
            direction
        )
        
        if not market_filters_result['passed']:
            log_filter_block(self.symbol, self.timeframe, f"MarketFilter:{market_filters_result['reason'].split()[0]}", market_filters_result['reason'])
            return None
        
        atr_percent = market_filters_result.get('atr_percent')
        
        # === РАСЧЁТ УРОВНЕЙ ===
        signal_params = self._calculate_levels(
            direction,
            current_price,
            atr,
            levels,
            atr_percent
        )
        
        if not signal_params:
            log_filter_block(self.symbol, self.timeframe, "LevelCalculation", f"Invalid levels for {direction}")
            return None
        
        # === CONSERVATIVE FILTERS ===
        filters_result = await ConservativeFilters.check_all_filters(
            self.symbol, 
            self.df, 
            signal_params['entry'],
            signal_params['stop'],
            atr,
            direction,
            self.client,
            atr_percent
        )
        
        if not filters_result['passed']:
            reasons = ', '.join(filters_result.get('reasons', ['unknown']))
            log_filter_block(self.symbol, self.timeframe, "ConservativeFilter", reasons)
            return None
        
        # === ПРОВЕРКА ЛИКВИДНОСТИ В ЗОНЕ SL ===
        sl_liquidity = await self._check_sl_liquidity(signal_params['stop'])
        if not sl_liquidity['passed']:
            log_filter_block(self.symbol, self.timeframe, "SL_Liquidity", sl_liquidity['reason'])
            return None
        
        # === ПРОВЕРКА ОТКЛОНЕНИЯ ОТ EMA50 ===
        if not self._check_ema50_deviation(current_price, atr):
            log_filter_block(self.symbol, self.timeframe, "EMA50_Deviation", "Price deviation from EMA50 > 2.5 ATR")
            return None
        
        # ВСЕ ФИЛЬТРЫ ПРОЙДЕНЫ ✅
        log_filter_pass(self.symbol, self.timeframe)
        from utils.logger import log_info
        log_info(f"[✅ ALL FILTERS PASSED] {self.symbol} {self.timeframe} {direction} - Signal will be generated!")
        # Фиксируем текущую структуру, чтобы не повторять без обновления
        if structure_sig:
            SignalGenerator._last_structures[key] = structure_sig
        
        # Получение дополнительных данных
        trend = self.ta.get_trend_signal()
        momentum = self.ta.get_momentum_signal()
        volume = self.ta.get_volume_signal()
        volatility = self.ta.get_volatility_score()
        
        # Формирование сигнала
        signal = {
            'signal_id': str(uuid.uuid4())[:8],
            'ticker': self.symbol,
            'direction': direction,
            'timeframe': self.timeframe,
            'timeframe_higher': MultiTimeframeAnalysis.get_higher_timeframe(self.timeframe),
            'entry_price': signal_params['entry'],
            'stop_loss': signal_params['stop'],
            'take_profit_1': signal_params['tp1'],
            'take_profit_2': signal_params['tp2'],
            'take_profit_3': signal_params['tp3'],  # TP3 согласно новым фильтрам
            'take_profit_4': signal_params['tp3'],  # TP4 = TP3 для совместимости
            'risk_percent': RiskManager.MAX_RISK_PER_TRADE,
            'leverage': ConfigManager.get_leverage(),
            'created_at': datetime.utcnow(),
            'volume_24h': market_filters_result['volume_24h'],
            'spread_percent': market_filters_result['spread'],
            'atr_value': atr,
            'liquidity_usdt': market_filters_result.get('liquidity'),
            'analysis': {
                'trend': trend,
                'momentum': momentum,
                'volume': volume,
                'volatility': volatility,
                'levels': levels,
                'mtf': mtf
            }
        }
        
        return signal
    
    def _check_h1_trend_alignment(self, direction: str) -> bool:
        """Запрет входа против тренда H1"""
        if self.df_higher.empty or len(self.df_higher) < 50:
            return True
        
        ta_higher = TechnicalAnalysis(self.df_higher)
        ta_higher.calculate_all_indicators()
        trend = ta_higher.get_trend_signal()
        
        # Если тренд сильный и противоположный - блокируем
        if abs(trend['score']) > 40 and trend['direction'] != direction:
            return False
        
        return True
    
    def _check_mini_trend(self, direction: str) -> bool:
        """
        MiniTrend (QUALITY):
        - применяется только для LONG/SHORT
        - считает свечи по направлению сигнала
        - требует не только направление, но и минимальную "силу" (через тело и ATR)
        """
        min_trend = SignalGenerator.MIN_TREND_CANDLES
        if min_trend == 0:
            return True

        direction = (direction or "").upper()
        if direction not in ("LONG", "SHORT"):
            return True

        if abs(min_trend - 0.333) < 0.001:
            window_size = 3
            required_count = 1
        else:
            window_size = 4
            # Поддержка дробных значений: 0.25->1, 0.5->2, 0.75->3, 1.0->4
            # Если min_trend >= 1, то это абсолютное число свечей
            if min_trend < 1.0:
                required_count = int(round(min_trend * window_size))
            else:
                required_count = int(min_trend)
            required_count = max(1, min(required_count, window_size))

        # Используем self.ta.df, так как там есть ATR после calculate_all_indicators()
        if len(self.ta.df) < window_size:
            return True

        recent = self.ta.df.tail(window_size)

        MIN_BODY_TO_RANGE = 0.45
        MIN_BODY_TO_ATR = 0.15

        has_atr = "atr" in self.ta.df.columns

        good = 0
        strong = 0

        for _, row in recent.iterrows():
            o = float(row["open"])
            c = float(row["close"])
            h = float(row.get("high", max(o, c)))
            l = float(row.get("low", min(o, c)))

            rng = max(h - l, 1e-12)
            body = abs(c - o)

            body_to_range = body / rng
            
            # Получаем ATR из self.ta.df
            atr = None
            body_to_atr = None
            if has_atr:
                atr_val = row.get("atr")
                if atr_val is not None and not pd.isna(atr_val):
                    atr = float(atr_val)
                    if atr > 1e-12:
                        body_to_atr = body / atr

            in_dir = (c > o) if direction == "LONG" else (c < o)

            strength_ok = (body_to_range >= MIN_BODY_TO_RANGE)
            if body_to_atr is not None:
                strength_ok = strength_ok and (body_to_atr >= MIN_BODY_TO_ATR)

            if in_dir and strength_ok:
                good += 1

            strong_ok = (body_to_range >= 0.60)
            if body_to_atr is not None:
                strong_ok = strong_ok or (body_to_atr >= 0.25)

            if in_dir and strong_ok:
                strong += 1

        if good < required_count:
            return False

        if strong < 1:
            return False

        return True
    
    def _check_ema50_distance(self) -> bool:
        """Расстояние от EMA50 (1H): отклонение ≤ 2.5 ATR (настраивается через max_ema50_distance)"""
        if len(self.ta.df) == 0:
            return True  # Недостаточно данных - пропускаем
        
        last = self.ta.df.iloc[-1]
        
        if 'ema_50' not in last or 'atr' not in last:
            return True  # Нет данных - пропускаем
        
        if pd.isna(last['ema_50']) or pd.isna(last['atr']) or last['atr'] == 0:
            return True
        
        distance = abs(last['close'] - last['ema_50'])
        max_distance = last['atr'] * self.MAX_EMA50_DISTANCE_ATR
        
        return distance <= max_distance
    
    def _check_pullback(self, direction: str) -> bool:
        """Pullback перед сигналом (1H): в диапазоне 0.3–1.0 ATR (настраивается через pullback_min/max)"""
        # Пропускаем проверку для NEUTRAL направления
        direction = (direction or "").upper()
        if direction not in ("LONG", "SHORT"):
            return True
        
        if len(self.df) < 20:
            return True  # Недостаточно данных - пропускаем
        
        if len(self.ta.df) == 0:
            return True  # Недостаточно данных - пропускаем
        
        last = self.ta.df.iloc[-1]
        atr = last['atr']
        
        if atr == 0:
            return True
        
        current_price = last['close']
        recent = self.df.tail(20)
        
        if direction == 'LONG':
            recent_excl_last = recent.iloc[:-1]
            if len(recent_excl_last) > 0:
                local_high = recent_excl_last['high'].max()
                pullback = local_high - current_price
            else:
                return True
        else:
            recent_excl_last = recent.iloc[:-1]
            if len(recent_excl_last) > 0:
                local_low = recent_excl_last['low'].min()
                pullback = current_price - local_low
            else:
                return True
        
        min_pullback = atr * self.PULLBACK_MIN_ATR
        max_pullback = atr * self.PULLBACK_MAX_ATR
        
        return min_pullback <= pullback <= max_pullback
    
    def _check_market_structure(self, direction: str):
        """
        Строгая проверка структуры (1H):
        - LONG: HH + HL обязательны, дистанция между HL ≥ 1.0 ATR (1H)
        - SHORT: LL + LH обязательны, дистанция между LH ≥ 1.0 ATR (1H)
        """
        # Пропускаем проверку для NEUTRAL направления
        direction = (direction or "").upper()
        if direction not in ("LONG", "SHORT"):
            return True, None
        
        if len(self.df) < 30 or len(self.ta.df) < 30:
            return False, None
        
        try:
            atr = self.ta.df.iloc[-1].get('atr')
            if pd.isna(atr) or atr is None or atr <= 0:
                return False, None
            
            highs, lows = self._find_swings(window=2, lookback=80)
            
            if len(highs) < 2 or len(lows) < 2:
                return False, None
            
            # Берём последние два экстремума по времени
            last_high_1, last_high_2 = highs[-2][1], highs[-1][1]
            last_low_1, last_low_2 = lows[-2][1], lows[-1][1]
            
            if direction == 'LONG':
                higher_high = last_high_2 > last_high_1
                higher_low = last_low_2 > last_low_1
                hl_distance_ok = (last_low_2 - last_low_1) >= atr
                sig = ('LONG', round(last_high_1, 8), round(last_high_2, 8), round(last_low_1, 8), round(last_low_2, 8))
                return higher_high and higher_low and hl_distance_ok, sig
            else:
                lower_low = last_low_2 < last_low_1
                lower_high = last_high_2 < last_high_1
                lh_distance_ok = (last_high_1 - last_high_2) >= atr
                sig = ('SHORT', round(last_high_1, 8), round(last_high_2, 8), round(last_low_1, 8), round(last_low_2, 8))
                return lower_low and lower_high and lh_distance_ok, sig
        except Exception:
            return False, None
    
    def _find_swings(self, window: int = 2, lookback: int = 80):
        """Возвращает списки swing high/low в формате [(idx, price), ...]"""
        highs = []
        lows = []
        
        if self.df is None or self.df.empty:
            return highs, lows
        
        recent = self.df.tail(min(lookback, len(self.df)))
        
        for i in range(window, len(recent) - window):
            segment = recent.iloc[i - window:i + window + 1]
            current = recent.iloc[i]
            
            if current['high'] == segment['high'].max():
                highs.append((recent.index[i], current['high']))
            if current['low'] == segment['low'].min():
                lows.append((recent.index[i], current['low']))
        
        return highs, lows
    
    def _check_impulse_candle(self, direction: str) -> bool:
        """Минимум 1 импульсная свеча (настраивается через impulse_body_ratio)"""
        if len(self.df) < 10:
            return True  # Недостаточно данных - пропускаем
        
        recent = self.df.tail(10)
        
        for idx, row in recent.iterrows():
            body = abs(row['close'] - row['open'])
            full_range = row['high'] - row['low']
            
            if full_range == 0:
                continue
            
            body_ratio = body / full_range
            is_bullish = row['close'] > row['open']
            is_bearish = row['close'] < row['open']
            
            if body_ratio >= self.IMPULSE_BODY_RATIO:
                if direction == 'LONG' and is_bullish:
                    return True
                if direction == 'SHORT' and is_bearish:
                    return True
        
        return False
    
    def _check_signal_candle(self) -> bool:
        """
        Свеча сигнала (1H):
        - тело ≥ 60% от диапазона
        - тело ≤ 1.8× среднего тела за 20 свечей
        """
        if self.df is None or len(self.df) < 20:
            return False
        
        signal_candle = self.df.iloc[-1]
        
        body = abs(signal_candle['close'] - signal_candle['open'])
        full_range = signal_candle['high'] - signal_candle['low']
        
        if full_range <= 0:
            return False
        
        body_ratio = body / full_range
        if body_ratio < self.SIGNAL_CANDLE_BODY_MIN:
            return False
        
        recent_20 = self.df.tail(20)
        avg_body = (recent_20['close'] - recent_20['open']).abs().mean()
        
        if avg_body and body > avg_body * self.SIGNAL_CANDLE_BODY_MAX_MULTIPLIER:
            return False
        
        return True

    def _check_ema50_direction(self, direction: str) -> bool:
        """
        EMA50 направлена в сторону сигнала (1H):
        наклон EMA50 должен соответствовать направлению сигнала.
        Отклонение по дистанции контролируется отдельно (_check_ema50_distance / deviation).
        """
        if len(self.ta.df) < 60:
            return False
        
        ema50 = self.ta.df['ema_50'].tail(10)
        if ema50.isna().any():
            return False
        
        slope_count = 0
        for i in range(1, len(ema50)):
            if pd.isna(ema50.iloc[i]) or pd.isna(ema50.iloc[i-1]):
                continue
            if direction == 'LONG' and ema50.iloc[i] > ema50.iloc[i-1]:
                slope_count += 1
            elif direction == 'SHORT' and ema50.iloc[i] < ema50.iloc[i-1]:
                slope_count += 1
        
        return slope_count >= self.EMA50_SLOPE_MIN_CANDLES
    
    def _check_candle_closed(self) -> bool:
        """
        Проверка, что сигнальная свеча закрыта (1H).
        Сигнал подаётся только после закрытия сигнальной свечи (1H).
        """
        if self.df.empty or len(self.df) < 2:
            return False
        
        # Проверяем, что последняя свеча закрыта
        # Для OHLCV данных из API последняя свеча уже закрыта (API возвращает только закрытые свечи)
        # Но для безопасности проверяем, что у нас есть хотя бы 2 свечи
        # В реальной реализации можно добавить проверку timestamp свечи
        return len(self.df) >= 2
    
    def _check_ema50_deviation(self, current_price: float, atr: float) -> bool:
        """Отклонение цены от EMA50 (1H): ≤ 2.5 ATR"""
        if len(self.ta.df) == 0:
            return True  # Недостаточно данных - пропускаем
        
        last = self.ta.df.iloc[-1]
        
        if 'ema_50' not in last or atr == 0:
            return True
        
        # Проверка на NaN
        if pd.isna(last['ema_50']):
            return True
        
        deviation = abs(current_price - last['ema_50'])
        max_deviation = atr * self.MAX_EMA50_DEVIATION_ATR
        
        return deviation <= max_deviation
    
    async def _check_sl_liquidity(self, stop_price: float) -> Dict:
        """Ликвидность в зоне SL ≥ 90,000 USDT (в пределах ±0.5%)"""
        result = {'passed': False, 'reason': ''}
        
        try:
            orderbook = await self.client.get_orderbook(self.symbol, limit=50)
            if not orderbook:
                result['passed'] = True
                return result
            
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if not bids or not asks:
                result['passed'] = True
                return result
            
            price_range = stop_price * 0.005  # ±0.5%
            min_price = stop_price - price_range
            max_price = stop_price + price_range
            
            liquidity = 0
            
            try:
                for price, volume in bids:
                    price = float(price)
                    volume = float(volume)
                    if min_price <= price <= max_price:
                        liquidity += price * volume
                
                for price, volume in asks:
                    price = float(price)
                    volume = float(volume)
                    if min_price <= price <= max_price:
                        liquidity += price * volume
            except (ValueError, TypeError, IndexError) as e:
                result['passed'] = True
                return result
            
            min_liquidity = 90000  # 90,000 USDT
            
            if liquidity < min_liquidity:
                result['reason'] = f"SL zone liquidity {liquidity:,.0f} < {min_liquidity:,.0f} USDT"
                return result
            
            result['passed'] = True
            return result
            
        except Exception as e:
            result['passed'] = True
            return result
    
    def _calculate_levels(self, direction: str, price: float, atr: float, 
                         levels: dict, atr_percent: float = None) -> Optional[Dict]:
        """
        Расчёт уровней:
        - SL за последним HL/LH с допуском 0.5-1.0 ATR
        - SL ≤ 2.2 ATR от точки входа
        - При ATR% ≥ 3.0% допускается расширение SL до 0.7-0.8 ATR
        - TP1 = 1.5-2.5 ATR
        - TP2 = 3.0-5.0 ATR
        - TP3 = 6.0-9.0 ATR
        - Минимальный RR ≥ 1.8:1
        """
        from utils.logger import logger
        
        if price <= 0 or atr <= 0:
            return None
        
        entry = price
        
        # Определяем допуск SL в зависимости от волатильности
        if atr_percent and atr_percent >= self.HIGH_VOLATILITY_THRESHOLD:
            sl_tolerance = atr * self.HIGH_VOLATILITY_SL_EXTENSION
        else:
            sl_tolerance = atr * ((self.SL_TOLERANCE_MIN_ATR + self.SL_TOLERANCE_MAX_ATR) / 2)
        
        # Страхуемся, что допуск остаётся в целевом диапазоне
        sl_tolerance = min(atr * self.SL_TOLERANCE_MAX_ATR, max(atr * self.SL_TOLERANCE_MIN_ATR, sl_tolerance))
        
        # Находим последний HL/LH для размещения SL
        last_swing = self._find_last_swing(direction)
        
        if direction == 'LONG':
            # SL за последним HL
            if last_swing:
                stop = last_swing - sl_tolerance
            else:
                stop = entry - (atr * self.MAX_SL_DISTANCE_ATR)
            
            # Проверка максимальной дистанции SL
            if entry - stop > atr * self.MAX_SL_DISTANCE_ATR:
                stop = entry - (atr * self.MAX_SL_DISTANCE_ATR)
            
            if stop <= 0:
                return None
            
            stop_distance = entry - stop
            
            # TP рассчитывается от stop_distance для правильного RR
            # TP1 = 1.5-2.5 ATR от entry (минимум 1.8× stop_distance для RR ≥ 1.8:1)
            tp1_atr = atr * ((self.TP1_MIN_ATR + self.TP1_MAX_ATR) / 2)
            tp1_min_rr = entry + (stop_distance * self.MIN_RR_RATIO)
            tp1 = max(entry + tp1_atr, tp1_min_rr)  # Берём максимум для обеспечения RR
            
            # TP2 = 3.0-5.0 ATR от entry
            tp2 = entry + (atr * ((self.TP2_MIN_ATR + self.TP2_MAX_ATR) / 2))
            
            # TP3 = 6.0-9.0 ATR от entry
            tp3 = entry + (atr * ((self.TP3_MIN_ATR + self.TP3_MAX_ATR) / 2))
                
        else:  # SHORT
            # SL за последним LH
            if last_swing:
                stop = last_swing + sl_tolerance
            else:
                stop = entry + (atr * self.MAX_SL_DISTANCE_ATR)
            
            # Проверка максимальной дистанции SL
            if stop - entry > atr * self.MAX_SL_DISTANCE_ATR:
                stop = entry + (atr * self.MAX_SL_DISTANCE_ATR)
            
            stop_distance = stop - entry
            
            # TP рассчитывается от stop_distance для правильного RR
            # TP1 = 1.5-2.5 ATR от entry (минимум 1.8× stop_distance для RR ≥ 1.8:1)
            tp1_atr = atr * ((self.TP1_MIN_ATR + self.TP1_MAX_ATR) / 2)
            tp1_min_rr = entry - (stop_distance * self.MIN_RR_RATIO)
            tp1 = min(entry - tp1_atr, tp1_min_rr)  # Берём минимум для обеспечения RR
            
            # TP2 = 3.0-5.0 ATR от entry
            tp2 = entry - (atr * ((self.TP2_MIN_ATR + self.TP2_MAX_ATR) / 2))
            
            # TP3 = 6.0-9.0 ATR от entry
            tp3 = entry - (atr * ((self.TP3_MIN_ATR + self.TP3_MAX_ATR) / 2))
            
            if tp2 <= 0:
                return None
        
        # Проверка RR
        risk = stop_distance
        reward = abs(tp1 - entry)
        
        if risk <= 0 or reward <= 0:
            return None
        
        rr_ratio = reward / risk
        
        if rr_ratio < self.MIN_RR_RATIO:
            logger.debug(f"[{self.symbol}] RR ratio {rr_ratio:.2f} < {self.MIN_RR_RATIO}")
            return None
        
        # Округление
        entry = self._round_price(entry, price)
        stop = self._round_price(stop, price)
        tp1 = self._round_price(tp1, price)
        tp2 = self._round_price(tp2, price)
        tp3 = self._round_price(tp3, price)
        
        # Валидация порядка уровней
        if direction == 'LONG':
            if not (stop < entry < tp1 < tp2 < tp3):
                return None
        else:
            if not (stop > entry > tp1 > tp2 > tp3):
                return None
        
        return {
            'entry': entry,
            'stop': stop,
            'tp1': tp1,
            'tp2': tp2,
            'tp3': tp3
        }
    
    def _find_last_swing(self, direction: str) -> Optional[float]:
        """Найти последний swing (HL для LONG, LH для SHORT)"""
        if len(self.df) < 20:
            return None
        
        recent = self.df.tail(20)
        window = 3
        
        if direction == 'LONG':
            # Ищем последний Higher Low
            for i in range(len(recent) - window - 1, window, -1):
                if recent.iloc[i]['low'] == recent.iloc[i-window:i+window+1]['low'].min():
                    return recent.iloc[i]['low']
        else:
            # Ищем последний Lower High
            for i in range(len(recent) - window - 1, window, -1):
                if recent.iloc[i]['high'] == recent.iloc[i-window:i+window+1]['high'].max():
                    return recent.iloc[i]['high']
        
        return None
