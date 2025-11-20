# 🚀 Установка Ультраконсервативного Крипто-Бота

## ⚡ Быстрый старт

### 1. Клонирование

```bash
cd C:\Users\MOD PC COMPANY\Desktop
cd tgbotigorkapa
```

### 2. Виртуальное окружение

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 3. PostgreSQL

**Установить:** https://www.postgresql.org/download/windows/

**Создать БД:**

```powershell
# Открыть SQL Shell (psql)
CREATE DATABASE crypto_signals;
```

### 4. Настройка .env

Файл `.env` уже создан с API ключами XT.com!

Отредактируйте:

```env
# XT.com - УЖЕ НАСТРОЕНО!
XT_API_KEY=4e74f8bf-7424-4521-ba71-ded15621319a
XT_API_SECRET=a0d77d78d99e2b7cec4a941277fccef00877660c

# Telegram - НАСТРОЙТЕ!
TELEGRAM_BOT_TOKEN=получите_от_BotFather
TELEGRAM_CHANNEL_ID=@ваш_канал
TELEGRAM_ADMIN_CHANNEL_ID=@админ_канал

# PostgreSQL - НАСТРОЙТЕ!
DB_PASSWORD=ваш_пароль_postgresql
```

### 5. Telegram бот

**Создать бота:**
1. Найдите @BotFather в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Скопируйте токен → `.env` → `TELEGRAM_BOT_TOKEN`

**Создать каналы:**
1. **Основной канал** (для сигналов):
   - Создайте публичный канал
   - Добавьте бота как администратора
   - Скопируйте @username → `.env` → `TELEGRAM_CHANNEL_ID`

2. **Админ-канал** (для логов):
   - Создайте приватный канал
   - Добавьте бота как администратора  
   - Скопируйте @username → `.env` → `TELEGRAM_ADMIN_CHANNEL_ID`

### 6. Добавить админов в БД

**КРИТИЧЕСКИ ВАЖНО!**

**Узнать Telegram ID:**
- Напишите @userinfobot → `/start`
- Скопируйте ваш ID (например: 123456789)

**Добавить в БД:**

```powershell
# Подключиться к БД
psql -U postgres -d crypto_signals

# Выполнить:
INSERT INTO admins (telegram_id, username, first_name) 
VALUES ('ваш_telegram_id', 'username', 'Имя');

INSERT INTO admins (telegram_id, username, first_name) 
VALUES ('id_второго_админа', 'username', 'Имя');

# Проверить
SELECT * FROM admins;

# Выйти
\q
```

### 7. Запуск

```powershell
python main.py
```

### 8. Проверка

**В админ-канале появится:**

```
🤖 Бот запущен

Торгуемые пары: 4
Таймфреймы: 1m, 5m, 15m, 1h, 4h
Мин. AI Score: 70
```

**Напишите боту:**

```
/start
/config
```

**Настройте:**

```
/set_pairs BTC/USDT ETH/USDT SOL/USDT
/set_timeframes 15m 1h 4h
/set_ai_score 80
/enable
```

---

## 🔧 Расширенная настройка

### Риск-параметры (в коде)

Файл `database/risk_manager.py`:

```python
MAX_RISK_PER_TRADE = 1.0      # 1% на сделку
MAX_TOTAL_RISK = 5.0          # 5% суммарный
MAX_SIGNALS_PER_DAY = 20      # Макс сигналов/день
COOLDOWN_HOURS = 4            # Cooldown для монеты
```

### Фильтры (в коде)

Файл `analysis/conservative_filters.py`:

```python
TOP_COINS_LIMIT = 100         # Только ТОП-100
MIN_VOLUME_24H = 5_000_000    # $5M минимум
MAX_SPREAD_PERCENT = 0.3      # 0.3% максимум
MAX_ATR_RATIO = 2.5           # Макс размер стопа
```

---

## 🆘 Частые проблемы

### Ошибка БД:

```
FATAL: password authentication failed
```

**Решение:** Проверьте пароль в `.env` → `DB_PASSWORD`

### Ошибка API XT.com:

```
ccxt.AuthenticationError
```

**Решение:** API ключи уже в `.env`, но проверьте права на XT.com:
- Зайдите на XT.com → API Management
- Проверьте, что API активен
- Права: Read Only (для сигналов достаточно)

### Ошибка Telegram:

```
Unauthorized: Forbidden
```

**Решение:**
1. Проверьте токен бота
2. Добавьте бота в каналы как **администратора**
3. Username каналов должен начинаться с `@`

### Команды не работают:

```
❌ У вас нет прав
```

**Решение:** Добавьте себя в таблицу `admins` (см. шаг 6)

---

## 📊 Мониторинг

### Логи:

```powershell
# Просмотр логов
type logs\bot_YYYYMMDD.log

# Последние 50 строк
Get-Content logs\bot_*.log -Tail 50
```

### База данных:

```sql
-- Активные сигналы
SELECT * FROM signals WHERE status IN ('WAITING', 'IN_POSITION');

-- Статистика
SELECT * FROM pair_stats;
SELECT * FROM daily_stats;

-- Последние сигналы
SELECT signal_id, ticker, direction, status, ai_score, created_at 
FROM signals 
ORDER BY created_at DESC 
LIMIT 10;
```

---

## ✅ Чек-лист готовности

Перед запуском убедитесь:

- [x] PostgreSQL установлен и запущен
- [x] База `crypto_signals` создана
- [x] `.env` файл заполнен
- [x] Telegram бот создан
- [x] 2 канала созданы и бот добавлен как админ
- [x] Админы добавлены в БД
- [x] Зависимости установлены (`pip install -r requirements.txt`)

---

## 🎓 Дополнительно

### Методы мониторинга

Файл `main_monitoring.py` содержит дополнительные методы.

**Скопируйте их в `main.py` в класс `CryptoSignalBot`:**

- `_check_waiting_signal()` - проверка сигналов в ожидании
- `_check_position_levels()` - проверка TP/SL
- `_hit_tp()` - обработка достижения TP
- _close_on_stop()` - закрытие по стоп-лоссу

### Тестирование

```powershell
python test_bot.py
```

Проверяет:
- ✅ Подключение к БД
- ✅ Подключение к XT.com
- ✅ Технический анализ
- ✅ Генерацию сигналов

---

## 🚀 Готово!

После настройки бот будет:

1. **Анализировать рынок** каждые 5 минут
2. **Генерировать сигналы** с AI Score и фильтрами
3. **Публиковать** в Telegram-канал
4. **Отслеживать** каждые 5 секунд:
   - Активацию входа
   - Достижение TP1/TP2/TP3/TP4
   - Срабатывание SL
   - Перенос в безубыток
5. **Отменять** неактуальные сигналы автоматически

**Все настройки управляются через Telegram!**

---

Успехов! 📈
