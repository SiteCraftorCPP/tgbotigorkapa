#!/bin/bash
# Скрипт для запуска бота на VPS

echo "============================================================"
echo "🚀 Запуск бота..."
echo "============================================================"

# Проверка, не запущен ли уже бот
PYTHON_PIDS=$(pgrep -f "python.*main.py" || true)
if [ -n "$PYTHON_PIDS" ]; then
    echo "⚠️ Бот уже запущен (PIDs: $PYTHON_PIDS)"
    echo "Сначала остановите бота: ./VPS_STOP_BOT.sh"
    exit 1
fi

# Запуск через systemd
echo "Запуск через systemd..."
sudo systemctl start tgbotigorkapa

# Небольшая задержка
sleep 3

# Проверка статуса
echo ""
echo "Проверка статуса..."
sudo systemctl status tgbotigorkapa --no-pager -l

echo ""
echo "============================================================"
echo "✅ Бот запущен!"
echo "============================================================"
echo ""
echo "💡 Команды для управления:"
echo "   Остановка:  sudo systemctl stop tgbotigorkapa"
echo "   Статус:     sudo systemctl status tgbotigorkapa"
echo "   Логи:       journalctl -u tgbotigorkapa -f"
echo "============================================================"

