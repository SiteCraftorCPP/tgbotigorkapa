import pandas as pd
import numpy as np
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import AverageTrueRange
from ta.volume import VolumeWeightedAveragePrice
import config

class TechnicalAnalysis:
    """Класс для технического анализа"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        
    def calculate_all_indicators(self) -> pd.DataFrame:
        """Расчёт всех индикаторов"""
        if self.df.empty:
            return self.df
        
        # EMA
        self.df['ema_21'] = EMAIndicator(
            close=self.df['close'],
            window=21
        ).ema_indicator()
        
        self.df['ema_50'] = EMAIndicator(
            close=self.df['close'],
            window=config.EMA_SHORT
        ).ema_indicator()
        
        self.df['ema_200'] = EMAIndicator(
            close=self.df['close'],
            window=config.EMA_LONG
        ).ema_indicator()
        
        # VWAP
        try:
            self.df['vwap'] = VolumeWeightedAveragePrice(
                high=self.df['high'],
                low=self.df['low'],
                close=self.df['close'],
                volume=self.df['volume']
            ).volume_weighted_average_price()
        except:
            self.df['vwap'] = self.df['close']
        
        # RSI
        self.df['rsi'] = RSIIndicator(
            close=self.df['close'],
            window=config.RSI_PERIOD
        ).rsi()
        
        # Stochastic
        stoch = StochasticOscillator(
            high=self.df['high'],
            low=self.df['low'],
            close=self.df['close']
        )
        self.df['stoch_k'] = stoch.stoch()
        self.df['stoch_d'] = stoch.stoch_signal()
        
        # MACD
        macd = MACD(
            close=self.df['close'],
            window_slow=config.MACD_SLOW,
            window_fast=config.MACD_FAST,
            window_sign=config.MACD_SIGNAL
        )
        self.df['macd'] = macd.macd()
        self.df['macd_signal'] = macd.macd_signal()
        self.df['macd_diff'] = macd.macd_diff()
        
        # ATR
        self.df['atr'] = AverageTrueRange(
            high=self.df['high'],
            low=self.df['low'],
            close=self.df['close'],
            window=config.ATR_PERIOD
        ).average_true_range()
        
        # Волатильность
        self.df['volatility'] = self.df['close'].pct_change().rolling(20).std() * 100
        
        # Volume MA
        self.df['volume_ma'] = self.df['volume'].rolling(config.VOLUME_MA_PERIOD).mean()
        
        return self.df
    
    def get_trend_signal(self) -> dict:
        """Определение тренда"""
        if len(self.df) < 2:
            return {'direction': 'NEUTRAL', 'score': 0}
        
        last = self.df.iloc[-1]
        prev = self.df.iloc[-2]
        
        score = 0
        signals = []
        
        # EMA тренд
        if last['close'] > last['ema_50'] > last['ema_200']:
            score += 30
            signals.append('Бычий тренд (EMA)')
        elif last['close'] < last['ema_50'] < last['ema_200']:
            score -= 30
            signals.append('Медвежий тренд (EMA)')
        
        # Пересечение EMA
        if prev['ema_50'] < prev['ema_200'] and last['ema_50'] > last['ema_200']:
            score += 20
            signals.append('Golden Cross')
        elif prev['ema_50'] > prev['ema_200'] and last['ema_50'] < last['ema_200']:
            score -= 20
            signals.append('Death Cross')
        
        # VWAP
        if last['close'] > last['vwap']:
            score += 10
        else:
            score -= 10
        
        return {
            'score': score,
            'signals': signals,
            'direction': 'LONG' if score > 0 else 'SHORT'
        }
    
    def get_momentum_signal(self) -> dict:
        """Анализ моментума"""
        if len(self.df) == 0:
            return {'direction': 'NEUTRAL', 'score': 0}
        
        last = self.df.iloc[-1]
        
        score = 0
        signals = []
        
        # RSI
        if last['rsi'] < config.RSI_OVERSOLD:
            score += 25
            signals.append(f'RSI перепродан ({last["rsi"]:.1f})')
        elif last['rsi'] > config.RSI_OVERBOUGHT:
            score -= 25
            signals.append(f'RSI перекуплен ({last["rsi"]:.1f})')
        elif 40 < last['rsi'] < 60:
            score += 5 if last['rsi'] > 50 else -5
        
        # Stochastic
        if last['stoch_k'] < 20 and last['stoch_k'] > last['stoch_d']:
            score += 15
            signals.append('Stoch бычий сигнал')
        elif last['stoch_k'] > 80 and last['stoch_k'] < last['stoch_d']:
            score -= 15
            signals.append('Stoch медвежий сигнал')
        
        # MACD
        if last['macd_diff'] > 0:
            score += 10
            signals.append('MACD бычий')
        else:
            score -= 10
            signals.append('MACD медвежий')
        
        return {
            'score': score,
            'signals': signals
        }
    
    def get_volume_signal(self) -> dict:
        """Анализ объёмов"""
        if len(self.df) == 0:
            return {'direction': 'NEUTRAL', 'score': 0}
        
        last = self.df.iloc[-1]
        
        score = 0
        signals = []
        
        if last['volume'] > last['volume_ma'] * 1.5:
            score += 20
            signals.append('Высокий объём')
        elif last['volume'] < last['volume_ma'] * 0.5:
            score -= 10
            signals.append('Низкий объём')
        
        return {
            'score': score,
            'signals': signals
        }
    
    def get_volatility_score(self) -> dict:
        """Оценка волатильности"""
        if len(self.df) == 0:
            return {'score': 0}
        
        last = self.df.iloc[-1]
        
        score = 0
        signals = []
        
        # ATR относительно цены
        atr_percent = (last['atr'] / last['close']) * 100
        
        if atr_percent > 2:
            score += 15
            signals.append(f'Высокая волатильность ({atr_percent:.2f}%)')
        elif atr_percent < 0.5:
            score -= 10
            signals.append(f'Низкая волатильность ({atr_percent:.2f}%)')
        else:
            score += 5
        
        return {
            'score': score,
            'signals': signals,
            'atr_percent': atr_percent
        }
    
    def calculate_support_resistance(self) -> dict:
        """Расчёт уровней поддержки и сопротивления"""
        if len(self.df) == 0:
            return {'support': None, 'resistance': None}
        
        last = self.df.iloc[-1]
        
        # Простой метод: локальные min/max за последние N свечей
        lookback = min(50, len(self.df))
        recent = self.df.tail(lookback)
        
        resistance = recent['high'].max()
        support = recent['low'].min()
        
        return {
            'support': support,
            'resistance': resistance,
            'current': last['close']
        }

