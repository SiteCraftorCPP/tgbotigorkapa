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
    
    async def _close_signal(self, signal: Signal, status: str, close_price: float):
        """Закрытие сигнала"""
        db = get_db()
        
        try:
            # Расчёт PnL
            if signal.direction == 'LONG':
                pnl_percent = ((close_price - signal.entry_price) / signal.entry_price) * 100
            else:
                pnl_percent = ((signal.entry_price - close_price) / signal.entry_price) * 100
            
            # С учётом плеча
            pnl_percent *= signal.leverage
            
            # Результат
            result = 'WIN' if status in ['TP1', 'TP2'] else 'LOSS'
            
            # Обновление в БД
            signal.status = status
            signal.result = result
            signal.pnl_percent = pnl_percent
            signal.closed_at = datetime.utcnow()
            
            db.commit()
            
            # Уведомление в Telegram
            await self.telegram_bot.update_signal_result(
                signal.signal_id,
                result,
                pnl_percent
            )
            
            log_info(f"🔒 Сигнал {signal.signal_id} закрыт: {result} ({pnl_percent:+.2f}%)")
            
        finally:
            db.close()
    
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

