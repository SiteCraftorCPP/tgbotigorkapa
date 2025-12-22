#!/bin/bash
# Простой скрипт для обновления БД через SQLite напрямую

set -e

echo "============================================================"
echo "Updating signal_volume_multiplier in database"
echo "============================================================"

# Определяем путь к БД
DB_PATH=""
if [ -f "bot.db" ]; then
    DB_PATH="bot.db"
elif [ -f "data/bot.db" ]; then
    DB_PATH="data/bot.db"
else
    echo "ERROR: Database file not found!"
    echo "Looking for: bot.db or data/bot.db"
    exit 1
fi

echo "Database found: $DB_PATH"

# Проверяем наличие sqlite3
if ! command -v sqlite3 &> /dev/null; then
    echo "ERROR: sqlite3 not found!"
    echo "Install it: apt-get install sqlite3"
    exit 1
fi

# Получаем текущие настройки
CURRENT_VALUE=$(sqlite3 "$DB_PATH" "SELECT value FROM bot_config WHERE key = 'filter_settings';" 2>/dev/null || echo "")

if [ -z "$CURRENT_VALUE" ]; then
    echo "ERROR: filter_settings not found in database!"
    echo "Creating new settings..."
    sqlite3 "$DB_PATH" "INSERT INTO bot_config (key, value) VALUES ('filter_settings', '{\"signal_volume_multiplier\": 1.03}');"
    echo "✅ New settings created with signal_volume_multiplier = 1.03"
else
    # Обновляем значение через Python для правильной обработки JSON
    python3 << 'PYTHON_SCRIPT'
import sqlite3
import json
import sys

db_path = sys.argv[1]
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT value FROM bot_config WHERE key = 'filter_settings'")
result = cursor.fetchone()

if not result:
    print("ERROR: filter_settings not found!")
    sys.exit(1)

settings = json.loads(result[0])
old_value = settings.get('signal_volume_multiplier', 1.05)
print(f"Current value: {old_value}")

settings['signal_volume_multiplier'] = 1.03

cursor.execute(
    "UPDATE bot_config SET value = ? WHERE key = 'filter_settings'",
    (json.dumps(settings),)
)
conn.commit()
conn.close()

print(f"✅ Updated: signal_volume_multiplier = {old_value} -> 1.03")
PYTHON_SCRIPT "$DB_PATH"
fi

echo ""
echo "============================================================"
echo "✅ Database updated successfully!"
echo "============================================================"
echo "Restart the bot to apply changes:"
echo "  sudo systemctl restart tgbotigorkapa"
echo "============================================================"

