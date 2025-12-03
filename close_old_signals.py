#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Закрытие старых активных сигналов для освобождения лимита
"""
from database.models import Signal, SessionLocal
from datetime import datetime, timedelta
from utils.logger import log_info

def close_old_active_signals(days_old: int = 1):
    """Закрыть активные сигналы старше N дней"""
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=days_old)
        
        old_signals = db.query(Signal).filter(
            Signal.status.in_(['WAITING', 'IN_POSITION', 'TP1_HIT', 'TP2_HIT', 'TP3_HIT']),
            Signal.created_at < cutoff
        ).all()
        
        if not old_signals:
            print(f"✅ Нет активных сигналов старше {days_old} дня")
            return 0
        
        print(f"🔍 Найдено {len(old_signals)} старых активных сигналов:")
        for sig in old_signals:
            age = datetime.utcnow() - sig.created_at
            print(f"  • {sig.ticker:15} | {sig.status:12} | Создан: {sig.created_at.strftime('%Y-%m-%d %H:%M')} ({age.days}д {age.seconds//3600}ч назад)")
        
        # Закрываем как CANCELLED
        for sig in old_signals:
            sig.status = 'CANCELLED'
            sig.closed_at = datetime.utcnow()
        
        db.commit()
        print(f"\n✅ Закрыто {len(old_signals)} старых сигналов")
        log_info(f"Closed {len(old_signals)} old active signals (older than {days_old} days)")
        
        return len(old_signals)
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        db.rollback()
        return 0
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("🗑️  ЗАКРЫТИЕ СТАРЫХ АКТИВНЫХ СИГНАЛОВ")
    print("=" * 60)
    
    closed = close_old_active_signals(days_old=1)
    
    # Показываем текущую статистику
    from database.risk_manager import RiskManager
    active_count = RiskManager.get_active_signals_count()
    max_allowed = RiskManager.MAX_ACTIVE_SIGNALS
    
    print(f"\n📊 Текущая статистика:")
    print(f"   Активных сигналов: {active_count}/{max_allowed}")
    
    if active_count < max_allowed:
        print(f"   ✅ Лимит не превышен, новые сигналы могут создаваться")
    else:
        print(f"   ⚠️  Лимит превышен! Увеличьте max_active_signals или закройте больше старых сигналов")

