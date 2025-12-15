"""
Генерация еженедельных отчётов о сигналах
Публикуется каждую пятницу вечером по времени США (EST)
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from database.models import Signal, SessionLocal
from utils.logger import log_info, log_error
import pytz


class WeeklyReportGenerator:
    """Генератор еженедельных отчётов о сигналах"""
    
    # Часовой пояс США (Eastern Time)
    US_TIMEZONE = pytz.timezone('US/Eastern')
    
    # Время публикации: пятница 20:00 EST (8 PM)
    PUBLISH_DAY = 4  # Пятница (0 = понедельник)
    PUBLISH_HOUR = 20  # 8 PM EST
    
    @classmethod
    def get_signal_status(cls, signal: Signal) -> Tuple[str, str]:
        """
        Определяет статус сигнала для отчёта
        
        Returns:
            Tuple[status_category, status_detail]:
            - status_category: 'closed_profit', 'closed_loss', 'open', 'cancelled'
            - status_detail: детальное описание
        """
        # Отменённые сигналы
        if signal.status == 'CANCELLED':
            return 'cancelled', 'Отменён'
        
        # Определяем, есть ли 4-й тейк
        has_tp4 = signal.take_profit_4 is not None and signal.take_profit_4 > 0
        
        # Закрыта по стопу
        if signal.status == 'STOPPED_OUT':
            if signal.result == 'BREAKEVEN':
                return 'closed_breakeven', 'Безубыток'
            # Если были достигнуты тейки до стопа, это частичный профит
            tps_hit = sum([signal.tp1_hit, signal.tp2_hit, signal.tp3_hit, signal.tp4_hit])
            if tps_hit > 0:
                return 'closed_partial', f'Стоп после TP{tps_hit}'
            return 'closed_loss', 'Стоп-лосс'
        
        # Полностью закрыта в плюс
        if signal.status == 'CLOSED_FULL_TP':
            return 'closed_profit', 'Все TP достигнуты'
        
        # Определяем, закрыта ли сделка полностью
        if has_tp4:
            # Есть 4 тейка: закрыта в плюс только если TP4 достигнут
            if signal.tp4_hit:
                return 'closed_profit', 'TP4 достигнут'
            # Открыта (TP1/TP2/TP3 достигнуты)
            if signal.tp3_hit:
                return 'open', 'TP3 достигнут, ждём TP4'
            if signal.tp2_hit:
                return 'open', 'TP2 достигнут'
            if signal.tp1_hit:
                return 'open', 'TP1 достигнут'
        else:
            # Только 3 тейка: закрыта в плюс если TP3 достигнут
            if signal.tp3_hit:
                return 'closed_profit', 'TP3 достигнут (финальный)'
            # Открыта (TP1/TP2 достигнуты)
            if signal.tp2_hit:
                return 'open', 'TP2 достигнут, ждём TP3'
            if signal.tp1_hit:
                return 'open', 'TP1 достигнут'
        
        # В ожидании или позиции без тейков
        if signal.status in ['WAITING', 'IN_POSITION']:
            return 'open', 'В работе'
        
        return 'open', signal.status
    
    @classmethod
    def calculate_profit_percent(cls, signal: Signal) -> float:
        """Вычисляет процент прибыли/убытка по сигналу"""
        if signal.pnl_percent is not None:
            return signal.pnl_percent
        
        entry = signal.entry_price
        if not entry or entry == 0:
            return 0.0
        
        # Определяем цену закрытия
        if signal.tp4_hit and signal.take_profit_4:
            close_price = signal.take_profit_4
        elif signal.tp3_hit:
            close_price = signal.take_profit_3
        elif signal.tp2_hit:
            close_price = signal.take_profit_2
        elif signal.tp1_hit:
            close_price = signal.take_profit_1
        else:
            return 0.0
        
        if signal.direction == 'LONG':
            return ((close_price - entry) / entry) * 100
        else:
            return ((entry - close_price) / entry) * 100
    
    @classmethod
    def generate_report(cls, days: int = 7) -> Dict:
        """
        Генерирует отчёт за указанный период
        
        Args:
            days: количество дней для анализа (по умолчанию 7)
        
        Returns:
            Dict с данными отчёта
        """
        db = SessionLocal()
        try:
            # Период отчёта
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Получаем все сигналы за период
            signals = db.query(Signal).filter(
                Signal.created_at >= start_date,
                Signal.created_at <= end_date
            ).order_by(Signal.created_at.desc()).all()
            
            # Категоризация сигналов
            closed_profit = []      # Закрыты в плюс (все TP достигнуты)
            closed_partial = []     # Частично закрыты (стоп после TP)
            closed_loss = []        # Закрыты в убыток
            closed_breakeven = []   # Безубыток
            open_signals = []       # Открытые (ещё в работе)
            cancelled = []          # Отменённые
            
            total_profit_pct = 0.0
            total_loss_pct = 0.0
            
            for signal in signals:
                status_cat, status_detail = cls.get_signal_status(signal)
                profit = cls.calculate_profit_percent(signal)
                
                signal_info = {
                    'signal': signal,
                    'status_detail': status_detail,
                    'profit_pct': profit,
                    'ticker': signal.ticker,
                    'direction': signal.direction,
                    'created_at': signal.created_at,
                    'tp1_hit': signal.tp1_hit,
                    'tp2_hit': signal.tp2_hit,
                    'tp3_hit': signal.tp3_hit,
                    'tp4_hit': signal.tp4_hit,
                    'has_tp4': signal.take_profit_4 is not None and signal.take_profit_4 > 0
                }
                
                if status_cat == 'closed_profit':
                    closed_profit.append(signal_info)
                    total_profit_pct += profit
                elif status_cat == 'closed_partial':
                    closed_partial.append(signal_info)
                    # Частичный профит тоже считаем
                    total_profit_pct += profit
                elif status_cat == 'closed_loss':
                    closed_loss.append(signal_info)
                    total_loss_pct += abs(profit)
                elif status_cat == 'closed_breakeven':
                    closed_breakeven.append(signal_info)
                elif status_cat == 'open':
                    open_signals.append(signal_info)
                elif status_cat == 'cancelled':
                    cancelled.append(signal_info)
            
            # Подсчёт статистики
            total_closed = len(closed_profit) + len(closed_partial) + len(closed_loss) + len(closed_breakeven)
            total_signals = len(signals) - len(cancelled)  # Без отменённых
            
            win_count = len(closed_profit) + len(closed_partial)
            loss_count = len(closed_loss)
            
            winrate = (win_count / total_closed * 100) if total_closed > 0 else 0
            lossrate = (loss_count / total_closed * 100) if total_closed > 0 else 0
            
            return {
                'period_start': start_date,
                'period_end': end_date,
                'days': days,
                
                # Категории сигналов
                'closed_profit': closed_profit,
                'closed_partial': closed_partial,
                'closed_loss': closed_loss,
                'closed_breakeven': closed_breakeven,
                'open_signals': open_signals,
                'cancelled': cancelled,
                
                # Статистика
                'total_signals': total_signals,
                'total_closed': total_closed,
                'win_count': win_count,
                'loss_count': loss_count,
                'breakeven_count': len(closed_breakeven),
                'open_count': len(open_signals),
                
                'winrate': winrate,
                'lossrate': lossrate,
                
                'total_profit_pct': total_profit_pct,
                'total_loss_pct': total_loss_pct,
                'net_profit_pct': total_profit_pct - total_loss_pct,
            }
            
        finally:
            db.close()
    
    @classmethod
    def format_report_message(cls, report: Dict) -> str:
        """Форматирует отчёт в красивое сообщение для Telegram"""
        
        # Заголовок
        period_start = report['period_start'].strftime('%d.%m.%Y')
        period_end = report['period_end'].strftime('%d.%m.%Y')
        
        # Эмодзи для результата
        if report['net_profit_pct'] > 0:
            result_emoji = "🟢"
            result_text = f"+{report['net_profit_pct']:.2f}%"
        elif report['net_profit_pct'] < 0:
            result_emoji = "🔴"
            result_text = f"{report['net_profit_pct']:.2f}%"
        else:
            result_emoji = "⚪"
            result_text = "0%"
        
        msg = f"""
📊 *WEEKLY SIGNAL REPORT*
━━━━━━━━━━━━━━━━━━━━━━━
📅 Period: `{period_start}` → `{period_end}`

{result_emoji} *Net Result: {result_text}*

━━━ 📈 *STATISTICS* ━━━

📋 Total signals: *{report['total_signals']}*
✅ Closed: *{report['total_closed']}*
⏳ Open: *{report['open_count']}*

"""
        
        # Закрытые в плюс
        if report['closed_profit']:
            msg += f"""
🎯 *CLOSED IN PROFIT ({len(report['closed_profit'])})*
"""
            for s in report['closed_profit'][:5]:  # Макс 5
                emoji = "🟢" if s['direction'] == 'LONG' else "🔴"
                tp_text = "TP4" if s['tp4_hit'] else "TP3"
                msg += f"  {emoji} `{s['ticker']}` → *{tp_text}* (+{s['profit_pct']:.1f}%)\n"
            if len(report['closed_profit']) > 5:
                msg += f"  _...и ещё {len(report['closed_profit']) - 5}_\n"
        
        # Частично закрытые
        if report['closed_partial']:
            msg += f"""
🎯 *PARTIAL PROFIT ({len(report['closed_partial'])})*
"""
            for s in report['closed_partial'][:3]:
                emoji = "🟢" if s['direction'] == 'LONG' else "🔴"
                msg += f"  {emoji} `{s['ticker']}` → {s['status_detail']} (+{s['profit_pct']:.1f}%)\n"
            if len(report['closed_partial']) > 3:
                msg += f"  _...и ещё {len(report['closed_partial']) - 3}_\n"
        
        # Закрытые в убыток
        if report['closed_loss']:
            msg += f"""
🛑 *CLOSED AT LOSS ({len(report['closed_loss'])})*
"""
            for s in report['closed_loss'][:3]:
                emoji = "🟢" if s['direction'] == 'LONG' else "🔴"
                msg += f"  {emoji} `{s['ticker']}` → Stop-loss\n"
            if len(report['closed_loss']) > 3:
                msg += f"  _...и ещё {len(report['closed_loss']) - 3}_\n"
        
        # Безубыток
        if report['closed_breakeven']:
            msg += f"""
🔄 *BREAKEVEN ({len(report['closed_breakeven'])})*
"""
            for s in report['closed_breakeven'][:3]:
                emoji = "🟢" if s['direction'] == 'LONG' else "🔴"
                msg += f"  {emoji} `{s['ticker']}` → BE\n"
        
        # Открытые сигналы
        if report['open_signals']:
            msg += f"""
⏳ *STILL OPEN ({len(report['open_signals'])})*
"""
            for s in report['open_signals'][:5]:
                emoji = "🟢" if s['direction'] == 'LONG' else "🔴"
                tp_status = ""
                if s['tp3_hit']:
                    tp_status = "TP3 ✅"
                elif s['tp2_hit']:
                    tp_status = "TP2 ✅"
                elif s['tp1_hit']:
                    tp_status = "TP1 ✅"
                else:
                    tp_status = "Waiting..."
                msg += f"  {emoji} `{s['ticker']}` → {tp_status}\n"
            if len(report['open_signals']) > 5:
                msg += f"  _...и ещё {len(report['open_signals']) - 5}_\n"
        
        # Итоговая статистика
        msg += f"""
━━━ 📊 *SUMMARY* ━━━

✅ Win rate: *{report['winrate']:.1f}%* ({report['win_count']}/{report['total_closed']})
❌ Loss rate: *{report['lossrate']:.1f}%* ({report['loss_count']}/{report['total_closed']})

💰 Total profit: *+{report['total_profit_pct']:.2f}%*
💸 Total loss: *-{report['total_loss_pct']:.2f}%*
📈 Net: *{result_text}*

━━━━━━━━━━━━━━━━━━━━━━━
_Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC_
"""
        
        return msg.strip()
    
    @classmethod
    def should_publish_now(cls) -> bool:
        """Проверяет, нужно ли публиковать отчёт сейчас (пятница вечером EST)"""
        now_est = datetime.now(cls.US_TIMEZONE)
        
        # Пятница = 4 (weekday())
        is_friday = now_est.weekday() == cls.PUBLISH_DAY
        is_publish_hour = now_est.hour == cls.PUBLISH_HOUR
        
        return is_friday and is_publish_hour
    
    @classmethod
    def get_next_publish_time(cls) -> datetime:
        """Возвращает время следующей публикации"""
        now_est = datetime.now(cls.US_TIMEZONE)
        
        # Находим следующую пятницу
        days_until_friday = (cls.PUBLISH_DAY - now_est.weekday()) % 7
        if days_until_friday == 0 and now_est.hour >= cls.PUBLISH_HOUR:
            days_until_friday = 7
        
        next_friday = now_est + timedelta(days=days_until_friday)
        next_publish = next_friday.replace(
            hour=cls.PUBLISH_HOUR, 
            minute=0, 
            second=0, 
            microsecond=0
        )
        
        return next_publish


class WeeklyReportScheduler:
    """Планировщик для еженедельных отчётов"""
    
    def __init__(self, bot):
        self.bot = bot
        self._last_report_date = None
        self._running = False
    
    async def start(self):
        """Запуск планировщика"""
        self._running = True
        log_info("[WeeklyReport] Scheduler started")
        
        while self._running:
            try:
                await self._check_and_publish()
            except Exception as e:
                log_error(str(e), "weekly_report_scheduler")
            
            # Проверка каждые 30 минут
            await asyncio.sleep(1800)
    
    def stop(self):
        """Остановка планировщика"""
        self._running = False
        log_info("[WeeklyReport] Scheduler stopped")
    
    async def _check_and_publish(self):
        """Проверка и публикация отчёта"""
        if not WeeklyReportGenerator.should_publish_now():
            return
        
        # Проверяем, не публиковали ли уже сегодня
        today = datetime.now(WeeklyReportGenerator.US_TIMEZONE).date()
        if self._last_report_date == today:
            return
        
        log_info("[WeeklyReport] Publishing weekly report...")
        
        try:
            # Генерируем отчёт за 7 дней
            report = WeeklyReportGenerator.generate_report(days=7)
            message = WeeklyReportGenerator.format_report_message(report)
            
            # Публикуем в канал
            await self.bot.send_to_channel(message)
            
            self._last_report_date = today
            log_info("[WeeklyReport] Report published successfully")
            
        except Exception as e:
            log_error(str(e), "publish_weekly_report")
    
    async def publish_now(self) -> str:
        """Принудительная публикация отчёта (для тестирования)"""
        report = WeeklyReportGenerator.generate_report(days=7)
        return WeeklyReportGenerator.format_report_message(report)

