#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт для добавления администраторов в бота
"""
import sys
from database.models import init_db
from database.admin_manager import AdminManager

def add_admin(telegram_id: str, username: str = None, first_name: str = None):
    """Добавить администратора"""
    print(f"Добавление администратора: {telegram_id}")
    
    success = AdminManager.add_admin(telegram_id, username, first_name)
    
    if success:
        print(f"✅ Администратор {telegram_id} успешно добавлен!")
        return True
    else:
        print(f"❌ Ошибка при добавлении администратора {telegram_id}")
        return False

def list_admins():
    """Показать список всех админов"""
    admins = AdminManager.get_all_admins()
    
    if not admins:
        print("📭 Администраторов не найдено")
        return
    
    print(f"\n📋 Список администраторов ({len(admins)}):")
    print("-" * 60)
    for admin in admins:
        print(f"ID: {admin.telegram_id}")
        if admin.username:
            print(f"  Username: @{admin.username}")
        if admin.first_name:
            print(f"  Имя: {admin.first_name}")
        print(f"  Добавлен: {admin.added_at}")
        print(f"  Активен: {'✅' if admin.is_active else '❌'}")
        print("-" * 60)

def main():
    """Главная функция"""
    # Инициализация БД
    init_db()
    
    if len(sys.argv) < 2:
        print("=" * 60)
        print("Управление администраторами бота")
        print("=" * 60)
        print("\nИспользование:")
        print("  python3 add_admin.py <telegram_id> [username] [first_name]")
        print("  python3 add_admin.py list  - показать всех админов")
        print("\nПримеры:")
        print("  python3 add_admin.py 123456789")
        print("  python3 add_admin.py 123456789 @username Имя")
        print("  python3 add_admin.py list")
        print("=" * 60)
        return
    
    if sys.argv[1] == "list":
        list_admins()
        return
    
    telegram_id = sys.argv[1]
    username = sys.argv[2] if len(sys.argv) > 2 else None
    first_name = sys.argv[3] if len(sys.argv) > 3 else None
    
    add_admin(telegram_id, username, first_name)
    print("\n" + "=" * 60)
    list_admins()

if __name__ == "__main__":
    main()

