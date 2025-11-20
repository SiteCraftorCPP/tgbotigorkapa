from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode
import config
from database.models import Signal, BotStats, get_db
from database.config_manager import ConfigManager
from database.admin_manager import AdminManager
from sqlalchemy import func
from datetime import datetime, timedelta
from functools import wraps

def admin_only(func):
    """Декоратор для проверки прав админа"""
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        
        if not AdminManager.is_admin(user_id):
            await update.message.reply_text(
                "❌ У вас нет прав для выполнения этой команды.\n"
                "Только администраторы могут использовать эту команду."
            )
            return
        
        return await func(self, update, context)
    return wrapper


class TelegramBot:
    """Telegram бот для публикации сигналов и управления"""
    
    def __init__(self):
        self.bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
        self.app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Настройка обработчиков команд"""
        # Публичные команды
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("stats", self.cmd_stats))
        self.app.add_handler(CommandHandler("today", self.cmd_today))
        self.app.add_handler(CommandHandler("week", self.cmd_week))
        
        # Админ команды - управление ботом
        self.app.add_handler(CommandHandler("enable", self.cmd_enable))
        self.app.add_handler(CommandHandler("disable", self.cmd_disable))
        self.app.add_handler(CommandHandler("config", self.cmd_config))
        
        # Админ команды - настройка параметров
        self.app.add_handler(CommandHandler("set_pairs", self.cmd_set_pairs))
        self.app.add_handler(CommandHandler("set_timeframes", self.cmd_set_timeframes))
        self.app.add_handler(CommandHandler("set_ai_score", self.cmd_set_ai_score))
        self.app.add_handler(CommandHandler("set_risk", self.cmd_set_risk))
        self.app.add_handler(CommandHandler("set_leverage", self.cmd_set_leverage))
        
        # Админ команды - управление админами
        self.app.add_handler(CommandHandler("add_admin", self.cmd_add_admin))
        self.app.add_handler(CommandHandler("remove_admin", self.cmd_remove_admin))
        self.app.add_handler(CommandHandler("list_admins", self.cmd_list_admins))
        
        # Команда помощи
        self.app.add_handler(CommandHandler("help", self.cmd_help))
    
    async def send_signal(self, signal: dict) -> bool:
        """Отправка сигнала в канал"""
        try:
            message = self._format_signal_message(signal)
            
            await self.bot.send_message(
                chat_id=config.TELEGRAM_CHANNEL_ID,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
            
            return True
        except Exception as e:
            await self.send_admin_message(f"❌ Ошибка отправки сигнала: {e}")
            return False
    
    async def send_admin_message(self, message: str):
        """Отправка сообщения в админ-канал"""
        try:
            await self.bot.send_message(
                chat_id=config.TELEGRAM_ADMIN_CHANNEL_ID,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            print(f"❌ Ошибка отправки в админ-канал: {e}")
    
    def _format_signal_message(self, signal: dict) -> str:
        """Форматирование ультраконсервативного сигнала"""
        
        emoji = "🟢" if signal['direction'] == 'LONG' else "🔴"
        
        # Расчёт потенциальной прибыли для всех 4 TP
        entry = signal['entry_price']
        tp1 = signal['take_profit_1']
        tp2 = signal['take_profit_2']
        tp3 = signal['take_profit_3']
        tp4 = signal['take_profit_4']
        stop = signal['stop_loss']
        
        if signal['direction'] == 'LONG':
            profit_tp1 = ((tp1 - entry) / entry) * 100
            profit_tp2 = ((tp2 - entry) / entry) * 100
            profit_tp3 = ((tp3 - entry) / entry) * 100
            profit_tp4 = ((tp4 - entry) / entry) * 100
            risk_percent = ((entry - stop) / entry) * 100
        else:
            profit_tp1 = ((entry - tp1) / entry) * 100
            profit_tp2 = ((entry - tp2) / entry) * 100
            profit_tp3 = ((entry - tp3) / entry) * 100
            profit_tp4 = ((entry - tp4) / entry) * 100
            risk_percent = ((stop - entry) / entry) * 100
        
        # Risk/Reward ratio
        rr = profit_tp1 / risk_percent if risk_percent > 0 else 0
        
        message = f"""
{emoji} *УЛЬТРАКОНСЕРВАТИВНЫЙ СИГНАЛ*

📊 *{signal['ticker']}* | {signal['direction']}
🕐 {signal['timeframe']} → {signal.get('timeframe_higher', 'H4')}

💰 *Вход:* `{entry}`
🛑 *Стоп:* `{stop}` (-{risk_percent:.2f}%)

🎯 *Take Profit (4 уровня):*
├ TP1: `{tp1}` (+{profit_tp1:.1f}%) [25%]
├ TP2: `{tp2}` (+{profit_tp2:.1f}%) [25%]
├ TP3: `{tp3}` (+{profit_tp3:.1f}%) [25%]
└ TP4: `{tp4}` (+{profit_tp4:.1f}%) [25%]

📈 *Параметры:*
• Риск: *{signal['risk_percent']}%* (макс 1%)
• Плечо: *x{signal['leverage']}*
• RR: *{rr:.1f}:1*
• AI Score: *{signal['ai_score']}/100*

📊 *Фильтры:*
• Объём 24ч: ${signal.get('volume_24h', 0)/1_000_000:.1f}M
• Спред: {signal.get('spread_percent', 0):.2f}%
• ATR: {signal.get('atr_value', 0):.2f}

⚠️ *После TP1 - перенос SL в безубыток!*

🆔 `{signal['signal_id']}`
"""
        return message.strip()
    
    async def update_signal_result(self, signal_id: str, result: str, pnl_percent: float):
        """Обновление результата сигнала в канале"""
        try:
            emoji = "✅" if result == "WIN" else "❌"
            pnl_emoji = "+" if pnl_percent > 0 else ""
            
            message = f"""
{emoji} *Сигнал закрыт*

🆔 ID: `{signal_id}`
📊 Результат: *{result}*
💵 PnL: *{pnl_emoji}{pnl_percent:.2f}%*
"""
            
            await self.bot.send_message(
                chat_id=config.TELEGRAM_CHANNEL_ID,
                text=message.strip(),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            print(f"❌ Ошибка обновления результата: {e}")
    
    # Команды бота
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        user_id = str(update.effective_user.id)
        is_admin = AdminManager.is_admin(user_id)
        
        message = """
🤖 *Крипто-сигнальный бот*

📊 Публичные команды:
/stats - Общая статистика
/today - Статистика за сегодня
/week - Статистика за неделю
/help - Помощь
"""
        
        if is_admin:
            message += """
⚙️ Админ-команды:
/config - Текущие настройки
/enable - Включить бота
/disable - Выключить бота

🔧 Настройка параметров:
/set_pairs - Изменить торгуемые пары
/set_timeframes - Изменить таймфреймы
/set_ai_score - Минимальный AI Score
/set_risk - Процент риска
/set_leverage - Плечо

👥 Управление админами:
/add_admin - Добавить админа
/remove_admin - Удалить админа
/list_admins - Список админов
"""
        
        await update.message.reply_text(message.strip(), parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        await self.cmd_start(update, context)
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats - общая статистика"""
        db = get_db()
        
        try:
            # Все сигналы
            total_signals = db.query(Signal).count()
            
            # Закрытые сигналы
            closed = db.query(Signal).filter(Signal.status.in_(['TP1', 'TP2', 'SL'])).all()
            
            if not closed:
                await update.message.reply_text("📊 Пока нет закрытых сигналов")
                return
            
            wins = len([s for s in closed if s.result == 'WIN'])
            losses = len([s for s in closed if s.result == 'LOSS'])
            
            winrate = (wins / len(closed)) * 100 if closed else 0
            total_pnl = sum([s.pnl_percent for s in closed if s.pnl_percent])
            avg_rr = sum([s.risk_reward for s in closed if s.risk_reward]) / len(closed) if closed else 0
            
            message = f"""
📊 *Общая статистика*

📈 Всего сигналов: {total_signals}
✅ Прибыльных: {wins}
❌ Убыточных: {losses}

💹 Winrate: *{winrate:.1f}%*
💰 Общий PnL: *{total_pnl:+.2f}%*
📊 Средний RR: *{avg_rr:.2f}*
"""
            await update.message.reply_text(message.strip(), parse_mode=ParseMode.MARKDOWN)
            
        finally:
            db.close()
    
    async def cmd_today(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статистика за сегодня"""
        db = get_db()
        
        try:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0)
            
            signals = db.query(Signal).filter(
                Signal.created_at >= today_start
            ).all()
            
            if not signals:
                await update.message.reply_text("📊 Сегодня сигналов пока нет")
                return
            
            closed = [s for s in signals if s.status in ['TP1', 'TP2', 'SL']]
            active = [s for s in signals if s.status == 'ACTIVE']
            
            wins = len([s for s in closed if s.result == 'WIN'])
            losses = len([s for s in closed if s.result == 'LOSS'])
            
            message = f"""
📊 *Статистика за сегодня*

📈 Всего сигналов: {len(signals)}
🟢 Активных: {len(active)}
✅ Прибыльных: {wins}
❌ Убыточных: {losses}
"""
            await update.message.reply_text(message.strip(), parse_mode=ParseMode.MARKDOWN)
            
        finally:
            db.close()
    
    async def cmd_week(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статистика за неделю"""
        db = get_db()
        
        try:
            week_start = datetime.utcnow() - timedelta(days=7)
            
            signals = db.query(Signal).filter(
                Signal.created_at >= week_start
            ).all()
            
            if not signals:
                await update.message.reply_text("📊 За неделю сигналов нет")
                return
            
            closed = [s for s in signals if s.status in ['TP1', 'TP2', 'SL']]
            
            wins = len([s for s in closed if s.result == 'WIN'])
            losses = len([s for s in closed if s.result == 'LOSS'])
            
            winrate = (wins / len(closed)) * 100 if closed else 0
            total_pnl = sum([s.pnl_percent for s in closed if s.pnl_percent])
            
            message = f"""
📊 *Статистика за неделю*

📈 Всего сигналов: {len(signals)}
✅ Прибыльных: {wins}
❌ Убыточных: {losses}
💹 Winrate: *{winrate:.1f}%*
💰 PnL: *{total_pnl:+.2f}%*
"""
            await update.message.reply_text(message.strip(), parse_mode=ParseMode.MARKDOWN)
            
        finally:
            db.close()
    
    @admin_only
    async def cmd_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Текущая конфигурация"""
        pairs = ConfigManager.get_trading_pairs()
        timeframes = ConfigManager.get_timeframes()
        enabled = ConfigManager.is_bot_enabled()
        ai_score = ConfigManager.get_min_ai_score()
        risk = ConfigManager.get_risk_percent()
        leverage = ConfigManager.get_leverage()
        
        status = "✅ Включен" if enabled else "⏸ Выключен"
        
        message = f"""
⚙️ *Текущие настройки бота*

🤖 Статус: {status}

📊 *Торговля:*
• Пары: {', '.join(pairs)}
• Таймфреймы: {', '.join(timeframes)}

🎯 *Параметры:*
• Мин. AI Score: {ai_score}/100
• Риск: {risk}%
• Плечо: x{leverage}

Для изменения используйте команды /set_*
"""
        await update.message.reply_text(message.strip(), parse_mode=ParseMode.MARKDOWN)
    
    @admin_only
    async def cmd_enable(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Включение бота"""
        ConfigManager.enable_bot()
        await update.message.reply_text("✅ Бот включен")
        await self.send_admin_message("✅ Бот включен")
    
    @admin_only
    async def cmd_disable(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выключение бота"""
        ConfigManager.disable_bot()
        await update.message.reply_text("⏸ Бот выключен")
        await self.send_admin_message("⏸ Бот выключен")
    
    @admin_only
    async def cmd_set_pairs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка торгуемых пар"""
        if not context.args:
            current = ConfigManager.get_trading_pairs()
            await update.message.reply_text(
                f"📊 Текущие пары: {', '.join(current)}\n\n"
                f"Использование:\n"
                f"`/set_pairs BTC/USDT ETH/USDT SOL/USDT`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        pairs = [p.strip() for p in context.args]
        ConfigManager.set_trading_pairs(pairs)
        
        await update.message.reply_text(
            f"✅ Торгуемые пары обновлены:\n{', '.join(pairs)}"
        )
        await self.send_admin_message(
            f"⚙️ Пары изменены: {', '.join(pairs)}"
        )
    
    @admin_only
    async def cmd_set_timeframes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка таймфреймов"""
        if not context.args:
            current = ConfigManager.get_timeframes()
            await update.message.reply_text(
                f"⏰ Текущие таймфреймы: {', '.join(current)}\n\n"
                f"Использование:\n"
                f"`/set_timeframes 5m 15m 1h 4h`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        timeframes = [t.strip() for t in context.args]
        ConfigManager.set_timeframes(timeframes)
        
        await update.message.reply_text(
            f"✅ Таймфреймы обновлены:\n{', '.join(timeframes)}"
        )
        await self.send_admin_message(
            f"⚙️ Таймфреймы изменены: {', '.join(timeframes)}"
        )
    
    @admin_only
    async def cmd_set_ai_score(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка минимального AI Score"""
        if not context.args:
            current = ConfigManager.get_min_ai_score()
            await update.message.reply_text(
                f"🎯 Текущий мин. AI Score: {current}/100\n\n"
                f"Использование:\n"
                f"`/set_ai_score 75`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        try:
            score = int(context.args[0])
            if not 0 <= score <= 100:
                raise ValueError
            
            ConfigManager.set('min_ai_score', str(score))
            await update.message.reply_text(f"✅ Мин. AI Score установлен: {score}/100")
            await self.send_admin_message(f"⚙️ Мин. AI Score изменён: {score}/100")
        except:
            await update.message.reply_text("❌ Ошибка: укажите число от 0 до 100")
    
    @admin_only
    async def cmd_set_risk(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка процента риска"""
        if not context.args:
            current = ConfigManager.get_risk_percent()
            await update.message.reply_text(
                f"⚠️ Текущий риск: {current}%\n\n"
                f"Использование:\n"
                f"`/set_risk 1.5`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        try:
            risk = float(context.args[0])
            if not 0 < risk <= 10:
                raise ValueError
            
            ConfigManager.set('risk_percent', str(risk))
            await update.message.reply_text(f"✅ Риск установлен: {risk}%")
            await self.send_admin_message(f"⚙️ Риск изменён: {risk}%")
        except:
            await update.message.reply_text("❌ Ошибка: укажите число от 0 до 10")
    
    @admin_only
    async def cmd_set_leverage(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка плеча"""
        if not context.args:
            current = ConfigManager.get_leverage()
            await update.message.reply_text(
                f"📈 Текущее плечо: x{current}\n\n"
                f"Использование:\n"
                f"`/set_leverage 20`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        try:
            leverage = int(context.args[0])
            if not 1 <= leverage <= 125:
                raise ValueError
            
            ConfigManager.set('default_leverage', str(leverage))
            await update.message.reply_text(f"✅ Плечо установлено: x{leverage}")
            await self.send_admin_message(f"⚙️ Плечо изменено: x{leverage}")
        except:
            await update.message.reply_text("❌ Ошибка: укажите число от 1 до 125")
    
    @admin_only
    async def cmd_add_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавление админа"""
        if not context.args:
            await update.message.reply_text(
                "Использование:\n"
                "`/add_admin USER_ID`\n\n"
                "Чтобы узнать ID, попросите пользователя написать @userinfobot",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        telegram_id = context.args[0]
        AdminManager.add_admin(telegram_id)
        
        await update.message.reply_text(f"✅ Админ {telegram_id} добавлен")
        await self.send_admin_message(f"👥 Новый админ добавлен: {telegram_id}")
    
    @admin_only
    async def cmd_remove_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Удаление админа"""
        if not context.args:
            await update.message.reply_text(
                "Использование:\n"
                "`/remove_admin USER_ID`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        telegram_id = context.args[0]
        
        # Проверка, что не удаляем последнего админа
        if AdminManager.count_admins() <= 1:
            await update.message.reply_text("❌ Нельзя удалить последнего админа!")
            return
        
        AdminManager.remove_admin(telegram_id)
        await update.message.reply_text(f"✅ Админ {telegram_id} удалён")
        await self.send_admin_message(f"👥 Админ удалён: {telegram_id}")
    
    @admin_only
    async def cmd_list_admins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список админов"""
        admins = AdminManager.get_all_admins()
        
        if not admins:
            await update.message.reply_text("📝 Нет активных админов")
            return
        
        message = "👥 *Список администраторов:*\n\n"
        for admin in admins:
            username = f"@{admin.username}" if admin.username else "нет username"
            name = admin.first_name or "нет имени"
            message += f"• {name} ({username})\n  ID: `{admin.telegram_id}`\n\n"
        
        await update.message.reply_text(message.strip(), parse_mode=ParseMode.MARKDOWN)
    
    def run(self):
        """Запуск бота"""
        self.app.run_polling()

