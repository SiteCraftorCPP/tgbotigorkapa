"""
Ультраконсервативные фильтры перед генерацией сигнала
"""

import pandas as pd
from typing import Optional, Dict
from exchange.xt_client import XTClient


class ConservativeFilters:
    """Фильтры для отсева некачественных сигналов"""
    
    # Константы
    TOP_COINS_LIMIT = 200
    MIN_VOLUME_24H = 3_000_000  # $3M минимум
    MAX_SPREAD_PERCENT = 0.3  # 0.3% максимум
    MIN_ATR_RATIO = 1.5  # Минимальная дистанция до ближайшего уровня в ATR
    MAX_ATR_RATIO = 2.5  # Максимальный размер стопа в ATR
    
    # Ограничение времён суток - ОТКЛЮЧЕНО (торгуем всегда)
    # FORBIDDEN_HOURS = [0, 1, 2, 3, 4, 5]  # Ночные часы низкой ликвидности
    
    # Минимальная корреляция с BTC/ETH для альткоинов
    MIN_BTC_CORRELATION = -0.3  # Не должно быть сильной отрицательной корреляции
    
    @staticmethod
    async def check_top_100(ticker: str, client: XTClient) -> bool:
        """Проверка, что монета в ТОП-100 по капитализации"""
        # TODO: Интеграция с CoinGecko/CoinMarketCap API
        # Пока упрощённо - все пары из списка считаем ТОП-100
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
        
        # Стоп должен быть не больше 2-2.5 ATR
        if atr_ratio > ConservativeFilters.MAX_ATR_RATIO:
            return False
        
        return True
    
    @staticmethod
    def check_level_quality(df: pd.DataFrame, level: float, direction: str) -> bool:
        """Проверка качества уровня (количество касаний, реакция цены)"""
        
        # Упрощённая проверка: есть ли исторические касания уровня
        tolerance = level * 0.002  # 0.2% допуск
        
        touches = 0
        for i in range(len(df)):
            low = df.iloc[i]['low']
            high = df.iloc[i]['high']
            
            if direction == 'LONG':
                if abs(low - level) <= tolerance:
                    touches += 1
            else:
                if abs(high - level) <= tolerance:
                    touches += 1
        
        # Минимум 2 касания для подтверждения уровня
        min_touches = 2
        return touches >= min_touches
    
    @staticmethod
    def check_distance_to_opposite_level(df: pd.DataFrame, entry: float, 
                                        direction: str, atr: float) -> bool:
        """Проверка дистанции до ближайшего противонаправленного уровня"""
        
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
        
        # Дистанция должна быть хотя бы 1.5 ATR
        return distance >= (atr * ConservativeFilters.MIN_ATR_RATIO)
    
    @staticmethod
    def check_time_of_day() -> bool:
        """Проверка времени суток - ОТКЛЮЧЕНО (торгуем всегда)"""
        # Ограничение по времени суток убрано - торгуем всегда
        return True
    
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
                               client: XTClient) -> Dict:
        """Проверка всех фильтров. Возвращает результат и метаданные"""
        
        result = {
            'passed': False,
            'volume_24h': None,
            'spread': None,
            'market_cap_rank': None,
            'reasons': []
        }
        
        # 1. ТОП-100
        if not await ConservativeFilters.check_top_100(ticker, client):
            result['reasons'].append("Не ТОП-100")
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
        
        # 4. Волатильность и размер стопа
        if not ConservativeFilters.check_volatility(df, atr, entry, stop):
            result['reasons'].append(f"Стоп > {ConservativeFilters.MAX_ATR_RATIO} ATR")
            return result
        
        # 5. Качество уровня
        if not ConservativeFilters.check_level_quality(df, entry, direction):
            result['reasons'].append("Слабый уровень входа")
            return result
        
        # 6. Дистанция до противоположного уровня
        if not ConservativeFilters.check_distance_to_opposite_level(df, entry, direction, atr):
            result['reasons'].append("Близко противонаправленный уровень")
            return result
        
        # 7. Ограничение времён суток - ОТКЛЮЧЕНО (торгуем всегда)
        # if not ConservativeFilters.check_time_of_day():
        #     result['reasons'].append("Неблагоприятное время суток (UTC)")
        #     return result
        
        # 8. BTC/ETH корреляция (согласно п.4 инструкции)
        if not await ConservativeFilters.check_btc_eth_correlation(ticker, direction, client):
            result['reasons'].append("Неблагоприятное движение BTC/ETH")
            return result
        
        # Все фильтры пройдены
        result['passed'] = True
        return result

