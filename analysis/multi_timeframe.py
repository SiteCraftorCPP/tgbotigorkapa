"""
Мультитаймфреймный анализ тренда
"""

import pandas as pd
from typing import Optional, Dict
from .indicators import TechnicalAnalysis


class MultiTimeframeAnalysis:
    """Анализ на нескольких таймфреймах"""
    
    @staticmethod
    def get_higher_timeframe(current_tf: str) -> str:
        """Получить старший таймфрейм"""
        mapping = {
            '1m': '5m',
            '5m': '15m',
            '15m': '1h',
            '1h': '4h',
            '4h': '1d',
            '1d': '1w'
        }
        return mapping.get(current_tf, '1h')
    
    @staticmethod
    def check_trend_alignment(df_higher: pd.DataFrame, df_lower: pd.DataFrame) -> Dict:
        """
        Проверка совпадения тренда на двух таймфреймах
        Старший = направление тренда
        Младший = точка входа
        """
        
        if df_higher.empty or df_lower.empty:
            return {'aligned': False, 'higher_trend': None, 'lower_signal': None}
        
        # Анализ старшего ТФ (тренд)
        ta_higher = TechnicalAnalysis(df_higher)
        ta_higher.calculate_all_indicators()
        trend_higher = ta_higher.get_trend_signal()
        
        # Анализ младшего ТФ (вход)
        ta_lower = TechnicalAnalysis(df_lower)
        ta_lower.calculate_all_indicators()
        trend_lower = ta_lower.get_trend_signal()
        
        # Проверка совпадения или нейтрального тренда на старшем ТФ
        higher_direction = trend_higher['direction']
        lower_direction = trend_lower['direction']
        
        # Разрешаем сигнал если:
        # 1. Тренд совпадает на обоих ТФ
        # 2. На старшем ТФ нейтральный тренд (score близок к 0)
        # 3. На старшем ТФ слабый тренд (score между -30 и +30) - ОСЛАБЛЕНО
        higher_score = trend_higher['score']
        is_neutral = abs(higher_score) < 30  # Нейтральный тренд если score между -30 и +30 (было 20)
        
        aligned = (higher_direction == lower_direction) or is_neutral
        
        # Дополнительная проверка: на старшем ТФ цена должна быть выше EMA200 для лонга
        # Но если тренд нейтральный или слабый, пропускаем эту проверку
        last_higher = ta_higher.df.iloc[-1]
        
        if is_neutral:
            strong_trend = True  # Нейтральный тренд разрешён
        elif higher_direction == 'LONG':
            # Для LONG: цена должна быть ВЫШЕ EMA200 (или очень близко - в пределах 2% снизу)
            price_ema_diff = (last_higher['close'] - last_higher['ema_200']) / last_higher['ema_200']
            # Разрешаем если цена выше EMA200 ИЛИ если цена ниже но очень близко (в пределах 2%)
            strong_trend = last_higher['close'] > last_higher['ema_200'] or (price_ema_diff > -0.02 and price_ema_diff <= 0)
        else:  # SHORT
            # Для SHORT: цена должна быть НИЖЕ EMA200 (или очень близко - в пределах 2% сверху)
            price_ema_diff = (last_higher['ema_200'] - last_higher['close']) / last_higher['ema_200']
            # Разрешаем если цена ниже EMA200 ИЛИ если цена выше но очень близко (в пределах 2%)
            strong_trend = last_higher['close'] < last_higher['ema_200'] or (price_ema_diff > -0.02 and price_ema_diff <= 0)
        
        return {
            'aligned': aligned and strong_trend,
            'higher_trend': higher_direction,
            'lower_signal': lower_direction,
            'higher_score': higher_score,
            'lower_score': trend_lower['score'],
            'is_neutral': is_neutral
        }
    
    @staticmethod
    def check_pullback_opportunity(df: pd.DataFrame, direction: str) -> bool:
        """
        Проверка наличия pullback (коррекции к уровню)
        Pullback к уровню (EMA50, RSI или S/R) с допуском ±0.5–1 ATR
        """
        
        if len(df) < 50:
            return False
        
        ta = TechnicalAnalysis(df)
        ta.calculate_all_indicators()
        
        last = ta.df.iloc[-1]
        prev = ta.df.iloc[-2]
        atr = last['atr']
        current_price = last['close']
        
        # Допуск в ATR: от 0.5 до 1 ATR
        tolerance_min = atr * 0.5
        tolerance_max = atr * 1.0
        
        if direction == 'LONG':
            # Pullback к EMA50 с допуском ±0.5–1 ATR
            ema50_distance = abs(current_price - last['ema_50'])
            near_ema50 = tolerance_min <= ema50_distance <= tolerance_max or ema50_distance < tolerance_min
            
            # RSI в зоне перепроданности или выходит из неё
            rsi_oversold_exit = (30 < last['rsi'] < 50 and last['rsi'] > prev['rsi']) or (last['rsi'] < 40)
            
            # Pullback к поддержке (S/R) - проверяем ближайший уровень поддержки
            # Упрощённо: если цена близка к EMA50, считаем что есть pullback
            price_above_ema = current_price > last['ema_50'] and (current_price - last['ema_50']) <= tolerance_max
            
            return near_ema50 or rsi_oversold_exit or price_above_ema
        
        else:  # SHORT
            # Pullback к EMA50 с допуском ±0.5–1 ATR
            ema50_distance = abs(current_price - last['ema_50'])
            near_ema50 = tolerance_min <= ema50_distance <= tolerance_max or ema50_distance < tolerance_min
            
            # RSI в зоне перекупленности или выходит из неё
            rsi_overbought_exit = (50 < last['rsi'] < 70 and last['rsi'] < prev['rsi']) or (last['rsi'] > 60)
            
            # Pullback к сопротивлению (S/R) - проверяем ближайший уровень сопротивления
            # Упрощённо: если цена близка к EMA50, считаем что есть pullback
            price_below_ema = current_price < last['ema_50'] and (last['ema_50'] - current_price) <= tolerance_max
            
            return near_ema50 or rsi_overbought_exit or price_below_ema

