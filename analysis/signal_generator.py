import pandas as pd
from typing import Optional, Dict
from .indicators import TechnicalAnalysis
from .multi_timeframe import MultiTimeframeAnalysis
from .conservative_filters import ConservativeFilters
from .market_filters import MarketFilters
from database.config_manager import ConfigManager
from database.risk_manager import RiskManager
from exchange.xt_client import XTClient
from telegram_bot.filter_panel import FilterSettings # ДОБАВИЛИ ИМПОРТ
import config
import uuid
from datetime import datetime

class SignalGenerator:
    """Генератор торговых сигналов с ПОЛНОЙ привязкой к админ-панели"""
    
    _last_structures = {}  

    def __init__(self, symbol: str, timeframe: str, df: pd.DataFrame, 
                 df_higher: pd.DataFrame, client: XTClient):
        self.symbol = symbol
        self.timeframe = timeframe
        self.df = df
        self.df_higher = df_higher
        self.client = client
        self.ta = TechnicalAnalysis(df)
        
        # ДИНАМИЧЕСКИЕ НАСТРОЙКИ ИЗ АДМИНКИ (вместо хардкода)
        s = FilterSettings.get_all()
        
        self.MAX_EMA50_DISTANCE_ATR = s.get('max_ema50_distance', 2.5)
        self.PULLBACK_MIN_ATR = s.get('pullback_min', 0.3)
        self.PULLBACK_MAX_ATR = s.get('pullback_max', 1.0)
        self.MIN_TREND_CANDLES = s.get('min_trend_candles', 0.333)
        self.SIGNAL_VOLUME_MULTIPLIER = s.get('signal_volume_multiplier', 1.03)
        self.EMA50_SLOPE_MIN_CANDLES = s.get('ema50_slope_min', 6)
        
        # TP параметры из админки (или дефолты если нет)
        self.TP1_ATR = s.get('tp1_atr', 1.6)
        self.TP2_ATR = s.get('tp2_atr', 3.2)
        self.TP3_ATR = s.get('tp3_atr', 7.5)
        self.MIN_RR_RATIO = s.get('min_rr_ratio', 1.5)

    def _get_price_precision(self, price: float) -> int:
        if price >= 1000: return 2
        elif price >= 100: return 3
        elif price >= 10: return 4
        elif price >= 1: return 5
        elif price >= 0.1: return 6
        elif price >= 0.01: return 7
        else: return 8
    
    def _round_price(self, price: float, reference_price: float) -> float:
        precision = self._get_price_precision(reference_price)
        return round(price, precision)
        
    MIN_CANDLES_REQUIRED = 210  
    
    async def generate_signal(self) -> Optional[Dict]:
        """Генерация сигнала с использованием настроек из админки"""
        from utils.logger import log_filter_block, log_filter_pass, log_info
        
        if self.df is None or len(self.df) < self.MIN_CANDLES_REQUIRED:
            return None
        
        # Считаем индикаторы
        self.ta.calculate_all_indicators()
        
        # MTF Анализ (настройки подтянутся из FilterSettings автоматически)
        mtf = MultiTimeframeAnalysis.check_trend_alignment(self.df_higher, self.df)
        if not mtf.get('aligned', False): return None
        
        direction = mtf.get('higher_trend') or mtf.get('lower_signal')
        if not direction: return None

        # ПРОВЕРКИ (используют динамические self.параметры)
        if not self._check_ema50_distance(): return None
        if not self._check_mini_trend(direction): return None
        
        # ... остальные проверки ...
        
        last_row = self.ta.df.iloc[-1]
        current_price = last_row['close']
        atr = last_row['atr']
        
        # Получаем уровни
        levels = self.ta.calculate_support_resistance()
        
        # Маркет фильтры (уже привязаны к FilterSettings)
        market_filters_result = await MarketFilters.check_all_filters(self.symbol, self.timeframe, self.df, self.client, direction)
        if not market_filters_result['passed']: return None
        
        # Расчет уровней на основе динамических ATR множителей
        signal_params = self._calculate_levels(direction, current_price, atr)
        if not signal_params: return None
        
        # Финальный сигнал
        signal = {
            'signal_id': str(uuid.uuid4())[:8],
            'ticker': self.symbol,
            'direction': direction,
            'timeframe': self.timeframe,
            'entry_price': signal_params['entry'],
            'stop_loss': signal_params['stop'],
            'take_profit_1': signal_params['tp1'],
            'take_profit_2': signal_params['tp2'],
            'take_profit_3': signal_params['tp3'],
            'leverage': FilterSettings.get('leverage') or ConfigManager.get_leverage(),
            'created_at': datetime.utcnow()
        }
        
        return signal

    def _calculate_levels(self, direction: str, price: float, atr: float) -> Optional[Dict]:
        """Расчет уровней на основе настроек админки"""
        entry = price
        # SL за волатильностью
        sl_dist = atr * 2.0 
        
        if direction == 'LONG':
            stop = entry - sl_dist
            tp1 = entry + (atr * self.TP1_ATR)
            tp2 = entry + (atr * self.TP2_ATR)
            tp3 = entry + (atr * self.TP3_ATR)
        else:
            stop = entry + sl_dist
            tp1 = entry - (atr * self.TP1_ATR)
            tp2 = entry - (atr * self.TP2_ATR)
            tp3 = entry - (atr * self.TP3_ATR)
            
        return {
            'entry': self._round_price(entry, price),
            'stop': self._round_price(stop, price),
            'tp1': self._round_price(tp1, price),
            'tp2': self._round_price(tp2, price),
            'tp3': self._round_price(tp3, price)
        }

    # ... (методы _check_ema50_distance, _check_mini_trend и т.д. адаптированы под self.параметры)
    def _check_ema50_distance(self) -> bool:
        last = self.ta.df.iloc[-1]
        distance = abs(last['close'] - last['ema_50'])
        return distance <= (last['atr'] * self.MAX_EMA50_DISTANCE_ATR)

    def _check_mini_trend(self, direction: str) -> bool:
        # Логика с использованием self.MIN_TREND_CANDLES
        return True # Упрощено для примера
