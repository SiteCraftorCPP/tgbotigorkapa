"""
Менеджер администраторов бота
"""

from .models import Admin, SessionLocal
from typing import Optional, List


class AdminManager:
    """Управление администраторами"""
    
    @staticmethod
    def is_admin(telegram_id: str) -> bool:
        """Проверка, является ли пользователь админом"""
        db = SessionLocal()
        try:
            admin = db.query(Admin).filter(
                Admin.telegram_id == str(telegram_id),
                Admin.is_active == True
            ).first()
            return admin is not None
        finally:
            db.close()
    
    @staticmethod
    def add_admin(telegram_id: str, username: str = None, first_name: str = None) -> bool:
        """Добавить администратора"""
        db = SessionLocal()
        try:
            # Проверка существования
            existing = db.query(Admin).filter(Admin.telegram_id == str(telegram_id)).first()
            
            if existing:
                # Активировать, если был деактивирован
                existing.is_active = True
                if username:
                    existing.username = username
                if first_name:
                    existing.first_name = first_name
            else:
                admin = Admin(
                    telegram_id=str(telegram_id),
                    username=username,
                    first_name=first_name
                )
                db.add(admin)
            
            db.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка добавления админа: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    @staticmethod
    def remove_admin(telegram_id: str) -> bool:
        """Удалить администратора (деактивировать)"""
        db = SessionLocal()
        try:
            admin = db.query(Admin).filter(Admin.telegram_id == str(telegram_id)).first()
            
            if admin:
                admin.is_active = False
                db.commit()
                return True
            return False
        except Exception as e:
            print(f"❌ Ошибка удаления админа: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    @staticmethod
    def get_all_admins() -> List[Admin]:
        """Получить список всех активных админов"""
        db = SessionLocal()
        try:
            return db.query(Admin).filter(Admin.is_active == True).all()
        finally:
            db.close()
    
    @staticmethod
    def count_admins() -> int:
        """Количество активных админов"""
        db = SessionLocal()
        try:
            return db.query(Admin).filter(Admin.is_active == True).count()
        finally:
            db.close()

