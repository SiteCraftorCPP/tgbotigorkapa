# 🛡️ Ultra-Conservative Crypto Signal Bot / Ультраконсервативный Крипто-Сигнальный Бот

🇬🇧 **English** | 🇷🇺 **Русский**

**Telegram bot for maximum-safe cryptocurrency futures trading on XT.com**

**Telegram-бот для максимально безопасной торговли криптовалютными фьючерсами на XT.com**

---

## 🌐 Multi-Language Support / Мультиязычность

The bot supports **English** and **Russian**. Users can switch language with `/language` command.

Бот поддерживает **английский** и **русский** языки. Пользователи могут переключить язык командой `/language`.

---

## 🎯 Philosophy / Философия

**EN**: Bot works like an ideal conservative trader:
- ✅ Multiple confirmations before entry
- ✅ Minimal risk (**≤1% per trade**)
- ✅ Absolute discipline
- ✅ Full automation 24/7
- ✅ Transparent results

**RU**: Бот работает как идеальный консервативный трейдер:
- ✅ Множество подтверждений перед входом
- ✅ Минимальный риск (**≤1% на сделку**)
- ✅ Абсолютная дисциплина
- ✅ Полная автоматизация 24/7
- ✅ Прозрачные результаты

---

## 🔐 Risk Management / Управление Рисками

| Parameter / Параметр | Value / Значение |
|----------|----------|
| Risk per trade / Риск на сделку | **≤ 1%** |
| Total risk / Суммарный риск | **≤ 20%** ⚡ *UPDATED* |
| Max signals/day / Макс. сигналов/день | **20** |
| Max signals per coin / Макс. на монету | **1** |
| Cooldown / Кулдаун | **4 hours / часа** |

---

## 🎯 Trading Logic / Торговая Логика

### 4 Take Profit Levels / 4 Уровня Take Profit

After **TP1** → Stop moves to **breakeven** / После **TP1** → стоп в **безубыток**!

- **TP1** (25%) - RR 1.5:1 → Breakeven / Безубыток
- **TP2** (25%) - RR 2.5:1
- **TP3** (25%) - RR 3.5:1  
- **TP4** (25%) - RR 5:1

### Multi-Timeframe Analysis / Мультитаймфреймный Анализ

**EN**:
- **Higher TF** - trend determination (H4/H1)
- **Lower TF** - entry point (pullback)
- Entry only when directions match

**RU**:
- **Старший ТФ** - определение тренда (H4/H1)
- **Младший ТФ** - точка входа (pullback)
- Вход только при совпадении направления

---

## 🔍 Ultra-Conservative Filters / Ультраконсервативные Фильтры

### Before signal generation / До генерации сигнала:

1. ✅ **TOP-100 coins only** / **Только монеты из ТОП-100**
2. ✅ **Volume ≥ $5M / 24h** / **Объём ≥ $5M / 24ч**
3. ✅ **Spread ≤ 0.3%** / **Спред ≤ 0.3%**
4. ✅ **Stop ≤ 2-2.5 ATR** / **Стоп ≤ 2-2.5 ATR**
5. ✅ **Level quality check** (min 2 touches) / **Проверка качества уровня** (мин. 2 касания)
6. ✅ **Distance to opposite level** (min 1.5 ATR) / **Дистанция до противоуровня** (мин. 1.5 ATR)
7. ✅ **Trend on 2 timeframes** / **Тренд на 2 таймфреймах**
8. ✅ **Pullback present** / **Наличие pullback**
9. ✅ **BTC/ETH correlation filter** ⚡ *NEW* / **Фильтр корреляции с BTC/ETH** ⚡ *НОВОЕ*
10. ✅ **Time of day restrictions** (no trading 0-5 UTC) ⚡ *NEW* / **Ограничение времён суток** (не торгуем 0-5 UTC) ⚡ *НОВОЕ*

---

## 📊 Technical Analysis / Технический Анализ

**EN**:
- **Trend**: EMA 50/100/200, VWAP
- **Momentum**: RSI, Stochastic (+ divergences)
- **Volume**: Volume MA, historical comparison
- **Volatility**: ATR
- **Candlestick patterns**: reversal formations

**RU**:
- **Тренд**: EMA 50/100/200, VWAP
- **Моментум**: RSI, Stochastic (+ дивергенции)
- **Объёмы**: Volume MA, сравнение с историей
- **Волатильность**: ATR
- **Свечные паттерны**: разворотные формации

---

## ⚡ Automatic Monitoring / Автоматический Мониторинг

**EN**: Bot tracks **every 5 seconds** (market analysis every 5 minutes):
- ✅ Entry activation
- ✅ TP1/TP2/TP3/TP4 reached
- ✅ SL triggered
- ✅ Breakeven move
- ✅ Cancellation conditions

**RU**: Бот отслеживает **каждые 5 секунд** (анализ рынка каждые 5 минут):
- ✅ Активация входа
- ✅ Достижение TP1/TP2/TP3/TP4
- ✅ Срабатывание SL
- ✅ Перенос в безубыток
- ✅ Условия отмены

---

## 🚫 Signal Cancellation / Отмена Сигнала

**EN**: Bot cancels signal if:
- ⏱ 24h waiting time expired
- 📉 Price moved away from entry zone (>1.5%)
- 🔄 Market structure changed
- 💥 Strong impulse against idea
- 🛑 Stop hit before entry

**RU**: Бот отменяет сигнал если:
- ⏱ Истекло 24ч ожидания
- 📉 Цена ушла от зоны входа (>1.5%)
- 🔄 Изменилась структура рынка
- 💥 Сильный импульс против идеи
- 🛑 Цена пробила стоп до входа

---

## 📱 Telegram Commands / Telegram Команды

### For all users / Для всех:

```
/start          - Bot info / Информация о боте
/stats          - Overall stats / Общая статистика
/today          - Today's stats / За сегодня
/week           - Weekly stats / За неделю
/language       - Change language / Сменить язык 🌐
/help           - Help / Помощь
```

### For admins / Для админов:

**Management / Управление:**
```
/enable         - Enable bot / Включить бота
/disable        - Disable bot / Выключить бота
/config         - Current settings / Текущие настройки
```

**Configuration / Настройка:**
```
/set_pairs BTC/USDT ETH/USDT
/set_timeframes 15m 1h 4h
/set_ai_score 75
/set_risk 1.0
/set_leverage 10
```

**Admin management / Управление админами:**
```
/add_admin USER_ID
/remove_admin USER_ID
/list_admins
```

---

## 📈 Signal Example / Пример Сигнала

```
🟢 ULTRA-CONSERVATIVE SIGNAL

📊 BTCUSDT | LONG
🕐 1h → 4h

💰 Entry: 62350
🛑 Stop: 60850 (-2.40%)

🎯 Take Profit (4 levels):
├ TP1: 63625 (+2.04%) [25%]
├ TP2: 65225 (+4.61%) [25%]
├ TP3: 66825 (+7.18%) [25%]
└ TP4: 69500 (+11.45%) [25%]

📈 Parameters:
• Risk: 1% (max 1%)
• Leverage: x10
• RR: 1.7:1
• AI Score: 85/100

📊 Filters:
• Volume 24h: $8.5M
• Spread: 0.12%
• ATR: 750.00

⚠️ After TP1 - move SL to breakeven!

🆔 a3f2e4b1
```

---

## 🛠 Installation / Установка

**EN**: See `SETUP.md` for detailed instructions.

**RU**: См. `SETUP.md` для подробных инструкций.

### Quick Start / Быстрый старт:

1. **Clone / Клонирование**
```bash
cd tgbotigorkapa
```

2. **Virtual environment / Виртуальное окружение**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

3. **PostgreSQL**
```sql
CREATE DATABASE crypto_signals;
```

4. **.env file / .env файл**
```env
XT_API_KEY=4e74f8bf-7424-4521-ba71-ded15621319a
XT_API_SECRET=a0d77d78d99e2b7cec4a941277fccef00877660c

TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHANNEL_ID=@your_channel
TELEGRAM_ADMIN_CHANNEL_ID=@admin_channel

DB_PASSWORD=your_password
```

5. **Add admins / Добавить админов**
```sql
INSERT INTO admins (telegram_id, username, first_name) 
VALUES ('your_telegram_id', 'username', 'Name');
```

6. **Run / Запуск**
```bash
python main.py
```

---

## 📁 Project Structure / Структура Проекта

```
├── analysis/
│   ├── indicators.py              # Technical indicators / Индикаторы
│   ├── signal_generator.py        # Signal generation / Генерация сигналов
│   ├── multi_timeframe.py         # Multi-TF analysis / Мультитаймфрейм
│   ├── conservative_filters.py    # Ultra-conservative filters / Фильтры
│   └── signal_cancellation.py     # Cancellation logic / Логика отмены
├── database/
│   ├── models.py                  # SQLAlchemy models / Модели
│   ├── config_manager.py          # Settings from DB / Настройки из БД
│   ├── admin_manager.py           # Admin management / Управление админами
│   ├── risk_manager.py            # Risk management / Риск-менеджмент
│   └── user_preferences.py        # User language / Язык пользователя 🌐
├── exchange/
│   └── xt_client.py               # XT.com client / Клиент XT.com
├── telegram_bot/
│   ├── bot.py                     # Main bot / Основной бот
│   ├── notifications.py           # All notification types / Уведомления
│   └── languages.py               # Translations EN/RU / Переводы 🌐
├── utils/
│   └── logger.py                  # Logging / Логирование
└── main.py                        # Entry point / Точка входа
```

---

## ⚠️ Important / Важно

**EN**:
1. **Add admins to DB** - commands won't work otherwise
2. **XT.com API keys** - both already in `.env`
3. **Telegram channels** - bot must be admin
4. **PostgreSQL** - must be running
5. **Language** - use `/language` to switch

**RU**:
1. **Добавьте админов в БД** - иначе команды не работают
2. **API ключи XT.com** - оба уже в `.env`
3. **Telegram каналы** - бот должен быть админом
4. **PostgreSQL** - должен быть запущен
5. **Язык** - используйте `/language` для смены

---

## 📊 Statistics / Статистика

**EN**: Bot stores in DB:
- All signals with full data
- Status of each TP (1-4)
- Cancellation reasons
- Winrate, PnL, Risk/Reward
- History by coins

**RU**: Бот хранит в БД:
- Все сигналы с полными данными
- Статус каждого TP (1-4)
- Причины отмен
- Winrate, PnL, Risk/Reward
- История по монетам

---

## 🎓 Documentation / Документация

- `README.md` - This file / Этот файл
- `SPECIFICATION.md` - Full TZ (EN + RU) / Полное ТЗ
- `SETUP.md` - Detailed installation / Подробная установка
- `ADMIN_SETUP.md` - Admin setup / Настройка админов
- `main_monitoring.py` - Monitoring methods / Методы мониторинга

---

## 🚀 Ready! / Готово!

**EN**: Bot fully complies with ultra-conservative strategy specification.

**Key differences from regular bots:**
- 🛡️ **4 Take Profit** instead of 2
- 🛡️ **Breakeven after TP1**
- 🛡️ **Multi-timeframe analysis**
- 🛡️ **6+ filters** before each signal
- 🛡️ **Auto-cancellation** of outdated signals
- 🛡️ **Risk management** at DB level
- 🌐 **Multi-language** support (EN/RU)

**RU**: Бот полностью соответствует спецификации ультраконсервативной стратегии.

**Главные отличия от обычных ботов:**
- 🛡️ **4 Take Profit** вместо 2
- 🛡️ **Безубыток после TP1**
- 🛡️ **Мультитаймфреймный анализ**
- 🛡️ **6+ фильтров** перед каждым сигналом
- 🛡️ **Автоотмена** неактуальных сигналов
- 🛡️ **Риск-менеджмент** на уровне БД
- 🌐 **Мультиязычность** (EN/RU)

---

**Disclaimer / Дисклеймер**: Bot does not guarantee profit. Trading involves risks. Use at your own risk. / Бот не гарантирует прибыль. Торговля сопряжена с рисками. Используйте на свой риск.

---

**License / Лицензия**: MIT
