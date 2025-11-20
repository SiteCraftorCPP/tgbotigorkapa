import pandas as pd
from typing import Optional, Dict
from .indicators import TechnicalAnalysis
from .multi_timeframe import MultiTimeframeAnalysis
from .conservative_filters import ConservativeFilters
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
        
        # ФИЛЬТР РИСК-МЕНЕДЖМЕНТА
        can_open, reason = RiskManager.can_open_new_signal(self.symbol)
        if not can_open:
            return None
        
        # Расчёт индикаторов
        self.ta.calculate_all_indicators()
        
        if self.ta.df.empty or len(self.ta.df) < 200:
            return None
        
        # МУЛЬТИТАЙМФРЕЙМНЫЙ АНАЛИЗ
        mtf = MultiTimeframeAnalysis.check_trend_alignment(self.df_higher, self.df)
        if not mtf['aligned']:
            return None  # Тренд не совпадает на двух ТФ
        
        direction = mtf['higher_trend']
        
        # ПРОВЕРКА PULLBACK (коррекция к уровню)
        if not MultiTimeframeAnalysis.check_pullback_opportunity(self.df, direction):
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
            return None
        
        # УЛЬТРАКОНСЕРВАТИВНЫЕ ФИЛЬТРЫ
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
            return None
        
        # Расчёт AI Score ПОСЛЕ прохождения всех фильтров
        ai_score = self._calculate_ai_score(trend, momentum, volume, volatility)
        
        # Повышаем требования к AI Score
        min_score = ConfigManager.get_min_ai_score()
        if ai_score < min_score:
            return None
        
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
            'ai_score': ai_score,
            'risk_percent': RiskManager.MAX_RISK_PER_TRADE,
            'leverage': ConfigManager.get_leverage(),
            'created_at': datetime.utcnow(),
            'volume_24h': filters_result['volume_24h'],
            'spread_percent': filters_result['spread'],
            'atr_value': atr,
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
    
    def _calculate_ai_score(self, trend, momentum, volume, volatility) -> int:
        """Расчёт AI Score на основе весов"""
        
        raw_score = (
            trend['score'] * config.WEIGHTS['trend'] +
            momentum['score'] * config.WEIGHTS['momentum'] +
            volume['score'] * config.WEIGHTS['volume'] +
            volatility['score'] * config.WEIGHTS['volatility']
        )
        
        # Нормализация к шкале 0-100
        # raw_score может быть от -100 до +100
        normalized = ((raw_score + 100) / 200) * 100
        
        return int(max(0, min(100, normalized)))
    
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
        if reward / risk < 1.5:  # Минимум 1.5:1 для TP1
            return None
        
        return {
            'entry': round(entry, 2),
            'stop': round(stop, 2),
            'tp1': round(tp1, 2),
            'tp2': round(tp2, 2),
            'tp3': round(tp3, 2),
            'tp4': round(tp4, 2)
        }

