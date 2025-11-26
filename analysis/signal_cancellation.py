"""
Логика отмены сигналов до входа
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple
from .indicators import TechnicalAnalysis


class SignalCancellation:
    """Проверка условий отмены сигнала до входа"""
    
    # Константы
    MAX_WAIT_TIME_HOURS = 24  # Максимальное время ожидания входа
    PRICE_DEVIATION_PERCENT = 1.5  # Максимальное отклонение цены от зоны входа
    
    @staticmethod
    def should_cancel(signal: dict, current_price: float, df: pd.DataFrame, 
                     created_at: datetime) -> Tuple[bool, Optional[str]]:
        """
        Проверка, нужно ли отменить сигнал
        Возвращает (нужно_отменить, причина)
        """
        
        entry = signal['entry_price']
        direction = signal['direction']
        
        # 1. Проверка времени ожидания
        time_elapsed = datetime.utcnow() - created_at
        if time_elapsed > timedelta(hours=SignalCancellation.MAX_WAIT_TIME_HOURS):
            return True, "Истекло время ожидания входа (24ч)"
        
        # 2. Проверка ухода цены от зоны входа
        price_deviation = abs(current_price - entry) / entry * 100
        
        if direction == 'LONG':
            # Цена ушла слишком высоко
            if current_price > entry * (1 + SignalCancellation.PRICE_DEVIATION_PERCENT / 100):
                return True, f"Цена ушла выше зоны входа (+{price_deviation:.1f}%)"
            
            # Цена пробила стоп до входа
            if current_price <= signal['stop_loss']:
                return True, "Цена пробила уровень стопа до активации входа"
        
        else:  # SHORT
            # Цена ушла слишком низко
            if current_price < entry * (1 - SignalCancellation.PRICE_DEVIATION_PERCENT / 100):
                return True, f"Цена ушла ниже зоны входа (-{price_deviation:.1f}%)"
            
            # Цена пробила стоп до входа
            if current_price >= signal['stop_loss']:
                return True, "Цена пробила уровень стопа до активации входа"
        
        # 3. Проверка смены структуры рынка
        if SignalCancellation._structure_changed(df, direction):
            return True, "Изменилась структура рынка"
        
        # 4. Проверка импульса против идеи
        if SignalCancellation._counter_impulse(df, direction):
            return True, "Сильный импульс против направления сигнала"
        
        return False, None
    
    @staticmethod
    def _structure_changed(df: pd.DataFrame, direction: str) -> bool:
        """Проверка изменения структуры рынка"""
        
        if len(df) < 20:
            return False
        
        ta = TechnicalAnalysis(df)
        ta.calculate_all_indicators()
        
        last = ta.df.iloc[-1]
        
        if direction == 'LONG':
            # Для лонга: цена упала ниже EMA200
            if last['close'] < last['ema_200']:
                return True
            
            # Медвежий кросс EMA50/100
            prev = ta.df.iloc[-2]
            if prev['ema_50'] > prev['ema_200'] and last['ema_50'] < last['ema_200']:
                return True
        
        else:  # SHORT
            # Для шорта: цена поднялась выше EMA200
            if last['close'] > last['ema_200']:
                return True
            
            # Бычий кросс EMA50/100
            prev = ta.df.iloc[-2]
            if prev['ema_50'] < prev['ema_200'] and last['ema_50'] > last['ema_200']:
                return True
        
        return False
    
    @staticmethod
    def _counter_impulse(df: pd.DataFrame, direction: str) -> bool:
        """Проверка сильного импульса против сигнала"""
        
        if len(df) < 5:
            return False
        
        # Последние 3 свечи
        recent = df.tail(3)
        
        if direction == 'LONG':
            # Три красные свечи подряд с большим телом
            bearish_candles = 0
            for i in range(len(recent)):
                candle = recent.iloc[i]
                if candle['close'] < candle['open']:
                    body_size = (candle['open'] - candle['close']) / candle['open']
                    if body_size > 0.02:  # Тело > 2%
                        bearish_candles += 1
            
            return bearish_candles >= 3
        
        else:  # SHORT
            # Три зелёные свечи подряд с большим телом
            bullish_candles = 0
            for i in range(len(recent)):
                candle = recent.iloc[i]
                if candle['close'] > candle['open']:
                    body_size = (candle['close'] - candle['open']) / candle['open']
                    if body_size > 0.02:
                        bullish_candles += 1
            
            return bullish_candles >= 3

