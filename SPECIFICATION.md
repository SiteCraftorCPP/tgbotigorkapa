# 📋 TECHNICAL SPECIFICATION / ТЕХНИЧЕСКОЕ ЗАДАНИЕ

## 🇬🇧 English Version

### 0. Project Description
The bot automatically analyzes the market, generates ultra-conservative cryptocurrency signals with a risk of no more than 1% per trade, uses 4 Take Profit levels, monitors the market in real time, and automatically reports all changes to a trade's status.

### 1. Core Principles
- The main goal is **capital safety**.
- Risk ≤ **1% per trade**.
- Total risk of all active trades ≤ **20%**.
- Only signals with **multiple confirmations**.
- No intuitive or emotional entries.
- The bot operates strictly by rules.

### 2. Bot Modules
- ✅ Market analysis
- ✅ Signal generation
- ✅ Signal filtering
- ✅ Signal state management
- ✅ Market monitoring
- ✅ Telegram notifications

### 3. Risk Management
- ✅ Position size calculated based on Stop Loss
- ✅ Max 1% risk per trade
- ✅ Max **20% total active risk**
- ✅ Max 20 signals per day
- ✅ Max 1 signal per coin at the same time
- ✅ No averaging down

**Implementation**: `database/risk_manager.py`

### 4. Pre-Signal Filters
- ✅ Only coins from TOP-100
- ✅ Daily volume ≥ $5–10M
- ✅ Spread ≤ 0.1–0.3%
- ✅ Volatility limited by ATR
- ✅ Multi-timeframe trend (H4/H1)
- ⏳ BTC/ETH correlation filter (optional)
- ⏳ News filter (optional)

**Implementation**: `analysis/conservative_filters.py`

### 5. Enhanced Analytics
- ✅ EMA 50/100/200
- ✅ Supply/demand zones
- ✅ Candlestick patterns
- ✅ RSI/Stochastic (including divergences)
- ✅ Volume analysis
- ✅ Two-timeframe confirmation (higher-TF trend + lower-TF entry)

**Implementation**: `analysis/indicators.py`, `analysis/multi_timeframe.py`

### 6. Additional Ultra-Conservative Conditions
- ✅ Level quality check (min 2 touches)
- ✅ Distance to the nearest opposite level (min 1.5 ATR)
- ✅ ATR filter for Stop Loss size (max 2.5 ATR)
- ⏳ Time-of-day restrictions (optional)
- ✅ Cooldown for coins (4 hours)
- ✅ "And-And-And logic": if any key condition is not satisfied — signal rejected

**Implementation**: `analysis/conservative_filters.py`

### 7. Entry Conditions

**LONG**:
- **Uptrend**
  - Higher timeframe structure (H4/H1) must show HH/HL
  - EMA 50/100/200 must be positioned below price
- **Pullback to strong support**
  - On lower TF, pullback down to significant support zone
- **Bullish reversal candlestick pattern**
- **RSI exits oversold** (30 < RSI < 45)
- **Volume confirms**
- **RR ≥ 2:1**
- **Stop ≤ 2–2.5 ATR**

**SHORT**:
- **Downtrend**
  - Higher timeframe structure (H4/H1) must show LH/LL
  - EMA 50/100/200 above price
- **Pullback to strong resistance**
  - Retracement up to supply zone
- **Bearish reversal pattern** (engulfing, pin bar, etc.)
- **RSI exits overbought** (55 < RSI < 70)
- **Volume confirms seller dominance**
- **RR ≥ 2:1**
- **Stop ≤ 2–2.5 ATR**

**Implementation**: `analysis/signal_generator.py`, `analysis/multi_timeframe.py`

### 8. Take Profit (4 Levels)
- ✅ **TP1** – 25%, move SL to breakeven
- ✅ **TP2** – 25%
- ✅ **TP3** – 25%
- ✅ **TP4** – 25%
- ✅ Bot automatically tracks each target

**Implementation**: `main_monitoring.py` → `_check_position_levels()`

### 9. Stop Loss
- ✅ Stop Loss is mandatory
- ✅ Cannot be moved further away
- ✅ After TP1 — move to breakeven
- ✅ When hit → status `stopped_out` + report

**Implementation**: `main_monitoring.py` → `_close_on_stop()`

### 10. Signal Cancellation
Before entry, bot cancels signal if:
- ✅ Price moves away from entry zone (>1.5%)
- ✅ Market structure shifts
- ✅ Momentum moves against idea
- ✅ Entry time expires (24h)
- ⏳ News events disrupt setup (optional)

**Implementation**: `analysis/signal_cancellation.py`

### 11. Automatic Market Monitoring
Bot must:
- ✅ Check prices via API every 1–5 seconds
- ✅ Activate entries
- ✅ Track TP1–TP4
- ✅ Track Stop Loss
- ✅ Cancel signals
- ✅ Trigger early exits
- ✅ Send all notifications automatically

**Implementation**: `main.py` → `monitor_active_signals()`

### 12. Notification Formats
7 types of notifications:
- ✅ Initial signal
- ✅ Entry activated
- ✅ TP1–TP4 reached
- ✅ SL hit
- ✅ Cancellation
- ✅ Warning

**Implementation**: `telegram_bot/notifications.py`

### 13. Data Storage
Database stores:
- ✅ Signal ID
- ✅ Trading pair
- ✅ Direction
- ✅ Entry levels
- ✅ TP1–TP4
- ✅ SL (initial and current)
- ✅ Statuses: `WAITING`, `IN_POSITION`, `TP1_HIT`, `TP2_HIT`, `TP3_HIT`, `TP4_HIT`, `STOPPED_OUT`, `CANCELLED`, `CLOSED_FULL_TP`
- ✅ TP flags

**Implementation**: `database/models.py`

### 14. Restrictions
- ✅ Only TOP-100 coins
- ✅ Up to 20 signals per day
- ✅ Up to 1 signal per coin
- ✅ No averaging
- ✅ No signals during high market uncertainty

### 15. Final Philosophy
Bot works like an ideal conservative trader:
- ✅ Multiple confirmations
- ✅ Minimal risk
- ✅ Absolute discipline
- ✅ Transparent results
- ✅ Full automation

### 🌐 Multilingual Support
- ✅ English and Russian languages
- ✅ User can switch via `/language` command
- ✅ All messages in user's preferred language

---

## 🇷🇺 Русская Версия

### 0. Описание проекта
Бот автоматически анализирует рынок, выдаёт ультраконсервативные криптовалютные сигналы с риском не более 1% на сделку, использует 4 Take Profit, отслеживает рынок в реальном времени и автоматически сообщает о всех изменениях статуса сделки.

### 1. Основные принципы
- Главная цель – **безопасность капитала**.
- Риск ≤ **1% на сделку**.
- Суммарный риск всех активных сделок ≤ **20%**.
- Только сигналы с **множественными подтверждениями**.
- Никаких интуитивных входов.
- Бот работает строго по правилам.

### 2. Модули бота
- ✅ Анализ рынка
- ✅ Генерация сигналов
- ✅ Фильтрация сигналов
- ✅ Управление состояниями
- ✅ Мониторинг рынка
- ✅ Telegram-уведомления

### 3. Управление рисками
- ✅ Формула расчёта позиции основана на SL
- ✅ Max 1% риск на сделку
- ✅ Max **20% суммарный риск**
- ✅ Max 20 сигналов в сутки
- ✅ Max 1 сигнал на монету одновременно
- ✅ Никаких усреднений

**Реализация**: `database/risk_manager.py`

### 4. Фильтры перед генерацией сигнала
- ✅ Монеты только из ТОП-100
- ✅ Объём ≥ $5–10M в сутки
- ✅ Спред ≤ 0.1–0.3%
- ✅ Волатильность ограничена по ATR
- ✅ Мульти-таймфрейм тренд (H4/H1)
- ⏳ BTC/ETH фильтр корреляции (опционально)
- ⏳ Фильтр новостей (опционально)

**Реализация**: `analysis/conservative_filters.py`

### 5. Аналитика (усиленная)
- ✅ EMA 50/100/200
- ✅ Уровни спроса/предложения
- ✅ Свечные паттерны
- ✅ RSI/Stochastic (включая дивергенции)
- ✅ Объёмы
- ✅ Подтверждение на двух таймфреймах (старший тренд + младший вход)

**Реализация**: `analysis/indicators.py`, `analysis/multi_timeframe.py`

### 6. Дополнительные ультраконсервативные условия
- ✅ Проверка качества уровня (мин. 2 касания)
- ✅ Дистанция до ближайшего противонаправленного уровня (мин. 1.5 ATR)
- ✅ Фильтр ATR по величине Stop Loss (макс. 2.5 ATR)
- ⏳ Ограничение времён суток (опционально)
- ✅ Cooldown для монет (4 часа)
- ✅ Логика "и-и-и": если одно ключевое условие не выполнено — сигнал запрещён

**Реализация**: `analysis/conservative_filters.py`

### 7. Условия входа

**ЛОНГ**:
- **Тренд вверх**
  - Цена должна находиться в устойчивом восходящем тренде на старших таймфреймах (H4/H1), формируя HH/HL
  - EMA 50/100/200 должны быть расположены под ценой, подтверждая восходящее направление
- **Коррекция к сильной поддержке**
  - На младших ТФ должна быть коррекция вниз к значимой зоне поддержки
- **Свечной разворот**
  - Должна появиться разворотная бычья свечная модель
- **RSI выходит из перепроданности** (30 < RSI < 45)
- **Объём подтверждает**
- **RR ≥ 2:1**
- **Стоп ≤ 2–2.5 ATR**

**ШОРТ**:
- **Тренд вниз**
  - Цена должна быть в нисходящем тренде на старших ТФ (H4/H1), формируя LH/LL
  - EMA 50/100/200 должны быть выше цены
- **Коррекция к сильному сопротивлению**
  - Откат вверх к зоне предложения
- **Свечной медвежий разворот**
  - Медвежье поглощение, пин-бар и т.п.
- **RSI выходит из перекупленности** (55 < RSI < 70)
- **Объём подтверждает доминацию продавца**
- **RR ≥ 2:1**
- **Стоп ≤ 2–2.5 ATR**

**Реализация**: `analysis/signal_generator.py`, `analysis/multi_timeframe.py`

### 8. Take Profit (4 уровня)
- ✅ **TP1** – 25%, перенос SL в безубыток
- ✅ **TP2** – 25%
- ✅ **TP3** – 25%
- ✅ **TP4** – 25%
- ✅ Бот автоматически отслеживает каждую цель

**Реализация**: `main_monitoring.py` → `_check_position_levels()`

### 9. Stop Loss
- ✅ Стоп обязателен
- ✅ Не отодвигается
- ✅ После TP1 — безубыток
- ✅ Достижение → статус `stopped_out` + отчёт

**Реализация**: `main_monitoring.py` → `_close_on_stop()`

### 10. Отмена сигнала
До входа бот может отменить сигнал при:
- ✅ Уходе цены от зоны входа (>1.5%)
- ✅ Смене структуры
- ✅ Импульсе против идеи
- ✅ Истечении времени (24ч)
- ⏳ Новостях (опционально)

**Реализация**: `analysis/signal_cancellation.py`

### 11. Автоматический мониторинг рынка
Бот обязан:
- ✅ Отслеживать цены по API 1–5 сек
- ✅ Активировать вход
- ✅ Фиксировать TP1–TP4
- ✅ Фиксировать SL
- ✅ Отменять сигнал
- ✅ Инициировать досрочный выход
- ✅ Отправлять все уведомления автоматически

**Реализация**: `main.py` → `monitor_active_signals()`

### 12. Форматы сообщений
7 типов уведомлений:
- ✅ Сигнал
- ✅ Вход активирован
- ✅ TP1–TP4
- ✅ SL
- ✅ Отмена
- ✅ Предупреждение

**Реализация**: `telegram_bot/notifications.py`

### 13. Хранение данных
БД хранит:
- ✅ ID сигнала
- ✅ Пара
- ✅ Направление
- ✅ Уровни входа
- ✅ TP1–TP4
- ✅ SL (первичный и текущий)
- ✅ Статусы: `WAITING`, `IN_POSITION`, `TP1_HIT`, `TP2_HIT`, `TP3_HIT`, `TP4_HIT`, `STOPPED_OUT`, `CANCELLED`, `CLOSED_FULL_TP`
- ✅ Флаги TP

**Реализация**: `database/models.py`

### 14. Ограничения
- ✅ Монеты только из ТОП-100
- ✅ До 20 сигналов в сутки
- ✅ До 1 сигнала на монету
- ✅ Запрет усреднения
- ✅ Запрет сигналов при высокой неопределённости

### 15. Финальная философия
Бот работает как идеальный консервативный трейдер:
- ✅ Множество подтверждений
- ✅ Минимальный риск
- ✅ Абсолютная дисциплина
- ✅ Прозрачные результаты
- ✅ Полная автоматизация

### 🌐 Мультиязычность
- ✅ Английский и русский языки
- ✅ Пользователь может переключить через команду `/language`
- ✅ Все сообщения на выбранном языке

---

## ✅ Implementation Status: 15/15 COMPLETE

All requirements from the technical specification are fully implemented!

