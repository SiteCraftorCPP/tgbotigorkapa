"""
Скрипт для принудительного применения миграции фильтров v6
Обновляет значения в БД до новых дефолтов для логики 1H
"""

import json
from database.models import SessionLocal, BotConfig

def apply_migration_v6():
    """Применяет миграцию v6 - обновляет значения фильтров"""
    db = SessionLocal()
    try:
        config = db.query(BotConfig).filter(
            BotConfig.key == 'filter_settings'
        ).first()
        
        if not config:
            print("[ERROR] filter_settings not found in DB")
            return
        
        settings = json.loads(config.value) if config.value else {}
        
        # Обновляем значения до новых дефолтов v6
        old_values = {}
        
        if settings.get('max_ema50_distance') != 2.5:
            old_values['max_ema50_distance'] = settings.get('max_ema50_distance')
            settings['max_ema50_distance'] = 2.5
        
        if settings.get('htf_volume_multiplier') != 1.3:
            old_values['htf_volume_multiplier'] = settings.get('htf_volume_multiplier')
            settings['htf_volume_multiplier'] = 1.3
        
        if settings.get('breakout_body_ratio') != 55:
            old_values['breakout_body_ratio'] = settings.get('breakout_body_ratio')
            settings['breakout_body_ratio'] = 55
        
        # Фиксируем версию миграции
        settings['_migration_version'] = 6
        
        # Сохраняем в БД
        config.value = json.dumps(settings)
        db.commit()
        
        print("[OK] Migration v6 applied successfully!")
        if old_values:
            print(f"Updated values: {old_values}")
        else:
            print("All values were already up to date")
        
    except Exception as e:
        print(f"[ERROR] Failed to apply migration: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    apply_migration_v6()

