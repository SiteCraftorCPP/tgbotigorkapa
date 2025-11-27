"""
Скрипт для исправления торговых пар в БД
Удаляет лишний текст и оставляет только пары
"""

from database.models import init_db, SessionLocal, BotConfig

def fix_trading_pairs():
    """Исправление торговых пар в БД"""
    db = SessionLocal()
    
    try:
        # Получаем текущее значение
        config = db.query(BotConfig).filter(BotConfig.key == 'trading_pairs').first()
        
        if not config:
            print("❌ Конфигурация trading_pairs не найдена")
            return
        
        current_value = config.value
        print(f"Текущее значение в БД: {current_value[:100]}...")  # Первые 100 символов
        
        # Пытаемся извлечь пары из строки
        # Убираем эмодзи и лишний текст
        import re
        
        # Ищем паттерн "BTC/USDT" или подобные
        pairs_pattern = r'\b[A-Z0-9]+/[A-Z0-9]+\b'
        pairs_found = re.findall(pairs_pattern, current_value)
        
        if pairs_found:
            # Убираем дубликаты, сохраняя порядок
            unique_pairs = list(dict.fromkeys(pairs_found))
            
            print(f"\nНайдено {len(unique_pairs)} уникальных пар:")
            print(f"Первые 10: {unique_pairs[:10]}")
            
            # Сохраняем исправленное значение
            pairs_str = ','.join(unique_pairs)
            config.value = pairs_str
            db.commit()
            
            print(f"\n✅ Исправлено! Сохранено {len(unique_pairs)} пар")
            print(f"Новое значение: {pairs_str[:200]}...")
        else:
            print("❌ Не удалось найти торговые пары в строке")
            print("Установим дефолтные пары...")
            
            default_pairs = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT']
            config.value = ','.join(default_pairs)
            db.commit()
            print(f"✅ Установлены дефолтные пары: {default_pairs}")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("ИСПРАВЛЕНИЕ ТОРГОВЫХ ПАР В БД")
    print("=" * 60)
    
    init_db()
    fix_trading_pairs()
    
    print("\n" + "=" * 60)
    print("Проверка результата:")
    print("=" * 60)
    
    from database.config_manager import ConfigManager
    pairs = ConfigManager.get_trading_pairs()
    print(f"📊 Загружено {len(pairs)} торговых пар")
    if len(pairs) > 0:
        print(f"Первые 10: {pairs[:10]}")

