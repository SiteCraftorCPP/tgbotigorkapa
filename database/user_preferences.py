"""
Управление настройками пользователей (язык и т.д.)
"""

from .models import SessionLocal, Base, engine
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from typing import Optional

class UserPreference(Base):
    __tablename__ = 'user_preferences'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String(50), unique=True, nullable=False)
    language = Column(String(5), default='en')  # 'en' или 'ru'
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserPreferenceManager:
    """Управление настройками пользователей"""
    
    @staticmethod
    def get_language(telegram_id: str) -> str:
        """Получить язык пользователя (по умолчанию 'en')"""
        db = SessionLocal()
        try:
            pref = db.query(UserPreference).filter(
                UserPreference.telegram_id == str(telegram_id)
            ).first()
            
            return pref.language if pref else 'en'
        finally:
            db.close()
    
    @staticmethod
    def set_language(telegram_id: str, language: str) -> bool:
        """Установить язык пользователя"""
        if language not in ['en', 'ru']:
            return False
        
        db = SessionLocal()
        try:
            pref = db.query(UserPreference).filter(
                UserPreference.telegram_id == str(telegram_id)
            ).first()
            
            if pref:
                pref.language = language
                pref.updated_at = datetime.utcnow()
            else:
                pref = UserPreference(telegram_id=str(telegram_id), language=language)
                db.add(pref)
            
            db.commit()
            return True
        except Exception as e:
            print(f"Ошибка установки языка: {e}")
            db.rollback()
            return False
        finally:
            db.close()

