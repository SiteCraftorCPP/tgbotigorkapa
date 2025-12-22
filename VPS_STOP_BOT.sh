#!/bin/bash
# Скрипт для остановки бота на VPS

echo "============================================================"
echo "🛑 Остановка бота..."
echo "============================================================"

# Остановка через systemd
echo "Остановка через systemd..."
sudo systemctl stop tgbotigorkapa 2>/dev/null && echo "✅ Бот остановлен через systemd" || echo "⚠️ Бот не был запущен через systemd"

# Дополнительная проверка и остановка процессов Python
echo ""
echo "Проверка процессов Python..."
PYTHON_PIDS=$(pgrep -f "python.*main.py" || true)

if [ -n "$PYTHON_PIDS" ]; then
    echo "Найдены процессы Python: $PYTHON_PIDS"
    kill -TERM $PYTHON_PIDS 2>/dev/null && echo "✅ Отправлен сигнал TERM процессам"
    sleep 2
    
    # Проверяем, остались ли процессы
    REMAINING=$(pgrep -f "python.*main.py" || true)
    if [ -n "$REMAINING" ]; then
        echo "⚠️ Процессы не завершились, отправляем KILL..."
        kill -9 $REMAINING 2>/dev/null && echo "✅ Процессы принудительно завершены"
    fi
else
    echo "✅ Процессы Python не найдены"
fi

# Финальная проверка
sleep 1
FINAL_CHECK=$(pgrep -f "python.*main.py" || true)
if [ -z "$FINAL_CHECK" ]; then
    echo ""
    echo "============================================================"
    echo "✅ Бот полностью остановлен!"
    echo "============================================================"
else
    echo ""
    echo "============================================================"
    echo "⚠️ Некоторые процессы могут быть активны:"
    echo "   PIDs: $FINAL_CHECK"
    echo "============================================================"
fi

