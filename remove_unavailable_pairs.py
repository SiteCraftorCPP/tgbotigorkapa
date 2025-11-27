"""
Скрипт для удаления недоступных торговых пар из БД
Удаляет пары, которые недоступны на XT.com/Binance
"""

from database.models import init_db, SessionLocal
from database.config_manager import ConfigManager

# Пары, которые недоступны на Binance/XT.com (из ошибок в логах)
UNAVAILABLE_PAIRS = [
    "LEO/USDT",   # Недоступен на Binance
    "USDE/USDT",  # Недоступен на Binance
    "DAI/USDT",   # Недоступен на Binance (есть только DAI/BUSD)
    "SHIB/USDT",  # Недоступен на Binance (есть только SHIB/BUSD)
    "USDT/USDT",  # Некорректная пара
    "USDC/USDT",  # Стейблкоины обычно не торгуются друг с другом
    "PYUSD/USDT", # Может быть недоступен
    "USD1/USDT",  # Недоступен
    "USDG/USDT",  # Недоступен
    "RLUSD/USDT", # Недоступен
    "FDUSD/USDT", # Может быть недоступен
    "USDD/USDT",  # Может быть недоступен
    "TUSD/USDT",  # Может быть недоступен
    "USDF/USDT",  # Недоступен
    "USDf/USDT",  # Недоступен
    "USDY/USDT",  # Недоступен
    "USD0/USDT",  # Недоступен
    "USDAI/USDT", # Недоступен
    "DUSD/USDT",  # Недоступен
    "GUSD/USDT",  # Недоступен
    "AUSD/USDT",  # Недоступен
    "FRXUSD/USDT", # Недоступен
    "EURC/USDT",  # Может быть недоступен
]


def main():
    print("=" * 60)
    print("УДАЛЕНИЕ НЕДОСТУПНЫХ ТОРГОВЫХ ПАР")
    print("=" * 60)
    
    # Инициализация БД
    init_db()
    
    # Получаем текущие пары
    current_pairs = ConfigManager.get_trading_pairs()
    print(f"\nТекущее количество пар: {len(current_pairs)}")
    
    # Фильтруем недоступные пары
    available_pairs = [p for p in current_pairs if p not in UNAVAILABLE_PAIRS]
    removed_pairs = [p for p in current_pairs if p in UNAVAILABLE_PAIRS]
    
    print(f"Удалено недоступных пар: {len(removed_pairs)}")
    if removed_pairs:
        print(f"Удалённые пары: {', '.join(removed_pairs[:10])}")
        if len(removed_pairs) > 10:
            print(f"... и ещё {len(removed_pairs) - 10}")
    
    print(f"\nОсталось доступных пар: {len(available_pairs)}")
    
    # Сохраняем обновлённый список
    if len(available_pairs) > 0:
        success = ConfigManager.set_trading_pairs(available_pairs)
        
        if success:
            print(f"\n✅ Успешно обновлено! Сохранено {len(available_pairs)} доступных пар")
            
            # Проверяем
            saved_pairs = ConfigManager.get_trading_pairs()
            print(f"Проверка: загружено {len(saved_pairs)} пар из БД")
        else:
            print("\n❌ Ошибка при сохранении!")
    else:
        print("\n⚠️  Внимание: не осталось доступных пар!")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()



