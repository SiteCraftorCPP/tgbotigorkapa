from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from telegram.constants import ParseMode
import config
from database.models import Signal, BotStats, get_db
from database.config_manager import ConfigManager
from database.admin_manager import AdminManager
from database.user_preferences import UserPreferenceManager
from .languages import t, get_user_lang
from sqlalchemy import func
from datetime import datetime, timedelta
from functools import wraps

def admin_only(func):
    """Декоратор для проверки прав админа"""
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_id = str(update.effective_user.id)
            lang = get_user_lang(user_id)
            
            is_admin = AdminManager.is_admin(user_id)
            print(f"[DEBUG] Command {func.__name__} called by user {user_id}, is_admin: {is_admin}")
            
            if not is_admin:
                await update.message.reply_text(t('no_permission', lang))
                return
            
            return await func(self, update, context)
        except Exception as e:
            print(f"[ERROR] Error in admin_only decorator: {e}")
            import traceback
            traceback.print_exc()
            try:
                await update.message.reply_text(f"Error: {str(e)}")
            except:
                pass
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
        self.app.add_handler(CommandHandler("language", self.cmd_language))
        
        # Админ команды - управление ботом
        self.app.add_handler(CommandHandler("enable", self.cmd_enable))
        self.app.add_handler(CommandHandler("disable", self.cmd_disable))
        self.app.add_handler(CommandHandler("config", self.cmd_config))
        
        # Админ команды - настройка параметров
        # ВАЖНО: Telegram не поддерживает подчеркивания в командах, используем дефисы
        self.app.add_handler(CommandHandler("setpairs", self.cmd_set_pairs))
        self.app.add_handler(CommandHandler("setp", self.cmd_set_pairs))  # Короткий вариант
        self.app.add_handler(CommandHandler("settimeframes", self.cmd_set_timeframes))
        self.app.add_handler(CommandHandler("settf", self.cmd_set_timeframes))  # Короткий вариант
        
        # Команда помощи
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        
        # Callback handlers для кнопок
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Обработчик всех неизвестных команд для отладки
        async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            command = update.message.text.split()[0] if update.message.text else "unknown"
            print(f"[DEBUG] Unknown command received: {command}")
            await update.message.reply_text(f"Unknown command: {command}")
        
        self.app.add_handler(MessageHandler(filters.COMMAND & ~filters.Regex("^(start|stats|today|week|language|enable|disable|config|setpairs|setp|settimeframes|settf|help)"), unknown_command))
    
    async def send_signal(self, signal: dict) -> bool:
        """Отправка сигнала в канал (всегда на английском)"""
        try:
            message = self._format_signal_message(signal, lang='en')
            
            # Кнопка с реферальной ссылкой XT.com
            keyboard = [
                [InlineKeyboardButton(
                    "💸 Official Partner XT CASHBACK 40%",
                    url="https://www.xt.com/en/accounts/register?ref=KINGELONMARS"
                )]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.bot.send_message(
                chat_id=config.TELEGRAM_CHANNEL_ID,
                text=message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
            return True
        except Exception as e:
            error_msg = f"Error sending signal: {e}"
            try:
                await self.send_admin_message(error_msg)
            except:
                print(f"[ERROR] {error_msg}")
            return False
    
    async def send_admin_message(self, message: str):
        """Отправка сообщения в админ-канал (или в основной, если админ-канал не указан)"""
        try:
            chat_id = config.TELEGRAM_ADMIN_CHANNEL_ID or config.TELEGRAM_CHANNEL_ID
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            print(f"[ERROR] Failed to send admin message: {e}")
    
    def _format_price(self, price: float) -> str:
        """Умное форматирование цены в зависимости от её величины"""
        if price >= 1000:
            # Большие цены (BTC, ETH и т.д.) - 2 знака после запятой
            return f"{price:.2f}"
        elif price >= 1:
            # Средние цены (1-1000) - 4 знака после запятой
            return f"{price:.4f}"
        elif price >= 0.01:
            # Малые цены (0.01-1) - 6 знаков после запятой
            return f"{price:.6f}"
        else:
            # Очень малые цены (<0.01) - 8 знаков после запятой
            return f"{price:.8f}".rstrip('0').rstrip('.')
    
    def _format_signal_message(self, signal: dict, lang: str = 'en') -> str:
        """Форматирование упрощенного сигнала"""
        
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
        
        # Форматирование цен с учётом их величины
        entry_str = self._format_price(entry)
        stop_str = self._format_price(stop)
        tp1_str = self._format_price(tp1)
        tp2_str = self._format_price(tp2)
        tp3_str = self._format_price(tp3)
        tp4_str = self._format_price(tp4)
        
        # Сигналы всегда на английском для канала
        message = f"""
📊 *{signal['ticker']}* | {signal['direction']}

💰 Entry: {entry_str}
🛑 Stop: {stop_str} (-{risk_percent:.2f}%)

🎯 Take Profit
├ TP1: {tp1_str} (+{profit_tp1:.1f}%)
├ TP2: {tp2_str} (+{profit_tp2:.1f}%)
├ TP3: {tp3_str} (+{profit_tp3:.1f}%)
└ TP4: {tp4_str} (+{profit_tp4:.1f}%)

⚠️ After TP1 - move SL to breakeven!
"""
        return message.strip()
    
    async def update_signal_result(self, signal_id: str, result: str, pnl_percent: float):
        """Обновление результата сигнала в канале (всегда на английском)"""
        try:
            emoji = "✅" if result == "WIN" else "❌"
            pnl_emoji = "+" if pnl_percent > 0 else ""
            
            message = f"""
{emoji} *Signal Closed*

🆔 ID: `{signal_id}`
📊 Result: *{result}*
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
        lang = get_user_lang(user_id)
        
        # Если язык не выбран (по умолчанию 'en' но пользователь ещё не выбирал)
        # Проверяем, есть ли запись в БД
        from database.user_preferences import UserPreference
        db = get_db()
        try:
            pref = db.query(UserPreference).filter(
                UserPreference.telegram_id == str(user_id)
            ).first()
            
            # Если пользователя нет в БД, показываем выбор языка
            if not pref:
                keyboard = [
                    [
                        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
                        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "👋 Welcome! Please select your language / Добро пожаловать! Выберите язык:",
                    reply_markup=reply_markup
                )
                return
        finally:
            db.close()
        
        # Если язык уже выбран, показываем меню в зависимости от прав
        # Проверяем, является ли пользователь админом
        is_admin = AdminManager.is_admin(user_id)
        
        if is_admin:
            message = t('cmd_start_admin', lang)
        else:
            message = t('cmd_start', lang)
        
        try:
            await update.message.reply_text(message.strip(), parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await update.message.reply_text(message.strip())
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        user_id = str(update.effective_user.id)
        lang = get_user_lang(user_id)
        
        await update.message.reply_text(t('cmd_help', lang))
    
    async def cmd_language(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /language - выбор языка"""
        user_id = str(update.effective_user.id)
        lang = get_user_lang(user_id)
        
        keyboard = [
            [
                InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
                InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            t('language_select', lang),
            reply_markup=reply_markup
        )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        
        # Обработка выбора языка
        if query.data.startswith("lang_"):
            lang = query.data.split("_")[1]
            UserPreferenceManager.set_language(user_id, lang)
            
            # После выбора языка показываем меню в зависимости от прав
            is_admin = AdminManager.is_admin(user_id)
            if is_admin:
                menu_text = t('cmd_start_admin', lang)
            else:
                menu_text = t('cmd_start', lang)
            
            message = t('language_changed', lang) + "\n\n" + menu_text
            try:
                await query.edit_message_text(message.strip(), parse_mode=ParseMode.MARKDOWN)
            except:
                await query.edit_message_text(message.strip())
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats - общая статистика"""
        user_id = str(update.effective_user.id)
        lang = get_user_lang(user_id)
        
        db = get_db()
        
        try:
            # Все сигналы
            total_signals = db.query(Signal).count()
            
            # Закрытые сигналы
            closed = db.query(Signal).filter(Signal.status.in_(['TP1', 'TP2', 'SL'])).all()
            
            if not closed:
                await update.message.reply_text(t('no_closed_signals', lang))
                return
            
            wins = len([s for s in closed if s.result == 'WIN'])
            losses = len([s for s in closed if s.result == 'LOSS'])
            
            winrate = (wins / len(closed)) * 100 if closed else 0
            total_pnl = sum([s.pnl_percent for s in closed if s.pnl_percent])
            avg_rr = sum([s.risk_reward for s in closed if s.risk_reward]) / len(closed) if closed else 0
            
            message = f"""
📊 *{t('overall_stats', lang)}*

{t('stats_total', lang, count=total_signals)}
{t('stats_profitable', lang, count=wins)}
{t('stats_unprofitable', lang, count=losses)}

{t('stats_winrate', lang, winrate=winrate)}
{t('stats_pnl', lang, pnl=total_pnl)}
{t('stats_avg_rr', lang, rr=avg_rr)}
"""
            try:
                await update.message.reply_text(message.strip(), parse_mode=ParseMode.MARKDOWN)
            except:
                await update.message.reply_text(message.strip())
            
        finally:
            db.close()
    
    async def cmd_today(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статистика за сегодня"""
        user_id = str(update.effective_user.id)
        lang = get_user_lang(user_id)
        
        db = get_db()
        
        try:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0)
            
            signals = db.query(Signal).filter(
                Signal.created_at >= today_start
            ).all()
            
            if not signals:
                await update.message.reply_text(t('no_signals_today', lang))
                return
            
            closed = [s for s in signals if s.status in ['TP1', 'TP2', 'SL']]
            active = [s for s in signals if s.status == 'ACTIVE']
            
            wins = len([s for s in closed if s.result == 'WIN'])
            losses = len([s for s in closed if s.result == 'LOSS'])
            
            message = f"""
📊 *{t('today_stats', lang)}*

{t('today_total', lang, count=len(signals))}
{t('today_active', lang, count=len(active))}
{t('stats_profitable', lang, count=wins)}
{t('stats_unprofitable', lang, count=losses)}
"""
            try:
                await update.message.reply_text(message.strip(), parse_mode=ParseMode.MARKDOWN)
            except:
                await update.message.reply_text(message.strip())
            
        finally:
            db.close()
    
    async def cmd_week(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статистика за неделю"""
        user_id = str(update.effective_user.id)
        lang = get_user_lang(user_id)
        
        db = get_db()
        
        try:
            week_start = datetime.utcnow() - timedelta(days=7)
            
            signals = db.query(Signal).filter(
                Signal.created_at >= week_start
            ).all()
            
            if not signals:
                await update.message.reply_text(t('no_signals_week', lang))
                return
            
            closed = [s for s in signals if s.status in ['TP1', 'TP2', 'SL']]
            
            wins = len([s for s in closed if s.result == 'WIN'])
            losses = len([s for s in closed if s.result == 'LOSS'])
            
            winrate = (wins / len(closed)) * 100 if closed else 0
            total_pnl = sum([s.pnl_percent for s in closed if s.pnl_percent])
            
            message = f"""
📊 *{t('week_stats', lang)}*

{t('week_total', lang, count=len(signals))}
{t('stats_profitable', lang, count=wins)}
{t('stats_unprofitable', lang, count=losses)}
{t('stats_winrate', lang, winrate=winrate)}
{t('week_pnl', lang, pnl=total_pnl)}
"""
            try:
                await update.message.reply_text(message.strip(), parse_mode=ParseMode.MARKDOWN)
            except:
                await update.message.reply_text(message.strip())
            
        finally:
            db.close()
    
    @admin_only
    async def cmd_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Текущая конфигурация"""
        user_id = str(update.effective_user.id)
        lang = get_user_lang(user_id)
        
        pairs = ConfigManager.get_trading_pairs()
        timeframes = ConfigManager.get_timeframes()
        enabled = ConfigManager.is_bot_enabled()
        
        status = t('enabled', lang) if enabled else t('disabled', lang)
        
        message = f"""
{t('config_title', lang)}

{t('config_status', lang, status=status)}

{t('config_trading', lang)}
{t('config_pairs', lang, pairs=', '.join(pairs))}
{t('config_timeframes', lang, timeframes=', '.join(timeframes))}

{t('use_commands', lang)}
"""
        try:
            await update.message.reply_text(message.strip(), parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            # Если ошибка с Markdown, отправляем без форматирования
            message_plain = f"""
{t('current_settings', lang)}

{t('status', lang)}: {status}

{t('trading', lang)}:
{t('pairs', lang)}: {', '.join(pairs)}
{t('timeframes', lang)}: {', '.join(timeframes)}

{t('use_commands', lang)}
"""
            await update.message.reply_text(message_plain.strip())
    
    @admin_only
    async def cmd_enable(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Включение бота"""
        user_id = str(update.effective_user.id)
        lang = get_user_lang(user_id)
        
        ConfigManager.enable_bot()
        await update.message.reply_text(t('bot_enabled', lang))
        await self.send_admin_message(t('bot_enabled', lang))
    
    @admin_only
    async def cmd_disable(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выключение бота"""
        user_id = str(update.effective_user.id)
        lang = get_user_lang(user_id)
        
        ConfigManager.disable_bot()
        await update.message.reply_text(t('bot_disabled', lang))
        await self.send_admin_message(t('bot_disabled', lang))
    
    @admin_only
    async def cmd_set_pairs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка торгуемых пар"""
        print(f"[DEBUG] cmd_set_pairs FUNCTION CALLED!")
        try:
            print(f"[DEBUG] cmd_set_pairs called, args: {context.args}")
            user_id = str(update.effective_user.id)
            lang = get_user_lang(user_id)
            print(f"[DEBUG] User ID: {user_id}, Lang: {lang}")
            
            if not context.args:
                current = ConfigManager.get_trading_pairs()
                message = f"{t('current_pairs', lang, pairs=', '.join(current))}\n\n{t('pairs_help', lang)}"
                try:
                    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
                except:
                    await update.message.reply_text(message)
                return
            
            pairs = [p.strip() for p in context.args]
            print(f"[DEBUG] Setting pairs: {pairs}")
            success = ConfigManager.set_trading_pairs(pairs)
            print(f"[DEBUG] Save result: {success}")
            
            if success:
                await update.message.reply_text(t('pairs_updated', lang, pairs=', '.join(pairs)))
                await self.send_admin_message(t('pairs_changed', lang, pairs=', '.join(pairs)))
            else:
                await update.message.reply_text(t('error', lang) + ": Failed to save pairs")
        except Exception as e:
            print(f"[ERROR] Exception in cmd_set_pairs: {e}")
            import traceback
            traceback.print_exc()
            try:
                await update.message.reply_text(f"Error: {str(e)}")
            except:
                pass
    
    @admin_only
    async def cmd_set_timeframes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка таймфреймов"""
        try:
            user_id = str(update.effective_user.id)
            lang = get_user_lang(user_id)
            
            if not context.args:
                current = ConfigManager.get_timeframes()
                message = f"{t('current_timeframes', lang, timeframes=', '.join(current))}\n\n{t('timeframes_help', lang)}"
                try:
                    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
                except:
                    await update.message.reply_text(message)
                return
            
            timeframes = [tf.strip() for tf in context.args]
            success = ConfigManager.set_timeframes(timeframes)
            
            if success:
                await update.message.reply_text(t('timeframes_updated', lang, timeframes=', '.join(timeframes)))
                await self.send_admin_message(t('timeframes_changed', lang, timeframes=', '.join(timeframes)))
            else:
                await update.message.reply_text(t('error', lang) + ": Failed to save timeframes")
        except Exception as e:
            await update.message.reply_text(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def run(self):
        """Запуск бота"""
        self.app.run_polling()

