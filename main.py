import asyncio
from datetime import datetime
from exchange.xt_client import XTClient
from analysis.signal_generator import SignalGenerator
from telegram_bot.bot import TelegramBot
from database.models import init_db, get_db, Signal
from database.config_manager import ConfigManager
from utils.logger import logger, log_signal, log_error, log_info, log_warning
import config

class CryptoSignalBot:
    """Главный класс бота"""
    
    def __init__(self):
        self.xt_client = XTClient()
        self.telegram_bot = TelegramBot()
        self.is_running = False
        
    async def initialize(self):
        """Инициализация бота"""
        log_info("🚀 Инициализация бота...")
        
        # Инициализация БД
        init_db()
        log_info("✅ База данных инициализирована")
        
        # Загрузка настроек из БД
        pairs = ConfigManager.get_trading_pairs()
        timeframes = ConfigManager.get_timeframes()
        min_score = ConfigManager.get_min_ai_score()
        
        # Отправка уведомления в админ-канал
        await self.telegram_bot.send_admin_message(
            "🤖 *Бот запущен*\n\n"
            f"Торгуемые пары: {len(pairs)}\n"
            f"Таймфреймы: {', '.join(timeframes)}\n"
            f"Мин. AI Score: {min_score}"
        )
        
        log_info("✅ Инициализация завершена")
    
    async def analyze_market(self):
        """Анализ рынка и генерация сигналов"""
        
        # Загрузка настроек из БД
        if not ConfigManager.is_bot_enabled():
            log_warning("Бот выключен, анализ пропущен")
            return
        
        log_info("📊 Начало анализа рынка...")
        
        pairs = ConfigManager.get_trading_pairs()
        timeframes = ConfigManager.get_timeframes()
        
        for pair in pairs:
            for timeframe in timeframes:
                try:
                    # Получение данных
                    df = await self.xt_client.get_ohlcv(pair, timeframe, limit=500)
                    
                    if df.empty:
                        log_warning(f"Нет данных для {pair} {timeframe}")
                        continue
                    
                    # Получение старшего таймфрейма
                    from analysis.multi_timeframe import MultiTimeframeAnalysis
                    higher_tf = MultiTimeframeAnalysis.get_higher_timeframe(timeframe)
                    df_higher = await self.xt_client.get_ohlcv(pair, higher_tf, limit=200)
                    
                    if df_higher.empty:
                        log_warning(f"Нет данных старшего ТФ для {pair} {higher_tf}")
                        continue
                    
                    # Генерация сигнала (теперь async и с доп. параметрами)
                    generator = SignalGenerator(pair, timeframe, df, df_higher, self.xt_client)
                    signal = await generator.generate_signal()
                    
                    if signal:
                        # Проверка дубликатов (не генерируем повторные сигналы для той же пары)
                        db = get_db()
                        try:
                            recent_signal = db.query(Signal).filter(
                                Signal.ticker == pair,
                                Signal.status == 'ACTIVE'
                            ).first()
                            
                            if recent_signal:
                                log_info(f"⏭ Пропуск {pair}: уже есть активный сигнал")
                                continue
                            
                            # Сохранение в БД (с 4 TP и доп. полями)
                            db_signal = Signal(
                                signal_id=signal['signal_id'],
                                ticker=signal['ticker'],
                                direction=signal['direction'],
                                entry_price=signal['entry_price'],
                                stop_loss=signal['stop_loss'],
                                take_profit_1=signal['take_profit_1'],
                                take_profit_2=signal['take_profit_2'],
                                take_profit_3=signal['take_profit_3'],
                                take_profit_4=signal['take_profit_4'],
                                risk_percent=signal['risk_percent'],
                                leverage=signal['leverage'],
                                ai_score=signal['ai_score'],
                                timeframe=signal['timeframe'],
                                timeframe_higher=signal.get('timeframe_higher'),
                                volume_24h=signal.get('volume_24h'),
                                spread_percent=signal.get('spread_percent'),
                                atr_value=signal.get('atr_value'),
                                status='WAITING'  # Новый сигнал в ожидании
                            )
                            
                            db.add(db_signal)
                            db.commit()
                            
                            # Отправка в Telegram
                            await self.telegram_bot.send_signal(signal)
                            
                            log_signal(signal)
                            
                        finally:
                            db.close()
                
                except Exception as e:
                    log_error(str(e), f"анализа {pair} {timeframe}")
                
                # Задержка между запросами (rate limit)
                await asyncio.sleep(1)
        
        log_info("✅ Анализ рынка завершён")
    
    async def monitor_active_signals(self):
        """Мониторинг активных сигналов (WAITING + IN_POSITION)"""
        db = get_db()
        
        try:
            # Мониторинг сигналов в ожидании входа И уже в позиции
            active_signals = db.query(Signal).filter(
                Signal.status.in_(['WAITING', 'IN_POSITION', 'TP1_HIT', 'TP2_HIT', 'TP3_HIT'])
            ).all()
            
            for signal in active_signals:
                try:
                    # Получение текущей цены
                    ticker = await self.xt_client.get_ticker(signal.ticker)
                    
                    if not ticker:
                        continue
                    
                    current_price = ticker['last']
                    
                    # WAITING: проверка активации входа или отмены
                    if signal.status == 'WAITING':
                        await self._check_waiting_signal(signal, current_price, db)
                    
                    # IN_POSITION: проверка TP/SL
                    elif signal.status in ['IN_POSITION', 'TP1_HIT', 'TP2_HIT', 'TP3_HIT']:
                        await self._check_position_levels(signal, current_price, db)
                
                except Exception as e:
                    log_error(str(e), f"мониторинга сигнала {signal.signal_id}")
        
        finally:
            db.close()
    
    async def _check_waiting_signal(self, signal: Signal, current_price: float, db):
        """Проверка сигнала в ожидании: активация входа или отмена"""
        from analysis.signal_cancellation import SignalCancellation
        from telegram_bot.notifications import TelegramNotifications
        
        # 1. Проверка условий отмены
        df = await self.xt_client.get_ohlcv(signal.ticker, signal.timeframe, limit=100)
        
        should_cancel, cancel_reason = SignalCancellation.should_cancel(
            {
                'entry_price': signal.entry_price,
                'stop_loss': signal.stop_loss,
                'direction': signal.direction,
                'signal_id': signal.signal_id
            },
            current_price,
            df,
            signal.created_at
        )
        
        if should_cancel:
            # Отмена сигнала
            signal.status = 'CANCELLED'
            signal.cancellation_reason = cancel_reason
            signal.closed_at = datetime.utcnow()
            db.commit()
            
            # Уведомление
            msg = TelegramNotifications.format_cancelled(
                {'signal_id': signal.signal_id, 'ticker': signal.ticker, 'direction': signal.direction},
                cancel_reason
            )
            await self.telegram_bot.send_admin_message(msg)
            
            log_info(f"🚫 Сигнал {signal.signal_id} отменён: {cancel_reason}")
            return
        
        # 2. Проверка активации входа
        entry_activated = False
        
        if signal.direction == 'LONG':
            if current_price <= signal.entry_price:
                entry_activated = True
        else:  # SHORT
            if current_price >= signal.entry_price:
                entry_activated = True
        
        if entry_activated:
            # Активация входа
            signal.status = 'IN_POSITION'
            signal.activated_at = datetime.utcnow()
            db.commit()
            
            # Уведомление
            msg = TelegramNotifications.format_entry_activated(
                {
                    'signal_id': signal.signal_id,
                    'ticker': signal.ticker,
                    'direction': signal.direction,
                    'stop_loss': signal.stop_loss
                },
                current_price
            )
            await self.telegram_bot.bot.send_message(
                chat_id=config.TELEGRAM_CHANNEL_ID,
                text=msg,
                parse_mode='Markdown'
            )
            
            log_info(f"✅ Вход активирован {signal.signal_id} @ {current_price}")
    
    async def _check_position_levels(self, signal: Signal, current_price: float, db):
        """Проверка достижения TP и SL для позиции"""
        from telegram_bot.notifications import TelegramNotifications
        
        # Определение текущего стопа (может быть безубыток после TP1)
        current_stop = signal.stop_loss_breakeven if signal.tp1_hit else signal.stop_loss
        
        if signal.direction == 'LONG':
            # Проверка SL
            if current_price <= current_stop:
                await self._close_on_stop(signal, current_price, db)
                return
            
            # Проверка TP4 (последний)
            if not signal.tp4_hit and current_price >= signal.take_profit_4:
                await self._hit_tp(signal, 4, current_price, db)
                # Полное закрытие
                signal.status = 'CLOSED_FULL_TP'
                signal.result = 'WIN'
                signal.closed_at = datetime.utcnow()
                db.commit()
                
                msg = TelegramNotifications.format_full_tp({
                    'signal_id': signal.signal_id,
                    'ticker': signal.ticker,
                    'direction': signal.direction,
                    'entry_price': signal.entry_price,
                    'activated_price': signal.entry_price,
                    'take_profit_4': signal.take_profit_4
                })
                await self.telegram_bot.bot.send_message(
                    chat_id=config.TELEGRAM_CHANNEL_ID,
                    text=msg,
                    parse_mode='Markdown'
                )
                return
            
            # Проверка TP3
            if not signal.tp3_hit and current_price >= signal.take_profit_3:
                await self._hit_tp(signal, 3, current_price, db)
                return
            
            # Проверка TP2
            if not signal.tp2_hit and current_price >= signal.take_profit_2:
                await self._hit_tp(signal, 2, current_price, db)
                return
            
            # Проверка TP1 (+ безубыток)
            if not signal.tp1_hit and current_price >= signal.take_profit_1:
                await self._hit_tp(signal, 1, current_price, db)
                # Перенос в безубыток
                signal.stop_loss_breakeven = signal.entry_price
                db.commit()
                return
        
        else:  # SHORT - зеркально
            if current_price >= current_stop:
                await self._close_on_stop(signal, current_price, db)
                return
            
            if not signal.tp4_hit and current_price <= signal.take_profit_4:
                await self._hit_tp(signal, 4, current_price, db)
                signal.status = 'CLOSED_FULL_TP'
                signal.result = 'WIN'
                signal.closed_at = datetime.utcnow()
                db.commit()
                return
            
            if not signal.tp3_hit and current_price <= signal.take_profit_3:
                await self._hit_tp(signal, 3, current_price, db)
                return
            
            if not signal.tp2_hit and current_price <= signal.take_profit_2:
                await self._hit_tp(signal, 2, current_price, db)
                return
            
            if not signal.tp1_hit and current_price <= signal.take_profit_1:
                await self._hit_tp(signal, 1, current_price, db)
                signal.stop_loss_breakeven = signal.entry_price
                db.commit()
                return
    
    async def _hit_tp(self, signal: Signal, tp_number: int, price: float, db):
        """Обработка достижения TP"""
        from telegram_bot.notifications import TelegramNotifications
        
        # Установка флага
        setattr(signal, f'tp{tp_number}_hit', True)
        signal.status = f'TP{tp_number}_HIT'
        db.commit()
        
        # Расчёт оставшейся позиции
        tps_hit = sum([signal.tp1_hit, signal.tp2_hit, signal.tp3_hit, signal.tp4_hit])
        remaining = 100 - (tps_hit * 25)
        
        # Уведомление
        msg = TelegramNotifications.format_tp_hit(
            {
                'signal_id': signal.signal_id,
                'ticker': signal.ticker,
                'direction': signal.direction,
                'entry_price': signal.entry_price,
                f'take_profit_{tp_number + 1}': getattr(signal, f'take_profit_{tp_number + 1}', 0) if tp_number < 4 else 0
            },
            tp_number,
            price,
            remaining
        )
        
        await self.telegram_bot.bot.send_message(
            chat_id=config.TELEGRAM_CHANNEL_ID,
            text=msg,
            parse_mode='Markdown'
        )
        
        log_info(f"🎯 TP{tp_number} достигнут {signal.signal_id} @ {price}")
    
    async def _close_on_stop(self, signal: Signal, price: float, db):
        """Закрытие по стоп-лоссу"""
        from telegram_bot.notifications import TelegramNotifications
        
        signal.status = 'STOPPED_OUT'
        signal.result = 'LOSS' if not signal.tp1_hit else 'BREAKEVEN'
        signal.closed_at = datetime.utcnow()
        
        # Расчёт PnL
        entry = signal.entry_price
        if signal.direction == 'LONG':
            pnl = ((price - entry) / entry) * 100
        else:
            pnl = ((entry - price) / entry) * 100
        
        signal.pnl_percent = pnl
        db.commit()
        
        # Уведомление
        msg = TelegramNotifications.format_stop_loss(
            {
                'signal_id': signal.signal_id,
                'ticker': signal.ticker,
                'direction': signal.direction,
                'entry_price': entry,
                'activated_price': entry,
                'stop_loss_breakeven': signal.stop_loss_breakeven,
                'tp1_hit': signal.tp1_hit,
                'tp2_hit': signal.tp2_hit,
                'tp3_hit': signal.tp3_hit,
                'tp4_hit': signal.tp4_hit
            },
            price
        )
        
        await self.telegram_bot.bot.send_message(
            chat_id=config.TELEGRAM_CHANNEL_ID,
            text=msg,
            parse_mode='Markdown'
        )
        
        log_info(f"🛑 Стоп-лосс {signal.signal_id} @ {price}, PnL: {pnl:.2f}%")
    
    async def run_cycle(self):
        """Один цикл работы бота"""
        
        # Анализ рынка
        await self.analyze_market()
        
        # Мониторинг активных сигналов
        await self.monitor_active_signals()
    
    async def run(self):
        """Основной цикл работы"""
        await self.initialize()
        
        self.is_running = True
        
        log_info("🤖 Бот запущен в основном цикле")
        
        while self.is_running:
            try:
                await self.run_cycle()
                
                # Пауза между циклами (5 минут)
                await asyncio.sleep(300)
                
            except KeyboardInterrupt:
                log_info("⏹ Получен сигнал остановки")
                break
            except Exception as e:
                log_error(str(e), "основного цикла")
                await self.telegram_bot.send_admin_message(f"❌ Критическая ошибка: {e}")
                await asyncio.sleep(60)
        
        log_info("👋 Бот остановлен")
        self.xt_client.close()

async def main():
    """Точка входа"""
    bot = CryptoSignalBot()
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹ Бот остановлен пользователем")

