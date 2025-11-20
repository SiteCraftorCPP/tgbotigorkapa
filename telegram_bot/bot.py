from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode
import config
from database.models import Signal, BotStats, get_db
from sqlalchemy import func
from datetime import datetime, timedelta

class TelegramBot:
    """Telegram бот для публикации сигналов и управления"""
    
    def __init__(self):
        self.bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
        self.app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Настройка обработчиков команд"""
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("stats", self.cmd_stats))
        self.app.add_handler(CommandHandler("today", self.cmd_today))
        self.app.add_handler(CommandHandler("week", self.cmd_week))
        self.app.add_handler(CommandHandler("enable", self.cmd_enable))
        self.app.add_handler(CommandHandler("disable", self.cmd_disable))
        self.app.add_handler(CommandHandler("pairs", self.cmd_pairs))
    
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
        """Форматирование сигнала для Telegram"""
        
        emoji = "🟢" if signal['direction'] == 'LONG' else "🔴"
        
        # Расчёт потенциальной прибыли
        entry = signal['entry_price']
        tp1 = signal['take_profit_1']
        tp2 = signal['take_profit_2']
        
        if signal['direction'] == 'LONG':
            profit_tp1 = ((tp1 - entry) / entry) * 100
            profit_tp2 = ((tp2 - entry) / entry) * 100
        else:
            profit_tp1 = ((entry - tp1) / entry) * 100
            profit_tp2 = ((entry - tp2) / entry) * 100
        
        message = f"""
{emoji} *Futures сигнал*

📊 Монета: *{signal['ticker']}*
📍 Направление: *{signal['direction']}*

💰 Вход: *{signal['entry_price']}*
🛑 Стоп: *{signal['stop_loss']}*
🎯 TP1: *{signal['take_profit_1']}* (+{profit_tp1:.2f}%)
🎯 TP2: *{signal['take_profit_2']}* (+{profit_tp2:.2f}%)

⚠️ Риск: *{signal['risk_percent']}%*
📈 Плечо: *х{signal['leverage']}*
🤖 AI Score: *{signal['ai_score']}/100*

🕐 Таймфрейм: {signal['timeframe']}
🆔 ID: `{signal['signal_id']}`
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
        message = """
🤖 *Крипто-сигнальный бот*

Доступные команды:
/stats - Общая статистика
/today - Статистика за сегодня
/week - Статистика за неделю
/pairs - Торгуемые пары
/enable - Включить бота (админ)
/disable - Выключить бота (админ)
"""
        await update.message.reply_text(message.strip(), parse_mode=ParseMode.MARKDOWN)
    
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
    
    async def cmd_pairs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список торгуемых пар"""
        pairs = "\n".join([f"• {pair}" for pair in config.TRADING_PAIRS])
        
        message = f"""
📊 *Торгуемые пары*

{pairs}

⏰ Таймфреймы: {", ".join(config.TIMEFRAMES)}
"""
        await update.message.reply_text(message.strip(), parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_enable(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Включение бота (только для админов)"""
        config.BOT_ENABLED = True
        await update.message.reply_text("✅ Бот включен")
        await self.send_admin_message("✅ Бот включен")
    
    async def cmd_disable(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выключение бота (только для админов)"""
        config.BOT_ENABLED = False
        await update.message.reply_text("⏸ Бот выключен")
        await self.send_admin_message("⏸ Бот выключен")
    
    def run(self):
        """Запуск бота"""
        self.app.run_polling()

