#!/bin/bash
# Скрипт установки Crypto Signal Bot на VPS

echo "=========================================="
echo "Установка Crypto Signal Bot на VPS"
echo "=========================================="

# 1. Обновление системы
echo ""
echo "[1/8] Обновление системы..."
sudo apt update
sudo apt upgrade -y

# 2. Установка Python и pip
echo ""
echo "[2/8] Установка Python и pip..."
sudo apt install -y python3 python3-pip python3-venv

# 3. Установка git
echo ""
echo "[3/8] Установка git..."
sudo apt install -y git

# 4. Установка дополнительных зависимостей
echo ""
echo "[4/8] Установка системных зависимостей..."
sudo apt install -y build-essential libssl-dev libffi-dev python3-dev

# 5. Клонирование репозитория
echo ""
echo "[5/8] Клонирование репозитория..."
cd ~
git clone https://github.com/SiteCraftorCPP/tgbotigorkapa.git
cd tgbotigorkapa

# 6. Создание виртуального окружения (опционально, но рекомендуется)
echo ""
echo "[6/8] Создание виртуального окружения..."
python3 -m venv venv
source venv/bin/activate

# 7. Установка Python зависимостей
echo ""
echo "[7/8] Установка Python зависимостей..."
pip install --upgrade pip
pip install -r requirements.txt

# 8. Создание .env файла
echo ""
echo "[8/8] Создание .env файла..."
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

echo ""
echo "=========================================="
echo "Установка завершена!"
echo "=========================================="
echo ""
echo "ВАЖНО: Отредактируйте файл .env и укажите:"
echo "  - XT_API_KEY и XT_API_SECRET"
echo "  - TELEGRAM_BOT_TOKEN"
echo "  - TELEGRAM_CHANNEL_ID"
echo ""
echo "Команды для продолжения:"
echo "  1. Редактировать .env: nano .env"
echo "  2. Инициализировать БД: python3 -c 'from database.models import init_db; init_db()'"
echo "  3. Запустить бота: python3 main.py"
echo ""
echo "Или использовать systemd для автозапуска (см. DEPLOY.md)"
echo "=========================================="

