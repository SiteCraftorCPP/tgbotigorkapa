#!/usr/bin/env python3
"""
Скрипт для проверки успешных сигналов, которые прошли все фильтры
"""
from database.models import init_db, Signal, SessionLocal
from datetime import datetime, timedelta
from collections import Counter

def check_successful_signals(days: int = 7):
    """Проверка сигналов, которые прошли фильтры за последние N дней"""
    init_db()
    db = SessionLocal()
    
    try:
        # Дата начала периода
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Все сигналы за период (если сигнал в БД - значит прошел фильтры)
        all_signals = db.query(Signal).filter(
            Signal.created_at >= start_date
        ).order_by(Signal.created_at.desc()).all()
        
        print(f"\n{'='*80}")
        print(f"📊 СИГНАЛЫ, ПРОШЕДШИЕ ФИЛЬТРЫ (за последние {days} дней)")
        print(f"{'='*80}\n")
        
        # Общая статистика
        total = len(all_signals)
        print(f"✅ Всего сигналов прошло фильтры: {total}\n")
        
        if total == 0:
            print("  ⚠️  Нет сигналов за этот период")
            return
        
        # Статистика по статусам
        statuses = Counter([s.status for s in all_signals])
        print("📈 Статистика по статусам:")
        print("-" * 80)
        for status, count in statuses.most_common():
            percentage = (count / total) * 100
            print(f"  • {status:20} : {count:3} ({percentage:5.1f}%)")
        
        # Статистика по результатам
        results = Counter([s.result for s in all_signals if s.result])
        if results:
            print(f"\n💰 Статистика по результатам:")
            print("-" * 80)
            for result, count in results.most_common():
                percentage = (count / total) * 100
                emoji = "🟢" if result == "WIN" else "🔴" if result == "LOSS" else "⚪"
                print(f"  {emoji} {result:10} : {count:3} ({percentage:5.1f}%)")
        
        # Статистика по направлениям
        directions = Counter([s.direction for s in all_signals])
        print(f"\n📊 Статистика по направлениям:")
        print("-" * 80)
        for direction, count in directions.most_common():
            percentage = (count / total) * 100
            emoji = "📈" if direction == "LONG" else "📉"
            print(f"  {emoji} {direction:10} : {count:3} ({percentage:5.1f}%)")
        
        # PnL статистика
        signals_with_pnl = [s for s in all_signals if s.pnl_percent is not None]
        if signals_with_pnl:
            total_pnl = sum([s.pnl_percent for s in signals_with_pnl])
            avg_pnl = total_pnl / len(signals_with_pnl)
            winning_pnl = [s.pnl_percent for s in signals_with_pnl if s.pnl_percent > 0]
            losing_pnl = [s.pnl_percent for s in signals_with_pnl if s.pnl_percent < 0]
            
            print(f"\n💵 PnL статистика:")
            print("-" * 80)
            print(f"  • Всего с PnL: {len(signals_with_pnl)}")
            if winning_pnl:
                print(f"  • Средний прибыльный PnL: +{sum(winning_pnl)/len(winning_pnl):.2f}%")
            if losing_pnl:
                print(f"  • Средний убыточный PnL: {sum(losing_pnl)/len(losing_pnl):.2f}%")
            print(f"  • Средний PnL: {avg_pnl:+.2f}%")
            print(f"  • Общий PnL: {total_pnl:+.2f}%")
        
        # Последние 10 сигналов
        print(f"\n🕐 Последние 10 сигналов:")
        print("-" * 80)
        for i, sig in enumerate(all_signals[:10], 1):
            age = datetime.utcnow() - sig.created_at
            age_str = f"{age.days}д {age.seconds//3600}ч {age.seconds%3600//60}м назад"
            
            status_emoji = {
                'WAITING': '⏳',
                'IN_POSITION': '🟢',
                'TP1_HIT': '🟡',
                'TP2_HIT': '🟠',
                'TP3_HIT': '🟢',
                'TP4_HIT': '🟢',
                'STOPPED_OUT': '🔴',
                'CANCELLED': '⚪',
                'CLOSED_FULL_TP': '✅'
            }.get(sig.status, '❓')
            
            result_str = f" | {sig.result}" if sig.result else ""
            pnl_str = f" | PnL: {sig.pnl_percent:+.2f}%" if sig.pnl_percent is not None else ""
            
            print(f"  {i:2}. {status_emoji} {sig.ticker:12} {sig.direction:5} | {sig.status:15}{result_str}{pnl_str}")
            print(f"      Создан: {sig.created_at.strftime('%Y-%m-%d %H:%M:%S')} ({age_str})")
        
        # Активные сигналы (блокирующие новые)
        active_signals = [s for s in all_signals if s.status in ['WAITING', 'IN_POSITION']]
        if active_signals:
            print(f"\n🔄 Активные сигналы (блокируют новые): {len(active_signals)}")
            print("-" * 80)
            for sig in active_signals:
                age = datetime.utcnow() - sig.created_at
                print(f"  • {sig.ticker:12} {sig.direction:5} | {sig.status:15} | {age.days}д {age.seconds//3600}ч назад")
        
        print(f"\n{'='*80}\n")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    check_successful_signals(days)




