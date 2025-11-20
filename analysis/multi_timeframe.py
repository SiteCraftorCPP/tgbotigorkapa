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
        
        # Проверка совпадения
        aligned = trend_higher['direction'] == trend_lower['direction']
        
        # Дополнительная проверка: на старшем ТФ цена должна быть выше EMA200 для лонга
        last_higher = ta_higher.df.iloc[-1]
        
        if trend_higher['direction'] == 'LONG':
            strong_trend = last_higher['close'] > last_higher['ema_200']
        else:
            strong_trend = last_higher['close'] < last_higher['ema_200']
        
        return {
            'aligned': aligned and strong_trend,
            'higher_trend': trend_higher['direction'],
            'lower_signal': trend_lower['direction'],
            'higher_score': trend_higher['score'],
            'lower_score': trend_lower['score']
        }
    
    @staticmethod
    def check_pullback_opportunity(df: pd.DataFrame, direction: str) -> bool:
        """
        Проверка наличия pullback (коррекции к уровню)
        """
        
        if len(df) < 50:
            return False
        
        ta = TechnicalAnalysis(df)
        ta.calculate_all_indicators()
        
        last = ta.df.iloc[-1]
        prev = ta.df.iloc[-2]
        
        if direction == 'LONG':
            # Цена откатила к EMA50 или нижней границе канала
            near_ema50 = abs(last['close'] - last['ema_50']) / last['close'] < 0.01
            
            # RSI в зоне перепроданности но уже выходит
            rsi_oversold_exit = 30 < last['rsi'] < 45 and last['rsi'] > prev['rsi']
            
            return near_ema50 or rsi_oversold_exit
        
        else:  # SHORT
            # Цена откатила к EMA50 или верхней границе канала
            near_ema50 = abs(last['close'] - last['ema_50']) / last['close'] < 0.01
            
            # RSI в зоне перекупленности но уже выходит
            rsi_overbought_exit = 55 < last['rsi'] < 70 and last['rsi'] < prev['rsi']
            
            return near_ema50 or rsi_overbought_exit

