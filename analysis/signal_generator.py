import pandas as pd
from typing import Optional, Dict
import uuid
from datetime import datetime
from .indicators import TechnicalAnalysis
from .multi_timeframe import MultiTimeframeAnalysis
from .conservative_filters import ConservativeFilters
from .market_filters import MarketFilters
from database.config_manager import ConfigManager
from exchange.xt_client import XTClient
from telegram_bot.filter_panel import FilterSettings
from utils.logger import log_filter_block, log_filter_pass, log_info, logger

class SignalGenerator:
    """Генератор сигналов с ПОЛНОЙ логикой и динамическими настройками"""
    
    _last_structures = {}  

    def __init__(self, symbol: str, timeframe: str, df: pd.DataFrame, 
                 df_higher: pd.DataFrame, client: XTClient):
        self.symbol = symbol
        self.timeframe = timeframe
        self.df = df
        self.df_higher = df_higher
        self.client = client
        self.ta = TechnicalAnalysis(df)
        
        # Загружаем настройки из админки
        s = FilterSettings.get_all()
        self.MAX_EMA50_DISTANCE_ATR = s.get('max_ema50_distance', 2.5)
        self.PULLBACK_MIN_ATR = s.get('pullback_min', 0.3)
        self.PULLBACK_MAX_ATR = s.get('pullback_max', 1.0)
        self.MIN_TREND_CANDLES = s.get('min_trend_candles', 0.333)
        self.SIGNAL_VOLUME_MULTIPLIER = s.get('signal_volume_multiplier', 1.03)
        self.EMA50_SLOPE_MIN_CANDLES = s.get('ema50_slope_min', 6)
        self.IMPULSE_BODY_RATIO = s.get('impulse_body_ratio', 43) / 100
        
        # Параметры целей
        self.TP1_ATR = s.get('tp1_atr', 1.6)
        self.TP2_ATR = s.get('tp2_atr', 3.2)
        self.TP3_ATR = s.get('tp3_atr', 7.5)
        self.MIN_RR_RATIO = s.get('min_rr_ratio', 1.5)

    async def generate_signal(self) -> Optional[Dict]:
        """Полный цикл проверок с логированием каждого шага"""
        
        # 1. Проверка достаточности данных
        if self.df is None or len(self.df) < 210:
            log_filter_block(self.symbol, self.timeframe, "InsufficientData", f"Candles: {len(self.df) if self.df is not None else 0}")
            return None
        
        # 2. Расчет индикаторов
        self.ta.calculate_all_indicators()
        
        # 3. Мультитаймфреймный анализ
        mtf = MultiTimeframeAnalysis.check_trend_alignment(self.df_higher, self.df)
        if not mtf.get('aligned', False):
            log_filter_block(self.symbol, self.timeframe, "MTF_Alignment", "Trend not aligned")
            return None
        
        direction = mtf.get('higher_trend') or mtf.get('lower_signal')
        
        # 4. Проверка EMA50 (дистанция)
        if not self._check_ema50_distance():
            log_filter_block(self.symbol, self.timeframe, "EMA50_Distance", "Too far from EMA50")
            return None
            
        # 5. Мини-тренд
        if not self._check_mini_trend(direction):
            log_filter_block(self.symbol, self.timeframe, "MiniTrend", "Weak short-term momentum")
            return None

        # 6. Рыночная структура (HH/HL или LL/LH)
        structure_ok, structure_sig = self._check_market_structure(direction)
        if not structure_ok:
            log_filter_block(self.symbol, self.timeframe, "MarketStructure", "Invalid HH/HL sequence")
            return None

        # 7. Импульсная свеча
        if not self._check_impulse_candle(direction):
            log_filter_block(self.symbol, self.timeframe, "ImpulseCandle", "No strong impulse found")
            return None

        # 8. Внешние маркет-фильтры (Volume, Spread, Liquidity, Funding)
        market_filters_result = await MarketFilters.check_all_filters(self.symbol, self.timeframe, self.df, self.client, direction)
        if not market_filters_result['passed']:
            # Логирование уже вшито внутри MarketFilters.check_all_filters
            return None
            
        # 9. Расчет уровней
        last_row = self.ta.df.iloc[-1]
        current_price = last_row['close']
        atr = last_row['atr']
        signal_params = self._calculate_levels(direction, current_price, atr)
        if not signal_params:
            log_filter_block(self.symbol, self.timeframe, "LevelCalc", "Invalid TP/SL calculation")
            return None
            
        # 10. Консервативные фильтры (Уровни, Bid/Ask)
        cons_result = await ConservativeFilters.check_all_filters(self.symbol, self.df, signal_params['entry'], signal_params['stop'], atr, direction, self.client)
        if not cons_result['passed']:
            reason = cons_result.get('reasons', ['Quality check failed'])[0]
            log_filter_block(self.symbol, self.timeframe, "ConservativeFilter", reason)
            return None

        # ЕСЛИ ВСЁ ПРОШЛО
        log_filter_pass(self.symbol, self.timeframe)
        
        return {
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

    def _check_ema50_distance(self) -> bool:
        last = self.ta.df.iloc[-1]
        if 'ema_50' not in last or 'atr' not in last: return True
        distance = abs(last['close'] - last['ema_50'])
        return distance <= (last['atr'] * self.MAX_EMA50_DISTANCE_ATR)

    def _check_mini_trend(self, direction: str) -> bool:
        recent = self.df.tail(3)
        if direction == 'LONG':
            return (recent['close'] > recent['open']).any()
        return (recent['close'] < recent['open']).any()

    def _check_market_structure(self, direction: str):
        # Упрощенная HH/HL логика для стабильности
        recent = self.df.tail(20)
        if direction == 'LONG':
            return recent['high'].max() > recent['high'].shift(1).max(), "sig"
        return recent['low'].min() < recent['low'].shift(1).min(), "sig"

    def _check_impulse_candle(self, direction: str) -> bool:
        recent_10 = self.df.tail(10)
        for _, row in recent_10.iterrows():
            body = abs(row['close'] - row['open'])
            full_range = row['high'] - row['low']
            if full_range > 0 and (body / full_range) >= self.IMPULSE_BODY_RATIO:
                if (direction == 'LONG' and row['close'] > row['open']) or \
                   (direction == 'SHORT' and row['close'] < row['open']):
                    return True
        return False

    def _calculate_levels(self, direction: str, price: float, atr: float) -> Optional[Dict]:
        entry = price
        sl_dist = atr * 2.0
        if direction == 'LONG':
            stop, tp1, tp2, tp3 = entry - sl_dist, entry + (atr * self.TP1_ATR), entry + (atr * self.TP2_ATR), entry + (atr * self.TP3_ATR)
        else:
            stop, tp1, tp2, tp3 = entry + sl_dist, entry - (atr * self.TP1_ATR), entry - (atr * self.TP2_ATR), entry - (atr * self.TP3_ATR)
        
        def _fmt(val): return round(val, 2 if price > 100 else 6)
        return {'entry': _fmt(entry), 'stop': _fmt(stop), 'tp1': _fmt(tp1), 'tp2': _fmt(tp2), 'tp3': _fmt(tp3)}
