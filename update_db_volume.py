#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой скрипт для обновления signal_volume_multiplier в БД
Работает напрямую с SQLite без зависимостей от других модулей
"""
import sqlite3
import json
import os
import sys

def get_db_path():
    """Определяет путь к БД"""
    # Пробуем найти БД в разных местах с правильными именами
    possible_paths = [
        'crypto_signals.db',  # Дефолтное имя из config.py
        'bot.db',
        'data/crypto_signals.db',
        'data/bot.db',
        os.path.expanduser('~/tgbotigorkapa/crypto_signals.db'),
        os.path.expanduser('~/tgbotigorkapa/bot.db'),
        os.path.join(os.path.dirname(__file__), 'crypto_signals.db'),
        os.path.join(os.path.dirname(__file__), 'bot.db'),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # Если не найдена, пробуем найти в текущей директории
    current_dir = os.getcwd()
    for db_name in ['crypto_signals.db', 'bot.db']:
        db_path = os.path.join(current_dir, db_name)
        if os.path.exists(db_path):
            return db_path
    
    # Пробуем найти любой .db файл в текущей директории
    for file in os.listdir(current_dir):
        if file.endswith('.db'):
            return os.path.join(current_dir, file)
    
    return None

def update_volume_setting():
    """Обновляет signal_volume_multiplier в БД"""
    db_path = get_db_path()
    
    if not db_path:
        print("ERROR: Database file not found!")
        print("Looking for: crypto_signals.db or bot.db")
        print("Current directory:", os.getcwd())
        print("Files in directory:", [f for f in os.listdir('.') if f.endswith('.db')])
        sys.exit(1)
    
    print(f"Database found: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Получаем текущие настройки
        cursor.execute("SELECT value FROM bot_config WHERE key = 'filter_settings'")
        result = cursor.fetchone()
        
        if not result:
            print("ERROR: filter_settings not found in database!")
            print("Creating new settings...")
            settings = {'signal_volume_multiplier': 1.03}
            cursor.execute(
                "INSERT INTO bot_config (key, value) VALUES (?, ?)",
                ('filter_settings', json.dumps(settings))
            )
            conn.commit()
            print("✅ New settings created with signal_volume_multiplier = 1.03")
            conn.close()
            return
        
        # Парсим JSON
        try:
            settings = json.loads(result[0])
        except json.JSONDecodeError:
            print("ERROR: Invalid JSON in filter_settings!")
            conn.close()
            sys.exit(1)
        
        old_value = settings.get('signal_volume_multiplier', 1.05)
        print(f"Current value: {old_value}")
        
        # Обновляем значение
        settings['signal_volume_multiplier'] = 1.03
        
        # Сохраняем обратно
        cursor.execute(
            "UPDATE bot_config SET value = ? WHERE key = 'filter_settings'",
            (json.dumps(settings),)
        )
        conn.commit()
        conn.close()
        
        print(f"✅ Updated: signal_volume_multiplier = 1.05 -> 1.03")
        print("✅ Database updated successfully!")
        
    except sqlite3.Error as e:
        print(f"ERROR: Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("=" * 60)
    print("Updating signal_volume_multiplier in database")
    print("=" * 60)
    update_volume_setting()
    print("=" * 60)
    print("Done! Restart the bot to apply changes.")
    print("=" * 60)

