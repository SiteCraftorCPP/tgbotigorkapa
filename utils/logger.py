import logging
import os
import sys
from datetime import datetime
import config

# Создание директории для логов
if not os.path.exists('logs'):
    os.makedirs('logs')

# Настройка UTF-8 для Windows консоли
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except:
            pass

# Настройка логирования
log_filename = f"logs/bot_{datetime.now().strftime('%Y%m%d')}.log"
filter_log_filename = f"logs/filters_{datetime.now().strftime('%Y%m%d')}.log"

# Создание handlers с правильной кодировкой
handlers = [
    logging.FileHandler(log_filename, encoding='utf-8'),
]

# StreamHandler для консоли с UTF-8
try:
    if sys.platform == 'win32':
        # Для Windows используем StreamHandler с UTF-8
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(getattr(logging, config.LOG_LEVEL))
        handlers.append(stream_handler)
    else:
        handlers.append(logging.StreamHandler())
except:
    handlers.append(logging.StreamHandler())

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)

logger = logging.getLogger('CryptoSignalBot')

# Отдельный логгер для фильтров
filter_logger = logging.getLogger('FilterStats')
filter_logger.setLevel(logging.INFO)
filter_handler = logging.FileHandler(filter_log_filename, encoding='utf-8')
filter_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
filter_logger.addHandler(filter_handler)

# Статистика по фильтрам
_filter_stats = {
    'total_checks': 0,
    'passed': 0,
    'blocked': {},  # {filter_name: count}
    'last_reset': datetime.now()
}

def log_signal(signal: dict):
    """Логирование сигнала"""
    logger.info(f"[SIGNAL] New signal: {signal['ticker']} {signal['direction']} Entry:{signal['entry_price']}")
    filter_logger.info(f"[SIGNAL GENERATED] {signal['ticker']} {signal['direction']} TF:{signal['timeframe']}")

def log_error(error: str, context: str = ""):
    """Логирование ошибки"""
    logger.error(f"[ERROR] {context}: {error}")

def log_info(message: str):
    """Информационное сообщение"""
    logger.info(message)

def log_warning(message: str):
    """Предупреждение"""
    logger.warning(f"[WARNING] {message}")

def log_filter_block(ticker: str, timeframe: str, filter_name: str, reason: str):
    """Логирование блокировки фильтром"""
    global _filter_stats
    _filter_stats['total_checks'] += 1
    
    if filter_name not in _filter_stats['blocked']:
        _filter_stats['blocked'][filter_name] = 0
    _filter_stats['blocked'][filter_name] += 1
    
    # Записываем в лог фильтров
    filter_logger.info(f"[BLOCKED] {ticker} {timeframe} | Filter: {filter_name} | Reason: {reason}")

def log_filter_pass(ticker: str, timeframe: str):
    """Логирование прохождения всех фильтров"""
    global _filter_stats
    _filter_stats['total_checks'] += 1
    _filter_stats['passed'] += 1
    filter_logger.info(f"[PASSED] {ticker} {timeframe} | All filters passed")

def log_api_check(ticker: str, status: str, data: str = ""):
    """Логирование проверки API"""
    filter_logger.info(f"[API] {ticker} | Status: {status} | {data}")

def get_filter_stats() -> dict:
    """Получить статистику по фильтрам"""
    global _filter_stats
    return _filter_stats.copy()

def reset_filter_stats():
    """Сбросить статистику фильтров"""
    global _filter_stats
    _filter_stats = {
        'total_checks': 0,
        'passed': 0,
        'blocked': {},
        'last_reset': datetime.now()
    }

def log_filter_summary():
    """Логировать сводку по фильтрам"""
    global _filter_stats
    
    summary = f"\n{'='*60}\n"
    summary += f"FILTER STATISTICS (since {_filter_stats['last_reset'].strftime('%Y-%m-%d %H:%M')})\n"
    summary += f"{'='*60}\n"
    summary += f"Total checks: {_filter_stats['total_checks']}\n"
    summary += f"Passed: {_filter_stats['passed']}\n"
    summary += f"Blocked: {_filter_stats['total_checks'] - _filter_stats['passed']}\n"
    summary += f"\nBlocked by filter:\n"
    
    # Сортируем по количеству блокировок
    sorted_blocks = sorted(_filter_stats['blocked'].items(), key=lambda x: x[1], reverse=True)
    for filter_name, count in sorted_blocks:
        pct = (count / max(_filter_stats['total_checks'], 1)) * 100
        summary += f"  - {filter_name}: {count} ({pct:.1f}%)\n"
    
    summary += f"{'='*60}\n"
    
    logger.info(summary)
    filter_logger.info(summary)
    
    return summary

