# 🆕 LATEST UPDATES / ПОСЛЕДНИЕ ОБНОВЛЕНИЯ

## 🇬🇧 English

### Version 2.0 - Multi-Language & Updated Risk Management

**Release Date**: 2024-11-20

#### ✨ New Features

1. **🌐 Multi-Language Support**
   - English and Russian languages
   - Users can switch via `/language` command
   - All bot messages translated (commands, signals, notifications)
   - User preferences stored in database

2. **📊 Updated Risk Management**
   - Total risk limit increased: **5% → 20%**
   - Allows more active signals simultaneously
   - Still maintains 1% risk per trade
   - Better capital utilization

3. **📋 New Specification Document**
   - `SPECIFICATION.md` - bilingual technical specification
   - Complete requirements list (EN + RU)
   - Implementation status for each requirement

#### 🔧 Technical Changes

**New Files:**
- `telegram_bot/languages.py` - Translation dictionary (200+ phrases)
- `database/user_preferences.py` - User language preferences
- `SPECIFICATION.md` - Full technical specification

**Modified Files:**
- `database/risk_manager.py` - `MAX_TOTAL_RISK = 20.0`
- `telegram_bot/bot.py` - Multi-language support added
- `database/migrations.sql` - `user_preferences` table added
- `README.md` - Bilingual documentation

**Removed Files:**
- `ULTRA_CONSERVATIVE.md` - Replaced by `SPECIFICATION.md`

#### 🎯 How to Use

**Switch Language:**
```
1. Send /language command
2. Click 🇬🇧 English or 🇷🇺 Русский
3. All messages now in your language!
```

**Risk Management:**
- Bot now can handle up to **20 active signals** (was 5)
- Each signal still limited to 1% risk
- Better diversification across multiple coins

#### 🔄 Migration Required

Run these SQL commands to update your database:

```sql
-- Add user_preferences table
CREATE TABLE IF NOT EXISTS user_preferences (
    id SERIAL PRIMARY KEY,
    telegram_id VARCHAR(50) UNIQUE NOT NULL,
    language VARCHAR(5) DEFAULT 'en',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_prefs_telegram_id 
ON user_preferences(telegram_id);
```

Or simply run: `python main.py` (will create table automatically)

#### 📦 Installation

No changes to installation process. See `SETUP.md`.

---

## 🇷🇺 Русский

### Версия 2.0 - Мультиязычность и Обновлённое Управление Рисками

**Дата выпуска**: 20.11.2024

#### ✨ Новые Возможности

1. **🌐 Поддержка Нескольких Языков**
   - Английский и русский языки
   - Переключение через команду `/language`
   - Все сообщения бота переведены (команды, сигналы, уведомления)
   - Предпочтения пользователя хранятся в БД

2. **📊 Обновлённое Управление Рисками**
   - Лимит суммарного риска увеличен: **5% → 20%**
   - Позволяет больше активных сигналов одновременно
   - Сохранён риск 1% на сделку
   - Лучшее использование капитала

3. **📋 Новый Документ Спецификации**
   - `SPECIFICATION.md` - двуязычная техническая спецификация
   - Полный список требований (EN + RU)
   - Статус реализации каждого требования

#### 🔧 Технические Изменения

**Новые Файлы:**
- `telegram_bot/languages.py` - Словарь переводов (200+ фраз)
- `database/user_preferences.py` - Языковые предпочтения пользователей
- `SPECIFICATION.md` - Полная техническая спецификация

**Изменённые Файлы:**
- `database/risk_manager.py` - `MAX_TOTAL_RISK = 20.0`
- `telegram_bot/bot.py` - Добавлена мультиязычность
- `database/migrations.sql` - Добавлена таблица `user_preferences`
- `README.md` - Двуязычная документация

**Удалённые Файлы:**
- `ULTRA_CONSERVATIVE.md` - Заменён на `SPECIFICATION.md`

#### 🎯 Как Использовать

**Сменить Язык:**
```
1. Отправьте команду /language
2. Нажмите 🇬🇧 English или 🇷🇺 Русский
3. Все сообщения теперь на вашем языке!
```

**Управление Рисками:**
- Бот теперь может обрабатывать до **20 активных сигналов** (было 5)
- Каждый сигнал всё ещё ограничен 1% риска
- Лучшая диверсификация по нескольким монетам

#### 🔄 Требуется Миграция

Выполните эти SQL команды для обновления БД:

```sql
-- Добавить таблицу user_preferences
CREATE TABLE IF NOT EXISTS user_preferences (
    id SERIAL PRIMARY KEY,
    telegram_id VARCHAR(50) UNIQUE NOT NULL,
    language VARCHAR(5) DEFAULT 'en',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_prefs_telegram_id 
ON user_preferences(telegram_id);
```

Или просто запустите: `python main.py` (создаст таблицу автоматически)

#### 📦 Установка

Нет изменений в процессе установки. См. `SETUP.md`.

---

## 🔗 Links / Ссылки

- **Full Specification** / **Полная Спецификация**: `SPECIFICATION.md`
- **Installation Guide** / **Руководство по Установке**: `SETUP.md`
- **Admin Setup** / **Настройка Админов**: `ADMIN_SETUP.md`
- **Main Documentation** / **Основная Документация**: `README.md`

---

## 📊 Comparison / Сравнение

| Feature / Параметр | v1.0 | v2.0 |
|-------|------|------|
| Languages / Языки | 🇷🇺 Russian only | 🇬🇧 EN + 🇷🇺 RU |
| Total Risk / Суммарный риск | 5% | **20%** ⚡ |
| Max Active Signals / Макс. активных | 5 | **20** |
| User Preferences / Настройки юзера | ❌ | ✅ |
| Specification Doc / Док. спецификации | ❌ | ✅ |

---

## ⚠️ Breaking Changes / Критические Изменения

**None!** / **Нет!**

All changes are **backward compatible**. Existing installations will work without modifications.

Все изменения **обратно совместимы**. Существующие установки будут работать без модификаций.

---

## 🚀 Next Steps / Следующие Шаги

**EN**:
1. Pull latest changes: `git pull`
2. Install new dependencies: `pip install -r requirements.txt` (no new deps)
3. Run bot: `python main.py`
4. Try `/language` command
5. Enjoy multi-language support!

**RU**:
1. Получить последние изменения: `git pull`
2. Установить зависимости: `pip install -r requirements.txt` (нет новых)
3. Запустить бота: `python main.py`
4. Попробовать команду `/language`
5. Наслаждайтесь мультиязычностью!

---

**Last Updated** / **Последнее Обновление**: 2024-11-20

