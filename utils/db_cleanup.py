"""
Автоматическая очистка старых данных в БД
"""
from datetime import datetime, timedelta
from database.models import Signal, SessionLocal
from utils.logger import logger


class DatabaseCleanup:
    """Очистка старых записей в БД"""
    
    # Хранить сигналы за последние N дней
    SIGNALS_RETENTION_DAYS = 30
    
    @classmethod
    def cleanup_old_signals(cls, days: int = None) -> int:
        """
        Удалить сигналы старше N дней
        
        Args:
            days: количество дней (по умолчанию SIGNALS_RETENTION_DAYS)
            
        Returns:
            Количество удалённых записей
        """
        if days is None:
            days = cls.SIGNALS_RETENTION_DAYS
        
        db = SessionLocal()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Удаляем только закрытые сигналы старше cutoff_date
            deleted = db.query(Signal).filter(
                Signal.created_at < cutoff_date,
                Signal.status.in_(['STOPPED_OUT', 'CLOSED_FULL_TP', 'CANCELLED', 'EXPIRED'])
            ).delete(synchronize_session=False)
            
            db.commit()
            
            if deleted > 0:
                logger.info(f"🗑️ Cleaned up {deleted} old signals (older than {days} days)")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Error cleaning up signals: {e}")
            db.rollback()
            return 0
        finally:
            db.close()
    
    @classmethod
    def get_db_stats(cls) -> dict:
        """Получить статистику БД"""
        db = SessionLocal()
        try:
            total_signals = db.query(Signal).count()
            
            active_signals = db.query(Signal).filter(
                Signal.status.in_(['WAITING', 'IN_POSITION', 'TP1_HIT', 'TP2_HIT', 'TP3_HIT'])
            ).count()
            
            closed_signals = db.query(Signal).filter(
                Signal.status.in_(['STOPPED_OUT', 'CLOSED_FULL_TP', 'CANCELLED', 'EXPIRED'])
            ).count()
            
            # Самый старый сигнал
            oldest = db.query(Signal).order_by(Signal.created_at.asc()).first()
            oldest_date = oldest.created_at if oldest else None
            
            # Сигналы за последние 24 часа
            day_ago = datetime.utcnow() - timedelta(days=1)
            signals_24h = db.query(Signal).filter(Signal.created_at >= day_ago).count()
            
            return {
                'total': total_signals,
                'active': active_signals,
                'closed': closed_signals,
                'oldest_date': oldest_date,
                'signals_24h': signals_24h
            }
            
        finally:
            db.close()
    
    @classmethod
    def vacuum_database(cls):
        """Оптимизация SQLite БД (VACUUM)"""
        from sqlalchemy import text
        db = SessionLocal()
        try:
            db.execute(text("VACUUM"))
            db.commit()
            logger.info("✅ Database vacuumed successfully")
        except Exception as e:
            logger.error(f"Error vacuuming database: {e}")
        finally:
            db.close()


async def run_scheduled_cleanup():
    """Запуск плановой очистки (вызывается из main.py)"""
    deleted = DatabaseCleanup.cleanup_old_signals()
    if deleted > 0:
        DatabaseCleanup.vacuum_database()
    return deleted

