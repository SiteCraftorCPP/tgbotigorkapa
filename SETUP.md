# 🚀 Быстрый старт

## 1. Настройка переменных окружения

Создайте файл `.env` в корне проекта с следующим содержимым:

```env
# XT.com API
XT_API_KEY=4e74f8bf-7424-4521-ba71-ded15621319a
XT_API_SECRET=your_xt_api_secret_here

# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHANNEL_ID=@your_channel
TELEGRAM_ADMIN_CHANNEL_ID=@your_admin_channel

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

# System
LOG_LEVEL=INFO
BOT_ENABLED=True
```

## 2. Получение Telegram Bot Token

1. Найдите @BotFather в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Скопируйте токен в `.env` → `TELEGRAM_BOT_TOKEN`

## 3. Создание Telegram каналов

### Основной канал (для сигналов):
1. Создайте публичный канал
2. Добавьте бота как администратора
3. Скопируйте username канала (например, @my_signals) в `.env` → `TELEGRAM_CHANNEL_ID`

### Админ-канал (для логов):
1. Создайте приватный канал
2. Добавьте бота как администратора
3. Скопируйте username в `.env` → `TELEGRAM_ADMIN_CHANNEL_ID`

## 4. Настройка PostgreSQL

### Windows:

1. Скачайте PostgreSQL с https://www.postgresql.org/download/windows/
2. Установите
3. Откройте pgAdmin или psql
4. Выполните:

```sql
CREATE DATABASE crypto_signals;
```

5. Обновите параметры в `.env`:
   - `DB_HOST=localhost`
   - `DB_PORT=5432`
   - `DB_NAME=crypto_signals`
   - `DB_USER=postgres`
   - `DB_PASSWORD=ваш_пароль`

### Или используйте Docker:

```bash
docker run -d \
  --name postgres-crypto \
  -e POSTGRES_DB=crypto_signals \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=your_password \
  -p 5432:5432 \
  postgres:14
```

## 5. Установка зависимостей

```bash
# Создать виртуальное окружение
python -m venv venv

# Активировать (Windows)
venv\Scripts\activate

# Активировать (Linux/Mac)
source venv/bin/activate

# Установить пакеты
pip install -r requirements.txt
```

## 6. Инициализация БД (опционально)

База создастся автоматически при первом запуске, либо вручную:

```bash
psql -U postgres -d crypto_signals -f database/migrations.sql
```

## 7. Запуск бота

```bash
python main.py
```

## 8. Проверка работы

В админ-канале должно появиться сообщение:
```
🤖 Бот запущен

Торгуемые пары: 4
Таймфреймы: 1m, 5m, 15m, 1h, 4h
Мин. AI Score: 70
```

## 9. Тестирование

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

### Проверка Telegram:

Отправьте команду `/start` боту в личку или в канал.

## 10. Мониторинг

- **Логи**: `logs/bot_YYYYMMDD.log`
- **Админ-канал**: все ошибки и уведомления
- **База данных**: таблица `signals` для всех сигналов

## Возможные проблемы

### Ошибка подключения к PostgreSQL:

```
FATAL: password authentication failed for user "postgres"
```

**Решение**: Проверьте пароль в `.env` и совпадает ли он с паролем PostgreSQL.

### Ошибка API ключа XT.com:

```
ccxt.AuthenticationError: XT {"returnCode":10004}
```

**Решение**: 
1. Проверьте правильность API ключа
2. Убедитесь, что у ключа есть права на чтение рынка (futures)
3. Проверьте, что IP не заблокирован

### Ошибка Telegram:

```
telegram.error.Unauthorized: Forbidden
```

**Решение**:
1. Проверьте токен бота
2. Убедитесь, что бот добавлен в канал как администратор
3. Проверьте правильность username канала (@channel)

### Нет данных от биржи:

```
❌ Ошибка получения OHLCV для BTC/USDT
```

**Решение**:
1. Проверьте интернет-соединение
2. Проверьте, что биржа доступна
3. Проверьте формат пары (должно быть `BTC/USDT`, а не `BTCUSDT`)

## Полезные команды

```bash
# Просмотр логов в реальном времени (Linux/Mac)
tail -f logs/bot_*.log

# Просмотр активных сигналов в БД
psql -U postgres -d crypto_signals -c "SELECT * FROM signals WHERE status='ACTIVE';"

# Статистика
psql -U postgres -d crypto_signals -c "SELECT * FROM pair_stats;"
psql -U postgres -d crypto_signals -c "SELECT * FROM daily_stats;"
```

## Рекомендации

1. **Начните с малого**: используйте 2-3 пары для начала
2. **Мониторинг**: следите за админ-каналом первые дни
3. **Бэкапы**: настройте автоматический бэкап БД
4. **Безопасность**: не публикуйте `.env` файл
5. **Тестирование**: первые дни следите за качеством сигналов

## Поддержка

При проблемах проверьте:
- ✅ Все API ключи заполнены
- ✅ PostgreSQL запущен
- ✅ Бот добавлен в каналы
- ✅ Виртуальное окружение активировано
- ✅ Все пакеты установлены

Удачи! 🚀

