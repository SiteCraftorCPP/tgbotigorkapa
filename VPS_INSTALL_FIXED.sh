#!/bin/bash
# Скрипт установки Crypto Signal Bot на VPS (с исправлением проблем apt)

echo "=========================================="
echo "Установка Crypto Signal Bot на VPS"
echo "=========================================="

# 0. Исправление проблем с репозиториями (если есть)
echo ""
echo "[0/9] Проверка и исправление репозиториев..."
if grep -r "monarx.com\|questing" /etc/apt/sources.list.d/ /etc/apt/sources.list 2>/dev/null; then
    echo "Обнаружен проблемный репозиторий. Исправление..."
    sudo rm -f /etc/apt/sources.list.d/*monarx* 2>/dev/null
    sudo rm -f /etc/apt/sources.list.d/*questing* 2>/dev/null
    sudo sed -i 's|.*monarx.com.*|# &|' /etc/apt/sources.list 2>/dev/null
    sudo sed -i 's|.*questing.*|# &|' /etc/apt/sources.list 2>/dev/null
    sudo apt clean
    sudo rm -rf /var/lib/apt/lists/*
fi

# 1. Обновление системы
echo ""
echo "[1/9] Обновление системы..."
sudo apt update || {
    echo "Ошибка при обновлении. Пропускаем обновление и продолжаем..."
}
sudo apt upgrade -y || {
    echo "Ошибка при обновлении пакетов. Продолжаем установку..."
}

# 2. Установка Python и pip
echo ""
echo "[2/9] Установка Python и pip..."
sudo apt install -y python3 python3-pip python3-venv || {
    echo "Ошибка установки Python. Проверьте доступность репозиториев."
    exit 1
}

# 3. Установка git
echo ""
echo "[3/9] Установка git..."
sudo apt install -y git || {
    echo "Ошибка установки git."
    exit 1
}

# 4. Установка дополнительных зависимостей
echo ""
echo "[4/9] Установка системных зависимостей..."
sudo apt install -y build-essential libssl-dev libffi-dev python3-dev || {
    echo "Предупреждение: некоторые системные зависимости не установлены."
}

# 5. Клонирование репозитория
echo ""
echo "[5/9] Клонирование репозитория..."
cd ~
if [ -d "tgbotigorkapa" ]; then
    echo "Директория уже существует. Обновление..."
    cd tgbotigorkapa
    git pull
else
    git clone https://github.com/SiteCraftorCPP/tgbotigorkapa.git
    cd tgbotigorkapa
fi

# 6. Создание виртуального окружения
echo ""
echo "[6/9] Создание виртуального окружения..."
python3 -m venv venv
source venv/bin/activate

# 7. Установка Python зависимостей
echo ""
echo "[7/9] Установка Python зависимостей..."
pip install --upgrade pip
pip install -r requirements.txt

# 8. Создание .env файла (если не существует)
echo ""
echo "[8/9] Создание .env файла..."
if [ ! -f .env ]; then
    cat > .env << 'EOF'
# XT.com API
XT_API_KEY=your_api_key_here
XT_API_SECRET=your_api_secret_here

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHANNEL_ID=your_channel_id_here

# Database (SQLite)
DB_FILE=crypto_signals.db
LOG_LEVEL=INFO
EOF
    echo ".env файл создан. НЕОБХОДИМО отредактировать его!"
else
    echo ".env файл уже существует."
fi

# 9. Инициализация БД
echo ""
echo "[9/9] Инициализация базы данных..."
python3 -c "from database.models import init_db; init_db()" || {
    echo "Ошибка инициализации БД. Проверьте настройки в .env"
}

echo ""
echo "=========================================="
echo "Установка завершена!"
echo "=========================================="
echo ""
echo "ВАЖНО: Отредактируйте файл .env:"
echo "  nano .env"
echo ""
echo "Затем запустите бота:"
echo "  source venv/bin/activate"
echo "  python3 main.py"
echo ""
echo "Или настройте systemd для автозапуска (см. VPS_COMMANDS.md)"
echo "=========================================="

