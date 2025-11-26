"""
Менеджер конфигурации бота из БД
"""

from .models import BotConfig, get_db, SessionLocal
from typing import Optional, List


class ConfigManager:
    """Управление настройками бота из БД"""
    
    @staticmethod
    def get(key: str, default: str = None) -> Optional[str]:
        """Получить значение настройки"""
        db = SessionLocal()
        try:
            config = db.query(BotConfig).filter(BotConfig.key == key).first()
            return config.value if config else default
        finally:
            db.close()
    
    @staticmethod
    def set(key: str, value: str, description: str = None) -> bool:
        """Установить значение настройки"""
        db = SessionLocal()
        try:
            config = db.query(BotConfig).filter(BotConfig.key == key).first()
            
            if config:
                config.value = value
                if description:
                    config.description = description
            else:
                config = BotConfig(key=key, value=value, description=description)
                db.add(config)
            
            db.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения настройки: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    @staticmethod
    def get_all() -> dict:
        """Получить все настройки"""
        db = SessionLocal()
        try:
            configs = db.query(BotConfig).all()
            return {c.key: c.value for c in configs}
        finally:
            db.close()
    
    # Специфичные геттеры
    
    @staticmethod
    def is_bot_enabled() -> bool:
        """Включен ли бот"""
        return ConfigManager.get('bot_enabled', 'true').lower() == 'true'
    
    @staticmethod
    def get_risk_percent() -> float:
        """Процент риска"""
        return float(ConfigManager.get('risk_percent', '1.0'))
    
    @staticmethod
    def get_leverage() -> int:
        """Плечо по умолчанию"""
        return int(ConfigManager.get('default_leverage', '10'))
    
    @staticmethod
    def get_trading_pairs() -> List[str]:
        """Торгуемые пары"""
        pairs_str = ConfigManager.get('trading_pairs', 'BTC/USDT,ETH/USDT')
        return [p.strip() for p in pairs_str.split(',') if p.strip()]
    
    @staticmethod
    def get_timeframes() -> List[str]:
        """Таймфреймы"""
        tf_str = ConfigManager.get('timeframes', '1m,5m,15m,1h,4h')
        return [t.strip() for t in tf_str.split(',') if t.strip()]
    
    @staticmethod
    def set_trading_pairs(pairs: List[str]) -> bool:
        """Установить торгуемые пары"""
        pairs_str = ','.join(pairs)
        return ConfigManager.set('trading_pairs', pairs_str)
    
    @staticmethod
    def set_timeframes(timeframes: List[str]) -> bool:
        """Установить таймфреймы"""
        tf_str = ','.join(timeframes)
        return ConfigManager.set('timeframes', tf_str)
    
    @staticmethod
    def enable_bot() -> bool:
        """Включить бота"""
        return ConfigManager.set('bot_enabled', 'true')
    
    @staticmethod
    def disable_bot() -> bool:
        """Выключить бота"""
        return ConfigManager.set('bot_enabled', 'false')

