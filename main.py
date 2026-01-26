import asyncio
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from exchange.xt_client import XTClient
from analysis.signal_generator import SignalGenerator
from telegram_bot.bot import TelegramBot
from utils.deepseek_client import get_deepseek_client
from database.models import init_db, Signal, SessionLocal
from database.config_manager import ConfigManager
from utils.logger import logger, log_signal, log_error, log_info, log_warning
from utils.cache import btc_cache
from utils.top_coins import update_trading_pairs_auto
from utils.db_cleanup import run_scheduled_cleanup
from telegram_bot.filter_panel import FilterSettings

# Отключаем шумные логи httpx
logging.getLogger("httpx").setLevel(logging.WARNING)

class CryptoSignalBot:
    """Главный класс бота с оптимизированным asyncio циклом"""
    
    ANALYSIS_INTERVAL_SEC = 60 
    SIGNAL_TIMEFRAME = '1h'
    
    def __init__(self):
        self.xt_client = XTClient()
        self.telegram_bot = TelegramBot()
        self.deepseek = get_deepseek_client()
        self.is_running = False
        
    async def initialize(self):
        log_info("🚀 Initializing bot modules...")
        init_db()
        FilterSettings.get_all(force_reload=True)
        FilterSettings._apply_to_filters()
        
        # Запуск Telegram Bot
        await self.telegram_bot.app.initialize()
        await self.telegram_bot.app.start()
        asyncio.create_task(self.telegram_bot.app.updater.start_polling(drop_pending_updates=True))
        log_info("✅ Telegram bot is online and responsive")
        
        await update_trading_pairs_auto(limit=300)

    async def _analyze_one(self, pair: str, tf: str):
        try:
            df = await self.xt_client.get_ohlcv(pair, tf, limit=500)
            if df is None or df.empty: return
            
            from analysis.multi_timeframe import MultiTimeframeAnalysis
            higher_tf = MultiTimeframeAnalysis.get_higher_timeframe(tf)
            df_higher = await self.xt_client.get_ohlcv(pair, higher_tf, limit=200)
            if df_higher is None or df_higher.empty: return
            
            generator = SignalGenerator(pair, tf, df, df_higher, self.xt_client)
            signal = await generator.generate_signal()
            
            if signal:
                await self._save_and_send_signal(signal)
        except Exception as e:
            log_error(f"Analyze error {pair}: {e}", "analyze_one")

    async def analyze_loop(self):
        log_info("🔎 Market analysis loop started")
        while self.is_running:
            if not ConfigManager.is_bot_enabled():
                await asyncio.sleep(5)
                continue
                
            start_time = time.time()
            pairs = ConfigManager.get_trading_pairs()
            await btc_cache.get_btc_ohlcv_1m(self.xt_client)
            
            for pair in pairs:
                if not self.is_running: break
                await self._analyze_one(pair, self.SIGNAL_TIMEFRAME)
                await asyncio.sleep(0.05) 
            
            elapsed = time.time() - start_time
            log_info(f"✨ Full scan finished: {len(pairs)} pairs in {elapsed:.1f}s")
            await asyncio.sleep(max(5, self.ANALYSIS_INTERVAL_SEC - (time.time() - start_time)))

    async def monitor_loop(self):
        """Цикл мониторинга TP/SL (Восстановлено!)"""
        log_info("🎯 Monitoring loop started")
        while self.is_running:
            db = SessionLocal()
            try:
                active = db.query(Signal).filter(Signal.status.in_(['WAITING', 'IN_POSITION', 'TP1_HIT', 'TP2_HIT', 'TP3_HIT'])).all()
                for signal in active:
                    ticker_data = await self.xt_client.get_ticker(signal.ticker)
                    if ticker_data and ticker_data.get('last'):
                        price = ticker_data['last']
                        if signal.status == 'WAITING':
                            await self._check_waiting_signal(signal, price, db)
                        else:
                            await self._check_position_levels(signal, price, db)
                db.commit()
            except Exception as e:
                log_error(f"Monitor loop error: {e}", "monitor_loop")
            finally:
                db.close()
            await asyncio.sleep(10) # Проверка каждые 10 сек

    async def _check_waiting_signal(self, signal, price, db):
        # Вход в позицию
        if (signal.direction == 'LONG' and price <= signal.entry_price) or \
           (signal.direction == 'SHORT' and price >= signal.entry_price):
            signal.status = 'IN_POSITION'
            signal.activated_at = datetime.utcnow()
            log_info(f"🟢 Position entered: {signal.ticker}")

    async def _check_position_levels(self, signal, price, db):
        sl = signal.stop_loss
        tp3 = signal.take_profit_3
        result = None
        pnl = 0
        
        if signal.direction == 'LONG':
            if price <= sl:
                result = 'LOSS'; signal.status = 'STOPPED_OUT'
                pnl = ((sl - signal.entry_price) / signal.entry_price) * 100
            elif price >= tp3:
                result = 'WIN'; signal.status = 'CLOSED_FULL_TP'
                pnl = ((tp3 - signal.entry_price) / signal.entry_price) * 100
        else:
            if price >= sl:
                result = 'LOSS'; signal.status = 'STOPPED_OUT'
                pnl = ((signal.entry_price - sl) / signal.entry_price) * 100
            elif price <= tp3:
                result = 'WIN'; signal.status = 'CLOSED_FULL_TP'
                pnl = ((signal.entry_price - tp3) / signal.entry_price) * 100
        
        if result:
            signal.closed_at = datetime.utcnow()
            signal.result = result
            signal.pnl_percent = pnl
            # ОТПРАВЛЯЕМ В КАНАЛ!
            await self.telegram_bot.update_signal_result(signal.signal_id, result, pnl)
            log_info(f"🏁 Signal {signal.ticker} closed: {result} ({pnl:.2f}%)")

    async def _save_and_send_signal(self, signal: dict):
        ticker = signal.get('ticker', 'UNKNOWN')
        db = SessionLocal()
        try:
            recent = db.query(Signal).filter(Signal.ticker == ticker, Signal.status.in_(['WAITING', 'IN_POSITION'])).first()
            if recent: return

            ds_result = await self.deepseek.analyze_signal(signal)
            if not ds_result.get('approved'): return

            from utils.chart import render_signal_chart
            df = await self.xt_client.get_ohlcv(ticker, signal['timeframe'], limit=200)
            chart_path = render_signal_chart(df, signal, ds_result.get('plan'))
            if chart_path: signal['chart_path'] = chart_path
            
            db_signal = Signal(
                signal_id=signal['signal_id'], ticker=ticker, direction=signal['direction'],
                entry_price=signal['entry_price'], stop_loss=signal['stop_loss'],
                take_profit_1=signal['take_profit_1'], take_profit_2=signal['take_profit_2'],
                take_profit_3=signal['take_profit_3'], status='WAITING'
            )
            db.add(db_signal)
            db.commit()
            
            await self.telegram_bot.send_signal(signal)
            log_signal(signal)
        except Exception as e:
            log_error(f"Save/Send error {ticker}: {e}", "save_signal")
        finally:
            db.close()

    async def run(self):
        self.is_running = True
        await self.initialize()
        
        await asyncio.gather(
            self.analyze_loop(),
            self.monitor_loop(), # ТЕПЕРЬ МОНИТОРИНГ ВКЛЮЧЕН
            run_scheduled_cleanup()
        )

async def main():
    bot = CryptoSignalBot()
    try:
        await bot.run()
    except KeyboardInterrupt:
        bot.is_running = False
        await bot.xt_client.close()

if __name__ == "__main__":
    asyncio.run(main())
