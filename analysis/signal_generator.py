import pandas as pd
from typing import Optional, Dict
from .indicators import TechnicalAnalysis
from database.config_manager import ConfigManager
import config
import uuid
from datetime import datetime

class SignalGenerator:
    """Генератор торговых сигналов"""
    
    def __init__(self, symbol: str, timeframe: str, df: pd.DataFrame):
        self.symbol = symbol
        self.timeframe = timeframe
        self.df = df
        self.ta = TechnicalAnalysis(df)
        
    def generate_signal(self) -> Optional[Dict]:
        """Генерация сигнала на основе анализа"""
        
        # Расчёт индикаторов
        self.ta.calculate_all_indicators()
        
        if self.ta.df.empty or len(self.ta.df) < 200:
            return None
        
        # Получение всех сигналов
        trend = self.ta.get_trend_signal()
        momentum = self.ta.get_momentum_signal()
        volume = self.ta.get_volume_signal()
        volatility = self.ta.get_volatility_score()
        levels = self.ta.calculate_support_resistance()
        
        # Расчёт AI Score
        ai_score = self._calculate_ai_score(trend, momentum, volume, volatility)
        
        # Фильтр по минимальному скору (из БД)
        min_score = ConfigManager.get_min_ai_score()
        if ai_score < min_score:
            return None
        
        # Определение направления
        direction = trend['direction']
        
        # Текущая цена
        current_price = self.ta.df.iloc[-1]['close']
        atr = self.ta.df.iloc[-1]['atr']
        
        # Расчёт уровней входа/выхода
        signal_params = self._calculate_levels(
            direction,
            current_price,
            atr,
            levels
        )
        
        if not signal_params:
            return None
        
        # Формирование сигнала
        signal = {
            'signal_id': str(uuid.uuid4())[:8],
            'ticker': self.symbol,
            'direction': direction,
            'timeframe': self.timeframe,
            'entry_price': signal_params['entry'],
            'stop_loss': signal_params['stop'],
            'take_profit_1': signal_params['tp1'],
            'take_profit_2': signal_params['tp2'],
            'ai_score': ai_score,
            'risk_percent': ConfigManager.get_risk_percent(),
            'leverage': ConfigManager.get_leverage(),
            'created_at': datetime.utcnow(),
            'analysis': {
                'trend': trend,
                'momentum': momentum,
                'volume': volume,
                'volatility': volatility,
                'levels': levels
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
        """Расчёт уровней входа, стопа и тейк-профитов"""
        
        # Entry = текущая цена (market order)
        entry = price
        
        if direction == 'LONG':
            # Stop loss на 1.5 ATR ниже
            stop = entry - (atr * 1.5)
            
            # TP1 на 2 ATR выше (RR 1:1.33)
            tp1 = entry + (atr * 2)
            
            # TP2 на 3 ATR выше (RR 1:2)
            tp2 = entry + (atr * 3)
            
            # Проверка, что не пробиваем сопротивление
            if tp2 > levels['resistance'] * 1.02:
                tp2 = levels['resistance'] * 0.99
                
        else:  # SHORT
            # Stop loss на 1.5 ATR выше
            stop = entry + (atr * 1.5)
            
            # TP1 на 2 ATR ниже
            tp1 = entry - (atr * 2)
            
            # TP2 на 3 ATR ниже
            tp2 = entry - (atr * 3)
            
            # Проверка, что не пробиваем поддержку
            if tp2 < levels['support'] * 0.98:
                tp2 = levels['support'] * 1.01
        
        # Валидация
        if direction == 'LONG':
            if stop >= entry or tp1 <= entry or tp2 <= tp1:
                return None
        else:
            if stop <= entry or tp1 >= entry or tp2 >= tp1:
                return None
        
        return {
            'entry': round(entry, 2),
            'stop': round(stop, 2),
            'tp1': round(tp1, 2),
            'tp2': round(tp2, 2)
        }

