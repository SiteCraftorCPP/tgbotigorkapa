#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ВОССТАНОВЛЕНИЕ НАСТРОЕК ФИЛЬТРОВ ПОСЛЕ ТЕСТИРОВАНИЯ
"""
from telegram_bot.filter_panel import FilterSettings
import json
from database.models import SessionLocal, BotConfig

def main():
    """Восстановление настроек из бэкапа"""
    print("=" * 60)
    print("🔄 ВОССТАНОВЛЕНИЕ НАСТРОЕК ФИЛЬТРОВ...")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        backup = db.query(BotConfig).filter(
            BotConfig.key == 'filter_settings_backup'
        ).first()
        
        if not backup:
            print("❌ Бэкап не найден! Восстанавливаю значения по умолчанию...")
            FilterSettings.reset_all()
        else:
            saved_settings = json.loads(backup.value)
            # Восстанавливаем каждую настройку
            for key, value in saved_settings.items():
                FilterSettings.set(key, value)
            print("✅ Настройки восстановлены из бэкапа")
        
        # Показываем текущие значения
        s = FilterSettings.get_all()
        print(f"\n📋 Восстановленные настройки:")
        print(f"   • min_liquidity: {s['min_liquidity']:,}")
        print(f"   • atr_min: {s['atr_min']}%")
        print(f"   • atr_max: {s['atr_max']}%")
        print(f"   • min_trend_candles: {s['min_trend_candles']}")
        print(f"   • min_rr_ratio: {s['min_rr_ratio']}")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Ошибка восстановления: {e}")
        print("Восстанавливаю значения по умолчанию...")
        FilterSettings.reset_all()
    finally:
        db.close()

if __name__ == "__main__":
    main()

