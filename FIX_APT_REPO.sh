#!/bin/bash
# Исправление проблемы с репозиторием apt

echo "Исправление проблемы с репозиторием..."

# 1. Найти и удалить проблемный репозиторий
echo "[1/3] Поиск проблемного репозитория..."
if grep -r "monarx.com" /etc/apt/sources.list.d/ 2>/dev/null; then
    echo "Найден проблемный репозиторий. Удаление..."
    sudo rm -f /etc/apt/sources.list.d/*monarx* 2>/dev/null
    sudo rm -f /etc/apt/sources.list.d/*questing* 2>/dev/null
fi

# 2. Проверить основной sources.list
if grep -q "monarx.com" /etc/apt/sources.list 2>/dev/null; then
    echo "Проблемный репозиторий найден в /etc/apt/sources.list"
    echo "Закомментируем строку..."
    sudo sed -i 's|.*monarx.com.*|# &|' /etc/apt/sources.list
fi

# 3. Очистить кэш apt
echo "[2/3] Очистка кэша apt..."
sudo apt clean
sudo rm -rf /var/lib/apt/lists/*

# 4. Обновление
echo "[3/3] Обновление списка пакетов..."
sudo apt update

echo ""
echo "Готово! Теперь можно продолжить установку бота."

