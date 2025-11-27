"""
Ультраконсервативные фильтры перед генерацией сигнала
"""

import pandas as pd
from typing import Optional, Dict
from exchange.xt_client import XTClient


class ConservativeFilters:
    """Фильтры для отсева некачественных сигналов"""
    
    # Константы
    TOP_COINS_LIMIT = 300
    MIN_VOLUME_24H = 2_500_000  # $2.5M минимум
    MAX_SPREAD_PERCENT = 0.35  # 0.35% максимум
    MIN_ATR_RATIO = 0.8  # Минимальная дистанция до ближайшего уровня в ATR (≥ 0.8 ATR)
    MAX_ATR_RATIO = 3.0  # Максимальный размер стопа в ATR (≤ 3 ATR)
    
    # Минимальная корреляция с BTC/ETH для альткоинов
    MIN_BTC_CORRELATION = -0.3  # Не должно быть сильной отрицательной корреляции
    
    # Channel Position Filter - адаптивные зоны
    CHANNEL_ZONES = {
        'low_volatility': {'atr_max': 1.0, 'forbidden_min': 0.35, 'forbidden_max': 0.65},    # ATR < 1%: 35-65%
        'medium_volatility': {'atr_max': 3.0, 'forbidden_min': 0.30, 'forbidden_max': 0.70}, # ATR 1-3%: 30-70%
        'high_volatility': {'atr_max': 100.0, 'forbidden_min': 0.25, 'forbidden_max': 0.75}  # ATR > 3%: 25-75%
    }
    
    @staticmethod
    async def check_top_100(ticker: str, client: XTClient) -> bool:
        """Проверка, что монета в ТОП-300 по капитализации"""
        # TODO: Интеграция с CoinGecko/CoinMarketCap API
        # Пока упрощённо - все пары из списка считаем ТОП-300
        return True
    
    @staticmethod
    async def check_volume(ticker: str, client: XTClient) -> Optional[float]:
        """Проверка объёма торгов за 24ч"""
        try:
            ticker_data = await client.get_ticker(ticker)
            
            if not ticker_data:
                return None
            
            # Объём в USDT за 24ч
            volume_24h = ticker_data.get('quoteVolume', 0)
            
            if volume_24h < ConservativeFilters.MIN_VOLUME_24H:
                return None
            
            return volume_24h
            
        except Exception as e:
            print(f"Ошибка проверки объёма {ticker}: {e}")
            return None
    
    @staticmethod
    async def check_spread(ticker: str, client: XTClient) -> Optional[float]:
        """Проверка спреда"""
        try:
            orderbook = await client.get_orderbook(ticker, limit=1)
            
            if not orderbook or not orderbook.get('bids') or not orderbook.get('asks'):
                return None
            
            best_bid = orderbook['bids'][0][0]
            best_ask = orderbook['asks'][0][0]
            
            spread_percent = ((best_ask - best_bid) / best_bid) * 100
            
            if spread_percent > ConservativeFilters.MAX_SPREAD_PERCENT:
                return None
            
            return spread_percent
            
        except Exception as e:
            print(f"Ошибка проверки спреда {ticker}: {e}")
            return None
    
    @staticmethod
    def check_volatility(df: pd.DataFrame, atr: float, entry: float, stop: float) -> bool:
        """Проверка волатильности и размера стопа относительно ATR"""
        
        # Размер стопа в ATR
        stop_distance = abs(entry - stop)
        atr_ratio = stop_distance / atr if atr > 0 else 999
        
        # Стоп должен быть не больше 3 ATR
        if atr_ratio > ConservativeFilters.MAX_ATR_RATIO:
            return False
        
        return True
    
    @staticmethod
    def check_level_quality(df: pd.DataFrame, level: float, direction: str) -> bool:
        """
        Проверка качества уровня: минимум 1 касание + подтверждение объёмом
        """
        if df.empty or len(df) < 20:
            return False
        
        tolerance = level * 0.002  # 0.2% допуск
        
        touches = 0
        volume_confirmed = False
        
        # Проверяем последние 50 свечей
        recent = df.tail(50)
        avg_volume = recent['volume'].mean()
        
        for i in range(len(recent)):
            row = recent.iloc[i]
            low = row['low']
            high = row['high']
            volume = row['volume']
            
            if direction == 'LONG':
                # Для LONG проверяем касание уровня снизу (low)
                if abs(low - level) <= tolerance:
                    touches += 1
                    # Подтверждение объёмом: объём выше среднего при касании
                    if volume > avg_volume * 1.2:
                        volume_confirmed = True
            else:  # SHORT
                # Для SHORT проверяем касание уровня сверху (high)
                if abs(high - level) <= tolerance:
                    touches += 1
                    # Подтверждение объёмом: объём выше среднего при касании
                    if volume > avg_volume * 1.2:
                        volume_confirmed = True
        
        # Минимум 1 касание + подтверждение объёмом
        return touches >= 1 and volume_confirmed
    
    @staticmethod
    def check_distance_to_opposite_level(df: pd.DataFrame, entry: float, 
                                        direction: str, atr: float) -> bool:
        """Проверка дистанции до ближайшего противонаправленного уровня (≥ 0.8 ATR)"""
        
        # Находим локальные максимумы и минимумы
        window = 20
        if len(df) < window:
            return False
        
        recent = df.tail(50)
        
        if direction == 'LONG':
            # Для лонга проверяем ближайшее сопротивление сверху
            resistances = recent[recent['high'] == recent['high'].rolling(window, center=True).max()]['high'].values
            
            if len(resistances) == 0:
                return True
            
            nearest_resistance = min([r for r in resistances if r > entry], default=entry * 1.1)
            distance = nearest_resistance - entry
            
        else:
            # Для шорта проверяем ближайшую поддержку снизу
            supports = recent[recent['low'] == recent['low'].rolling(window, center=True).min()]['low'].values
            
            if len(supports) == 0:
                return True
            
            nearest_support = max([s for s in supports if s < entry], default=entry * 0.9)
            distance = entry - nearest_support
        
        # Дистанция должна быть хотя бы 0.8 ATR
        return distance >= (atr * ConservativeFilters.MIN_ATR_RATIO)
    
    @staticmethod
    def check_channel_position(df: pd.DataFrame, entry: float, atr_percent: float, direction: str) -> Dict:
        """
        Channel Position Filter (адаптивный): не входить в сделку в середине канала
        
        Если ATR% < 1% → запрет зоны 35–65% диапазона
        Если ATR% от 1% до 3% → запрет зоны 30–70%
        Если ATR% > 3% → запрет зоны 25–75%
        
        Returns:
            {'passed': bool, 'reason': str, 'position_percent': float}
        """
        result = {
            'passed': False,
            'reason': '',
            'position_percent': None
        }
        
        if df.empty or len(df) < 20:
            result['passed'] = True
            result['reason'] = "Not enough data for channel check"
            return result
        
        # Находим локальный High и Low за последние 50 свечей
        recent = df.tail(50)
        local_high = recent['high'].max()
        local_low = recent['low'].min()
        
        if local_high == local_low:
            result['passed'] = True
            result['reason'] = "No price range (high == low)"
            return result
        
        # Позиция цены в канале (0 = low, 1 = high)
        channel_range = local_high - local_low
        position_percent = (entry - local_low) / channel_range
        result['position_percent'] = position_percent
        
        # Определяем запретную зону по волатильности
        if atr_percent < 1.0:
            zone = ConservativeFilters.CHANNEL_ZONES['low_volatility']
        elif atr_percent <= 3.0:
            zone = ConservativeFilters.CHANNEL_ZONES['medium_volatility']
        else:
            zone = ConservativeFilters.CHANNEL_ZONES['high_volatility']
        
        forbidden_min = zone['forbidden_min']
        forbidden_max = zone['forbidden_max']
        
        # Проверяем, находится ли цена в запретной зоне
        if forbidden_min <= position_percent <= forbidden_max:
            result['reason'] = f"Price in forbidden channel zone: {position_percent*100:.1f}% (forbidden: {forbidden_min*100:.0f}%-{forbidden_max*100:.0f}% for ATR {atr_percent:.2f}%)"
            return result
        
        # Дополнительная проверка: для LONG цена должна быть ближе к low, для SHORT - к high
        if direction == 'LONG' and position_percent > 0.7:
            result['reason'] = f"LONG entry too high in channel: {position_percent*100:.1f}% > 70%"
            return result
        
        if direction == 'SHORT' and position_percent < 0.3:
            result['reason'] = f"SHORT entry too low in channel: {position_percent*100:.1f}% < 30%"
            return result
        
        result['passed'] = True
        return result
    
    @staticmethod
    async def check_btc_eth_correlation(ticker: str, direction: str, client: XTClient) -> bool:
        """
        Проверка корреляции с BTC/ETH
        Для альткоинов: не входим против сильного движения BTC/ETH
        """
        
        # Для самих BTC/ETH этот фильтр не применяется
        if ticker in ['BTC/USDT', 'ETH/USDT', 'BTCUSDT', 'ETHUSDT']:
            return True
        
        try:
            # Получаем данные BTC
            btc_ticker = await client.get_ticker('BTC/USDT')
            if not btc_ticker:
                return True  # Если нет данных, пропускаем фильтр
            
            # Получаем изменение цены BTC за последний час
            btc_change = btc_ticker.get('percentage', 0)
            
            # Если BTC сильно падает (-2% и более), не открываем лонги по альткоинам
            if direction == 'LONG' and btc_change < -2.0:
                return False
            
            # Если BTC сильно растёт (+2% и более), не открываем шорты по альткоинам
            if direction == 'SHORT' and btc_change > 2.0:
                return False
            
            return True
            
        except Exception as e:
            print(f"Ошибка проверки BTC корреляции: {e}")
            return True  # При ошибке пропускаем фильтр
    
    @staticmethod
    async def check_all_filters(ticker: str, df: pd.DataFrame, entry: float, 
                               stop: float, atr: float, direction: str, 
                               client: XTClient, atr_percent: float = None) -> Dict:
        """Проверка всех фильтров. Возвращает результат и метаданные"""
        
        result = {
            'passed': False,
            'volume_24h': None,
            'spread': None,
            'market_cap_rank': None,
            'reasons': []
        }
        
        # 1. ТОП-300
        if not await ConservativeFilters.check_top_100(ticker, client):
            result['reasons'].append("Не ТОП-300")
            return result
        
        # 2. Объём
        volume = await ConservativeFilters.check_volume(ticker, client)
        if volume is None:
            result['reasons'].append(f"Объём < ${ConservativeFilters.MIN_VOLUME_24H:,.0f}")
            return result
        result['volume_24h'] = volume
        
        # 3. Спред
        spread = await ConservativeFilters.check_spread(ticker, client)
        if spread is None:
            result['reasons'].append(f"Спред > {ConservativeFilters.MAX_SPREAD_PERCENT}%")
            return result
        result['spread'] = spread
        
        # 4. Волатильность и размер стопа (≤ 3 ATR)
        stop_distance = abs(entry - stop)
        atr_ratio = stop_distance / atr if atr > 0 else 999
        if not ConservativeFilters.check_volatility(df, atr, entry, stop):
            result['reasons'].append(f"Стоп {atr_ratio:.2f} ATR > {ConservativeFilters.MAX_ATR_RATIO} ATR")
            return result
        
        # 5. Качество уровня (минимум 1 касание + подтверждение объёмом)
        if not ConservativeFilters.check_level_quality(df, entry, direction):
            result['reasons'].append("Качество уровня: недостаточно касаний или нет подтверждения объёмом")
            return result
        
        # 6. Дистанция до противоположного уровня (≥ 0.8 ATR)
        if not ConservativeFilters.check_distance_to_opposite_level(df, entry, direction, atr):
            result['reasons'].append(f"Дистанция до противоположного уровня < {ConservativeFilters.MIN_ATR_RATIO} ATR")
            return result
        
        # 7. Channel Position Filter (адаптивный)
        if atr_percent is not None:
            channel_check = ConservativeFilters.check_channel_position(df, entry, atr_percent, direction)
            if not channel_check['passed']:
                result['reasons'].append(channel_check['reason'])
            return result
        
        # 8. BTC/ETH корреляция
        if not await ConservativeFilters.check_btc_eth_correlation(ticker, direction, client):
            result['reasons'].append("Неблагоприятное движение BTC/ETH")
            return result
        
        # Все фильтры пройдены
        result['passed'] = True
        return result
