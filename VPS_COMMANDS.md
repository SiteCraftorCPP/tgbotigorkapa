# Команды для установки бота на VPS

## Быстрая установка (скопируйте и выполните все команды подряд)

```bash
# 1. Обновление системы
sudo apt update && sudo apt upgrade -y

# 2. Установка Python, pip и git
sudo apt install -y python3 python3-pip python3-venv git build-essential libssl-dev libffi-dev python3-dev

# 3. Клонирование репозитория
cd ~
git clone https://github.com/SiteCraftorCPP/tgbotigorkapa.git
cd tgbotigorkapa

# 4. Создание виртуального окружения (рекомендуется)
python3 -m venv venv
source venv/bin/activate

# 5. Установка зависимостей
pip install --upgrade pip
pip install -r requirements.txt

# 6. Создание .env файла
cat > .env << 'EOF'
# XT.com API
XT_API_KEY=your_api_key_here
XT_API_SECRET=your_api_secret_here

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHANNEL_ID=your_channel_id_here

# Database
DB_FILE=crypto_signals.db
LOG_LEVEL=INFO
EOF

# 7. Редактирование .env (укажите свои данные)
nano .env

# 8. Инициализация базы данных
python3 -c "from database.models import init_db; init_db()"

# 9. Тестовый запуск
python3 main.py
```

## Или используйте скрипт автоматической установки

```bash
# Скачать скрипт
wget https://raw.githubusercontent.com/SiteCraftorCPP/tgbotigorkapa/master/VPS_INSTALL.sh

# Сделать исполняемым
chmod +x VPS_INSTALL.sh

# Запустить
./VPS_INSTALL.sh
```

## Настройка автозапуска через systemd

```bash
# 1. Создать файл сервиса
sudo nano /etc/systemd/system/crypto-signal-bot.service
```

Вставьте следующее содержимое (замените `your_user` и `/home/your_user` на ваши данные):

```ini
[Unit]
Description=Crypto Signal Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/home/your_user/tgbotigorkapa
Environment="PATH=/home/your_user/tgbotigorkapa/venv/bin"
ExecStart=/home/your_user/tgbotigorkapa/venv/bin/python3 /home/your_user/tgbotigorkapa/main.py
Restart=always
RestartSec=10
StandardOutput=append:/home/your_user/tgbotigorkapa/logs/bot_systemd.log
StandardError=append:/home/your_user/tgbotigorkapa/logs/bot_systemd_error.log

[Install]
WantedBy=multi-user.target
```

```bash
# 2. Перезагрузить systemd
sudo systemctl daemon-reload

# 3. Включить автозапуск
sudo systemctl enable crypto-signal-bot

# 4. Запустить бота
sudo systemctl start crypto-signal-bot

# 5. Проверить статус
sudo systemctl status crypto-signal-bot

# 6. Просмотр логов
sudo journalctl -u crypto-signal-bot -f
```

## Управление ботом через systemd

```bash
# Запустить
sudo systemctl start crypto-signal-bot

# Остановить
sudo systemctl stop crypto-signal-bot

# Перезапустить
sudo systemctl restart crypto-signal-bot

# Статус
sudo systemctl status crypto-signal-bot

# Логи в реальном времени
sudo journalctl -u crypto-signal-bot -f

# Последние 100 строк логов
sudo journalctl -u crypto-signal-bot -n 100
```

## Запуск в фоне без systemd

```bash
# Запуск с nohup
nohup python3 main.py > bot.log 2>&1 &

# Остановка
pkill -f "python3 main.py"

# Просмотр логов
tail -f bot.log
```

## Проверка работы

```bash
# Проверить процессы
ps aux | grep python

# Проверить логи
tail -f logs/bot_*.log
tail -f logs/filters_*.log
```

## Обновление бота

```bash
cd ~/tgbotigorkapa
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart crypto-signal-bot
```

