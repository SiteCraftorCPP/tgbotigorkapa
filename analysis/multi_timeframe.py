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
        # 2. На старшем ТФ нейтральный/слабый тренд (score между -50 и +50)
        # СМЯГЧЕНО: разрешаем почти любой тренд
        higher_score = trend_higher['score']
        is_neutral = abs(higher_score) < 60  # Нейтральный тренд если score между -60 и +60 (было 30)
        
        aligned = (higher_direction == lower_direction) or is_neutral
        
        # Дополнительная проверка: на старшем ТФ цена должна быть выше EMA200 для лонга
        # Но если тренд нейтральный или слабый, пропускаем эту проверку
        last_higher = ta_higher.df.iloc[-1]
        
        # СМЯГЧЕНО: для нейтральных трендов пропускаем проверку EMA200
        # Для сильных трендов проверяем позицию относительно EMA200
        if is_neutral:
            # Если тренд нейтральный - пропускаем проверку структуры
            strong_trend = True
        elif 'ema_200' not in last_higher or pd.isna(last_higher['ema_200']):
            strong_trend = True  # Если нет EMA200, пропускаем проверку
        else:
            # Для сильных трендов: разрешаем если цена в пределах 30% от EMA200
            price_ema_diff = abs(last_higher['close'] - last_higher['ema_200']) / last_higher['ema_200']
            strong_trend = price_ema_diff < 0.30  # 30% допуск (очень мягко)
        
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
        СМЯГЧЕНО для увеличения количества сигналов
        """
        
        if len(df) < 20:
            return False
        
        ta = TechnicalAnalysis(df)
        ta.calculate_all_indicators()
        
        last = ta.df.iloc[-1]
        prev = ta.df.iloc[-2]
        atr = last['atr']
        current_price = last['close']
        
        # Допуск в ATR: от 0 до 3 ATR (СМЯГЧЕНО: было 0.5-1)
        tolerance_max = atr * 3.0
        
        if direction == 'LONG':
            # Pullback к EMA50 с допуском до 3 ATR
            ema50_distance = abs(current_price - last['ema_50'])
            near_ema50 = ema50_distance <= tolerance_max
            
            # RSI в разумной зоне (не сильно перекуплен) - СМЯГЧЕНО
            rsi_ok = last['rsi'] < 75  # было много условий
            
            # Цена выше EMA20 (краткосрочный тренд вверх)
            price_above_ema20 = current_price > last['ema_21']
            
            return near_ema50 or rsi_ok or price_above_ema20
        
        else:  # SHORT
            # Pullback к EMA50 с допуском до 3 ATR
            ema50_distance = abs(current_price - last['ema_50'])
            near_ema50 = ema50_distance <= tolerance_max
            
            # RSI в разумной зоне (не сильно перепродан) - СМЯГЧЕНО
            rsi_ok = last['rsi'] > 25  # было много условий
            
            # Цена ниже EMA20 (краткосрочный тренд вниз)
            price_below_ema20 = current_price < last['ema_21']
            
            return near_ema50 or rsi_ok or price_below_ema20

