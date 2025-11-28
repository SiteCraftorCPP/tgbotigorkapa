import pandas as pd
from typing import Optional, Dict
from .indicators import TechnicalAnalysis
from .multi_timeframe import MultiTimeframeAnalysis
from .conservative_filters import ConservativeFilters
from .market_filters import MarketFilters  # Рыночные фильтры
from database.config_manager import ConfigManager
from database.risk_manager import RiskManager
from exchange.xt_client import XTClient
import config
import uuid
from datetime import datetime

class SignalGenerator:
    """Генератор ультраконсервативных торговых сигналов"""
    
    # Минимальный RR для TP1
    MIN_RR_RATIO = 1.2  # ≥ 1.2:1
    
    # Минимальная дистанция между уровнями (в процентах)
    MIN_LEVEL_DISTANCE_PERCENT = 0.1  # 0.1% минимум
    
    def __init__(self, symbol: str, timeframe: str, df: pd.DataFrame, 
                 df_higher: pd.DataFrame, client: XTClient):
        self.symbol = symbol
        self.timeframe = timeframe
        self.df = df
        self.df_higher = df_higher
        self.client = client
        self.ta = TechnicalAnalysis(df)
    
    def _get_price_precision(self, price: float) -> int:
        """Определяет количество знаков после запятой для округления цены"""
        if price >= 1000:
            return 2  # BTC, ETH - 2 знака
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
            return 8  # Очень дешёвые монеты
    
    def _round_price(self, price: float, reference_price: float) -> float:
        """Округление цены с учётом её величины"""
        precision = self._get_price_precision(reference_price)
        return round(price, precision)
        
    async def generate_signal(self) -> Optional[Dict]:
        """Генерация ультраконсервативного сигнала"""
        from utils.logger import log_filter_block, log_filter_pass
        
        # ФИЛЬТР РИСК-МЕНЕДЖМЕНТА
        can_open, reason = RiskManager.can_open_new_signal(self.symbol)
        if not can_open:
            log_filter_block(self.symbol, self.timeframe, "RiskManager", reason)
            return None
        
        # Расчёт индикаторов
        self.ta.calculate_all_indicators()
        
        if self.ta.df.empty or len(self.ta.df) < 150:
            log_filter_block(self.symbol, self.timeframe, "DataCheck", f"Not enough data: {len(self.ta.df)} candles < 150")
            return None
        
        # МУЛЬТИТАЙМФРЕЙМНЫЙ АНАЛИЗ
        mtf = MultiTimeframeAnalysis.check_trend_alignment(self.df_higher, self.df)
        if not mtf['aligned']:
            mtf_reason = f"Trend not aligned: higher={mtf.get('higher_trend')} (score={mtf.get('higher_score', 0):.0f}), lower={mtf.get('lower_signal')}"
            if mtf.get('is_neutral'):
                mtf_reason += " | Higher TF is neutral but structure check failed"
            log_filter_block(self.symbol, self.timeframe, "MTF_Alignment", mtf_reason)
            return None
        
        direction = mtf['higher_trend']
        
        # ПРОВЕРКА PULLBACK (коррекция к уровню)
        if not MultiTimeframeAnalysis.check_pullback_opportunity(self.df, direction):
            log_filter_block(self.symbol, self.timeframe, "Pullback", f"No pullback opportunity for {direction}")
            return None
        
        # ПРОВЕРКА MARKET STRUCTURE (HH/HL для LONG, LH/LL для SHORT)
        if not self._check_market_structure(direction):
            log_filter_block(self.symbol, self.timeframe, "MarketStructure", f"Invalid structure for {direction}")
            return None
        
        # Получение всех сигналов
        trend = self.ta.get_trend_signal()
        momentum = self.ta.get_momentum_signal()
        volume = self.ta.get_volume_signal()
        volatility = self.ta.get_volatility_score()
        levels = self.ta.calculate_support_resistance()
        
        # Текущая цена
        current_price = self.ta.df.iloc[-1]['close']
        atr = self.ta.df.iloc[-1]['atr']
        
        # Расчёт уровней входа/выхода (с 3 TP, RR ≥ 1.25)
        signal_params = self._calculate_levels(
            direction,
            current_price,
            atr,
            levels
        )
        
        if not signal_params:
            # Детальная причина: проверяем почему уровни не прошли
            stop_distance = atr * 2.0
            rr = (stop_distance * 1.5) / stop_distance if stop_distance > 0 else 0
            atr_pct = (atr / current_price * 100) if current_price > 0 else 0
            log_filter_block(
                self.symbol, self.timeframe, "LevelCalculation", 
                f"Invalid levels for {direction} | Price: {current_price:.6f}, ATR: {atr:.6f} ({atr_pct:.3f}%), Stop dist: {stop_distance:.6f}"
            )
            return None
        
        # === MARKET FILTERS (STRICT) ===
        market_filters_result = await MarketFilters.check_all_filters(
            self.symbol,
            self.timeframe,
            self.df,
            self.client,
            direction  # Pass direction for BTC trend filter
        )
        
        if not market_filters_result['passed']:
            log_filter_block(self.symbol, self.timeframe, f"MarketFilter:{market_filters_result['reason'].split()[0]}", market_filters_result['reason'])
            return None
        
        # Получаем ATR% для Channel Position Filter
        atr_percent = market_filters_result.get('atr_percent')
        
        # Дополнительные консервативные фильтры (с передачей atr_percent)
        filters_result = await ConservativeFilters.check_all_filters(
            self.symbol, 
            self.df, 
            signal_params['entry'],
            signal_params['stop'],
            atr,
            direction,
            self.client,
            atr_percent  # Для Channel Position Filter
        )
        
        if not filters_result['passed']:
            reasons = ', '.join(filters_result.get('reasons', ['unknown']))
            log_filter_block(self.symbol, self.timeframe, "ConservativeFilter", reasons)
            return None
        
        # ВСЕ ФИЛЬТРЫ ПРОЙДЕНЫ
        log_filter_pass(self.symbol, self.timeframe)
        
        # Формирование сигнала с расширенными данными
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
            'take_profit_3': signal_params['tp3'],
            'take_profit_4': signal_params['tp4'],
            'risk_percent': RiskManager.MAX_RISK_PER_TRADE,
            'leverage': ConfigManager.get_leverage(),
            'created_at': datetime.utcnow(),
            'volume_24h': market_filters_result['volume_24h'],  # Из рыночных фильтров
            'spread_percent': market_filters_result['spread'],  # Из рыночных фильтров
            'atr_value': atr,
            'liquidity_usdt': market_filters_result.get('liquidity'),  # Ликвидность
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
    
    def _calculate_levels(self, direction: str, price: float, atr: float, levels: dict) -> Optional[Dict]:
        """Расчёт уровней входа, стопа и 3 тейк-профитов"""
        from utils.logger import logger
        
        # Валидация входных данных
        if price <= 0:
            logger.debug(f"[{self.symbol}] Invalid price: {price}")
            return None
        
        if atr <= 0:
            logger.debug(f"[{self.symbol}] Invalid ATR: {atr}")
            return None
        
        # Проверка минимального ATR (должен быть хотя бы 0.1% от цены)
        min_atr = price * 0.001  # 0.1%
        if atr < min_atr:
            logger.debug(f"[{self.symbol}] ATR too small: {atr} < {min_atr} (0.1% of price)")
            return None
        
        # Entry = текущая цена
        entry = price
        
        if direction == 'LONG':
            # Stop loss на 2 ATR ниже (ультраконсервативно)
            stop = entry - (atr * 2.0)
            
            # Проверка, что stop не отрицательный
            if stop <= 0:
                logger.debug(f"[{self.symbol}] Stop <= 0 for LONG: {stop}")
                return None
            
            # Расчёт дистанции для TP
            stop_distance = entry - stop
            
            # Проверка минимальной дистанции (0.25% от цены минимум - ослаблено с 0.5%)
            min_distance = entry * 0.0025
            if stop_distance < min_distance:
                logger.debug(f"[{self.symbol}] Stop distance too small: {stop_distance} < {min_distance}")
                return None
            
            # 3 уровня TP с увеличивающейся дистанцией
            tp1 = entry + (stop_distance * 1.5)  # RR 1.5:1
            tp2 = entry + (stop_distance * 2.5)  # RR 2.5:1
            tp3 = entry + (stop_distance * 3.5)  # RR 3.5:1
            
            # Проверка, что не пробиваем сопротивление
            if tp3 > levels['resistance'] * 1.02:
                tp3 = levels['resistance'] * 0.99
                # Пересчитываем остальные TP пропорционально
                total_distance = tp3 - entry
                if total_distance <= 0:
                    return None
                tp1 = entry + (total_distance * 0.4)
                tp2 = entry + (total_distance * 0.7)
                
        else:  # SHORT
            # Stop loss на 2 ATR выше
            stop = entry + (atr * 2.0)
            
            stop_distance = stop - entry
            
            # Проверка минимальной дистанции (0.25% от цены минимум)
            min_distance = entry * 0.0025
            if stop_distance < min_distance:
                logger.debug(f"[{self.symbol}] Stop distance too small: {stop_distance} < {min_distance}")
                return None
            
            tp1 = entry - (stop_distance * 1.5)
            tp2 = entry - (stop_distance * 2.5)
            tp3 = entry - (stop_distance * 3.5)
            
            # Проверка, что TP не отрицательные
            if tp3 <= 0:
                logger.debug(f"[{self.symbol}] TP3 <= 0 for SHORT: {tp3}")
                return None
            
            # Проверка, что не пробиваем поддержку
            if tp3 < levels['support'] * 0.98:
                tp3 = levels['support'] * 1.01
                total_distance = entry - tp3
                if total_distance <= 0:
                    return None
                tp1 = entry - (total_distance * 0.4)
                tp2 = entry - (total_distance * 0.7)
        
        # Округление с учётом величины цены
        entry = self._round_price(entry, price)
        stop = self._round_price(stop, price)
        tp1 = self._round_price(tp1, price)
        tp2 = self._round_price(tp2, price)
        tp3 = self._round_price(tp3, price)
        
        # КРИТИЧЕСКАЯ ПРОВЕРКА: все уровни должны быть РАЗНЫМИ после округления
        all_levels = [entry, stop, tp1, tp2, tp3]
        if len(set(all_levels)) < len(all_levels):
            logger.warning(f"[{self.symbol}] Duplicate levels after rounding: entry={entry}, stop={stop}, tp1={tp1}, tp2={tp2}, tp3={tp3}")
            return None
        
        # Валидация порядка уровней
        if direction == 'LONG':
            if not (stop < entry < tp1 < tp2 < tp3):
                logger.debug(f"[{self.symbol}] Invalid LONG level order: stop={stop}, entry={entry}, tp1={tp1}, tp2={tp2}, tp3={tp3}")
                return None
        else:
            if not (stop > entry > tp1 > tp2 > tp3):
                logger.debug(f"[{self.symbol}] Invalid SHORT level order: stop={stop}, entry={entry}, tp1={tp1}, tp2={tp2}, tp3={tp3}")
                return None
        
        # Проверка минимальной дистанции между уровнями (в процентах)
        min_dist_pct = self.MIN_LEVEL_DISTANCE_PERCENT / 100
        
        def check_distance(level1, level2, name1, name2):
            dist_pct = abs(level1 - level2) / entry
            if dist_pct < min_dist_pct:
                logger.debug(f"[{self.symbol}] Distance {name1}-{name2} too small: {dist_pct*100:.4f}% < {self.MIN_LEVEL_DISTANCE_PERCENT}%")
                return False
            return True
        
        if not check_distance(entry, stop, "entry", "stop"):
            return None
        if not check_distance(entry, tp1, "entry", "tp1"):
            return None
        if not check_distance(tp1, tp2, "tp1", "tp2"):
            return None
        if not check_distance(tp2, tp3, "tp2", "tp3"):
            return None
        
        # Проверка минимального RR (≥ 1.25:1 для TP1)
        risk = abs(entry - stop)
        reward = abs(tp1 - entry)
        
        if risk <= 0 or reward <= 0:
            logger.debug(f"[{self.symbol}] Invalid risk/reward: risk={risk}, reward={reward}")
            return None
        
        rr_ratio = reward / risk
        if rr_ratio < self.MIN_RR_RATIO:
            logger.debug(f"[{self.symbol}] RR ratio too low: {rr_ratio:.2f} < {self.MIN_RR_RATIO}")
            return None
        
        # TP4 = TP3 (для обратной совместимости, но не используется в сообщении)
        tp4 = tp3
        
        return {
            'entry': entry,
            'stop': stop,
            'tp1': tp1,
            'tp2': tp2,
            'tp3': tp3,
            'tp4': tp4  # Для совместимости
        }

    def _check_market_structure(self, direction: str) -> bool:
        """
        Проверка структуры рынка (HH/HL для LONG, LH/LL для SHORT)
        
        LONG: Higher Highs и Higher Lows (восходящий тренд)
        SHORT: Lower Highs и Lower Lows (нисходящий тренд)
        """
        if len(self.df) < 50:
            return False
        
        # Берём последние 30 свечей для анализа
        recent = self.df.tail(30)
        
        # Находим локальные максимумы и минимумы (с окном 5)
        window = 5
        highs = []
        lows = []
        
        for i in range(window, len(recent) - window):
            # Локальный максимум
            if recent.iloc[i]['high'] == recent.iloc[i-window:i+window+1]['high'].max():
                highs.append(recent.iloc[i]['high'])
            
            # Локальный минимум
            if recent.iloc[i]['low'] == recent.iloc[i-window:i+window+1]['low'].min():
                lows.append(recent.iloc[i]['low'])
        
        # Нужно минимум 2 точки для анализа
        if len(highs) < 2 or len(lows) < 2:
            return True  # Недостаточно данных - пропускаем фильтр
        
        # Анализ структуры
        # Запрет только при противоположной структуре
        if direction == 'LONG':
            # Для LONG: запрещаем только если явная противоположная структура (LH/LL)
            lower_highs = highs[-1] < highs[-2]
            lower_lows = lows[-1] < lows[-2]
            # Блокируем только если ОБА условия противоположной структуры выполнены
            if lower_highs and lower_lows:
                return False
            # В остальных случаях разрешаем (HH/HL или нейтральная структура)
            return True
        
        else:  # SHORT
            # Для SHORT: запрещаем только если явная противоположная структура (HH/HL)
            higher_highs = highs[-1] > highs[-2]
            higher_lows = lows[-1] > lows[-2]
            # Блокируем только если ОБА условия противоположной структуры выполнены
            if higher_highs and higher_lows:
                return False
            # В остальных случаях разрешаем (LH/LL или нейтральная структура)
            return True
