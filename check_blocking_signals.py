#!/usr/bin/env python3
"""
Скрипт для проверки блокирующих сигналов в БД
"""
from database.models import init_db, Signal, SessionLocal
from datetime import datetime, timedelta

def check_blocking_signals():
    """Проверка активных сигналов, которые блокируют новые"""
    init_db()
    db = SessionLocal()
    
    try:
        # 1. Активные сигналы (блокируют новые)
        active_signals = db.query(Signal).filter(
            Signal.status.in_(['WAITING', 'IN_POSITION', 'TP1_HIT', 'TP2_HIT', 'TP3_HIT'])
        ).all()
        
        print(f"\n🔴 АКТИВНЫЕ СИГНАЛЫ (блокируют новые): {len(active_signals)}")
        print("=" * 80)
        
        if active_signals:
            for sig in active_signals:
                age = datetime.utcnow() - sig.created_at
                print(f"  • {sig.ticker:15} | {sig.status:12} | Создан: {sig.created_at.strftime('%Y-%m-%d %H:%M')} ({age.days}д {age.seconds//3600}ч назад)")
        else:
            print("  ✅ Нет активных сигналов")
        
        # 2. Недавно закрытые сигналы (cooldown 1 час)
        cooldown_time = datetime.utcnow() - timedelta(hours=1)
        recent_closed = db.query(Signal).filter(
            Signal.closed_at.isnot(None),
            Signal.closed_at >= cooldown_time
        ).all()
        
        print(f"\n⏳ НЕДАВНО ЗАКРЫТЫЕ (cooldown 1ч): {len(recent_closed)}")
        print("=" * 80)
        
        if recent_closed:
            for sig in recent_closed:
                time_since_close = datetime.utcnow() - sig.closed_at
                remaining = timedelta(hours=1) - time_since_close
                if remaining.total_seconds() > 0:
                    print(f"  • {sig.ticker:15} | Закрыт: {sig.closed_at.strftime('%Y-%m-%d %H:%M')} | Осталось: {int(remaining.total_seconds()/60)} мин")
        else:
            print("  ✅ Нет сигналов в cooldown")
        
        # 3. Старые зависшие сигналы (старше 7 дней)
        old_threshold = datetime.utcnow() - timedelta(days=7)
        old_active = db.query(Signal).filter(
            Signal.status.in_(['WAITING', 'IN_POSITION', 'TP1_HIT', 'TP2_HIT', 'TP3_HIT']),
            Signal.created_at < old_threshold
        ).all()
        
        print(f"\n⚠️  СТАРЫЕ ЗАВИСШИЕ СИГНАЛЫ (старше 7 дней): {len(old_active)}")
        print("=" * 80)
        
        if old_active:
            print("  ⚠️  ВНИМАНИЕ: Эти сигналы могут блокировать новые!")
            for sig in old_active:
                age = datetime.utcnow() - sig.created_at
                print(f"  • {sig.ticker:15} | {sig.status:12} | Создан: {sig.created_at.strftime('%Y-%m-%d %H:%M')} ({age.days} дней назад)")
            print("\n  💡 Рекомендация: Закройте эти сигналы командой:")
            print("     sqlite3 ~/tgbotigorkapa/crypto_signals.db \"UPDATE signals SET status='CANCELLED', closed_at=datetime('now') WHERE status IN ('WAITING', 'IN_POSITION') AND created_at < datetime('now', '-7 days');\"")
        else:
            print("  ✅ Нет старых зависших сигналов")
        
        # 4. Статистика по статусам
        print(f"\n📊 СТАТИСТИКА ПО СТАТУСАМ:")
        print("=" * 80)
        from sqlalchemy import func
        statuses = db.query(Signal.status, func.count(Signal.id)).group_by(Signal.status).all()
        for status, count in statuses:
            print(f"  • {status:20} : {count:4}")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_blocking_signals()

