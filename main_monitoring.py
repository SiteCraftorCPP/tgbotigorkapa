"""
Дополнительные методы мониторинга для main.py
Скопируйте эти методы в класс CryptoSignalBot
"""

from database.models import Signal
from telegram_bot.notifications import TelegramNotifications
from analysis.signal_cancellation import SignalCancellation
from utils.logger import log_info
from datetime import datetime


async def _check_waiting_signal(self, signal: Signal, current_price: float, db):
    """Проверка сигнала в ожидании: активация входа или отмена"""
    
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
        # Для лонга: цена коснулась или прошла entry сверху вниз
        if current_price <= signal.entry_price:
            entry_activated = True
    else:  # SHORT
        # Для шорта: цена коснулась или прошла entry снизу вверх
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
            chat_id=self.telegram_bot.bot._token.split(':')[0],  # channel_id
            text=msg,
            parse_mode='Markdown'
        )
        
        log_info(f"✅ Вход активирован {signal.signal_id} @ {current_price}")


async def _check_position_levels(self, signal: Signal, current_price: float, db):
    """Проверка достижения TP и SL для позиции"""
    
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
            f'take_profit_{tp_number + 1}': getattr(signal, f'take_profit_{tp_number + 1}', 0)
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
"""

Добавьте эти методы в класс CryptoSignalBot в main.py:
- _check_waiting_signal
- _check_position_levels
- _hit_tp
- _close_on_stop
"""

