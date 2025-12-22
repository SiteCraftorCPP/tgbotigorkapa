#!/bin/bash
# Скрипт для перезапуска бота на VPS

echo "============================================================"
echo "🔄 Перезапуск бота..."
echo "============================================================"

# Остановка
if [ -f "VPS_STOP_BOT.sh" ]; then
    chmod +x VPS_STOP_BOT.sh
    ./VPS_STOP_BOT.sh
else
    sudo systemctl stop tgbotigorkapa 2>/dev/null || true
    sleep 2
fi

# Запуск
if [ -f "VPS_START_BOT.sh" ]; then
    chmod +x VPS_START_BOT.sh
    ./VPS_START_BOT.sh
else
    sudo systemctl start tgbotigorkapa
    sleep 3
    sudo systemctl status tgbotigorkapa --no-pager -l
fi

