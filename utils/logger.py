import logging
import os
from datetime import datetime
import config

# Создание директории для логов
if not os.path.exists('logs'):
    os.makedirs('logs')

# Настройка логирования
log_filename = f"logs/bot_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('CryptoSignalBot')

def log_signal(signal: dict):
    """Логирование сигнала"""
    logger.info(f"🔔 Новый сигнал: {signal['ticker']} {signal['direction']} | AI Score: {signal['ai_score']}")

def log_error(error: str, context: str = ""):
    """Логирование ошибки"""
    logger.error(f"❌ Ошибка {context}: {error}")

def log_info(message: str):
    """Информационное сообщение"""
    logger.info(message)

def log_warning(message: str):
    """Предупреждение"""
    logger.warning(f"⚠️ {message}")

