"""
Менеджер рисков для ультраконсервативной торговли
"""

from .models import Signal, SessionLocal
from datetime import datetime, timedelta
from typing import Optional, Tuple


class RiskManager:
    """Управление рисками согласно ТЗ"""
    
    # Константы
    MAX_RISK_PER_TRADE = 1.0  # 1% на сделку
    MAX_TOTAL_RISK = 10.0  # 10% суммарный риск
    MAX_SIGNALS_PER_DAY = 20
    MAX_SIGNALS_PER_COIN = 1
    COOLDOWN_HOURS = 1  # Cooldown 1 час для монеты после закрытия сигнала
    
    @staticmethod
    def can_open_new_signal(ticker: str) -> Tuple[bool, str]:
        """Проверка возможности открытия нового сигнала"""
        db = SessionLocal()
        
        try:
            # Нормализация тикера (CAKE/USDT и CAKE/USD считаются одной парой)
            base_coin = ticker.split('/')[0] if '/' in ticker else ticker
            
            # 1. Проверка активного сигнала на эту монету (с учётом разных форматов)
            # Блокируем только WAITING и IN_POSITION (TP1_HIT/TP2_HIT/TP3_HIT не блокируют - это частично закрытые)
            active_signal = db.query(Signal).filter(
                (Signal.ticker == ticker) | (Signal.ticker.like(f"{base_coin}/%")),
                Signal.status.in_(['WAITING', 'IN_POSITION'])
            ).first()
            
            if active_signal:
                return False, f"Уже есть активный сигнал на {active_signal.ticker}"
            
            # 2. Проверка cooldown для монеты (с учётом разных форматов)
            cooldown_time = datetime.utcnow() - timedelta(hours=RiskManager.COOLDOWN_HOURS)
            recent_signal = db.query(Signal).filter(
                (Signal.ticker == ticker) | (Signal.ticker.like(f"{base_coin}/%")),
                Signal.closed_at.isnot(None),  # Только закрытые сигналы
                Signal.closed_at >= cooldown_time
            ).first()
            
            if recent_signal:
                return False, f"Cooldown для {ticker} (ещё {RiskManager.COOLDOWN_HOURS} час)"
            
            # Убраны ограничения:
            # - Лимит сигналов за сутки (MAX_SIGNALS_PER_DAY)
            # - Суммарный риск (MAX_TOTAL_RISK)
            # - Риск на сделку (MAX_RISK_PER_TRADE) - используется только для расчёта размера позиции
            
            return True, "OK"
            
        finally:
            db.close()
    
    @staticmethod
    def calculate_position_size(entry_price: float, stop_loss: float, 
                               account_balance: float, risk_percent: float = MAX_RISK_PER_TRADE) -> float:
        """Расчёт размера позиции на основе SL"""
        
        # Размер риска в USDT
        risk_amount = account_balance * (risk_percent / 100)
        
        # Разница между входом и стопом (в процентах)
        stop_distance_percent = abs(entry_price - stop_loss) / entry_price
        
        # Размер позиции = риск / дистанция до стопа
        position_size = risk_amount / stop_distance_percent
        
        return position_size
    
    @staticmethod
    def get_active_signals_count() -> int:
        """Количество активных сигналов"""
        db = SessionLocal()
        try:
            return db.query(Signal).filter(
                Signal.status.in_(['WAITING', 'IN_POSITION', 'TP1_HIT', 'TP2_HIT', 'TP3_HIT'])
            ).count()
        finally:
            db.close()
    
    @staticmethod
    def get_current_total_risk() -> float:
        """Текущий суммарный риск"""
        active_count = RiskManager.get_active_signals_count()
        return active_count * RiskManager.MAX_RISK_PER_TRADE

