# Инструкция по развертыванию на VPS

## Требования
- Python 3.7+
- pip

## Установка

1. Клонировать репозиторий:
```bash
git clone https://github.com/SiteCraftorCPP/tgbotigorkapa.git
cd tgbotigorkapa
```

2. Установить зависимости:
```bash
pip install -r requirements.txt
```

3. Создать файл `.env` с настройками:
```bash
# XT.com API
XT_API_KEY=your_api_key
XT_API_SECRET=your_api_secret

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHANNEL_ID=your_channel_id

# Database
DB_FILE=crypto_signals.db
LOG_LEVEL=INFO
```

4. Инициализировать базу данных:
```bash
python -c "from database.models import init_db; init_db()"
```

## Запуск

### Вариант 1: Прямой запуск
```bash
python main.py
```

### Вариант 2: Через start_bot.py
```bash
python start_bot.py
```

### Вариант 3: В фоне с nohup
```bash
nohup python main.py > bot.log 2>&1 &
```

### Вариант 4: С systemd (рекомендуется)
Создать файл `/etc/systemd/system/crypto-signal-bot.service`:
```ini
[Unit]
Description=Crypto Signal Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/tgbotigorkapa
ExecStart=/usr/bin/python3 /path/to/tgbotigorkapa/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Запуск:
```bash
sudo systemctl start crypto-signal-bot
sudo systemctl enable crypto-signal-bot
```

## Проверка работы

Логи находятся в папке `logs/`:
- `bot_YYYYMMDD.log` - основной лог
- `filters_YYYYMMDD.log` - лог фильтров

## Остановка

Если запущен в фоне:
```bash
pkill -f "python main.py"
```

Если через systemd:
```bash
sudo systemctl stop crypto-signal-bot
```

