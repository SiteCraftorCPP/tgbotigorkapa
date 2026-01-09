# -*- coding: utf-8 -*-
"""
Миграция: добавление полей reset_level и reset_price в таблицу signals
"""
import sqlite3
import os
import sys

def get_db_path():
    """Определяет путь к БД"""
    possible_paths = [
        'crypto_signals.db',
        'bot.db',
        os.path.expanduser('~/tgbotigorkapa/crypto_signals.db'),
        os.path.join(os.path.dirname(__file__), 'crypto_signals.db'),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path

    current_dir = os.getcwd()
    db_path = os.path.join(current_dir, 'crypto_signals.db')
    if os.path.exists(db_path):
        return db_path

    return None

def add_reset_fields():
    """Добавляет поля reset_level и reset_price в таблицу signals"""
    db_file = get_db_path()
    if not db_file:
        print("ERROR: Database file not found!")
        print(f"Looking for: crypto_signals.db or bot.db")
        print(f"Current directory: {os.getcwd()}")
        sys.exit(1)

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    try:
        # Проверяем, существуют ли уже поля
        cursor.execute("PRAGMA table_info(signals)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'reset_level' not in columns:
            cursor.execute("ALTER TABLE signals ADD COLUMN reset_level INTEGER")
            print("✅ Добавлено поле reset_level")
        else:
            print("ℹ️  Поле reset_level уже существует")
        
        if 'reset_price' not in columns:
            cursor.execute("ALTER TABLE signals ADD COLUMN reset_price REAL")
            print("✅ Добавлено поле reset_price")
        else:
            print("ℹ️  Поле reset_price уже существует")
        
        conn.commit()
        print("✅ Миграция завершена успешно")
        
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    print("============================================================")
    print("Добавление полей reset_level и reset_price в таблицу signals")
    print("============================================================")
    add_reset_fields()
