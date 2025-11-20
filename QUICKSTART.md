# ⚡ QUICK START / БЫСТРЫЙ СТАРТ

## 🇬🇧 English

### Prerequisites
- Python 3.10+
- PostgreSQL 14+
- Telegram account

### Installation (5 minutes)

**1. Install dependencies**
```bash
cd tgbotigorkapa
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**2. Setup PostgreSQL**
```sql
CREATE DATABASE crypto_signals;
```

**3. Configure .env**

The `.env` file already contains XT.com API keys! Just add:

```env
# Already configured ✅
XT_API_KEY=4e74f8bf-7424-4521-ba71-ded15621319a
XT_API_SECRET=a0d77d78d99e2b7cec4a941277fccef00877660c

# Configure these ⚠️
TELEGRAM_BOT_TOKEN=get_from_BotFather
TELEGRAM_CHANNEL_ID=@your_channel
TELEGRAM_ADMIN_CHANNEL_ID=@admin_channel

DB_PASSWORD=your_postgresql_password
```

**4. Get Telegram Bot Token**
- Message @BotFather in Telegram
- Send `/newbot`
- Copy token to `.env`

**5. Create Telegram Channels**
- Create 2 channels (main + admin)
- Add bot as administrator to both
- Copy usernames to `.env`

**6. Add Admins to Database**
```bash
# Get your Telegram ID from @userinfobot
psql -U postgres -d crypto_signals

# Then:
INSERT INTO admins (telegram_id, username, first_name) 
VALUES ('your_telegram_id', 'username', 'Name');
```

**7. Run**
```bash
python main.py
```

**8. Test**
```
Message your bot: /start
Switch language: /language
Check status: /config
Enable bot: /enable
```

---

## 🇷🇺 Русский

### Требования
- Python 3.10+
- PostgreSQL 14+
- Telegram аккаунт

### Установка (5 минут)

**1. Установить зависимости**
```bash
cd tgbotigorkapa
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**2. Настроить PostgreSQL**
```sql
CREATE DATABASE crypto_signals;
```

**3. Настроить .env**

Файл `.env` уже содержит API ключи XT.com! Добавьте только:

```env
# Уже настроено ✅
XT_API_KEY=4e74f8bf-7424-4521-ba71-ded15621319a
XT_API_SECRET=a0d77d78d99e2b7cec4a941277fccef00877660c

# Настройте это ⚠️
TELEGRAM_BOT_TOKEN=получите_от_BotFather
TELEGRAM_CHANNEL_ID=@ваш_канал
TELEGRAM_ADMIN_CHANNEL_ID=@админ_канал

DB_PASSWORD=ваш_пароль_postgresql
```

**4. Получить токен Telegram бота**
- Напишите @BotFather в Telegram
- Отправьте `/newbot`
- Скопируйте токен в `.env`

**5. Создать Telegram каналы**
- Создайте 2 канала (основной + админ)
- Добавьте бота как администратора в оба
- Скопируйте username в `.env`

**6. Добавить админов в БД**
```bash
# Получите ваш Telegram ID от @userinfobot
psql -U postgres -d crypto_signals

# Затем:
INSERT INTO admins (telegram_id, username, first_name) 
VALUES ('ваш_telegram_id', 'username', 'Имя');
```

**7. Запустить**
```bash
python main.py
```

**8. Проверить**
```
Напишите боту: /start
Сменить язык: /language
Проверить статус: /config
Включить бота: /enable
```

---

## 📚 Full Documentation / Полная Документация

- **README.md** - Main info / Основная информация
- **SPECIFICATION.md** - Technical specs / Техническое задание
- **SETUP.md** - Detailed setup / Подробная установка
- **ADMIN_SETUP.md** - Admin configuration / Настройка админов

---

## ⚠️ Troubleshooting / Решение Проблем

**Database Error:**
```
FATAL: password authentication failed
```
→ Check DB_PASSWORD in `.env` / Проверьте DB_PASSWORD в `.env`

**Telegram Error:**
```
Unauthorized: Forbidden
```
→ Add bot as admin to channels / Добавьте бота админом в каналы

**Commands Don't Work:**
```
❌ No permission
```
→ Add yourself to `admins` table / Добавьте себя в таблицу `admins`

---

## 🚀 You're Ready! / Готово!

Bot will:
- Analyze market every 5 minutes
- Generate ultra-conservative signals
- Monitor positions every 5 seconds
- Send all updates to Telegram

Бот будет:
- Анализировать рынок каждые 5 минут
- Генерировать ультраконсервативные сигналы
- Мониторить позиции каждые 5 секунд
- Отправлять все обновления в Telegram

**Good luck! / Удачи!** 📈

