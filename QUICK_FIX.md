# Быстрое исправление проблемы с репозиторием

## Выполните эти команды на VPS:

```bash
# 1. Удалить проблемный репозиторий
sudo rm -f /etc/apt/sources.list.d/*monarx* 2>/dev/null
sudo rm -f /etc/apt/sources.list.d/*questing* 2>/dev/null

# 2. Закомментировать в основном файле (если есть)
sudo sed -i 's|.*monarx.com.*|# &|' /etc/apt/sources.list 2>/dev/null
sudo sed -i 's|.*questing.*|# &|' /etc/apt/sources.list 2>/dev/null

# 3. Очистить кэш apt
sudo apt clean
sudo rm -rf /var/lib/apt/lists/*

# 4. Обновить список пакетов
sudo apt update

# 5. Продолжить установку бота
sudo apt install -y python3 python3-pip python3-venv git build-essential libssl-dev libffi-dev python3-dev
```

