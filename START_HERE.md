# 🚀 НАЧНИТЕ ОТСЮДА

## Проект готов на 100%!

Крипто-сигнальный бот для фьючерсов XT.com с полной автоматизацией и админ-панелью через Telegram.

---

## 📋 Что реализовано

✅ **ВСЁ из ТЗ + дополнительно:**

1. **Анализ рынка 24/7**
   - Подключение к XT.com через CCXT
   - Технический анализ (EMA, RSI, MACD, Stochastic, ATR, VWAP)
   - AI Score для оценки качества сигналов

2. **Генерация сигналов**
   - LONG/SHORT с уровнями Entry/Stop/TP1/TP2
   - Автоматический расчёт на основе ATR
   - Фильтрация по AI Score (настраиваемый порог)

3. **Telegram интеграция**
   - Публикация сигналов в канал
   - Админ-канал для логов/ошибок
   - 15+ команд управления

4. **База данных PostgreSQL**
   - Хранение всех сигналов
   - Статистика (Winrate, PnL, RR)
   - Настройки в БД (не .env!)

5. **Система администраторов** 👥 (НОВОЕ!)
   - Два конкретных юзера через БД
   - Все настройки только через Telegram
   - Проверка прав для каждой команды
   - Нельзя удалить последнего админа

6. **Управление через Telegram** ⚙️
   - `/set_pairs` - торгуемые пары
   - `/set_timeframes` - таймфреймы
   - `/set_ai_score` - минимальный AI Score
   - `/set_risk` - процент риска
   - `/set_leverage` - плечо
   - `/enable` / `/disable` - вкл/выкл бота

---

## 🎯 Быстрый старт

### Шаг 1: Настройка окружения

```bash
# Виртуальное окружение
python -m venv venv
venv\Scripts\activate

# Установка пакетов
pip install -r requirements.txt
```

### Шаг 2: PostgreSQL

1. Установите PostgreSQL
2. Создайте БД:
```sql
CREATE DATABASE crypto_signals;
```
3. Запустите миграции (автоматически при первом запуске)

### Шаг 3: Telegram бот

1. @BotFather → `/newbot` → получите токен
2. Создайте 2 канала:
   - Основной (для сигналов) - добавьте бота как админа
   - Админ-канал (для логов) - добавьте бота как админа
3. Скопируйте username каналов (например: @my_signals)

### Шаг 4: .env файл

Создайте `.env` в корне проекта:

```env
# XT.com API
XT_API_KEY=4e74f8bf-7424-4521-ba71-ded15621319a
XT_API_SECRET=ваш_секретный_ключ_от_XT

# Telegram
TELEGRAM_BOT_TOKEN=ваш_токен_от_botfather
TELEGRAM_CHANNEL_ID=@your_signals_channel
TELEGRAM_ADMIN_CHANNEL_ID=@your_admin_channel

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=crypto_signals
DB_USER=postgres
DB_PASSWORD=ваш_пароль_от_postgresql

# System
LOG_LEVEL=INFO
BOT_ENABLED=True
```

### Шаг 5: Добавить админов в БД

**ВАЖНО!** Без этого шага вы не сможете управлять ботом!

1. Узнайте свой Telegram ID:
   - Напишите @userinfobot → `/start`
   - Скопируйте ваш ID (например: 123456789)

2. Добавьте себя и второго админа в БД:

```bash
# Подключитесь к БД
psql -U postgres -d crypto_signals

# Выполните SQL:
INSERT INTO admins (telegram_id, username, first_name) 
VALUES ('ваш_telegram_id', 'ваш_username', 'Ваше Имя');

INSERT INTO admins (telegram_id, username, first_name) 
VALUES ('id_второго_админа', 'username_админа', 'Имя Админа');

# Проверьте
SELECT * FROM admins;
```

**Подробнее: ADMIN_SETUP.md**

### Шаг 6: Запуск бота

```bash
python main.py
```

### Шаг 7: Проверка и настройка

Напишите боту в личку:

```
/start       # Проверка прав
/config      # Текущие настройки
/set_pairs BTC/USDT ETH/USDT SOL/USDT
/set_timeframes 15m 1h 4h
/set_ai_score 75
/enable      # Включить бота
```

---

## 📚 Документация

- **README.md** - общее описание проекта
- **SETUP.md** - подробная установка и настройка
- **ADMIN_SETUP.md** - настройка администраторов
- **TZ_CHECKLIST.md** - выполнение всех пунктов ТЗ
- **GIT_PUSH.md** - инструкция по пушу в GitHub
- **test_bot.py** - тестирование компонентов

---

## 🔧 Админ-команды (только для админов из БД)

### Управление ботом:
```
/enable          # Включить
/disable         # Выключить
/config          # Текущие настройки
```

### Настройка параметров:
```
/set_pairs BTC/USDT ETH/USDT
/set_timeframes 5m 15m 1h 4h
/set_ai_score 75
/set_risk 1.5
/set_leverage 20
```

### Управление админами:
```
/add_admin 123456789
/remove_admin 123456789
/list_admins
```

### Статистика (доступна всем):
```
/stats           # Общая
/today           # За сегодня
/week            # За неделю
```

---

## 🎯 Структура проекта

```
tgbotigorkapa/
├── analysis/              # Технический анализ
│   ├── indicators.py      # EMA, RSI, MACD, ATR, VWAP
│   └── signal_generator.py # Генерация сигналов с AI Score
├── database/              # База данных
│   ├── models.py          # Таблицы: signals, bot_stats, bot_config, admins
│   ├── config_manager.py  # Управление настройками из БД
│   ├── admin_manager.py   # Проверка прав админов
│   └── migrations.sql     # SQL миграции
├── exchange/              # Биржа
│   └── xt_client.py       # Клиент XT.com (OHLCV, orderbook, funding)
├── telegram_bot/          # Telegram
│   └── bot.py             # Бот с командами и админ-панелью
├── utils/                 # Утилиты
│   └── logger.py          # Логирование
├── main.py                # Запуск бота
├── config.py              # Базовая конфигурация
├── test_bot.py            # Тестирование
└── requirements.txt       # Зависимости
```

---

## ⚠️ Важно

1. **Админы в БД обязательны!** Без них команды не работают
2. **Все настройки через Telegram**, а не .env
3. **API Secret XT.com** нужно получить в настройках биржи
4. **Telegram каналы** - бот должен быть админом
5. **PostgreSQL** должен быть запущен

---

## 🧪 Тестирование

Перед запуском основного бота:

```bash
python test_bot.py
```

Проверит:
- ✅ Подключение к БД
- ✅ Подключение к XT.com
- ✅ Технический анализ
- ✅ Генерацию сигналов

---

## 🆘 Проблемы?

### Ошибка БД:
```
FATAL: password authentication failed
```
→ Проверьте пароль в `.env`

### Ошибка API:
```
ccxt.AuthenticationError
```
→ Проверьте XT_API_KEY и XT_API_SECRET

### Ошибка Telegram:
```
Unauthorized: Forbidden
```
→ Проверьте токен и добавьте бота в каналы как админа

### Команды не работают:
```
❌ У вас нет прав
```
→ Добавьте себя в таблицу admins (см. ADMIN_SETUP.md)

---

## 📊 Пример работы

### В основном канале:
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

### При закрытии:
```
✅ Сигнал закрыт

🆔 ID: a3f2e4b1
📊 Результат: WIN
💵 PnL: +8.8%
```

---

## 🚀 Готово к запуску!

Всё работает и соответствует ТЗ на 100%.

**Следующие шаги:**
1. Настроить окружение (шаги 1-4)
2. Добавить админов в БД (шаг 5) ← ОБЯЗАТЕЛЬНО!
3. Запустить бота (шаг 6)
4. Настроить через Telegram (шаг 7)
5. Наслаждаться автоматическими сигналами! 🎉

---

Успехов в трейдинге! 📈💰

