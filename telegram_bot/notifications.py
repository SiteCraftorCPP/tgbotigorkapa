"""
Все типы уведомлений для Telegram
"""

from telegram import Bot
from telegram.constants import ParseMode


class TelegramNotifications:
    """Форматирование всех типов уведомлений"""
    
    @staticmethod
    def format_entry_activated(signal: dict, activation_price: float) -> str:
        """Уведомление об активации входа"""
        emoji = "🟢" if signal['direction'] == 'LONG' else "🔴"
        
        return f"""
{emoji} *ВХОД АКТИВИРОВАН*

🆔 `{signal['signal_id']}`
📊 *{signal['ticker']}* | {signal['direction']}

💰 Цена входа: `{activation_price}`
🛑 Стоп-лосс: `{signal['stop_loss']}`

Позиция открыта! Ожидаем TP1...
"""
    
    @staticmethod
    def format_tp_hit(signal: dict, tp_number: int, tp_price: float, 
                     remaining_percent: int) -> str:
        """Уведомление о достижении TP"""
        
        emoji_map = {1: "🎯", 2: "🎯🎯", 3: "🎯🎯🎯", 4: "🎯🎯🎯🎯"}
        emoji = emoji_map.get(tp_number, "🎯")
        
        # Расчёт прибыли
        entry = signal['entry_price']
        if signal['direction'] == 'LONG':
            profit = ((tp_price - entry) / entry) * 100
        else:
            profit = ((entry - tp_price) / entry) * 100
        
        breakeven_note = ""
        if tp_number == 1:
            breakeven_note = "\n\n✅ *СТОП ПЕРЕНЕСЁН В БЕЗУБЫТОК!*"
        
        message = f"""
{emoji} *TP{tp_number} ДОСТИГНУТ!*

🆔 `{signal['signal_id']}`
📊 *{signal['ticker']}* | {signal['direction']}

💰 TP{tp_number}: `{tp_price}` 
📈 Профит: *+{profit:.2f}%*
💵 Закрыто: *25%* позиции

🔄 Осталось: *{remaining_percent}%* позиции
"""
        
        if tp_number < 4:
            next_tp = signal[f'take_profit_{tp_number + 1}']
            message += f"⏭ Следующий: TP{tp_number + 1} = `{next_tp}`"
        
        message += breakeven_note
        
        return message.strip()
    
    @staticmethod
    def format_stop_loss(signal: dict, close_price: float) -> str:
        """Уведомление о срабатывании стоп-лосса"""
        
        # Расчёт убытка
        entry = signal.get('activated_price', signal['entry_price'])
        if signal['direction'] == 'LONG':
            loss = ((close_price - entry) / entry) * 100
        else:
            loss = ((entry - close_price) / entry) * 100
        
        # Проверка, был ли безубыток
        was_breakeven = signal.get('stop_loss_breakeven') is not None
        
        if was_breakeven:
            emoji = "🔄"
            title = "ЗАКРЫТО ПО БЕЗУБЫТКУ"
            loss_text = f"Результат: *0%* (безубыток)"
        else:
            emoji = "🛑"
            title = "СТОП-ЛОСС"
            loss_text = f"Убыток: *{loss:.2f}%*"
        
        # Какие TP были достигнуты
        tps_hit = []
        for i in range(1, 5):
            if signal.get(f'tp{i}_hit'):
                tps_hit.append(f"TP{i}")
        
        tps_text = ""
        if tps_hit:
            tps_text = f"\n✅ Достигнуты: {', '.join(tps_hit)}"
        
        return f"""
{emoji} *{title}*

🆔 `{signal['signal_id']}`
📊 *{signal['ticker']}* | {signal['direction']}

💰 Цена закрытия: `{close_price}`
📉 {loss_text}{tps_text}

Сделка закрыта.
"""
    
    @staticmethod
    def format_full_tp(signal: dict) -> str:
        """Уведомление о полном закрытии по TP4"""
        
        entry = signal.get('activated_price', signal['entry_price'])
        tp4 = signal['take_profit_4']
        
        if signal['direction'] == 'LONG':
            total_profit = ((tp4 - entry) / entry) * 100
        else:
            total_profit = ((entry - tp4) / entry) * 100
        
        return f"""
🎉 *ВСЕ TP ДОСТИГНУТЫ!*

🆔 `{signal['signal_id']}`
📊 *{signal['ticker']}* | {signal['direction']}

✅ TP1, TP2, TP3, TP4 - все закрыты!

💰 Максимальный профит: *+{total_profit:.2f}%*
📈 Средний профит: *+{total_profit * 0.625:.2f}%*

🎯 Идеальное выполнение сигнала!
"""
    
    @staticmethod
    def format_cancelled(signal: dict, reason: str) -> str:
        """Уведомление об отмене сигнала"""
        
        return f"""
⚠️ *СИГНАЛ ОТМЕНЁН*

🆔 `{signal['signal_id']}`
📊 *{signal['ticker']}* | {signal['direction']}

📋 Причина: _{reason}_

Сигнал удалён из очереди.
"""
    
    @staticmethod
    def format_warning(signal: dict, warning_text: str) -> str:
        """Предупреждение по активному сигналу"""
        
        return f"""
⚠️ *ПРЕДУПРЕЖДЕНИЕ*

🆔 `{signal['signal_id']}`
📊 *{signal['ticker']}*

{warning_text}
"""

