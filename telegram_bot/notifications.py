"""
Все типы уведомлений для Telegram
"""

from telegram import Bot
from telegram.constants import ParseMode


class TelegramNotifications:
    """Форматирование всех типов уведомлений"""
    
    @staticmethod
    def format_entry_activated(signal: dict, activation_price: float) -> str:
        """Entry activation notification (English for channel)"""
        emoji = "🟢" if signal['direction'] == 'LONG' else "🔴"
        
        return f"""
{emoji} *ENTRY ACTIVATED*

🆔 `{signal['signal_id']}`
📊 *{signal['ticker']}* | {signal['direction']}

💰 Entry price: `{activation_price}`
🛑 Stop-loss: `{signal['stop_loss']}`

Position opened! Awaiting TP1...
"""
    
    @staticmethod
    def format_tp_hit(signal: dict, tp_number: int, tp_price: float, 
                     remaining_percent: int) -> str:
        """TP hit notification (English for channel)"""
        
        emoji_map = {1: "🎯", 2: "🎯🎯", 3: "🎯🎯🎯", 4: "🎯🎯🎯🎯"}
        emoji = emoji_map.get(tp_number, "🎯")
        
        # Profit calculation
        entry = signal['entry_price']
        if signal['direction'] == 'LONG':
            profit = ((tp_price - entry) / entry) * 100
        else:
            profit = ((entry - tp_price) / entry) * 100
        
        breakeven_note = ""
        if tp_number == 1:
            breakeven_note = "\n\n✅ *STOP MOVED TO BREAKEVEN!*"
        
        message = f"""
{emoji} *TP{tp_number} REACHED!*

🆔 `{signal['signal_id']}`
📊 *{signal['ticker']}* | {signal['direction']}

💰 TP{tp_number}: `{tp_price}` 
📈 Profit: *+{profit:.2f}%*
💵 Closed: *25%* position

🔄 Remaining: *{remaining_percent}%* position
"""
        
        if tp_number < 4:
            next_tp = signal[f'take_profit_{tp_number + 1}']
            message += f"⏭ Next: TP{tp_number + 1} = `{next_tp}`"
        
        message += breakeven_note
        
        return message.strip()
    
    @staticmethod
    def format_stop_loss(signal: dict, close_price: float) -> str:
        """Stop-loss notification (English for channel)"""
        
        # Loss calculation
        entry = signal.get('activated_price', signal['entry_price'])
        if signal['direction'] == 'LONG':
            loss = ((close_price - entry) / entry) * 100
        else:
            loss = ((entry - close_price) / entry) * 100
        
        # Check if breakeven was set
        was_breakeven = signal.get('stop_loss_breakeven') is not None
        
        if was_breakeven:
            emoji = "🔄"
            title = "CLOSED AT BREAKEVEN"
            loss_text = f"Result: *0%* (breakeven)"
        else:
            emoji = "🛑"
            title = "STOP-LOSS"
            loss_text = f"Loss: *{loss:.2f}%*"
        
        # Which TPs were reached
        tps_hit = []
        for i in range(1, 5):
            if signal.get(f'tp{i}_hit'):
                tps_hit.append(f"TP{i}")
        
        tps_text = ""
        if tps_hit:
            tps_text = f"\n✅ Reached: {', '.join(tps_hit)}"
        
        return f"""
{emoji} *{title}*

🆔 `{signal['signal_id']}`
📊 *{signal['ticker']}* | {signal['direction']}

💰 Close price: `{close_price}`
📉 {loss_text}{tps_text}

Trade closed.
"""
    
    @staticmethod
    def format_full_tp(signal: dict) -> str:
        """Full TP4 closure notification (English for channel)"""
        
        entry = signal.get('activated_price', signal['entry_price'])
        tp4 = signal['take_profit_4']
        
        if signal['direction'] == 'LONG':
            total_profit = ((tp4 - entry) / entry) * 100
        else:
            total_profit = ((entry - tp4) / entry) * 100
        
        return f"""
🎉 *ALL TPs REACHED!*

🆔 `{signal['signal_id']}`
📊 *{signal['ticker']}* | {signal['direction']}

✅ TP1, TP2, TP3, TP4 - all closed!

💰 Max profit: *+{total_profit:.2f}%*
📈 Avg profit: *+{total_profit * 0.625:.2f}%*

🎯 Perfect signal execution!
"""
    
    @staticmethod
    def format_cancelled(signal: dict, reason: str) -> str:
        """Signal cancellation notification (English for channel)"""
        
        return f"""
⚠️ *SIGNAL CANCELLED*

🆔 `{signal['signal_id']}`
📊 *{signal['ticker']}* | {signal['direction']}

📋 Reason: _{reason}_

Signal removed from queue.
"""
    
    @staticmethod
    def format_warning(signal: dict, warning_text: str) -> str:
        """Warning notification (English for channel)"""
        
        return f"""
⚠️ *WARNING*

🆔 `{signal['signal_id']}`
📊 *{signal['ticker']}*

{warning_text}
"""

