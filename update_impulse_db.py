#!/usr/bin/env python3
# Обновление настроек импульса в БД
import sqlite3
import json
import os

def get_db_path():
    for path in ['crypto_signals.db', 'bot.db']:
        if os.path.exists(path):
            return path
    return None

db_path = get_db_path()
if not db_path:
    print("ERROR: Database not found!")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT value FROM bot_config WHERE key = 'filter_settings'")
result = cursor.fetchone()

if result:
    settings = json.loads(result[0])
    old_body = settings.get('impulse_body_ratio', 50)
    old_mult = settings.get('impulse_avg_multiplier', 1.1)
    
    settings['impulse_body_ratio'] = 43
    settings['impulse_avg_multiplier'] = 1.05
    
    cursor.execute("UPDATE bot_config SET value = ? WHERE key = 'filter_settings'", (json.dumps(settings),))
    conn.commit()
    
    print(f"Updated: impulse_body_ratio {old_body}->43, impulse_avg_multiplier {old_mult}->1.05")
else:
    print("ERROR: filter_settings not found!")

conn.close()

