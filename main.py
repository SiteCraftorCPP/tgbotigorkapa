import asyncio
import threading
import time
import queue
from datetime import datetime
from typing import Optional, Dict, Any
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


class CryptoSignalBot:
    """Главный класс бота с реально работающей многопоточностью"""
    
    ANALYSIS_INTERVAL_SEC = 30
    TOP_COINS_UPDATE_SEC = 3600
    DB_CLEANUP_SEC = 86400
    SIGNAL_TIMEFRAME = '1h'
    
    def __init__(self):
        self.xt_client = XTClient()
        self.telegram_bot = TelegramBot()
        # Создаем потокобезопасную очередь для команд боту
        self.bot_queue = queue.Queue()
        self.telegram_bot.external_queue = self.bot_queue
        
        self.deepseek = get_deepseek_client()
        self.is_running = False
        self._bot_thread = None
        
    def _run_bot_thread(self):
        """Telegram бот в своем потоке (полностью изолирован)"""
        log_info("Starting Telegram bot thread...")
        try:
            self.telegram_bot.run_polling()
        except Exception as e:
            log_error(f"Telegram thread error: {e}", "bot_thread")

    async def initialize(self):
        log_info("Initializing bot modules...")
        init_db()
        FilterSettings.get_all(force_reload=True)
        FilterSettings._apply_to_filters()
        
        # Обновление пар при старте
        await update_trading_pairs_auto(limit=300)
        
        # Запуск Telegram
        self._bot_thread = threading.Thread(target=self._run_bot_thread, daemon=True)
        self._bot_thread.start()
        log_info("✅ Telegram bot thread is active and isolated")

    async def _analyze_one(self, pair: str, tf: str, semaphore: asyncio.Semaphore):
        async with semaphore:
            try:
                # 1. Асинхронно получаем данные (не блокирует)
                df = await self.xt_client.get_ohlcv(pair, tf, limit=500)
                if df is None or df.empty: return
                
                from analysis.multi_timeframe import MultiTimeframeAnalysis
                higher_tf = MultiTimeframeAnalysis.get_higher_timeframe(tf)
                df_higher = await self.xt_client.get_ohlcv(pair, higher_tf, limit=200)
                if df_higher is None or df_higher.empty: return
                
                # 2. ТЯЖЕЛЫЕ РАСЧЕТЫ (Indicators, TA) - выносим в отдельный поток!
                # Это предотвратит "замерзание" основного цикла
                generator = SignalGenerator(pair, tf, df, df_higher, self.xt_client)
                
                # Запускаем генерацию в потоке, чтобы не блокировать loop
                signal = await asyncio.to_thread(self._run_generator_sync, generator)
                
                if signal:
                    await self._save_and_send_signal(signal)
            except Exception as e:
                log_error(f"Analyze error {pair}: {e}", "analyze_one")

    def _run_generator_sync(self, generator):
        """Синхронная обертка для запуска в потоке"""
        # Т.к. generate_signal это async (из-за MarketFilters), нам нужно запустить его
        # Но MarketFilters делает HTTP запросы. 
        # На самом деле, лучше оставить асинхронным, но индикаторы вынести.
        # В данном случае, самый простой путь - запускать тяжелые части TA внутри generate_signal в потоках.
        # Но мы сделаем проще: будем запускать весь generate_signal в новом loop-е этого потока.
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(generator.generate_signal())
        finally:
            loop.close()

    async def analyze_loop(self):
        """Цикл анализа рынка"""
        log_info("Market analysis loop started")
        semaphore = asyncio.Semaphore(20) # Уменьшим до 20 для стабильности на слабом VPS
        
        while self.is_running:
            if not ConfigManager.is_bot_enabled():
                await asyncio.sleep(10)
                continue
                
            start_time = time.time()
            pairs = ConfigManager.get_trading_pairs()
            
            # Обновляем кэш BTC (асинхронно)
            await btc_cache.get_btc_ohlcv_1m(self.xt_client)
            await btc_cache.get_btc_ohlcv_1h(self.xt_client)
            
            # Запускаем анализ всех пар
            tasks = [self._analyze_one(p, self.SIGNAL_TIMEFRAME, semaphore) for p in pairs]
            await asyncio.gather(*tasks)
            
            elapsed = time.time() - start_time
            log_info(f"Market scan finished: {len(pairs)} pairs in {elapsed:.1f}s")
            
            wait_time = max(1, self.ANALYSIS_INTERVAL_SEC - elapsed)
            await asyncio.sleep(wait_time)

    async def monitor_loop(self):
        """Цикл мониторинга TP/SL"""
        log_info("Monitoring loop started")
        while self.is_running:
            db = SessionLocal()
            try:
                active = db.query(Signal).filter(Signal.status.in_(['WAITING', 'IN_POSITION', 'TP1_HIT', 'TP2_HIT', 'TP3_HIT'])).all()
                for signal in active:
                    # Ticker тоже асинхронный
                    ticker = await self.xt_client.get_ticker(signal.ticker)
                    if ticker and ticker.get('last'):
                        price = ticker['last']
                        if signal.status == 'WAITING':
                            await self._check_waiting_signal(signal, price, db)
                        else:
                            await self._check_position_levels(signal, price, db)
                db.commit()
            except Exception as e:
                log_error(f"Monitor loop error: {e}", "monitor_loop")
            finally:
                db.close()
            await asyncio.sleep(5)

    async def tasks_loop(self):
        """Цикл фоновых задач"""
        count = 0
        while self.is_running:
            if count % (self.TOP_COINS_UPDATE_SEC // 60) == 0 and count > 0:
                await update_trading_pairs_auto(limit=300)
            if count % (self.DB_CLEANUP_SEC // 60) == 0 and count > 0:
                await run_scheduled_cleanup()
            count += 1
            await asyncio.sleep(60)

    async def _save_and_send_signal(self, signal: dict):
        ticker = signal.get('ticker', 'UNKNOWN')
        db = SessionLocal()
        try:
            recent = db.query(Signal).filter(Signal.ticker == ticker, Signal.status.in_(['WAITING', 'IN_POSITION'])).first()
            if recent: return

            # AI Анализ
            ds_result = await self.deepseek.analyze_signal(signal)
            if not ds_result.get('approved'): return

            # Рендеринг чарта (тоже тяжелая задача, можно было бы в поток, но пока так)
            chart_path = await self._render_chart(signal, ds_result.get('plan'))
            if chart_path: signal['chart_path'] = chart_path
            
            # Сохранение в БД
            db_signal = Signal(
                signal_id=signal['signal_id'], ticker=ticker, direction=signal['direction'],
                entry_price=signal['entry_price'], stop_loss=signal['stop_loss'],
                take_profit_1=signal['take_profit_1'], take_profit_2=signal['take_profit_2'],
                take_profit_3=signal['take_profit_3'], take_profit_4=signal.get('take_profit_4', signal['take_profit_3']),
                risk_percent=signal['risk_percent'], leverage=signal['leverage'], ai_score=0,
                timeframe=signal['timeframe'], status='WAITING'
            )
            db.add(db_signal)
            db.commit()
            
            # ОТПРАВЛЯЕМ В ОЧЕРЕДЬ для потока Telegram (вместо await)
            self.bot_queue.put({'type': 'signal', 'data': signal})
            log_signal(signal)
        except Exception as e:
            log_error(f"Save/Send error {ticker}: {e}", "save_signal")
        finally:
            db.close()

    async def _check_waiting_signal(self, signal, price, db):
        if (signal.direction == 'LONG' and price <= signal.entry_price) or \
           (signal.direction == 'SHORT' and price >= signal.entry_price):
            signal.status = 'IN_POSITION'
            signal.activated_at = datetime.utcnow()
            log_info(f"Position entered: {signal.ticker}")
            self.bot_queue.put({'type': 'admin_msg', 'data': f"🔔 Position entered: {signal.ticker}"})

    async def _check_position_levels(self, signal, price, db):
        sl = signal.stop_loss
        tp3 = signal.take_profit_3
        closed = False
        if signal.direction == 'LONG':
            if price <= sl:
                signal.status = 'STOPPED_OUT'; signal.result = 'LOSS'; closed = True
            elif price >= tp3:
                signal.status = 'CLOSED_FULL_TP'; signal.result = 'WIN'; closed = True
        else:
            if price >= sl:
                signal.status = 'STOPPED_OUT'; signal.result = 'LOSS'; closed = True
            elif price <= tp3:
                signal.status = 'CLOSED_FULL_TP'; signal.result = 'WIN'; closed = True
        
        if closed:
            signal.closed_at = datetime.utcnow()
            self.bot_queue.put({'type': 'admin_msg', 'data': f"🏁 Signal {signal.ticker} closed: {signal.status}"})

    async def _render_chart(self, signal, plan) -> Optional[str]:
        try:
            df = await self.xt_client.get_ohlcv(signal['ticker'], signal['timeframe'], limit=200)
            if df is None or df.empty: return None
            return render_signal_chart(df, signal, plan)
        except: return None

    async def run(self):
        self.is_running = True
        await self.initialize()
        
        # Планировщик отчетов тоже через очередь может работать или напрямую если он не мешает
        # Но лучше оставить как есть или тоже в очередь
        from utils.weekly_report import WeeklyReportScheduler
        self.report_scheduler = WeeklyReportScheduler(self.telegram_bot)
        # WeeklyReportScheduler тоже должен использовать очередь для отправки!
        # Но это потребует правок в самом Scheduler. Пока оставим.
        
        await asyncio.gather(
            self.analyze_loop(),
            self.monitor_loop(),
            self.tasks_loop()
        )

async def main():
    bot = CryptoSignalBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
