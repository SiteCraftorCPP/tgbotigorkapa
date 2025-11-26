import pandas as pd
from typing import Optional, Dict
from .indicators import TechnicalAnalysis
from .multi_timeframe import MultiTimeframeAnalysis
from .conservative_filters import ConservativeFilters
from .market_filters import MarketFilters  # НОВЫЕ рыночные фильтры
from database.config_manager import ConfigManager
from database.risk_manager import RiskManager
from exchange.xt_client import XTClient
import config
import uuid
from datetime import datetime

class SignalGenerator:
    """Генератор ультраконсервативных торговых сигналов"""
    
    def __init__(self, symbol: str, timeframe: str, df: pd.DataFrame, 
                 df_higher: pd.DataFrame, client: XTClient):
        self.symbol = symbol
        self.timeframe = timeframe
        self.df = df
        self.df_higher = df_higher
        self.client = client
        self.ta = TechnicalAnalysis(df)
        
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
        
        if self.ta.df.empty or len(self.ta.df) < 200:
            log_filter_block(self.symbol, self.timeframe, "DataCheck", f"Not enough data: {len(self.ta.df)} candles < 200")
            return None
        
        # МУЛЬТИТАЙМФРЕЙМНЫЙ АНАЛИЗ
        mtf = MultiTimeframeAnalysis.check_trend_alignment(self.df_higher, self.df)
        if not mtf['aligned']:
            log_filter_block(self.symbol, self.timeframe, "MTF_Alignment", f"Trend not aligned: higher={mtf.get('higher_trend')}, lower={mtf.get('lower_signal')}")
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
        
        # Расчёт уровней входа/выхода (теперь с 4 TP)
        signal_params = self._calculate_levels(
            direction,
            current_price,
            atr,
            levels
        )
        
        if not signal_params:
            log_filter_block(self.symbol, self.timeframe, "LevelCalculation", f"Invalid levels for {direction}")
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
        
        # Дополнительные консервативные фильтры
        filters_result = await ConservativeFilters.check_all_filters(
            self.symbol, 
            self.df, 
            signal_params['entry'],
            signal_params['stop'],
            atr,
            direction,
            self.client
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
            'liquidity_usdt': market_filters_result.get('liquidity'),  # НОВОЕ: ликвидность
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
        """Расчёт уровней входа, стопа и 4 тейк-профитов"""
        
        # Entry = текущая цена или лимитный ордер чуть лучше
        entry = price
        
        if direction == 'LONG':
            # Stop loss на 2 ATR ниже (ультраконсервативно)
            stop = entry - (atr * 2.0)
            
            # Расчёт дистанции для TP (RR минимум 2:1)
            stop_distance = entry - stop
            
            # 4 уровня TP с увеличивающейся дистанцией
            tp1 = entry + (stop_distance * 1.5)  # RR 1.5:1
            tp2 = entry + (stop_distance * 2.5)  # RR 2.5:1
            tp3 = entry + (stop_distance * 3.5)  # RR 3.5:1
            tp4 = entry + (stop_distance * 5.0)  # RR 5:1
            
            # Проверка, что не пробиваем сопротивление
            if tp4 > levels['resistance'] * 1.02:
                tp4 = levels['resistance'] * 0.99
                # Пересчитываем остальные TP пропорционально
                total_distance = tp4 - entry
                tp1 = entry + (total_distance * 0.25)
                tp2 = entry + (total_distance * 0.50)
                tp3 = entry + (total_distance * 0.75)
                
        else:  # SHORT
            # Stop loss на 2 ATR выше
            stop = entry + (atr * 2.0)
            
            stop_distance = stop - entry
            
            tp1 = entry - (stop_distance * 1.5)
            tp2 = entry - (stop_distance * 2.5)
            tp3 = entry - (stop_distance * 3.5)
            tp4 = entry - (stop_distance * 5.0)
            
            # Проверка, что не пробиваем поддержку
            if tp4 < levels['support'] * 0.98:
                tp4 = levels['support'] * 1.01
                total_distance = entry - tp4
                tp1 = entry - (total_distance * 0.25)
                tp2 = entry - (total_distance * 0.50)
                tp3 = entry - (total_distance * 0.75)
        
        # Валидация
        if direction == 'LONG':
            if stop >= entry or tp1 <= entry or tp4 <= tp3 <= tp2 <= tp1:
                return None
        else:
            if stop <= entry or tp1 >= entry or tp4 >= tp3 >= tp2 >= tp1:
                return None
        
        # Проверка минимального RR
        risk = abs(entry - stop)
        reward = abs(tp1 - entry)
        if reward / risk < 1.4:  # Минимум 1.4:1 для TP1
            return None
        
        return {
            'entry': round(entry, 2),
            'stop': round(stop, 2),
            'tp1': round(tp1, 2),
            'tp2': round(tp2, 2),
            'tp3': round(tp3, 2),
            'tp4': round(tp4, 2)
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
        if direction == 'LONG':
            # Для LONG: последний high > предыдущего (HH) И последний low > предыдущего (HL)
            higher_highs = highs[-1] > highs[-2]
            higher_lows = lows[-1] > lows[-2]
            return higher_highs or higher_lows  # Хотя бы одно условие
        
        else:  # SHORT
            # Для SHORT: последний high < предыдущего (LH) И последний low < предыдущего (LL)
            lower_highs = highs[-1] < highs[-2]
            lower_lows = lows[-1] < lows[-2]
            return lower_highs or lower_lows  # Хотя бы одно условие

