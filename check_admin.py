#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Проверка и добавление администратора
"""
import sys
from database.models import init_db
from database.admin_manager import AdminManager

def check_admin(telegram_id: str):
    """Проверить, является ли пользователь админом"""
    is_admin = AdminManager.is_admin(telegram_id)
    
    if is_admin:
        print(f"✅ Пользователь {telegram_id} является администратором")
    else:
        print(f"❌ Пользователь {telegram_id} НЕ является администратором")
        print(f"\nДобавить этого пользователя в админы? (y/n)")
        response = input().strip().lower()
        if response == 'y':
            AdminManager.add_admin(telegram_id)
            print(f"✅ Пользователь {telegram_id} добавлен в админы!")
        else:
            print("Отменено")

def list_all_admins():
    """Показать всех админов"""
    admins = AdminManager.get_all_admins()
    
    print(f"\n📋 Все администраторы ({len(admins)}):")
    print("=" * 60)
    for admin in admins:
        print(f"ID: {admin.telegram_id}")
        if admin.username:
            print(f"  Username: @{admin.username}")
        if admin.first_name:
            print(f"  Имя: {admin.first_name}")
        print(f"  Активен: {'✅' if admin.is_active else '❌'}")
        print("-" * 60)

def main():
    init_db()
    
    if len(sys.argv) < 2:
        print("=" * 60)
        print("Проверка администраторов")
        print("=" * 60)
        print("\nИспользование:")
        print("  python3 check_admin.py <telegram_id>  - проверить/добавить админа")
        print("  python3 check_admin.py list         - показать всех админов")
        print("\nКак узнать свой Telegram ID:")
        print("  1. Напишите боту @userinfobot в Telegram")
        print("  2. Или отправьте /start боту и посмотрите логи")
        print("=" * 60)
        return
    
    if sys.argv[1] == "list":
        list_all_admins()
        return
    
    telegram_id = sys.argv[1]
    check_admin(telegram_id)
    list_all_admins()

if __name__ == "__main__":
    main()

