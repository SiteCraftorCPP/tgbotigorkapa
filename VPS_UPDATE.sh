#!/bin/bash
# Скрипт для обновления бота на VPS

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR" || exit 1

echo "🔄 Начинаем обновление бота..."

# Остановка бота если запущен
echo "⏹️  Останавливаем бота..."
screen -S bot -X quit 2>/dev/null
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

# Запуск бота
echo "🚀 Запускаем бота..."
screen -dmS bot bash -c "cd $SCRIPT_DIR && source venv/bin/activate && python3 main.py 2>&1 | tee -a logs/bot_$(date +%Y%m%d).log"

sleep 2

# Проверка что процесс запустился
if screen -list | grep -q "bot"; then
    echo "✅ Бот успешно обновлён и запущен!"
    echo ""
    echo "Команды для управления:"
    echo "  screen -r bot          - подключиться к сессии"
    echo "  screen -S bot -X quit   - остановить бота"
    echo "  screen -list           - список сессий"
else
    echo "❌ Ошибка: бот не запустился"
    exit 1
fi



























