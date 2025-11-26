#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Проверка ID пользователя из логов бота
"""
import re
import sys

def extract_user_ids_from_logs(log_file):
    """Извлечь ID пользователей из логов"""
    user_ids = set()
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                # Ищем строки с DEBUG и user_id
                if 'DEBUG' in line and 'user' in line:
                    match = re.search(r'user (\d+)', line)
                    if match:
                        user_ids.add(match.group(1))
                
                # Ищем sendMessage - это означает взаимодействие
                if 'sendMessage' in line:
                    # Попробуем найти ID в предыдущих строках
                    pass
    except Exception as e:
        print(f"Ошибка чтения логов: {e}")
    
    return user_ids

def main():
    import glob
    
    log_files = glob.glob('logs/bot_*.log')
    if not log_files:
        print("Логи не найдены")
        return
    
    latest_log = max(log_files, key=lambda x: x)
    print(f"Анализ лога: {latest_log}\n")
    
    user_ids = extract_user_ids_from_logs(latest_log)
    
    if user_ids:
        print("Найденные ID пользователей:")
        for uid in sorted(user_ids):
            print(f"  - {uid}")
    else:
        print("ID пользователей не найдены в логах")
        print("\nПопросите пользователя отправить /start боту")
        print("Затем проверьте логи с помощью:")
        print("  tail -f logs/bot_*.log | grep DEBUG")

if __name__ == "__main__":
    main()

