#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт для запуска бота локально
"""
import subprocess
import sys
import os

def main():
    """Запуск бота"""
    print("=" * 60)
    print("🚀 Запуск Crypto Signal Bot...")
    print("=" * 60)
    
    # Проверка текущей директории
    if not os.path.exists('main.py'):
        print("❌ Ошибка: файл main.py не найден!")
        print(f"   Текущая директория: {os.getcwd()}")
        sys.exit(1)
    
    try:
        # Запуск бота
        os.system('python main.py')
    except KeyboardInterrupt:
        print("\n\n⚠️  Бот остановлен пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Ошибка при запуске: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()




