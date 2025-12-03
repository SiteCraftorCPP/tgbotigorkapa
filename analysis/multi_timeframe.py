"""
Мультитаймфреймный анализ тренда и структуры
"""

import pandas as pd
from typing import Optional, Dict
from .indicators import TechnicalAnalysis


class MultiTimeframeAnalysis:
    """Анализ на нескольких таймфреймах"""
    
    # Настраиваемые параметры (применяются через FilterSettings)
    TREND_NEUTRAL_THRESHOLD = 25  # Порог нейтральности тренда (score)
    TREND_STRONG_THRESHOLD = 40  # Порог сильного тренда H1 (score)
    
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
        Проверка совпадения тренда на двух таймфреймах (M15 и H1)
        
        Условия:
        - Тренд M15 и H1 совпадает или нейтрален
        - Запрет входа против тренда H1
        """
        
        if df_higher.empty or df_lower.empty:
            return {'aligned': False, 'higher_trend': None, 'lower_signal': None}
        
        # Анализ старшего ТФ (H1 - тренд)
        ta_higher = TechnicalAnalysis(df_higher)
        ta_higher.calculate_all_indicators()
        trend_higher = ta_higher.get_trend_signal()
        
        # Анализ младшего ТФ (M15 - вход)
        ta_lower = TechnicalAnalysis(df_lower)
        ta_lower.calculate_all_indicators()
        trend_lower = ta_lower.get_trend_signal()
        
        higher_direction = trend_higher['direction']
        lower_direction = trend_lower['direction']
        higher_score = trend_higher['score']
        lower_score = trend_lower['score']
        
        # Нейтральный тренд если score между -threshold и +threshold
        threshold = MultiTimeframeAnalysis.TREND_NEUTRAL_THRESHOLD
        strong_threshold = MultiTimeframeAnalysis.TREND_STRONG_THRESHOLD
        
        higher_neutral = abs(higher_score) < threshold
        lower_neutral = abs(lower_score) < threshold
        
        # Тренд совпадает
        trends_match = (higher_direction == lower_direction)
        
        # Разрешаем если:
        # 1. Тренды совпадают
        # 2. Один из трендов нейтральный
        # 3. Старший тренд нейтральный (разрешаем вход по младшему)
        allowed = trends_match or higher_neutral or (lower_neutral and not (abs(higher_score) > strong_threshold))
        
        # Запрет входа против сильного тренда H1 (score > strong_threshold)
        if abs(higher_score) > strong_threshold and not trends_match and not higher_neutral:
            allowed = False
        
        return {
            'aligned': allowed,
            'higher_trend': higher_direction,
            'lower_signal': lower_direction,
            'higher_score': higher_score,
            'lower_score': lower_score,
            'is_neutral': higher_neutral
        }
    
    @staticmethod
    def check_pullback_opportunity(df: pd.DataFrame, direction: str) -> bool:
        """
        Проверка наличия pullback
        """
        return True  # Всегда разрешаем для тестирования
    
    @staticmethod
    def check_market_structure(df: pd.DataFrame, direction: str) -> Dict:
        """
        Проверка структуры рынка:
        - Для лонга: HH + HL обязательны
        - Для шорта: LL + LH обязательны
        """
        result = {'passed': False, 'reason': '', 'structure': None}
        
        if len(df) < 30:
            result['reason'] = "Not enough data for structure analysis"
            return result
        
        recent = df.tail(30)
        
        # Находим локальные экстремумы
        window = 5
        highs = []
        lows = []
        
        for i in range(window, len(recent) - window):
            # Локальный максимум
            if recent.iloc[i]['high'] == recent.iloc[i-window:i+window+1]['high'].max():
                highs.append({
                    'price': recent.iloc[i]['high'],
                    'index': i
                })
            
            # Локальный минимум
            if recent.iloc[i]['low'] == recent.iloc[i-window:i+window+1]['low'].min():
                lows.append({
                    'price': recent.iloc[i]['low'],
                    'index': i
                })
        
        if len(highs) < 2 or len(lows) < 2:
            result['reason'] = "Not enough swing points"
            return result
        
        # Анализ структуры
        last_two_highs = [h['price'] for h in highs[-2:]]
        last_two_lows = [l['price'] for l in lows[-2:]]
        
        if direction == 'LONG':
            # HH + HL обязательны
            higher_high = last_two_highs[-1] > last_two_highs[-2]
            higher_low = last_two_lows[-1] > last_two_lows[-2]
            
            if higher_high and higher_low:
                result['passed'] = True
                result['structure'] = 'HH+HL'
            else:
                result['reason'] = f"Invalid LONG structure: HH={higher_high}, HL={higher_low}"
        
        else:  # SHORT
            # LL + LH обязательны
            lower_low = last_two_lows[-1] < last_two_lows[-2]
            lower_high = last_two_highs[-1] < last_two_highs[-2]
            
            if lower_low and lower_high:
                result['passed'] = True
                result['structure'] = 'LL+LH'
            else:
                result['reason'] = f"Invalid SHORT structure: LL={lower_low}, LH={lower_high}"
        
        return result
    
    @staticmethod
    def check_mini_trend(df: pd.DataFrame, direction: str) -> Dict:
        """
        Мини-тренд: минимум 3 из последних 4 свечей в направлении сигнала
        """
        result = {'passed': False, 'reason': '', 'count': 0}
        
        if len(df) < 4:
            result['reason'] = "Not enough data for mini-trend"
            return result
        
        recent = df.tail(4)
        count = 0
        
        for idx, row in recent.iterrows():
            if direction == 'LONG' and row['close'] > row['open']:
                count += 1
            elif direction == 'SHORT' and row['close'] < row['open']:
                count += 1
        
        result['count'] = count
        
        if count >= 3:
            result['passed'] = True
        else:
            result['reason'] = f"Mini-trend: only {count}/4 candles in {direction} direction"
        
        return result
    
    @staticmethod
    def check_ema50_slope(df: pd.DataFrame, direction: str) -> Dict:
        """
        Наклон EMA50 в нужную сторону ≥ 7 из 10 свечей
        """
        result = {'passed': False, 'reason': '', 'slope_count': 0}
        
        if len(df) < 60:  # Нужно 50 для EMA + 10 для анализа
            result['passed'] = True  # Пропускаем если недостаточно данных
            return result
        
        ta = TechnicalAnalysis(df)
        ta.calculate_all_indicators()
        
        if 'ema_50' not in ta.df.columns:
            result['passed'] = True
            return result
        
        ema50 = ta.df['ema_50'].tail(10)
        
        slope_count = 0
        for i in range(1, len(ema50)):
            if direction == 'LONG' and ema50.iloc[i] > ema50.iloc[i-1]:
                slope_count += 1
            elif direction == 'SHORT' and ema50.iloc[i] < ema50.iloc[i-1]:
                slope_count += 1
        
        result['slope_count'] = slope_count
        
        if slope_count >= 7:
            result['passed'] = True
        else:
            result['reason'] = f"EMA50 slope: only {slope_count}/10 candles in {direction} direction"
        
        return result
