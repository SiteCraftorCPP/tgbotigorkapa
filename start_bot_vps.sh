#!/bin/bash
# Скрипт для запуска бота на VPS через screen

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR" || exit 1

# Активация виртуального окружения
source venv/bin/activate

# Проверка, что screen установлен
if ! command -v screen &> /dev/null; then
    echo "❌ screen не установлен. Установите: apt install screen"
    exit 1
fi

# Остановка старой сессии если есть
screen -S bot -X quit 2>/dev/null

# Создание директории для логов если нет
mkdir -p logs

# Запуск бота в новой screen сессии
echo "🚀 Запуск бота в screen сессии..."
screen -dmS bot bash -c "cd $SCRIPT_DIR && source venv/bin/activate && python3 main.py 2>&1 | tee -a logs/bot_$(date +%Y%m%d).log"

sleep 2

# Проверка что процесс запустился
if screen -list | grep -q "bot"; then
    echo "✅ Бот запущен в screen сессии 'bot'"
    echo ""
    echo "Команды для управления:"
    echo "  screen -r bot          - подключиться к сессии"
    echo "  screen -S bot -X quit   - остановить бота"
    echo "  screen -list           - список сессий"
else
    echo "❌ Ошибка: бот не запустился"
    exit 1
fi

