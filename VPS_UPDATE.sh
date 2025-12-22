#!/bin/bash
# Скрипт для обновления бота на VPS

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR" || exit 1

echo "🔄 Начинаем обновление бота..."

# Остановка бота если запущен (systemd service)
echo "⏹️  Останавливаем бота..."
sudo systemctl stop tgbotigorkapa.service 2>/dev/null
sleep 2

# Получение обновлений из git
echo "📥 Получаем обновления из git..."
git pull origin master

if [ $? -ne 0 ]; then
    echo "❌ Ошибка при получении обновлений из git"
    exit 1
fi

# Активация виртуального окружения
echo "🐍 Активируем виртуальное окружение..."
source venv/bin/activate

# Обновление зависимостей (опционально, если requirements.txt изменился)
echo "📦 Проверяем зависимости..."
pip install -q -r requirements.txt

# Применение настроек фильтров (если нужно)
echo "⚙️  Применяем настройки фильтров..."
python3 -c "from telegram_bot.filter_panel import FilterSettings; FilterSettings._apply_to_filters()" 2>/dev/null

# Запуск бота (systemd service)
echo "🚀 Запускаем бота..."
sudo systemctl start tgbotigorkapa.service

sleep 2

# Проверка что процесс запустился
if sudo systemctl is-active --quiet tgbotigorkapa.service; then
    echo "✅ Бот успешно обновлён и запущен!"
    echo ""
    echo "Команды для управления:"
    echo "  sudo systemctl status tgbotigorkapa.service  - статус бота"
    echo "  sudo systemctl stop tgbotigorkapa.service    - остановить бота"
    echo "  sudo systemctl start tgbotigorkapa.service   - запустить бота"
    echo "  sudo systemctl restart tgbotigorkapa.service  - перезапустить бота"
    echo "  sudo journalctl -u tgbotigorkapa.service -f   - логи в реальном времени"
else
    echo "❌ Ошибка: бот не запустился"
    echo "Проверьте логи: sudo journalctl -u tgbotigorkapa.service -n 50"
    exit 1
fi



























