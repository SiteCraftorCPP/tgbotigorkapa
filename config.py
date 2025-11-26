import os
from dotenv import load_dotenv

load_dotenv()

# XT.com API
XT_API_KEY = os.getenv('XT_API_KEY')
XT_API_SECRET = os.getenv('XT_API_SECRET')

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
TELEGRAM_ADMIN_CHANNEL_ID = os.getenv('TELEGRAM_ADMIN_CHANNEL_ID')  # Опционально, если не указан - используется основной канал

# Admins (через запятую, например: "123456789,987654321")
TELEGRAM_ADMIN_IDS = os.getenv('TELEGRAM_ADMIN_IDS', '').split(',') if os.getenv('TELEGRAM_ADMIN_IDS') else []

# Database
# Используем SQLite (файловая БД, работает без сервера)
DB_FILE = os.getenv('DB_FILE', 'crypto_signals.db')
DATABASE_URL = f"sqlite:///{DB_FILE}"

# System
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Technical Analysis Parameters
EMA_SHORT = 50
EMA_LONG = 200
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
ATR_PERIOD = 14
VOLUME_MA_PERIOD = 20


