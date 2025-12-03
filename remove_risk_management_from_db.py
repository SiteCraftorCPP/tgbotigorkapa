#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Удаление настроек риск-менеджмента из базы данных
"""
from database.models import SessionLocal, BotConfig
import json

def remove_risk_management_settings():
    """Удалить max_active_signals и cooldown_hours из filter_settings в БД"""
    db = SessionLocal()
    try:
        # Получаем текущие настройки
        config = db.query(BotConfig).filter(
            BotConfig.key == 'filter_settings'
        ).first()
        
        if not config:
            print("✅ Настройки filter_settings не найдены в БД")
            return
        
        # Парсим JSON
        try:
            settings = json.loads(config.value)
        except json.JSONDecodeError:
            print("❌ Ошибка: не удалось распарсить JSON из filter_settings")
            return
        
        # Удаляем настройки риск-менеджмента
        removed = []
        if 'max_active_signals' in settings:
            del settings['max_active_signals']
            removed.append('max_active_signals')
        
        if 'cooldown_hours' in settings:
            del settings['cooldown_hours']
            removed.append('cooldown_hours')
        
        if 'min_data_candles' in settings:
            del settings['min_data_candles']
            removed.append('min_data_candles')
        
        if not removed:
            print("✅ Настройки риск-менеджмента уже отсутствуют в БД")
            return
        
        # Сохраняем обратно в БД
        config.value = json.dumps(settings)
        db.commit()
        
        print(f"✅ Удалены настройки из БД: {', '.join(removed)}")
        print(f"📊 Всего настроек осталось: {len(settings)}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("🗑️  УДАЛЕНИЕ НАСТРОЕК РИСК-МЕНЕДЖМЕНТА ИЗ БД")
    print("=" * 60)
    remove_risk_management_settings()

