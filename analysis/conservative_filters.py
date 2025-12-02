"""
Conservative filters for signal validation
Full implementation of level quality and additional checks
"""

import pandas as pd
from typing import Optional, Dict
from exchange.xt_client import XTClient


class ConservativeFilters:
    """Фильтры качества сигнала и уровней"""
    
    # ========================================================================
    # УРОВНИ
    # ========================================================================
    
    MIN_LEVEL_TOUCHES = 2  # Минимум 2 касания уровня
    MIN_HTF_LEVEL_TOUCHES = 2  # HTF: минимум 2 касания
    HTF_VOLUME_MULTIPLIER = 1.3  # HTF: объём ≥ 1.3× среднего
    MIN_OPPOSITE_LEVEL_DISTANCE_ATR = 1.4  # Дистанция до противоположного уровня ≥ 1.4 ATR
    BREAKOUT_BODY_RATIO = 0.55  # Свеча пробоя: тело ≥ 55% выше/ниже уровня
    
    # ========================================================================
    # CHANNEL POSITION
    # ========================================================================
    
    # Адаптивные зоны по волатильности (не используются в новой версии)
    CHANNEL_ZONES = {
        'low_volatility': {'atr_max': 1.0, 'forbidden_min': 0.40, 'forbidden_max': 0.60},
        'medium_volatility': {'atr_max': 3.0, 'forbidden_min': 0.35, 'forbidden_max': 0.65},
        'high_volatility': {'atr_max': 100.0, 'forbidden_min': 0.30, 'forbidden_max': 0.70}
    }
    
    # ========================================================================
    # VOLUME CONTRACTION
    # ========================================================================
    
    VOLUME_CONTRACTION_RATIO = 0.8  # Откат на пониженном объёме < 80% среднего
    
    # ========================================================================
    # BID/ASK IMBALANCE
    # ========================================================================
    
    MAX_BID_ASK_IMBALANCE = 0.35  # Дисбаланс Bid/Ask ≤ 35%
    
    @staticmethod
    async def check_all_filters(ticker: str, df: pd.DataFrame, entry: float, 
                               stop: float, atr: float, direction: str, 
                               client: XTClient, atr_percent: float = None) -> Dict:
        """Проверка всех консервативных фильтров"""
        
        result = {
            'passed': False,
            'volume_24h': None,
            'spread': None,
            'market_cap_rank': None,
            'reasons': []
        }
        
        # 1. Находим ближайший уровень поддержки/сопротивления
        support_resistance_level = ConservativeFilters._find_nearest_level(df, entry, direction)
        
        if support_resistance_level:
            # 1. Качество уровня (минимум 2 касания)
            level_quality = ConservativeFilters.check_level_quality(df, support_resistance_level, direction)
            if not level_quality['passed']:
                result['reasons'].append(level_quality['reason'])
                return result
            
            # 2. Качество HTF уровня (минимум 2 касания + объём)
            htf_quality = ConservativeFilters.check_htf_level_quality(df, support_resistance_level, direction)
            if not htf_quality['passed']:
                result['reasons'].append(htf_quality['reason'])
                return result
            
            # 4. Свеча пробоя уровня (тело ≥ 55% выше/ниже уровня)
            breakout_check = ConservativeFilters.check_breakout_candle(df, support_resistance_level, direction)
            if not breakout_check['passed']:
                result['reasons'].append(breakout_check['reason'])
                return result
        
        # 3. Дистанция до противоположного уровня ≥ 1.4 ATR
        opposite_distance = ConservativeFilters.check_opposite_level_distance(df, entry, direction, atr)
        if not opposite_distance['passed']:
            result['reasons'].append(opposite_distance['reason'])
            return result
        
        # 5. Откат на пониженном объёме (volume contraction)
        volume_contraction = ConservativeFilters.check_volume_contraction(df)
        if not volume_contraction['passed']:
            result['reasons'].append(volume_contraction['reason'])
            return result
        
        # 6. Дисбаланс Bid/Ask ≤ 35%
        bid_ask_check = await ConservativeFilters.check_bid_ask_imbalance(ticker, client)
        if not bid_ask_check['passed']:
            result['reasons'].append(bid_ask_check['reason'])
            return result
        
        # Все фильтры пройдены
        result['passed'] = True
        return result
    
    @staticmethod
    def _find_nearest_level(df: pd.DataFrame, entry: float, direction: str) -> Optional[float]:
        """Найти ближайший уровень поддержки/сопротивления"""
        if df.empty or len(df) < 50:
            return None
        
        recent = df.tail(50)
        window = 10
        
        if direction == 'LONG':
            # Для лонга: ищем ближайшую поддержку снизу
            supports = []
            for i in range(window, len(recent) - window):
                if recent.iloc[i]['low'] == recent.iloc[i-window:i+window+1]['low'].min():
                    if recent.iloc[i]['low'] < entry:
                        supports.append(recent.iloc[i]['low'])
            
            if supports:
                return max(supports)  # Ближайшая поддержка снизу
        else:
            # Для шорта: ищем ближайшее сопротивление сверху
            resistances = []
            for i in range(window, len(recent) - window):
                if recent.iloc[i]['high'] == recent.iloc[i-window:i+window+1]['high'].max():
                    if recent.iloc[i]['high'] > entry:
                        resistances.append(recent.iloc[i]['high'])
            
            if resistances:
                return min(resistances)  # Ближайшее сопротивление сверху
        
        return None
    
    @staticmethod
    def check_level_quality(df: pd.DataFrame, level: float, direction: str) -> Dict:
        """
        Проверка качества уровня: минимум 2 касания
        """
        result = {'passed': False, 'reason': ''}
        
        if df.empty or len(df) < 50:
            result['passed'] = True
            return result
        
        tolerance = level * 0.003  # 0.3% допуск
        touches = 0
        
        recent = df.tail(50)
        
        for idx, row in recent.iterrows():
            low = row['low']
            high = row['high']
            
            if direction == 'LONG':
                if abs(low - level) <= tolerance:
                    touches += 1
            else:
                if abs(high - level) <= tolerance:
                    touches += 1
        
        if touches < ConservativeFilters.MIN_LEVEL_TOUCHES:
            result['reason'] = f"Level touches {touches} < {ConservativeFilters.MIN_LEVEL_TOUCHES}"
            return result
        
        result['passed'] = True
        return result
    
    @staticmethod
    def check_htf_level_quality(df: pd.DataFrame, level: float, direction: str) -> Dict:
        """
        HTF уровень: минимум 2 касания + объём ≥ 1.3× среднего
        """
        result = {'passed': False, 'reason': ''}
        
        if df.empty or len(df) < 50:
            result['passed'] = True
            return result
        
        tolerance = level * 0.005  # 0.5% допуск для HTF
        touches = 0
        volume_confirmed = False
        
        recent = df.tail(50)
        avg_volume = recent['volume'].mean()
        
        for idx, row in recent.iterrows():
            low = row['low']
            high = row['high']
            volume = row['volume']
            
            touched = False
            
            if direction == 'LONG':
                if abs(low - level) <= tolerance:
                    touched = True
            else:
                if abs(high - level) <= tolerance:
                    touched = True
            
            if touched:
                touches += 1
                if volume >= avg_volume * ConservativeFilters.HTF_VOLUME_MULTIPLIER:
                    volume_confirmed = True
        
        if touches < ConservativeFilters.MIN_HTF_LEVEL_TOUCHES:
            result['reason'] = f"HTF level touches {touches} < {ConservativeFilters.MIN_HTF_LEVEL_TOUCHES}"
            return result
        
        if not volume_confirmed:
            result['reason'] = f"HTF level not confirmed by volume (need ≥ {ConservativeFilters.HTF_VOLUME_MULTIPLIER}× avg)"
            return result
        
        result['passed'] = True
        return result
    
    @staticmethod
    def check_opposite_level_distance(df: pd.DataFrame, entry: float, 
                                      direction: str, atr: float) -> Dict:
        """Дистанция до противоположного уровня ≥ 1.4 ATR"""
        result = {'passed': False, 'reason': ''}
        
        if df.empty or len(df) < 50 or atr == 0:
            result['passed'] = True
            return result
        
        recent = df.tail(50)
        window = 10
        
        if direction == 'LONG':
            # Для лонга: ищем ближайшее сопротивление сверху
            resistances = []
            for i in range(window, len(recent) - window):
                if recent.iloc[i]['high'] == recent.iloc[i-window:i+window+1]['high'].max():
                    if recent.iloc[i]['high'] > entry:
                        resistances.append(recent.iloc[i]['high'])
            
            if not resistances:
                result['passed'] = True
                return result
            
            nearest = min(resistances)
            distance = nearest - entry
            
        else:  # SHORT
            # Для шорта: ищем ближайшую поддержку снизу
            supports = []
            for i in range(window, len(recent) - window):
                if recent.iloc[i]['low'] == recent.iloc[i-window:i+window+1]['low'].min():
                    if recent.iloc[i]['low'] < entry:
                        supports.append(recent.iloc[i]['low'])
            
            if not supports:
                result['passed'] = True
                return result
            
            nearest = max(supports)
            distance = entry - nearest
        
        min_distance = atr * ConservativeFilters.MIN_OPPOSITE_LEVEL_DISTANCE_ATR
        
        if distance < min_distance:
            result['reason'] = f"Opposite level distance {distance/atr:.2f} ATR < {ConservativeFilters.MIN_OPPOSITE_LEVEL_DISTANCE_ATR} ATR"
            return result
        
        result['passed'] = True
        return result
    
    @staticmethod
    def check_breakout_candle(df: pd.DataFrame, level: float, direction: str) -> Dict:
        """
        Свеча пробоя уровня: тело ≥ 55% свечи выше/ниже уровня
        Или цена находится близко к уровню (в пределах 0.5% от уровня)
        """
        result = {'passed': False, 'reason': ''}
        
        if df.empty or len(df) < 5:
            result['passed'] = True
            return result
        
        current_price = df.iloc[-1]['close']
        level_tolerance = level * 0.005  # 0.5% допуск
        
        # Если цена близко к уровню (в пределах 0.5%) - разрешаем
        if direction == 'LONG' and abs(current_price - level) <= level_tolerance:
            result['passed'] = True
            return result
        elif direction == 'SHORT' and abs(current_price - level) <= level_tolerance:
            result['passed'] = True
            return result
        
        # Проверяем последние 5 свечей на наличие пробоя
        recent = df.tail(5)
        
        for idx, row in recent.iterrows():
            body = abs(row['close'] - row['open'])
            full_range = row['high'] - row['low']
            
            if full_range == 0:
                continue
            
            if direction == 'LONG':
                # Для лонга: свеча закрылась выше уровня
                if row['close'] > level:
                    # Проверяем, что тело ≥ 55% свечи выше уровня
                    body_above = row['close'] - max(row['open'], level)
                    candle_above = row['high'] - level
                    
                    if candle_above > 0 and body_above / candle_above >= ConservativeFilters.BREAKOUT_BODY_RATIO:
                        result['passed'] = True
                        return result
            else:
                # Для шорта: свеча закрылась ниже уровня
                if row['close'] < level:
                    body_below = min(row['open'], level) - row['close']
                    candle_below = level - row['low']
                    
                    if candle_below > 0 and body_below / candle_below >= ConservativeFilters.BREAKOUT_BODY_RATIO:
                        result['passed'] = True
                        return result
        
        result['reason'] = f"No valid breakout candle (body ≥ {ConservativeFilters.BREAKOUT_BODY_RATIO*100:.0f}% above/below level)"
        return result
    
    @staticmethod
    def check_volume_contraction(df: pd.DataFrame) -> Dict:
        """Откат на пониженном объёме (volume contraction)"""
        result = {'passed': False, 'reason': ''}
        
        if df.empty or len(df) < 20:
            result['passed'] = True
            return result
        
        # Средний объём за последние 20 свечей
        recent_20 = df.tail(20)
        avg_volume = recent_20['volume'].mean()
        
        # Объём последних 3 свечей (откат)
        recent_3 = df.tail(3)
        pullback_volume = recent_3['volume'].mean()
        
        if avg_volume == 0:
            result['passed'] = True
            return result
        
        volume_ratio = pullback_volume / avg_volume
        
        # Откат должен быть на пониженном объёме
        if volume_ratio > ConservativeFilters.VOLUME_CONTRACTION_RATIO:
            result['reason'] = f"Pullback volume {volume_ratio*100:.0f}% > {ConservativeFilters.VOLUME_CONTRACTION_RATIO*100:.0f}% (no contraction)"
            return result
        
        result['passed'] = True
        return result
    
    @staticmethod
    async def check_bid_ask_imbalance(ticker: str, client: XTClient) -> Dict:
        """Дисбаланс Bid/Ask ≤ 35%"""
        result = {'passed': False, 'reason': ''}
        
        try:
            orderbook = await client.get_orderbook(ticker, limit=20)
            
            if not orderbook:
                result['passed'] = True
                return result
            
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if not bids or not asks:
                result['passed'] = True
                return result
            
            # Суммарный объём (с проверкой на пустые списки)
            try:
                total_bid_volume = sum(float(vol) for _, vol in bids[:10] if len(bids) > 0)
                total_ask_volume = sum(float(vol) for _, vol in asks[:10] if len(asks) > 0)
            except (ValueError, TypeError, IndexError) as e:
                result['passed'] = True
                return result
            
            total_volume = total_bid_volume + total_ask_volume
            
            if total_volume == 0:
                result['passed'] = True
                return result
            
            # Дисбаланс
            imbalance = abs(total_bid_volume - total_ask_volume) / total_volume
            
            if imbalance > ConservativeFilters.MAX_BID_ASK_IMBALANCE:
                result['reason'] = f"Bid/Ask imbalance {imbalance*100:.1f}% > {ConservativeFilters.MAX_BID_ASK_IMBALANCE*100:.0f}%"
                return result
            
            result['passed'] = True
            return result
            
        except Exception as e:
            result['passed'] = True
            return result
