#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ОТКЛЮЧЕНИЕ ВСЕХ ФИЛЬТРОВ ДЛЯ ТЕСТИРОВАНИЯ
Цель: увидеть хотя бы один сигнал в Telegram канале
"""
from telegram_bot.filter_panel import FilterSettings
import json
from database.models import SessionLocal, BotConfig

def save_current_settings():
    """Сохранить текущие настройки для восстановления"""
    current = FilterSettings.get_all()
    db = SessionLocal()
    try:
        backup = BotConfig(
            key='filter_settings_backup',
            value=json.dumps(current),
            description='Backup before test - restore with restore_filters.py'
        )
        db.add(backup)
        db.commit()
        print("✅ Текущие настройки сохранены для восстановления")
    except Exception as e:
        print(f"⚠️ Ошибка сохранения бэкапа: {e}")
        db.rollback()
    finally:
        db.close()

def main():
    """МАКСИМАЛЬНОЕ ослабление всех фильтров"""
    print("=" * 60)
    print("🚨 ОТКЛЮЧЕНИЕ ВСЕХ ФИЛЬТРОВ ДЛЯ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    
    # Сохраняем текущие настройки
    save_current_settings()
    
    # МАКСИМАЛЬНО ослабляем ВСЕ фильтры
    changes = []
    
    # Рынок
    FilterSettings.set('min_liquidity', 10_000)  # Было 300,000
    FilterSettings.set('atr_min', 0.01)  # Было 0.3
    FilterSettings.set('atr_max', 20.0)  # Было 3.5
    FilterSettings.set('max_atr_deviation', 100.0)  # Было 35
    changes.append("Рынок: ликвидность 10k, ATR 0.01-20%")
    
    # Тренд
    FilterSettings.set('min_trend_candles', 0)  # Было 3
    FilterSettings.set('max_ema50_distance', 10.0)  # Было 2.0
    FilterSettings.set('max_ema50_deviation', 10.0)  # Было 2.2
    changes.append("Тренд: 0 свечей, EMA50 до 10 ATR")
    
    # Pullback
    FilterSettings.set('pullback_min', 0.0)  # Было 0.3
    FilterSettings.set('pullback_max', 5.0)  # Было 0.6
    changes.append("Pullback: 0-5 ATR")
    
    # Индикаторы
    FilterSettings.set('min_rr_ratio', 0.1)  # Было 1.8
    FilterSettings.set('rsi_max_long', 100)  # Было 68
    FilterSettings.set('rsi_min_short', 0)  # Было 32
    FilterSettings.set('adx_min', 0)  # Было 18
    FilterSettings.set('adx_max', 100)  # Было 45
    changes.append("Индикаторы: RR 0.1, RSI/ADX отключены")
    
    # Качество сигнала
    FilterSettings.set('impulse_body_ratio', 10)  # Было 60
    FilterSettings.set('impulse_avg_multiplier', 1.0)  # Было 1.25
    FilterSettings.set('max_dirty_candles', 20)  # Было 3
    FilterSettings.set('max_saw_candles', 20)  # Было 3
    FilterSettings.set('pattern_check_enabled', False)  # Было True
    changes.append("Качество: все проверки ослаблены")
    
    # Уровни
    FilterSettings.set('min_level_touches', 0)  # Было 2
    FilterSettings.set('min_opposite_distance', 0.0)  # Было 1.4
    FilterSettings.set('breakout_body_ratio', 10)  # Было 55
    changes.append("Уровни: все проверки отключены")
    
    # SL/TP
    FilterSettings.set('max_sl_distance', 10.0)  # Было 1.6
    FilterSettings.set('min_sl_liquidity', 1_000)  # Было 90,000
    changes.append("SL/TP: максимально ослаблены")
    
    print("\n✅ ВСЕ фильтры ослаблены:")
    for change in changes:
        print(f"   • {change}")
    
    print("\n" + "=" * 60)
    print("⚠️  ВАЖНО: Для восстановления запустите restore_filters.py")
    print("=" * 60)

if __name__ == "__main__":
    main()

