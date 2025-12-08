from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from telegram.constants import ParseMode
from telegram.error import RetryAfter
import config
from database.models import Signal, BotStats, SessionLocal
from database.config_manager import ConfigManager
from database.admin_manager import AdminManager
from database.user_preferences import UserPreferenceManager
from .languages import t, get_user_lang
from .filter_panel import FilterPanel, FilterSettings, handle_filter_panel_callback
from sqlalchemy import func
from datetime import datetime, timedelta
import os
from functools import wraps

def admin_only(func):
    """Декоратор для проверки прав админа"""
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_id = str(update.effective_user.id)
            lang = get_user_lang(user_id)
            
            is_admin = AdminManager.is_admin(user_id)
            from utils.logger import logger
            logger.info(f"[DEBUG] Command {func.__name__} called by user {user_id}, is_admin: {is_admin}")
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
        self._flood_control_blocked_count = 0  # Счетчик заблокированных сигналов
        self._last_flood_notification_time = None  # Время последнего уведомления
    
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
        
        # Админ команды - настройка параметров
        # ВАЖНО: Telegram не поддерживает подчеркивания в командах, используем дефисы
        self.app.add_handler(CommandHandler("setpairs", self.cmd_set_pairs))
        self.app.add_handler(CommandHandler("setp", self.cmd_set_pairs))  # Короткий вариант
        self.app.add_handler(CommandHandler("settimeframes", self.cmd_set_timeframes))
        self.app.add_handler(CommandHandler("settf", self.cmd_set_timeframes))  # Короткий вариант
        
        # Команды для управления топ монетами
        self.app.add_handler(CommandHandler("topcoins", self.cmd_top_coins))
        self.app.add_handler(CommandHandler("top", self.cmd_top_coins))  # Короткий вариант
        self.app.add_handler(CommandHandler("refresh", self.cmd_refresh_coins))  # Принудительное обновление
        self.app.add_handler(CommandHandler("pairs", self.cmd_list_pairs))  # Показать текущий список
        
        # Команды для управления БД
        self.app.add_handler(CommandHandler("dbstats", self.cmd_db_stats))  # Статистика БД
        self.app.add_handler(CommandHandler("cleanup", self.cmd_cleanup_db))  # Очистка БД
        
        # Команда панели управления фильтрами
        self.app.add_handler(CommandHandler("filters", self.cmd_filters))  # Панель фильтров
        self.app.add_handler(CommandHandler("panel", self.cmd_filters))  # Альтернатива
        self.app.add_handler(CommandHandler("filters_status", self.cmd_filters_status))  # Статус фильтров
        
        # Команда помощи
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        
        # Callback handlers для кнопок
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Обработчик всех неизвестных команд для отладки
        async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            command = update.message.text.split()[0] if update.message.text else "unknown"
            print(f"[DEBUG] Unknown command received: {command}")
            await update.message.reply_text(f"Unknown command: {command}")
        
        self.app.add_handler(MessageHandler(filters.COMMAND & ~filters.Regex("^(start|stats|today|week|language|enable|disable|config|setpairs|setp|settimeframes|settf|topcoins|top|refresh|pairs|dbstats|cleanup|filters|panel|filters_status|help)"), unknown_command))
    
    async def send_signal(self, signal: dict) -> bool:
        """Отправка сигнала в канал (всегда на английском)"""
        from utils.logger import logger
        ticker = signal.get('ticker', 'UNKNOWN')
        
        # Дополнительный барьер: если DeepSeek отклонил — не отправляем
        ds = signal.get('deepseek')
        if isinstance(ds, dict) and ds.get('approved') is False:
            reason = (ds.get('plan') or {}).get('reason') or ds.get('error') or 'Rejected by DeepSeek'
            logger.info(f"[DEEPSEEK] Block sending {ticker}: {reason}")
            try:
                await self.send_admin_message(f"🤖 DeepSeek rejected {ticker}: {reason}")
            except Exception:
                pass
            return False
        
        try:
            logger.info(f"[TELEGRAM] Preparing to send signal {ticker} to channel...")
            
            # ВАЛИДАЦИЯ: проверяем что сигнал корректный
            entry = signal.get('entry_price', 0)
            stop = signal.get('stop_loss', 0)
            tp1 = signal.get('take_profit_1', 0)
            tp2 = signal.get('take_profit_2', 0)
            tp3 = signal.get('take_profit_3', 0)
            
            # Проверка на нулевые/одинаковые значения
            all_levels = [entry, stop, tp1, tp2, tp3]
            if any(level <= 0 for level in all_levels):
                logger.error(f"[BLOCKED] Invalid signal - zero levels: {ticker} entry={entry}, stop={stop}, tp1={tp1}, tp2={tp2}, tp3={tp3}")
                return False
            
            # Проверка на дубликаты (tp2 и tp3 могут быть одинаковыми - это нормально)
            critical_levels = [entry, stop, tp1, tp2]
            if len(set(critical_levels)) < len(critical_levels):
                logger.error(f"[BLOCKED] Invalid signal - duplicate critical levels: {ticker} entry={entry}, stop={stop}, tp1={tp1}, tp2={tp2}")
                return False
            
            # Проверка минимальной дистанции (0.1% между уровнями)
            min_dist = entry * 0.001
            if abs(entry - stop) < min_dist or abs(entry - tp1) < min_dist:
                logger.error(f"[BLOCKED] Invalid signal - levels too close: {ticker} min_dist={min_dist}")
                return False
            
            # Проверка наличия TELEGRAM_CHANNEL_ID
            if not config.TELEGRAM_CHANNEL_ID:
                logger.error(f"[ERROR] TELEGRAM_CHANNEL_ID not configured!")
                return False
            
            logger.info(f"[TELEGRAM] Channel ID: {config.TELEGRAM_CHANNEL_ID}")
            
            deepseek_result = signal.get('deepseek') or {}
            chart_path = signal.get('chart_path')

            message = self._format_signal_message(signal, lang='en')
            logger.debug(f"[TELEGRAM] Message formatted, length: {len(message)} chars")
            
            # Кнопка с реферальной ссылкой XT.com
            keyboard = [
                [InlineKeyboardButton(
                    "40% CASHBACK 💸 Official partner XT",
                    url="https://www.xt.com/en/accounts/register?ref=TRADINGBOT"
                )]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            logger.info(f"[TELEGRAM] Sending message to channel {config.TELEGRAM_CHANNEL_ID}...")
            
            # Обработка Flood control с повторной попыткой
            import asyncio
            
            max_retries = 5  # Увеличиваем количество попыток
            
            for attempt in range(max_retries):
                try:
                    if chart_path and os.path.exists(chart_path):
                        with open(chart_path, "rb") as photo:
                            await self.bot.send_photo(
                                chat_id=config.TELEGRAM_CHANNEL_ID,
                                photo=photo,
                                caption=message,
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=reply_markup
                            )
                    else:
                        await self.bot.send_message(
                            chat_id=config.TELEGRAM_CHANNEL_ID,
                            text=message,
                            parse_mode=ParseMode.MARKDOWN,
                            reply_markup=reply_markup
                        )
                    logger.info(f"[TELEGRAM] ✅ Signal {ticker} successfully sent to channel!")
                    return True
                except RetryAfter as e:
                    # Правильная обработка RetryAfter
                    retry_delay = e.retry_after + 1  # +1 секунда для безопасности
                    if attempt < max_retries - 1:
                        logger.warning(f"[TELEGRAM] Flood control for {ticker}, waiting {retry_delay}s (attempt {attempt + 1}/{max_retries})...")
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        logger.error(f"[TELEGRAM] Flood control exceeded for {ticker} after {max_retries} attempts")
                        # Увеличиваем счетчик и отправляем уведомление админу
                        self._flood_control_blocked_count += 1
                        await self._notify_flood_control_blocked(ticker, retry_delay)
                        return False
                except Exception as e:
                    error_str = str(e)
                    # Проверка на другие ошибки Flood control (на всякий случай)
                    if "Flood control" in error_str or "retry_after" in error_str.lower():
                        import re
                        retry_match = re.search(r'retry after (\d+)', error_str, re.IGNORECASE)
                        if retry_match:
                            retry_delay = int(retry_match.group(1)) + 1
                        else:
                            retry_delay = (attempt + 1) * 5
                        
                        if attempt < max_retries - 1:
                            logger.warning(f"[TELEGRAM] Flood control (generic) for {ticker}, waiting {retry_delay}s (attempt {attempt + 1}/{max_retries})...")
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            logger.error(f"[TELEGRAM] Flood control exceeded for {ticker} after {max_retries} attempts")
                            # Увеличиваем счетчик и отправляем уведомление админу
                            self._flood_control_blocked_count += 1
                            await self._notify_flood_control_blocked(ticker, retry_delay)
                            return False
                    else:
                        # Другая ошибка - логируем и возвращаем False
                        error_msg = f"Error sending signal {ticker}: {e}"
                        logger.error(f"[TELEGRAM] {error_msg}")
                        import traceback
                        logger.error(f"[TELEGRAM] Traceback: {traceback.format_exc()}")
                        try:
                            await self.send_admin_message(error_msg)
                        except:
                            logger.error(f"[ERROR] Could not send admin message: {error_msg}")
                        return False
        except Exception as e:
            error_msg = f"Unexpected error sending signal {ticker}: {e}"
            logger.error(f"[TELEGRAM] {error_msg}")
            import traceback
            logger.error(f"[TELEGRAM] Traceback: {traceback.format_exc()}")
            return False
    
    async def _notify_flood_control_blocked(self, ticker: str, retry_delay: int):
        """Уведомление админа о блокировке из-за Flood control"""
        from datetime import datetime
        
        # Отправляем уведомление не чаще раза в 5 минут
        now = datetime.now()
        if self._last_flood_notification_time:
            time_since_last = (now - self._last_flood_notification_time).total_seconds()
            if time_since_last < 300:  # 5 минут
                return
        
        self._last_flood_notification_time = now
        
        message = (
            f"⚠️ *Telegram API Flood Control*\n\n"
            f"Сигнал *{ticker}* не отправлен из-за ограничения Telegram API.\n"
            f"Ожидание: {retry_delay} сек\n"
            f"Заблокировано сигналов: {self._flood_control_blocked_count}\n\n"
            f"Бот автоматически повторяет попытки, но при большом количестве сигналов "
            f"Telegram может временно блокировать отправку."
        )
        
        try:
            await self.send_admin_message(message)
        except Exception as e:
            logger.error(f"[ERROR] Could not send flood control notification: {e}")
    
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
        """Форматирование сигнала"""
        
        emoji = "🟢" if signal['direction'] == 'LONG' else "🔴"
        
        # Расчёт потенциальной прибыли для TP1, TP2, TP3 (TP4 убран)
        entry = signal['entry_price']
        tp1 = signal['take_profit_1']
        tp2 = signal['take_profit_2']
        tp3 = signal['take_profit_3']
        stop = signal['stop_loss']
        leverage = 10  # отображаем проценты с учётом плеча 10х
        
        if signal['direction'] == 'LONG':
            profit_tp1 = ((tp1 - entry) / entry) * 100
            profit_tp2 = ((tp2 - entry) / entry) * 100
            profit_tp3 = ((tp3 - entry) / entry) * 100
            risk_percent = ((entry - stop) / entry) * 100
        else:
            profit_tp1 = ((entry - tp1) / entry) * 100
            profit_tp2 = ((entry - tp2) / entry) * 100
            profit_tp3 = ((entry - tp3) / entry) * 100
            risk_percent = ((stop - entry) / entry) * 100

        # Отображаем проценты с учётом плеча
        profit_tp1 *= leverage
        profit_tp2 *= leverage
        profit_tp3 *= leverage
        risk_percent *= leverage
        
        # Форматирование цен с учётом их величины
        entry_str = self._format_price(entry)
        stop_str = self._format_price(stop)
        tp1_str = self._format_price(tp1)
        tp2_str = self._format_price(tp2)
        tp3_str = self._format_price(tp3)
        
        # Сигналы всегда на английском для канала
        message = f"""
📊 *{signal['ticker']}* | {signal['direction']}

💰 Entry: {entry_str}
🛑 Stop: {stop_str} (-{risk_percent:.2f}%)

🎯 Take Profit
├ TP1: {tp1_str} (+{profit_tp1:.1f}%)
├ TP2: {tp2_str} (+{profit_tp2:.1f}%)
└ TP3: {tp3_str} (+{profit_tp3:.1f}%)

⚡️ Leverage 10x
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
        from database.models import SessionLocal
        db = SessionLocal()
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
        """Команда /help - показывает все доступные команды"""
        user_id = str(update.effective_user.id)
        lang = get_user_lang(user_id)
        
        # Проверяем, является ли пользователь админом
        is_admin = AdminManager.is_admin(user_id)
        
        if is_admin:
            message = t('cmd_start_admin', lang)
        else:
            message = t('cmd_start', lang)
        
        try:
            await update.message.reply_text(message.strip(), parse_mode=ParseMode.MARKDOWN)
        except:
            await update.message.reply_text(message.strip())
    
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
        
        user_id = str(update.effective_user.id)
        
        # Обработка панели фильтров (только для админов)
        if query.data.startswith("fp_") or query.data == "noop":
            # Проверяем права админа
            if not AdminManager.is_admin(user_id):
                await query.answer("⛔ Доступ запрещён", show_alert=True)
                return
            await handle_filter_panel_callback(update, context)
            return
        
        await query.answer()
        
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
        
        from database.models import SessionLocal
        db = SessionLocal()
        
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
        
        from database.models import SessionLocal
        db = SessionLocal()
        
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
        
        from database.models import SessionLocal
        db = SessionLocal()
        
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
        try:
            user_id = str(update.effective_user.id)
            lang = get_user_lang(user_id)
            
            # Если нет аргументов, показываем текущие пары
            if not context.args:
                current = ConfigManager.get_trading_pairs()
                pairs_str = ', '.join(current[:20])  # Показываем первые 20
                if len(current) > 20:
                    pairs_str += f"\n... и ещё {len(current) - 20} пар"
                
                message = f"{t('current_pairs', lang, pairs=pairs_str)}\n\n{t('pairs_help', lang)}"
                try:
                    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
                except:
                    await update.message.reply_text(message)
                return
            
            # Получаем пары из аргументов
            pairs = [p.strip().upper() for p in context.args if p.strip()]
            
            # Если пары переданы через аргументы, но их мало, пробуем получить из текста сообщения
            if len(pairs) < 2 and update.message.text:
                # Пробуем извлечь пары из текста после команды
                text = update.message.text
                if '/setpairs' in text.lower() or '/setp' in text.lower():
                    # Убираем команду и разбиваем по пробелам/запятым
                    text_after_cmd = text.split(maxsplit=1)[1] if len(text.split()) > 1 else ""
                    if text_after_cmd:
                        # Разбиваем по пробелам, запятым, переносам строк
                        pairs = [p.strip().upper() for p in text_after_cmd.replace(',', ' ').replace('\n', ' ').split() if p.strip() and '/' in p]
            
            if not pairs:
                await update.message.reply_text(f"{t('error', lang)}: No pairs specified. Use: `/setpairs BTC/USDT ETH/USDT`", parse_mode=ParseMode.MARKDOWN)
                return
            
            # Фильтруем только валидные пары (должны содержать /)
            valid_pairs = [p for p in pairs if '/' in p and len(p.split('/')) == 2]
            
            if not valid_pairs:
                await update.message.reply_text(f"{t('error', lang)}: Invalid pair format. Use: `BTC/USDT ETH/USDT`", parse_mode=ParseMode.MARKDOWN)
                return
            
            # Убираем дубликаты, сохраняя порядок
            unique_pairs = list(dict.fromkeys(valid_pairs))
            
            # Сохраняем пары
            success = ConfigManager.set_trading_pairs(unique_pairs)
            
            if success:
                # Формируем сообщение с подтверждением
                pairs_preview = ', '.join(unique_pairs[:10])
                if len(unique_pairs) > 10:
                    pairs_preview += f"\n... и ещё {len(unique_pairs) - 10} пар"
                
                confirm_message = f"✅ {t('pairs_updated', lang, pairs=pairs_preview)}\n\n📊 Всего установлено: {len(unique_pairs)} пар"
                
                await update.message.reply_text(confirm_message, parse_mode=ParseMode.MARKDOWN)
                
                # Отправляем уведомление админам
                admin_message = f"⚙️ {t('pairs_changed', lang, pairs=f'{len(unique_pairs)} pairs')}\nПервые 5: {', '.join(unique_pairs[:5])}"
                await self.send_admin_message(admin_message)
            else:
                await update.message.reply_text(f"{t('error', lang)}: Failed to save pairs to database")
                
        except Exception as e:
            from utils.logger import log_error
            log_error(f"Error in cmd_set_pairs: {e}", "cmd_set_pairs")
            import traceback
            traceback.print_exc()
            try:
                await update.message.reply_text(f"❌ Error: {str(e)}")
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
    
    @admin_only
    async def cmd_top_coins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать информацию о топ монетах"""
        try:
            user_id = str(update.effective_user.id)
            lang = get_user_lang(user_id)
            
            from utils.top_coins import TopCoinsService
            
            # Получаем информацию о кэше
            cache_info = TopCoinsService.get_cache_info()
            
            # Текущие торговые пары
            current_pairs = ConfigManager.get_trading_pairs()
            
            # Формируем сообщение
            last_update = cache_info['last_update']
            if last_update:
                last_update_str = last_update.strftime('%Y-%m-%d %H:%M UTC')
            else:
                last_update_str = "Never"
            
            next_update = cache_info['next_update']
            if next_update:
                next_update_str = next_update.strftime('%Y-%m-%d %H:%M UTC')
            else:
                next_update_str = "Soon"
            
            message = f"""
📊 *Top Coins Status*

🔄 *Auto-update:* Enabled (every hour)
📅 *Last update:* {last_update_str}
⏰ *Next update:* {next_update_str}

📈 *Current pairs:* {len(current_pairs)}
✅ *Cache valid:* {'Yes' if cache_info['is_valid'] else 'No'}

💡 *Commands:*
• `/pairs` - show current pairs list
• `/refresh` - force update top 200
• `/setpairs` - manual set pairs
"""
            await update.message.reply_text(message.strip(), parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            await update.message.reply_text(f"Error: {str(e)}")
    
    @admin_only
    async def cmd_refresh_coins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Принудительное обновление списка топ монет"""
        try:
            user_id = str(update.effective_user.id)
            lang = get_user_lang(user_id)
            
            await update.message.reply_text("🔄 Updating top 200 coins from CoinGecko...")
            
            from utils.top_coins import update_trading_pairs_auto, TopCoinsService
            
            # Принудительное обновление
            success = await update_trading_pairs_auto(limit=200)
            
            if success:
                pairs = ConfigManager.get_trading_pairs()
                
                # Показываем первые 20 пар
                pairs_preview = ', '.join(pairs[:20])
                if len(pairs) > 20:
                    pairs_preview += f"\n... +{len(pairs) - 20} more"
                
                message = f"""
✅ *Top coins updated successfully!*

📊 *Total pairs:* {len(pairs)}

🏆 *Top 20:*
{pairs_preview}

💡 Use `/pairs` to see full list
"""
                await update.message.reply_text(message.strip(), parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text("❌ Failed to update. Using cached data.")
                
        except Exception as e:
            await update.message.reply_text(f"Error: {str(e)}")
    
    @admin_only
    async def cmd_list_pairs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать полный список торговых пар"""
        try:
            user_id = str(update.effective_user.id)
            lang = get_user_lang(user_id)
            
            pairs = ConfigManager.get_trading_pairs()
            
            if not pairs:
                await update.message.reply_text("❌ No trading pairs configured")
                return
            
            # Разбиваем на группы по 50 для читаемости
            chunks = [pairs[i:i+50] for i in range(0, len(pairs), 50)]
            
            # Первое сообщение с заголовком
            header = f"📋 *Trading Pairs ({len(pairs)} total)*\n\n"
            
            for idx, chunk in enumerate(chunks):
                # Формируем список с номерами
                numbered_pairs = [f"{i+1+idx*50}. {pair}" for i, pair in enumerate(chunk)]
                pairs_text = '\n'.join(numbered_pairs)
                
                if idx == 0:
                    message = header + f"```\n{pairs_text}\n```"
                else:
                    message = f"```\n{pairs_text}\n```"
                
                try:
                    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
                except:
                    # Если Markdown не работает, отправляем без форматирования
                    await update.message.reply_text(pairs_text)
                
                # Небольшая пауза между сообщениями
                if idx < len(chunks) - 1:
                    import asyncio
                    await asyncio.sleep(0.5)
            
        except Exception as e:
            await update.message.reply_text(f"Error: {str(e)}")
    
    @admin_only
    async def cmd_db_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать статистику базы данных"""
        try:
            user_id = str(update.effective_user.id)
            lang = get_user_lang(user_id)
            
            from utils.db_cleanup import DatabaseCleanup
            
            stats = DatabaseCleanup.get_db_stats()
            
            oldest_str = stats['oldest_date'].strftime('%Y-%m-%d %H:%M') if stats['oldest_date'] else "N/A"
            
            message = f"""
📊 *Database Statistics*

📈 *Signals:*
├ Total: {stats['total']}
├ Active: {stats['active']}
├ Closed: {stats['closed']}
└ Last 24h: {stats['signals_24h']}

📅 *Oldest signal:* {oldest_str}

🗑️ *Auto-cleanup:* Every 24 hours
📦 *Retention:* 30 days

💡 Use `/cleanup` to manually clean old signals
"""
            await update.message.reply_text(message.strip(), parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            await update.message.reply_text(f"Error: {str(e)}")
    
    @admin_only
    async def cmd_cleanup_db(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ручная очистка старых сигналов"""
        try:
            user_id = str(update.effective_user.id)
            lang = get_user_lang(user_id)
            
            # Проверяем аргумент (количество дней)
            days = 30  # По умолчанию
            if context.args:
                try:
                    days = int(context.args[0])
                    if days < 1:
                        days = 1
                    if days > 365:
                        days = 365
                except:
                    pass
            
            await update.message.reply_text(f"🗑️ Cleaning signals older than {days} days...")
            
            from utils.db_cleanup import DatabaseCleanup
            
            # Получаем статистику до очистки
            stats_before = DatabaseCleanup.get_db_stats()
            
            # Очищаем
            deleted = DatabaseCleanup.cleanup_old_signals(days=days)
            
            # Оптимизируем БД
            if deleted > 0:
                DatabaseCleanup.vacuum_database()
            
            # Получаем статистику после
            stats_after = DatabaseCleanup.get_db_stats()
            
            message = f"""
✅ *Cleanup Complete*

🗑️ *Deleted:* {deleted} old signals

📊 *Before:* {stats_before['total']} signals
📊 *After:* {stats_after['total']} signals

💾 Database optimized!
"""
            await update.message.reply_text(message.strip(), parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            await update.message.reply_text(f"Error: {str(e)}")
    
    @admin_only
    async def cmd_filters(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Панель управления фильтрами"""
        try:
            user_id = str(update.effective_user.id)
            lang = get_user_lang(user_id)
            
            # Загружаем текущие настройки
            FilterSettings.get_all()
            
            message = """
⚙️ *ПАНЕЛЬ УПРАВЛЕНИЯ ФИЛЬТРАМИ*

Здесь вы можете настроить все параметры фильтрации сигналов.

📊 Выберите категорию для настройки:
"""
            
            await update.message.reply_text(
                message.strip(),
                reply_markup=FilterPanel.get_main_menu(),
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            await update.message.reply_text(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
    
    @admin_only
    async def cmd_filters_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Вывод текущих настроек всех фильтров (то же, что кнопка '📋 Текущие настройки')"""
        try:
            # Загружаем текущие настройки
            FilterSettings.get_all()
            
            # Используем тот же метод, что и кнопка в панели
            text = FilterPanel.get_settings_text()
            
            await update.message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            await update.message.reply_text(f"Ошибка: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def run(self):
        """Запуск бота"""
        self.app.run_polling()

