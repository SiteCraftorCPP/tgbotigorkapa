import os
from dotenv import load_dotenv

load_dotenv()

# XT.com API
XT_API_KEY = os.getenv('XT_API_KEY')
XT_API_SECRET = os.getenv('XT_API_SECRET')

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
TELEGRAM_ADMIN_CHANNEL_ID = os.getenv('TELEGRAM_ADMIN_CHANNEL_ID')

# Database
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'crypto_signals')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Bot Settings
RISK_PERCENT = float(os.getenv('RISK_PERCENT', '1.0'))
DEFAULT_LEVERAGE = int(os.getenv('DEFAULT_LEVERAGE', '10'))
MIN_AI_SCORE = int(os.getenv('MIN_AI_SCORE', '70'))
TIMEFRAMES = os.getenv('TIMEFRAMES', '1m,5m,15m,1h,4h').split(',')
TRADING_PAIRS = os.getenv('TRADING_PAIRS', 'BTC/USDT,ETH/USDT,BNB/USDT,SOL/USDT').split(',')

# System
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
BOT_ENABLED = os.getenv('BOT_ENABLED', 'True').lower() == 'true'

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

# Signal Weights для AI Score
WEIGHTS = {
    'trend': 0.25,
    'momentum': 0.20,
    'volume': 0.15,
    'volatility': 0.15,
    'rsi': 0.15,
    'macd': 0.10
}

