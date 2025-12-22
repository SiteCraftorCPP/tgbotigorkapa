#!/bin/bash
# Скрипт для обновления бота на VPS и применения изменений в БД
# Обновление объёма импульсной свечи: 1.05->1.03, 20->40 свечей

set -e  # Остановка при ошибке

echo "============================================================"
echo "🔄 Обновление бота и применение изменений в БД"
echo "============================================================"

# Переход в директорию проекта
cd ~/tgbotigorkapa || { echo "❌ Директория не найдена!"; exit 1; }

echo ""
echo "📥 Получение обновлений из Git..."
git fetch origin
git pull origin master

echo ""
echo "✅ Код обновлён"

echo ""
echo "🔧 Применение изменений в БД..."
python3 << 'PYTHON_SCRIPT'
from database.models import init_db
from telegram_bot.filter_panel import FilterSettings

print("Инициализация БД...")
init_db()
print("✅ База данных инициализирована")

# Загружаем текущие настройки
current_settings = FilterSettings.get_all(force_reload=True)
old_value = current_settings.get('signal_volume_multiplier', 1.05)
print(f"Текущее значение: {old_value}x среднего")

# Обновляем настройку
FilterSettings._settings['signal_volume_multiplier'] = 1.03
print(f"Новое значение: 1.03x среднего за 40 свечей")

# Сохраняем в БД
FilterSettings._save_to_db()
print("💾 Настройки сохранены в базу данных")

# Применяем к классам фильтров
FilterSettings._apply_to_filters()
print("✅ Настройки применены ко всем классам фильтров")

# Проверка
from analysis.market_filters import MarketFilters
from analysis.signal_generator import SignalGenerator

print("\n📋 Проверка применённых настроек:")
print(f"   MarketFilters.IMPULSE_VOLUME_MULTIPLIER = {MarketFilters.IMPULSE_VOLUME_MULTIPLIER}")
print(f"   SignalGenerator.SIGNAL_VOLUME_MULTIPLIER = {SignalGenerator.SIGNAL_VOLUME_MULTIPLIER}")

if MarketFilters.IMPULSE_VOLUME_MULTIPLIER == 1.03 and SignalGenerator.SIGNAL_VOLUME_MULTIPLIER == 1.03:
    print("\n✅ Все настройки применены корректно!")
else:
    print("\n⚠️ ВНИМАНИЕ: Настройки применены некорректно!")
    print("   Перезапустите бота для применения изменений")

print("\n✨ Готово! Перезапустите бота для применения изменений")
PYTHON_SCRIPT

echo ""
echo "============================================================"
echo "🔄 Перезапуск бота..."
echo "============================================================"

# Остановка бота
sudo systemctl stop tgbotigorkapa || echo "⚠️ Бот не был запущен"

# Небольшая задержка
sleep 2

# Запуск бота
sudo systemctl start tgbotigorkapa

# Проверка статуса
sleep 3
sudo systemctl status tgbotigorkapa --no-pager -l

echo ""
echo "============================================================"
echo "✅ Обновление завершено!"
echo "============================================================"
echo ""
echo "📋 Изменения:"
echo "   • Объём импульсной свечи: 1.05→1.03× среднего"
echo "   • Период расчёта: 20→40 свечей"
echo "   • Исправлена обработка конфликтов polling"
echo ""
echo "💡 Проверьте логи: journalctl -u tgbotigorkapa -f"
echo "============================================================"

