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

# DeepSeek AI
DEEPSEEK_API_KEYS = [k.strip() for k in os.getenv('DEEPSEEK_API_KEYS', '').split(',') if k.strip()]
DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
DEEPSEEK_API_BASE = os.getenv('DEEPSEEK_API_BASE', 'https://api.deepseek.com')

# Fallback keys provided for local testing (override via .env in production)
if not DEEPSEEK_API_KEYS:
    DEEPSEEK_API_KEYS = [
        "sk-a5fb722bd2e24a3a8a91026b511bc8b6",
        "sk-fc1ce12604dc470083901dee28b43050",
        "sk-beee0468c09140b2b167b8416df9baa4",
        "sk-de69818ec81d4a8085c0bda1f568e628",
    ]

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


