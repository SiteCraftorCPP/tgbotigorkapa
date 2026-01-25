import asyncio
import threading
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
import time


class CryptoSignalBot:
    """Главный класс бота с поддержкой многопоточности для Telegram"""
    
    BATCH_SIZE = 50
    MAX_CONCURRENT_TASKS = 40
    ANALYSIS_INTERVAL_CYCLES = 6
    TOP_COINS_UPDATE_CYCLES = 720
    DB_CLEANUP_CYCLES = 17280
    SIGNAL_TIMEFRAME = '1h'
    
    def __init__(self):
        self.xt_client = XTClient()
        self.telegram_bot = TelegramBot()
        self.deepseek = get_deepseek_client()
        self.is_running = False
        self._semaphore = None
        self._bot_thread = None
        
    def _run_bot_thread(self):
        """Запуск Telegram бота в отдельном потоке со своим loop-ом"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        log_info("Starting Telegram bot in a separate thread...")
        try:
            # Инициализация и запуск polling (блокирует поток)
            self.telegram_bot.app.run_polling(drop_pending_updates=True)
        except Exception as e:
            log_error(f"Telegram bot thread error: {e}", "bot_thread")
        finally:
            loop.close()

    async def initialize(self):
        """Инициализация бота"""
        log_info("Initializing bot...")
        init_db()
        
        # Загрузка настроек
        FilterSettings.get_all(force_reload=True)
        FilterSettings._apply_to_filters()
        
        # Запуск планировщика отчётов в основном цикле
        from utils.weekly_report import WeeklyReportScheduler
        self.report_scheduler = WeeklyReportScheduler(self.telegram_bot)
        asyncio.create_task(self.report_scheduler.start())
        
        # Обновление пар
        from analysis.market_filters import MarketFilters
        top_coins_limit = MarketFilters.TOP_COINS_LIMIT
        await update_trading_pairs_auto(limit=top_coins_limit)
        
        # Запуск Telegram бота в ОТДЕЛЬНОМ ПОТОКЕ
        self._bot_thread = threading.Thread(target=self._run_bot_thread, daemon=True)
        self._bot_thread.start()
        log_info("✅ Telegram bot started in separate thread")
        
        log_info("Initialization complete")
    
    async def _process_pair_timeframe(self, pair: str, timeframe: str) -> dict:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_TASKS)
        
        async with self._semaphore:
            try:
                async with api_rate_limiter:
                    df = await self.xt_client.get_ohlcv(pair, timeframe, limit=500)
                
                if df is None or df.empty:
                    return {'pair': pair, 'timeframe': timeframe, 'status': 'no_data'}
                
                from analysis.multi_timeframe import MultiTimeframeAnalysis
                higher_tf = MultiTimeframeAnalysis.get_higher_timeframe(timeframe)
                
                async with api_rate_limiter:
                    df_higher = await self.xt_client.get_ohlcv(pair, higher_tf, limit=200)
                
                if df_higher is None or df_higher.empty:
                    return {'pair': pair, 'timeframe': timeframe, 'status': 'no_higher_data'}
                
                generator = SignalGenerator(pair, timeframe, df, df_higher, self.xt_client)
                signal = await generator.generate_signal()
                
                if signal:
                    return {'pair': pair, 'timeframe': timeframe, 'status': 'signal', 'signal': signal}
                
                return {'pair': pair, 'timeframe': timeframe, 'status': 'no_signal'}
            except Exception as e:
                return {'pair': pair, 'timeframe': timeframe, 'status': 'error', 'error': str(e)}
    
    async def analyze_market_parallel(self):
        if not ConfigManager.is_bot_enabled():
            return
        
        pairs = ConfigManager.get_trading_pairs()
        timeframe = self.SIGNAL_TIMEFRAME
        log_info(f"Starting market analysis: {len(pairs)} pairs")
        
        start_time = time.time()
        await btc_cache.get_btc_ohlcv_1m(self.xt_client)
        await btc_cache.get_btc_ohlcv_1h(self.xt_client)
        
        all_tasks = [(pair, timeframe) for pair in pairs]
        signals_found = 0
        
        for i in range(0, len(all_tasks), self.BATCH_SIZE):
            batch = all_tasks[i:i + self.BATCH_SIZE]
            batch_coroutines = [self._process_pair_timeframe(p, tf) for p, tf in batch]
            batch_results = await asyncio.gather(*batch_coroutines, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, dict) and result.get('status') == 'signal':
                    await self._save_and_send_signal(result['signal'])
                    signals_found += 1
            
            await asyncio.sleep(0.1) # Минимальная задержка чтобы не вешать цикл
        
        elapsed = time.time() - start_time
        log_info(f"Analysis complete: {elapsed:.1f}s | Signals: {signals_found}")
    
    async def _save_and_send_signal(self, signal: dict):
        ticker = signal.get('ticker', 'UNKNOWN')
        db = SessionLocal()
        try:
            # Проверка дубликатов
            recent = db.query(Signal).filter(Signal.ticker == ticker, Signal.status.in_(['WAITING', 'IN_POSITION'])).first()
            if recent: return

            # DeepSeek
            ds_result = await self.deepseek.analyze_signal(signal)
            signal['deepseek'] = ds_result
            if not ds_result.get('approved'): return

            # Chart
            chart_path = await self._render_chart(signal, ds_result.get('plan'))
            if chart_path: signal['chart_path'] = chart_path
                            
            # Save
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
            
            # Send (используем бот-объект напрямую для отправки из основного потока)
            await self.telegram_bot.send_signal(signal)
            log_signal(signal)
        except Exception as e:
            log_error(f"Save/Send error for {ticker}: {e}", "save_signal")
            db.rollback()
        finally:
            db.close()

    async def monitor_active_signals(self):
        db = SessionLocal()
        try:
            active_signals = db.query(Signal).filter(Signal.status.in_(['WAITING', 'IN_POSITION', 'TP1_HIT', 'TP2_HIT', 'TP3_HIT'])).all()
            for signal in active_signals:
                ticker_data = await self.xt_client.get_ticker(signal.ticker)
                if ticker_data and ticker_data.get('last'):
                    price = ticker_data['last']
                    if signal.status == 'WAITING':
                        await self._check_waiting_signal(signal, price, db)
                    else:
                        await self._check_position_levels(signal, price, db)
        finally:
            db.close()

    async def _check_waiting_signal(self, signal, price, db):
        # Активация входа
        entry = False
        if signal.direction == 'LONG' and price <= signal.entry_price: entry = True
        elif signal.direction == 'SHORT' and price >= signal.entry_price: entry = True
        
        if entry:
            signal.status = 'IN_POSITION'
            signal.activated_at = datetime.utcnow()
            db.commit()
            log_info(f"Entry activated: {signal.ticker}")

    async def _check_position_levels(self, signal, price, db):
        # Упрощенная логика TP/SL
        sl = signal.stop_loss
        if signal.direction == 'LONG':
            if price <= sl:
                signal.status = 'STOPPED_OUT'
                signal.result = 'LOSS'
                signal.closed_at = datetime.utcnow()
                db.commit()
            elif price >= signal.take_profit_3:
                signal.status = 'CLOSED_FULL_TP'
                signal.result = 'WIN'
                signal.closed_at = datetime.utcnow()
                db.commit()
        else:
            if price >= sl:
                signal.status = 'STOPPED_OUT'
                signal.result = 'LOSS'
                signal.closed_at = datetime.utcnow()
                db.commit()
            elif price <= signal.take_profit_3:
                signal.status = 'CLOSED_FULL_TP'
                signal.result = 'WIN'
                signal.closed_at = datetime.utcnow()
                db.commit()

    async def _render_chart(self, signal, plan) -> Optional[str]:
        try:
            df = await self.xt_client.get_ohlcv(signal['ticker'], signal['timeframe'], limit=200)
            if df is None or df.empty: return None
            return render_signal_chart(df, signal, plan)
        except: return None

    async def run(self):
        """Основной цикл (анализ рынка)"""
        self.is_running = True
        await self.initialize()
        
        cycle_count = 0
        last_analysis_time = 0
        
        while self.is_running:
            try:
                await self.monitor_active_signals()
                
                curr = time.time()
                if curr - last_analysis_time >= (self.ANALYSIS_INTERVAL_CYCLES * 5):
                    last_analysis_time = curr
                    await self.analyze_market_parallel()
                
                if cycle_count % self.TOP_COINS_UPDATE_CYCLES == 0 and cycle_count > 0:
                    await update_trading_pairs_auto()
                
                if cycle_count % self.DB_CLEANUP_CYCLES == 0 and cycle_count > 0:
                    await run_scheduled_cleanup()
                
                cycle_count += 1
                await asyncio.sleep(5)
            except KeyboardInterrupt: break
            except Exception as e:
                log_error(f"Main loop error: {e}", "main_loop")
                await asyncio.sleep(10)
        
        self.xt_client.close()

async def main():
    bot = CryptoSignalBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
