import asyncio
from datetime import datetime
from typing import Optional
from exchange.xt_client import XTClient
from analysis.signal_generator import SignalGenerator
from analysis.market_filters import MarketFilters
from telegram_bot.bot import TelegramBot
from utils.deepseek_client import get_deepseek_client
from utils.chart import render_signal_chart
from database.models import init_db, Signal, SessionLocal
from database.config_manager import ConfigManager
from utils.logger import logger, log_signal, log_error, log_info, log_warning, log_filter_summary
from utils.cache import btc_cache, api_rate_limiter
from utils.top_coins import TopCoinsService, update_trading_pairs_auto
from utils.db_cleanup import DatabaseCleanup, run_scheduled_cleanup
from telegram_bot.filter_panel import FilterSettings
import config
import time


class CryptoSignalBot:
    """Главный класс бота с поддержкой автоматического топ-200 монет"""
    
    # Настройки параллельной обработки
    BATCH_SIZE = 40  # Размер батча для параллельной обработки
    MAX_CONCURRENT_TASKS = 30  # Максимум одновременных задач
    ANALYSIS_INTERVAL_CYCLES = 24  # Интервал анализа (24 цикла * 5 сек = 2 минуты)
    TOP_COINS_UPDATE_CYCLES = 720  # Обновление топ монет каждый час (720 * 5 сек = 3600 сек)
    DB_CLEANUP_CYCLES = 17280  # Очистка БД раз в сутки (17280 * 5 сек = 86400 сек)
    
    def __init__(self):
        self.xt_client = XTClient()
        self.telegram_bot = TelegramBot()
        self.deepseek = get_deepseek_client()
        self.is_running = False
        self.polling_task = None
        self._semaphore = None  # Будет создан в async контексте
        
    async def initialize(self):
        """Инициализация бота"""
        log_info("Initializing bot...")
        
        # Инициализация БД
        init_db()
        log_info("Database initialized")
        
        # Запуск Telegram бота (polling)
        log_info("Initializing Telegram bot...")
        
        # Удаляем webhook если есть
        try:
            await self.telegram_bot.app.bot.delete_webhook(drop_pending_updates=True)
            log_info("Webhook deleted")
        except Exception as e:
            log_info(f"Webhook check: {e}")
        
        # Инициализируем и запускаем Application
        await self.telegram_bot.app.initialize()
        await self.telegram_bot.app.start()
        log_info("Telegram bot app started")
        
        # Запускаем polling в отдельной задаче (блокирующий вызов)
        # В v21+ start_polling запускает polling и работает в фоне
        self.polling_task = asyncio.create_task(self._run_telegram_polling())
        await asyncio.sleep(3)  # Даем время на запуск polling
        log_info("✅ Telegram bot polling task started")
        
        # Загрузка настроек из БД и применение к фильтрам
        FilterSettings.get_all(force_reload=True)  # Принудительно загружает из БД
        FilterSettings._apply_to_filters()  # Применяет настройки к классам фильтров
        log_info("✅ Filter settings loaded from DB and applied to all filter classes")
        
        # Автоматическое обновление торговых пар на топ-N (из настроек)
        from analysis.market_filters import MarketFilters
        top_coins_limit = MarketFilters.TOP_COINS_LIMIT
        log_info(f"Fetching top {top_coins_limit} coins on XT by volume (USDT)...")
        success = await update_trading_pairs_auto(limit=top_coins_limit)
        if success:
            log_info(f"✅ Trading pairs auto-updated to top {top_coins_limit} coins")
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
        # Создаем semaphore если еще не создан (для Python 3.7 совместимости)
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_TASKS)
        
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
                    log_info(f"[✅ SIGNAL GENERATED] {pair} {timeframe} {signal.get('direction')} - Entry: {signal.get('entry_price')}, Stop: {signal.get('stop_loss')}")
                    log_info(f"[✅ SIGNAL WILL BE SENT] {pair} {timeframe} - Signal passed all filters, will be saved and sent to Telegram channel")
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
        # Создаем semaphore если еще не создан (для Python 3.7 совместимости)
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_TASKS)
        
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
            for idx, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    errors_count += 1
                    pair, tf = batch[idx] if idx < len(batch) else ("unknown", "unknown")
                    log_error(f"Exception in {pair} {tf}: {str(result)}", "analyze_market_parallel")
                    continue
                    
                # Логируем только сигналы, остальное засоряет логи
                if result and result.get('status') == 'signal':
                    signal = result['signal']
                    log_info(f"✅ Signal found: {signal.get('ticker')} {signal.get('timeframe')} - processing...")
                    try:
                        await self._save_and_send_signal(signal)
                        signals_found += 1
                    except Exception as save_error:
                        log_error(f"Error in _save_and_send_signal for {signal.get('ticker')}: {str(save_error)}", "save_signal")
                elif result and result.get('status') == 'error':
                    errors_count += 1
                    pair = result.get('pair', 'unknown')
                    tf = result.get('timeframe', 'unknown')
                    error_msg = result.get('error', 'Unknown error')
                    # Логируем только первые 10 ошибок каждого типа, чтобы не засорять логи
                    if errors_count <= 10 or errors_count % 50 == 0:
                        log_error(f"Error in {pair} {tf}: {error_msg}", "analyze_market_parallel")
            
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
        ticker = signal.get('ticker', 'UNKNOWN')
        log_info(f"[DEBUG] _save_and_send_signal called for {ticker}")
        try:
            db = SessionLocal()
            log_info(f"[DEBUG] DB session created for {ticker}")
            # Валидация уровней сигнала перед сохранением
            entry = signal.get('entry_price', 0)
            stop = signal.get('stop_loss', 0)
            tp1 = signal.get('take_profit_1', 0)
            tp2 = signal.get('take_profit_2', 0)
            tp3 = signal.get('take_profit_3', 0)
            
            log_info(f"[DEBUG] Validating {ticker}: entry={entry}, stop={stop}, tp1={tp1}, tp2={tp2}, tp3={tp3}")
            
            # Проверка, что все уровни разные и валидные
            if entry <= 0 or stop <= 0 or tp1 <= 0 or tp2 <= 0 or tp3 <= 0:
                log_info(f"[BLOCKED] Invalid signal levels for {ticker}: entry={entry}, stop={stop}, tp1={tp1}")
                return
            
            # Проверка, что основные уровни разные (tp2==tp3 допускается)
            if entry == stop or entry == tp1 or stop == tp1 or tp1 == tp2:
                log_info(f"Duplicate signal levels for {signal.get('ticker')}: critical levels must be different")
                return
            
            # Проверка дубликатов
            log_info(f"[DEBUG] Checking duplicates for {ticker}...")
            recent_signal = db.query(Signal).filter(
                Signal.ticker == signal['ticker'],
                Signal.status.in_(['WAITING', 'IN_POSITION'])
            ).first()
            
            if recent_signal:
                log_info(f"[BLOCKED] Skipping {ticker}: active signal exists (ID: {recent_signal.signal_id}, Status: {recent_signal.status})")
                return
            
            log_info(f"[DEBUG] No duplicates for {ticker}, proceeding to save...")

            # DeepSeek анализ перед сохранением/отправкой
            log_info(f"[DEEPSEEK] Sending {ticker} to DeepSeek for validation...")
            ds_result = await self.deepseek.analyze_signal(signal)
            signal['deepseek'] = ds_result

            if not ds_result.get('approved'):
                reason = (ds_result.get('plan') or {}).get('reason') or ds_result.get('error') or 'Rejected'
                log_info(f"[DEEPSEEK] ❌ Rejected {ticker}: {reason}")
                try:
                    await self.telegram_bot.send_rejected_message(f"🤖 DeepSeek rejected {ticker}: {reason}")
                except Exception:
                    pass
                return

            # Пытаемся построить график по плану DeepSeek
            plan = ds_result.get('plan') if isinstance(ds_result, dict) else None
            chart_path = await self._render_chart(signal, plan)
            if chart_path:
                signal['chart_path'] = chart_path
                            
            # Сохранение в БД
            log_info(f"[SAVING] Saving signal {signal['ticker']} {signal['direction']} to database...")
            try:
                log_info(f"[SAVING] Creating Signal object for {signal['ticker']}...")
                db_signal = Signal(
                    signal_id=signal['signal_id'],
                    ticker=signal['ticker'],
                    direction=signal['direction'],
                    entry_price=signal['entry_price'],
                    stop_loss=signal['stop_loss'],
                    take_profit_1=signal['take_profit_1'],
                    take_profit_2=signal['take_profit_2'],
                    take_profit_3=signal['take_profit_3'],
                    take_profit_4=signal.get('take_profit_4', signal['take_profit_3']),  # Use TP3 if TP4 not provided
                    risk_percent=signal['risk_percent'],
                    leverage=signal['leverage'],
                    ai_score=0,  # Set default value for deprecated field
                    timeframe=signal['timeframe'],
                    timeframe_higher=signal.get('timeframe_higher'),
                    volume_24h=signal.get('volume_24h'),
                    spread_percent=signal.get('spread_percent'),
                    atr_value=signal.get('atr_value'),
                    status='WAITING'
                )
                
                log_info(f"[SAVING] Adding signal {signal['ticker']} to session...")
                db.add(db_signal)
                
                log_info(f"[SAVING] Committing signal {signal['ticker']} to database...")
                db.commit()
                log_info(f"[SAVED] Signal {signal['ticker']} saved to database.")
                
                # Record signal time for cooldown
                MarketFilters.record_signal_time(signal['ticker'])
                
                # Send to Telegram
                log_info(f"[TELEGRAM] Sending signal {signal['ticker']} to Telegram channel...")
                send_result = await self.telegram_bot.send_signal(signal)
                if send_result:
                    log_info(f"[TELEGRAM] ✅ Signal {signal['ticker']} successfully sent to channel!")
                else:
                    log_warning(f"[TELEGRAM] ⚠️ Signal {signal['ticker']} NOT sent to channel (send_signal returned False)")
                
                log_signal(signal)
            except Exception as db_error:
                log_error(f"Database error saving {signal['ticker']}: {str(db_error)}", "save_signal_db")
                db.rollback()
                raise
                            
        except Exception as e:
            log_error(str(e), f"saving signal {signal.get('ticker', 'unknown')}")
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
                    
                    if not ticker or 'last' not in ticker:
                        continue
                    
                    current_price = ticker.get('last', 0)
                    if current_price <= 0:
                        continue
                    
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
        
        if df is None or df.empty:
            log_error(f"Cannot get OHLCV data for {signal.ticker} {signal.timeframe} - skipping cancellation check", "check_waiting_signal")
            return
        
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
            try:
                signal.status = 'CANCELLED'
                signal.cancellation_reason = cancel_reason
                signal.closed_at = datetime.utcnow()
                db.commit()
                log_info(f"Signal {signal.signal_id} cancelled: {cancel_reason}")
            except Exception as e:
                log_error(f"Error cancelling signal {signal.signal_id}: {str(e)}", "check_waiting_signal")
                db.rollback()
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
            try:
                signal.status = 'IN_POSITION'
                signal.activated_at = datetime.utcnow()
                db.commit()
                log_info(f"Entry activated {signal.signal_id} @ {current_price}")
            except Exception as e:
                log_error(f"Error activating entry for signal {signal.signal_id}: {str(e)}", "check_waiting_signal")
                db.rollback()

    async def _render_chart(self, signal: dict, plan: dict) -> Optional[str]:
        """Строит график с уровнями для публикации"""
        try:
            df = await self.xt_client.get_ohlcv(signal['ticker'], signal['timeframe'], limit=200)
            if df is None or df.empty:
                return None
            return render_signal_chart(df, signal, plan)
        except Exception as e:
            log_warning(f"Chart render failed for {signal.get('ticker')}: {e}")
            return None
    
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
                try:
                    signal.stop_loss_breakeven = signal.entry_price
                    db.commit()
                except Exception as e:
                    log_error(f"Error setting breakeven for signal {signal.signal_id}: {str(e)}", "check_position_levels")
                    db.rollback()
                return
        
        else:  # SHORT - зеркально
            if current_price >= current_stop:
                await self._close_on_stop(signal, current_price, db)
                return
            
            if not signal.tp4_hit and current_price <= signal.take_profit_4:
                await self._hit_tp(signal, 4, current_price, db)
                try:
                    signal.status = 'CLOSED_FULL_TP'
                    signal.result = 'WIN'
                    signal.closed_at = datetime.utcnow()
                    db.commit()
                except Exception as e:
                    log_error(f"Error closing TP4 for signal {signal.signal_id}: {str(e)}", "check_position_levels")
                    db.rollback()
                return
            
            if not signal.tp3_hit and current_price <= signal.take_profit_3:
                await self._hit_tp(signal, 3, current_price, db)
                return
            
            if not signal.tp2_hit and current_price <= signal.take_profit_2:
                await self._hit_tp(signal, 2, current_price, db)
                return
            
            if not signal.tp1_hit and current_price <= signal.take_profit_1:
                await self._hit_tp(signal, 1, current_price, db)
                try:
                    signal.stop_loss_breakeven = signal.entry_price
                    db.commit()
                except Exception as e:
                    log_error(f"Error setting breakeven for signal {signal.signal_id}: {str(e)}", "check_position_levels")
                    db.rollback()
                return
    
    async def _hit_tp(self, signal: Signal, tp_number: int, price: float, db):
        """Обработка достижения TP"""
        try:
            setattr(signal, f'tp{tp_number}_hit', True)
            signal.status = f'TP{tp_number}_HIT'
            db.commit()
            
            tps_hit = sum([signal.tp1_hit, signal.tp2_hit, signal.tp3_hit, signal.tp4_hit])
            remaining = 100 - (tps_hit * 25)
            
            log_info(f"TP{tp_number} reached {signal.signal_id} @ {price}, remaining: {remaining}%")
        except Exception as e:
            log_error(f"Error hitting TP{tp_number} for signal {signal.signal_id}: {str(e)}", "hit_tp")
            db.rollback()
    
    async def _close_on_stop(self, signal: Signal, price: float, db):
        """Закрытие по стоп-лоссу"""
        try:
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
        except Exception as e:
            log_error(f"Error closing stop for signal {signal.signal_id}: {str(e)}", "close_on_stop")
            db.rollback()
    
    async def _run_telegram_polling(self):
        """Запуск Telegram polling в фоне"""
        try:
            log_info("Starting Telegram polling...")
            
            # Удаляем webhook перед polling
            try:
                await self.telegram_bot.app.bot.delete_webhook(drop_pending_updates=True)
                log_info("Webhook deleted before polling")
            except Exception as e:
                log_info(f"Webhook check: {e}")
            
            # Запускаем polling - обновления обрабатываются автоматически через Application
            await self.telegram_bot.app.updater.start_polling(
                drop_pending_updates=True,
                allowed_updates=None,
                bootstrap_retries=-1
            )
            log_info("✅ Telegram polling started successfully - waiting for updates...")
            
            # Держим задачу активной - polling работает автоматически
            # Application обрабатывает обновления через зарегистрированные обработчики
            # Проверяем, что Application запущен и готов обрабатывать обновления
            while self.is_running:
                # Проверяем статус polling
                if self.telegram_bot.app.updater.running:
                    await asyncio.sleep(1)
                else:
                    log_error("Polling stopped unexpectedly!", "Telegram polling")
                    break
                    
        except asyncio.CancelledError:
            log_info("Polling cancelled (normal shutdown)")
        except Exception as e:
            log_error(f"Error in Telegram polling: {str(e)}", "Telegram polling")
            import traceback
            log_error(f"Traceback: {traceback.format_exc()}", "Telegram polling")
        finally:
            # Останавливаем polling при выходе
            try:
                if self.telegram_bot.app.updater.running:
                    await self.telegram_bot.app.updater.stop()
                    log_info("Polling stopped")
            except Exception as e:
                log_info(f"Error stopping polling: {e}")
    
    async def run(self):
        """Основной цикл работы"""
        self.is_running = True  # Устанавливаем ПЕРЕД initialize
        await self.initialize()
        
        log_info("Bot running in main loop")
        
        # Счётчик циклов
        cycle_count = 0
        last_analysis_time = 0  # Время последнего запуска анализа
        
        while self.is_running:
            try:
                # Мониторинг активных сигналов КАЖДЫЕ 5 СЕКУНД
                await self.monitor_active_signals()
                
                # Анализ рынка каждые 2 МИНУТЫ (24 цикла * 5 сек = 120 сек)
                # Проверяем по времени, а не по cycle_count, чтобы не пропускать запуски
                current_time = time.time()
                time_since_last_analysis = current_time - last_analysis_time
                
                if time_since_last_analysis >= (self.ANALYSIS_INTERVAL_CYCLES * 5):
                    last_analysis_time = current_time
                    await self.analyze_market_parallel()
                
                # Автоматическое обновление топ монет КАЖДЫЙ ЧАС (720 циклов * 5 сек = 3600 сек)
                if cycle_count % self.TOP_COINS_UPDATE_CYCLES == 0 and cycle_count > 0:
                    log_info("🔄 Auto-updating top coins list...")
                    # Используем значение из настроек фильтров
                    from analysis.market_filters import MarketFilters
                    top_coins_limit = MarketFilters.TOP_COINS_LIMIT
                    success = await update_trading_pairs_auto(limit=top_coins_limit)
                    if success:
                        pairs = ConfigManager.get_trading_pairs()
                        log_info(f"✅ Top coins updated: {len(pairs)} pairs (limit: {top_coins_limit})")
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
        if self.polling_task:
            self.polling_task.cancel()
        try:
            # Останавливаем Application (это остановит polling)
            await self.telegram_bot.app.stop()
            await self.telegram_bot.app.shutdown()
        except Exception as e:
            log_error(f"Error stopping Telegram bot: {str(e)}", "shutdown")
        
        self.xt_client.close()


async def main():
    """Точка входа"""
    import sys
    
    # Проверка версии Python
    if sys.version_info < (3, 8):
        print("❌ Требуется Python 3.8 или выше")
        sys.exit(1)
    
    if sys.version_info >= (3, 14):
        print("⚠️ Python 3.14+ не протестирован. Рекомендуется Python 3.8-3.13")
    
    bot = CryptoSignalBot()
    await bot.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
