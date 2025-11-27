import asyncio
from datetime import datetime
from exchange.xt_client import XTClient
from analysis.signal_generator import SignalGenerator
from analysis.market_filters import MarketFilters
from telegram_bot.bot import TelegramBot
from database.models import init_db, get_db, Signal, SessionLocal
from database.config_manager import ConfigManager
from utils.logger import logger, log_signal, log_error, log_info, log_warning, log_filter_summary
from utils.cache import btc_cache, api_rate_limiter
from utils.top_coins import TopCoinsService, update_trading_pairs_auto
from utils.db_cleanup import DatabaseCleanup, run_scheduled_cleanup
import config
import time


class CryptoSignalBot:
    """Главный класс бота с поддержкой автоматического топ-100 монет"""
    
    # Настройки параллельной обработки
    BATCH_SIZE = 40  # Размер батча для параллельной обработки
    MAX_CONCURRENT_TASKS = 30  # Максимум одновременных задач
    ANALYSIS_INTERVAL_CYCLES = 120  # Интервал анализа (120 циклов * 5 сек = 10 минут)
    TOP_COINS_UPDATE_CYCLES = 720  # Обновление топ монет каждый час (720 * 5 сек = 3600 сек)
    DB_CLEANUP_CYCLES = 17280  # Очистка БД раз в сутки (17280 * 5 сек = 86400 сек)
    
    def __init__(self):
        self.xt_client = XTClient()
        self.telegram_bot = TelegramBot()
        self.is_running = False
        self.polling_task = None
        self._semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_TASKS)
        
    async def initialize(self):
        """Инициализация бота"""
        log_info("Initializing bot...")
        
        # Инициализация БД
        init_db()
        log_info("Database initialized")
        
        # Запуск Telegram бота (polling)
        await self.telegram_bot.app.initialize()
        await self.telegram_bot.app.start()
        
        # Запускаем polling в отдельной задаче
        self.polling_task = asyncio.create_task(self._run_telegram_polling())
        await asyncio.sleep(3)
        log_info("OK: Telegram bot started (polling)")
        
        # Автоматическое обновление торговых пар на топ-100
        log_info("Fetching top 100 coins by market cap...")
        success = await update_trading_pairs_auto(limit=100)
        if success:
            log_info("✅ Trading pairs auto-updated to top 100 coins")
        else:
            log_warning("⚠️ Could not auto-update pairs, using existing config")
        
        # Загрузка настроек из БД
        pairs = ConfigManager.get_trading_pairs()
        timeframes = ConfigManager.get_timeframes()
        
        log_info(f"Loaded {len(pairs)} trading pairs, {len(timeframes)} timeframes")
        log_info("Initialization complete")
    
    async def _process_pair_timeframe(self, pair: str, timeframe: str) -> dict:
        """
        Обработка одной пары на одном таймфрейме
        Возвращает результат или None
        """
        async with self._semaphore:
            try:
                # Rate limiting
                async with api_rate_limiter:
                    # Получение данных с небольшой задержкой для rate limit
                    df = await self.xt_client.get_ohlcv(pair, timeframe, limit=500)
                
                if df is None or df.empty:
                    return {'pair': pair, 'timeframe': timeframe, 'status': 'no_data'}
                
                # Получение старшего таймфрейма
                from analysis.multi_timeframe import MultiTimeframeAnalysis
                higher_tf = MultiTimeframeAnalysis.get_higher_timeframe(timeframe)
                
                async with api_rate_limiter:
                    df_higher = await self.xt_client.get_ohlcv(pair, higher_tf, limit=200)
                
                if df_higher is None or df_higher.empty:
                    return {'pair': pair, 'timeframe': timeframe, 'status': 'no_higher_data'}
                
                # Генерация сигнала
                generator = SignalGenerator(pair, timeframe, df, df_higher, self.xt_client)
                signal = await generator.generate_signal()
                
                if signal:
                    log_info(f"[SIGNAL GENERATED] {pair} {timeframe} {signal.get('direction')} - Entry: {signal.get('entry_price')}, Stop: {signal.get('stop_loss')}")
                    return {
                        'pair': pair,
                        'timeframe': timeframe,
                        'status': 'signal',
                        'signal': signal
                    }
                
                return {'pair': pair, 'timeframe': timeframe, 'status': 'no_signal'}
                
            except Exception as e:
                import re
                error_clean = re.sub(r'[^\x00-\x7F]+', '[?]', str(e))
                return {
                    'pair': pair,
                    'timeframe': timeframe,
                    'status': 'error',
                    'error': error_clean
                }
    
    async def analyze_market_parallel(self):
        """
        Параллельный анализ рынка для 200+ торговых пар
        Использует батчи для оптимальной производительности
        """
        if not ConfigManager.is_bot_enabled():
            log_warning("Bot disabled, skipping analysis")
            return
        
        pairs = ConfigManager.get_trading_pairs()
        timeframes = ConfigManager.get_timeframes()
        
        total_combinations = len(pairs) * len(timeframes)
        log_info(f"Starting parallel market analysis: {len(pairs)} pairs x {len(timeframes)} timeframes = {total_combinations} combinations")
        
        start_time = time.time()
        
        # Предварительно загружаем BTC данные в кэш
        log_info("Pre-loading BTC data to cache...")
        await btc_cache.get_btc_ohlcv_1m(self.xt_client)
        await btc_cache.get_btc_ohlcv_1h(self.xt_client)
        await btc_cache.get_btc_ticker(self.xt_client)
        
        # Создаём все задачи
        all_tasks = []
        for pair in pairs:
            for timeframe in timeframes:
                all_tasks.append((pair, timeframe))
        
        # Обрабатываем батчами
        results = []
        signals_found = 0
        errors_count = 0
        
        for i in range(0, len(all_tasks), self.BATCH_SIZE):
            batch = all_tasks[i:i + self.BATCH_SIZE]
            batch_num = i // self.BATCH_SIZE + 1
            total_batches = (len(all_tasks) + self.BATCH_SIZE - 1) // self.BATCH_SIZE
            
            # Создаём корутины для батча
            batch_coroutines = [
                self._process_pair_timeframe(pair, tf) 
                for pair, tf in batch
            ]
            
            # Выполняем батч параллельно
            batch_results = await asyncio.gather(*batch_coroutines, return_exceptions=True)
            
            # Обрабатываем результаты батча
            for result in batch_results:
                if isinstance(result, Exception):
                    errors_count += 1
                    continue
                    
                if result and result.get('status') == 'signal':
                    signal = result['signal']
                    await self._save_and_send_signal(signal)
                    signals_found += 1
                elif result and result.get('status') == 'error':
                    errors_count += 1
            
            # Логируем прогресс каждые 5 батчей
            if batch_num % 5 == 0 or batch_num == total_batches:
                progress = (i + len(batch)) / len(all_tasks) * 100
                log_info(f"Progress: {progress:.1f}% ({i + len(batch)}/{len(all_tasks)})")
            
            # Небольшая пауза между батчами
            await asyncio.sleep(0.5)
        
        elapsed = time.time() - start_time
        log_info(f"Market analysis complete in {elapsed:.1f}s | Signals: {signals_found} | Errors: {errors_count}")
    
    async def _save_and_send_signal(self, signal: dict):
        """Сохранение сигнала в БД и отправка в Telegram"""
        db = SessionLocal()
        try:
            # Валидация уровней сигнала перед сохранением
            entry = signal.get('entry_price', 0)
            stop = signal.get('stop_loss', 0)
            tp1 = signal.get('take_profit_1', 0)
            tp2 = signal.get('take_profit_2', 0)
            tp3 = signal.get('take_profit_3', 0)
            
            # Проверка, что все уровни разные и валидные
            if entry <= 0 or stop <= 0 or tp1 <= 0 or tp2 <= 0 or tp3 <= 0:
                log_info(f"Invalid signal levels for {signal.get('ticker')}: entry={entry}, stop={stop}, tp1={tp1}")
                return
            
            # Проверка, что уровни разные
            if entry == stop or entry == tp1 or stop == tp1 or tp1 == tp2 or tp2 == tp3:
                log_info(f"Duplicate signal levels for {signal.get('ticker')}: all levels must be different")
                return
            
            # Проверка дубликатов
            recent_signal = db.query(Signal).filter(
                Signal.ticker == signal['ticker'],
                Signal.status.in_(['WAITING', 'IN_POSITION', 'TP1_HIT', 'TP2_HIT', 'TP3_HIT'])
            ).first()
            
            if recent_signal:
                log_info(f"Skipping {signal['ticker']}: active signal exists (ID: {recent_signal.signal_id}, Status: {recent_signal.status})")
                return
            
            # Сохранение в БД
            log_info(f"[SAVING] Saving signal {signal['ticker']} {signal['direction']} to database...")
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
                timeframe=signal['timeframe'],
                timeframe_higher=signal.get('timeframe_higher'),
                volume_24h=signal.get('volume_24h'),
                spread_percent=signal.get('spread_percent'),
                atr_value=signal.get('atr_value'),
                status='WAITING'
            )
            
            db.add(db_signal)
            db.commit()
            log_info(f"[SAVED] Signal {signal['ticker']} saved to database (ID: {db_signal.id})")
            
            # Record signal time for cooldown
            MarketFilters.record_signal_time(signal['ticker'])
            
            # Send to Telegram
            log_info(f"[SENDING] Sending signal {signal['ticker']} to Telegram channel...")
            send_result = await self.telegram_bot.send_signal(signal)
            
            if send_result:
                log_info(f"[SENT] Signal {signal['ticker']} successfully sent to Telegram channel")
                log_signal(signal)
            else:
                log_error(f"Failed to send signal {signal['ticker']} to Telegram channel", "send_signal")
            
        except Exception as e:
            log_error(str(e), f"saving signal {signal.get('ticker', 'unknown')}")
            import traceback
            log_error(traceback.format_exc(), f"traceback for {signal.get('ticker', 'unknown')}")
            db.rollback()
        finally:
            db.close()
                
    async def analyze_market(self):
        """
        Обёртка для обратной совместимости
        Вызывает параллельный анализ
        """
        await self.analyze_market_parallel()
    
    async def monitor_active_signals(self):
        """Мониторинг активных сигналов (WAITING + IN_POSITION)"""
        db = SessionLocal()
        
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
                    log_error(str(e), f"monitor signal {signal.signal_id}")
        
        finally:
            db.close()
    
    async def _check_waiting_signal(self, signal: Signal, current_price: float, db):
        """Проверка сигнала в ожидании: активация входа или отмена"""
        from analysis.signal_cancellation import SignalCancellation
        
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
            signal.status = 'CANCELLED'
            signal.cancellation_reason = cancel_reason
            signal.closed_at = datetime.utcnow()
            db.commit()
            log_info(f"Signal {signal.signal_id} cancelled: {cancel_reason}")
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
            signal.status = 'IN_POSITION'
            signal.activated_at = datetime.utcnow()
            db.commit()
            log_info(f"Entry activated {signal.signal_id} @ {current_price}")
    
    async def _check_position_levels(self, signal: Signal, current_price: float, db):
        """Проверка достижения TP и SL для позиции"""
        current_stop = signal.stop_loss_breakeven if signal.tp1_hit else signal.stop_loss
        
        if signal.direction == 'LONG':
            # Проверка SL
            if current_price <= current_stop:
                await self._close_on_stop(signal, current_price, db)
                return
            
            # Проверка TP4 (последний)
            if not signal.tp4_hit and current_price >= signal.take_profit_4:
                await self._hit_tp(signal, 4, current_price, db)
                signal.status = 'CLOSED_FULL_TP'
                signal.result = 'WIN'
                signal.closed_at = datetime.utcnow()
                db.commit()
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
        setattr(signal, f'tp{tp_number}_hit', True)
        signal.status = f'TP{tp_number}_HIT'
        db.commit()
        
        tps_hit = sum([signal.tp1_hit, signal.tp2_hit, signal.tp3_hit, signal.tp4_hit])
        remaining = 100 - (tps_hit * 25)
        
        log_info(f"TP{tp_number} reached {signal.signal_id} @ {price}, remaining: {remaining}%")
    
    async def _close_on_stop(self, signal: Signal, price: float, db):
        """Закрытие по стоп-лоссу"""
        signal.status = 'STOPPED_OUT'
        signal.result = 'LOSS' if not signal.tp1_hit else 'BREAKEVEN'
        signal.closed_at = datetime.utcnow()
        
        entry = signal.entry_price
        if signal.direction == 'LONG':
            pnl = ((price - entry) / entry) * 100
        else:
            pnl = ((entry - price) / entry) * 100
        
        signal.pnl_percent = pnl
        db.commit()
        
        log_info(f"Stop-loss {signal.signal_id} @ {price}, PnL: {pnl:.2f}%")
    
    async def _run_telegram_polling(self):
        """Запуск Telegram polling в фоне"""
        try:
            await self.telegram_bot.app.updater.start_polling(
                drop_pending_updates=True,
                allowed_updates=None,
                bootstrap_retries=-1
            )
            log_info("OK: Polling started successfully")
        except asyncio.CancelledError:
            log_info("Polling cancelled (normal shutdown)")
        except Exception as e:
            log_error(str(e), "Telegram polling")
            import traceback
            traceback.print_exc()
    
    async def run(self):
        """Основной цикл работы"""
        await self.initialize()
        
        self.is_running = True
        
        log_info("Bot running in main loop")
        
        # Счётчик циклов
        cycle_count = 0
        
        while self.is_running:
            try:
                # Мониторинг активных сигналов КАЖДЫЕ 5 СЕКУНД
                await self.monitor_active_signals()
                
                # Анализ рынка каждые 10 МИНУТ (120 циклов * 5 сек = 600 сек)
                if cycle_count % self.ANALYSIS_INTERVAL_CYCLES == 0:
                    await self.analyze_market_parallel()
                
                # Автоматическое обновление топ монет КАЖДЫЙ ЧАС (720 циклов * 5 сек = 3600 сек)
                if cycle_count % self.TOP_COINS_UPDATE_CYCLES == 0 and cycle_count > 0:
                    log_info("🔄 Auto-updating top coins list...")
                    success = await update_trading_pairs_auto(limit=100)
                    if success:
                        pairs = ConfigManager.get_trading_pairs()
                        log_info(f"✅ Top coins updated: {len(pairs)} pairs")
                    log_filter_summary()
                
                # Очистка старых сигналов РАЗ В СУТКИ (17280 циклов * 5 сек = 86400 сек)
                if cycle_count % self.DB_CLEANUP_CYCLES == 0 and cycle_count > 0:
                    log_info("🗑️ Running scheduled database cleanup...")
                    await run_scheduled_cleanup()
                
                cycle_count += 1
                
                # Пауза между циклами
                await asyncio.sleep(5)
                
            except KeyboardInterrupt:
                log_info("Shutdown signal received")
                break
            except Exception as e:
                log_error(str(e), "main loop")
                await asyncio.sleep(60)
        
        log_info("Bot stopped")
        
        # Остановка Telegram бота
        await self.telegram_bot.app.updater.stop()
        await self.telegram_bot.app.stop()
        await self.telegram_bot.app.shutdown()
        
        self.xt_client.close()


async def main():
    """Точка входа"""
    bot = CryptoSignalBot()
    await bot.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
