# 🤖 Крипто-сигнальный бот для фьючерсов

Полностью автоматизированный бот для генерации торговых сигналов на фьючерсном рынке криптовалют с интеграцией Telegram.

## 🚀 Возможности

- ✅ Анализ рынка в реальном времени (биржа XT.com)
- ✅ Технический анализ (EMA, RSI, MACD, Stochastic, ATR, VWAP)
- ✅ Генерация сигналов LONG/SHORT с AI Score
- ✅ Автоматическая публикация в Telegram-канал
- ✅ Мониторинг активных сигналов
- ✅ Расчёт уровней входа/стопа/тейк-профитов
- ✅ Статистика результативности (Winrate, PnL, RR)
- ✅ Админ-панель через Telegram
- ✅ База данных PostgreSQL
- ✅ Логирование и обработка ошибок

## 📋 Требования

- Python 3.10+
- PostgreSQL 14+
- Telegram Bot Token
- API ключи XT.com

## 🛠 Установка

### 1. Клонирование репозитория

```bash
git clone <your-repo-url>
cd tgbotigorkapa
```

### 2. Создание виртуального окружения

```bash
python -m venv venv
venv\Scripts\activate  # Windows
# или
source venv/bin/activate  # Linux/Mac
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Настройка базы данных

Создайте базу данных PostgreSQL:

```sql
CREATE DATABASE crypto_signals;
```

### 5. Настройка переменных окружения

Скопируйте `.env.example` в `.env` и заполните:

```bash
cp .env.example .env
```

Отредактируйте `.env`:

```env
# XT.com API
XT_API_KEY=your_xt_api_key
XT_API_SECRET=your_xt_secret

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHANNEL_ID=@your_channel
TELEGRAM_ADMIN_CHANNEL_ID=@admin_channel

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=crypto_signals
DB_USER=postgres
DB_PASSWORD=your_password

# Bot Settings
RISK_PERCENT=1.0
DEFAULT_LEVERAGE=10
MIN_AI_SCORE=70
TIMEFRAMES=1m,5m,15m,1h,4h
TRADING_PAIRS=BTC/USDT,ETH/USDT,BNB/USDT,SOL/USDT
```

### 6. Инициализация базы данных

База создастся автоматически при первом запуске, либо вручную:

```python
from database.models import init_db
init_db()
```

## 🚀 Запуск

```bash
python main.py
```

## 📱 Telegram команды

### Для пользователей:
- `/start` - Информация о боте
- `/stats` - Общая статистика
- `/today` - Статистика за сегодня
- `/week` - Статистика за неделю
- `/pairs` - Список торгуемых пар

### Для админов:
- `/enable` - Включить бота
- `/disable` - Выключить бота

## 📊 Формат сигнала

```
🟢 Futures сигнал

📊 Монета: BTCUSDT
📍 Направление: LONG

💰 Вход: 62350
🛑 Стоп: 61700
🎯 TP1: 62900 (+0.88%)
🎯 TP2: 63500 (+1.84%)

⚠️ Риск: 1%
📈 Плечо: х10
🤖 AI Score: 82/100

🕐 Таймфрейм: 1h
🆔 ID: a3f2e4b1
```

## 🏗 Архитектура

```
tgbotigorkapa/
├── analysis/              # Модули анализа
│   ├── indicators.py      # Технические индикаторы
│   └── signal_generator.py # Генератор сигналов
├── database/              # База данных
│   └── models.py          # SQLAlchemy модели
├── exchange/              # Интеграция с биржей
│   └── xt_client.py       # Клиент XT.com
├── telegram_bot/          # Telegram бот
│   └── bot.py             # Основной бот
├── utils/                 # Утилиты
│   └── logger.py          # Логирование
├── logs/                  # Логи (создается автоматически)
├── config.py              # Конфигурация
├── main.py                # Точка входа
├── requirements.txt       # Зависимости
├── .env.example           # Пример конфига
└── README.md              # Документация
```

## 🔧 Настройка

### Изменение торгуемых пар

В `.env`:
```env
TRADING_PAIRS=BTC/USDT,ETH/USDT,SOL/USDT
```

### Изменение таймфреймов

В `.env`:
```env
TIMEFRAMES=5m,15m,1h,4h
```

### Изменение порога AI Score

В `.env`:
```env
MIN_AI_SCORE=75
```

### Настройка весов индикаторов

В `config.py`:
```python
WEIGHTS = {
    'trend': 0.25,
    'momentum': 0.20,
    'volume': 0.15,
    'volatility': 0.15,
    'rsi': 0.15,
    'macd': 0.10
}
```

## 📈 Статистика

Бот сохраняет в БД:
- ID сигнала
- Тикер, направление
- Уровни входа/выхода
- AI Score
- Результат (WIN/LOSS)
- PnL (%)
- Risk/Reward
- Временные метки

## 🔍 Логирование

Логи сохраняются в `logs/bot_YYYYMMDD.log`

Уровни:
- INFO - Общая информация
- WARNING - Предупреждения
- ERROR - Ошибки

## ⚠️ Важные замечания

1. **API ключи**: Храните в `.env`, не коммитьте в Git
2. **Rate Limits**: Бот учитывает лимиты API биржи
3. **Тестирование**: Рекомендуется начать с небольшого кол-ва пар
4. **Мониторинг**: Следите за админ-каналом Telegram
5. **База данных**: Регулярно делайте бэкапы

## 🐛 Отладка

### Проверка соединения с биржей:

```python
from exchange.xt_client import XTClient
import asyncio

async def test():
    client = XTClient()
    ticker = await client.get_ticker('BTC/USDT')
    print(ticker)

asyncio.run(test())
```

### Проверка генерации сигналов:

```python
from analysis.signal_generator import SignalGenerator
from exchange.xt_client import XTClient
import asyncio

async def test():
    client = XTClient()
    df = await client.get_ohlcv('BTC/USDT', '1h', 500)
    generator = SignalGenerator('BTC/USDT', '1h', df)
    signal = generator.generate_signal()
    print(signal)

asyncio.run(test())
```

## 📝 TODO

- [ ] Веб-панель для управления
- [ ] Интеграция с другими биржами (Binance, Bybit)
- [ ] ML модель для прогнозирования
- [ ] Backtesting модуль
- [ ] Авто-трейдинг (опционально)

## 📄 Лицензия

MIT License

## 👨‍💻 Автор

Разработано для автоматизации крипто-трейдинга

## 🆘 Поддержка

При возникновении проблем:
1. Проверьте логи в `logs/`
2. Проверьте админ-канал Telegram
3. Убедитесь, что все API ключи корректны
4. Проверьте соединение с БД

---

**Дисклеймер**: Бот предоставляется "как есть". Торговля криптовалютами сопряжена с рисками. Используйте на свой риск.

