"""
Мультиязычность для бота
"""

TRANSLATIONS = {
    'en': {
        # Команды
        'cmd_start': """
🤖 *Ultra-Conservative Crypto Signal Bot*

📊 Public commands:
/stats - Overall statistics
/today - Today's statistics
/week - Weekly statistics
/language - Change language
/help - Help

⚙️ Admin commands:
/config - Current settings
/enable - Enable bot
/disable - Disable bot

🔧 Settings:
/set_pairs - Trading pairs
/set_timeframes - Timeframes
/set_ai_score - Min AI Score
/set_risk - Risk percentage
/set_leverage - Leverage

👥 Admin management:
/add_admin - Add admin
/remove_admin - Remove admin
/list_admins - List admins
""",
        'cmd_help': 'See /start for all commands',
        
        # Сигналы
        'signal_title': 'ULTRA-CONSERVATIVE SIGNAL',
        'entry': 'Entry',
        'stop': 'Stop',
        'take_profit': 'Take Profit (4 levels)',
        'parameters': 'Parameters',
        'risk': 'Risk',
        'leverage': 'Leverage',
        'ai_score': 'AI Score',
        'filters': 'Filters',
        'volume_24h': 'Volume 24h',
        'spread': 'Spread',
        'after_tp1': 'After TP1 - move SL to breakeven!',
        
        # Уведомления
        'entry_activated': 'ENTRY ACTIVATED',
        'entry_price': 'Entry price',
        'stop_loss': 'Stop-loss',
        'position_opened': 'Position opened! Awaiting TP1...',
        
        'tp_reached': 'TP{n} REACHED!',
        'profit': 'Profit',
        'closed': 'Closed',
        'position': 'position',
        'remaining': 'Remaining',
        'next': 'Next',
        'sl_moved_breakeven': 'STOP MOVED TO BREAKEVEN!',
        
        'all_tp_reached': 'ALL TPs REACHED!',
        'max_profit': 'Max profit',
        'avg_profit': 'Avg profit',
        'perfect_execution': 'Perfect signal execution!',
        
        'stop_loss_hit': 'STOP-LOSS',
        'closed_breakeven': 'CLOSED AT BREAKEVEN',
        'result': 'Result',
        'breakeven': 'breakeven',
        'loss': 'Loss',
        'reached': 'Reached',
        'trade_closed': 'Trade closed.',
        
        'signal_cancelled': 'SIGNAL CANCELLED',
        'reason': 'Reason',
        'removed_from_queue': 'Signal removed from queue.',
        
        'warning': 'WARNING',
        
        # Статистика
        'no_closed_signals': '📊 No closed signals yet',
        'overall_stats': 'Overall Statistics',
        'total_signals': 'Total signals',
        'profitable': 'Profitable',
        'unprofitable': 'Unprofitable',
        'winrate': 'Winrate',
        'total_pnl': 'Total PnL',
        'avg_rr': 'Avg RR',
        
        'today_stats': 'Today\'s Statistics',
        'active': 'Active',
        'no_signals_today': '📊 No signals today yet',
        
        'week_stats': 'Weekly Statistics',
        'no_signals_week': '📊 No signals this week',
        
        # Настройки
        'current_settings': 'Current Bot Settings',
        'status': 'Status',
        'enabled': 'Enabled',
        'disabled': 'Disabled',
        'trading': 'Trading',
        'pairs': 'Pairs',
        'timeframes': 'Timeframes',
        'min_ai_score': 'Min. AI Score',
        'use_commands': 'Use /set_* commands to change',
        
        'bot_enabled': '✅ Bot enabled',
        'bot_disabled': '⏸ Bot disabled',
        
        # Языки
        'language_select': 'Select language / Выберите язык:',
        'language_changed': '✅ Language changed to English',
        
        # Ошибки
        'no_permission': '❌ You don\'t have permission for this command.\nOnly administrators can use this command.',
        'error': '❌ Error',
        'usage': 'Usage',
    },
    
    'ru': {
        # Команды
        'cmd_start': """
🤖 *Ультраконсервативный Крипто-Сигнальный Бот*

📊 Публичные команды:
/stats - Общая статистика
/today - Статистика за сегодня
/week - Статистика за неделю
/language - Сменить язык
/help - Помощь

⚙️ Админ-команды:
/config - Текущие настройки
/enable - Включить бота
/disable - Выключить бота

🔧 Настройка параметров:
/set_pairs - Торгуемые пары
/set_timeframes - Таймфреймы
/set_ai_score - Мин. AI Score
/set_risk - Процент риска
/set_leverage - Плечо

👥 Управление админами:
/add_admin - Добавить админа
/remove_admin - Удалить админа
/list_admins - Список админов
""",
        'cmd_help': 'См. /start для всех команд',
        
        # Сигналы
        'signal_title': 'УЛЬТРАКОНСЕРВАТИВНЫЙ СИГНАЛ',
        'entry': 'Вход',
        'stop': 'Стоп',
        'take_profit': 'Take Profit (4 уровня)',
        'parameters': 'Параметры',
        'risk': 'Риск',
        'leverage': 'Плечо',
        'ai_score': 'AI Score',
        'filters': 'Фильтры',
        'volume_24h': 'Объём 24ч',
        'spread': 'Спред',
        'after_tp1': 'После TP1 - перенос SL в безубыток!',
        
        # Уведомления
        'entry_activated': 'ВХОД АКТИВИРОВАН',
        'entry_price': 'Цена входа',
        'stop_loss': 'Стоп-лосс',
        'position_opened': 'Позиция открыта! Ожидаем TP1...',
        
        'tp_reached': 'TP{n} ДОСТИГНУТ!',
        'profit': 'Профит',
        'closed': 'Закрыто',
        'position': 'позиции',
        'remaining': 'Осталось',
        'next': 'Следующий',
        'sl_moved_breakeven': 'СТОП ПЕРЕНЕСЁН В БЕЗУБЫТОК!',
        
        'all_tp_reached': 'ВСЕ TP ДОСТИГНУТЫ!',
        'max_profit': 'Максимальный профит',
        'avg_profit': 'Средний профит',
        'perfect_execution': 'Идеальное выполнение сигнала!',
        
        'stop_loss_hit': 'СТОП-ЛОСС',
        'closed_breakeven': 'ЗАКРЫТО ПО БЕЗУБЫТКУ',
        'result': 'Результат',
        'breakeven': 'безубыток',
        'loss': 'Убыток',
        'reached': 'Достигнуты',
        'trade_closed': 'Сделка закрыта.',
        
        'signal_cancelled': 'СИГНАЛ ОТМЕНЁН',
        'reason': 'Причина',
        'removed_from_queue': 'Сигнал удалён из очереди.',
        
        'warning': 'ПРЕДУПРЕЖДЕНИЕ',
        
        # Статистика
        'no_closed_signals': '📊 Пока нет закрытых сигналов',
        'overall_stats': 'Общая статистика',
        'total_signals': 'Всего сигналов',
        'profitable': 'Прибыльных',
        'unprofitable': 'Убыточных',
        'winrate': 'Winrate',
        'total_pnl': 'Общий PnL',
        'avg_rr': 'Средний RR',
        
        'today_stats': 'Статистика за сегодня',
        'active': 'Активных',
        'no_signals_today': '📊 Сегодня сигналов пока нет',
        
        'week_stats': 'Статистика за неделю',
        'no_signals_week': '📊 За неделю сигналов нет',
        
        # Настройки
        'current_settings': 'Текущие настройки бота',
        'status': 'Статус',
        'enabled': 'Включен',
        'disabled': 'Выключен',
        'trading': 'Торговля',
        'pairs': 'Пары',
        'timeframes': 'Таймфреймы',
        'min_ai_score': 'Мин. AI Score',
        'use_commands': 'Для изменения используйте команды /set_*',
        
        'bot_enabled': '✅ Бот включен',
        'bot_disabled': '⏸ Бот выключен',
        
        # Языки
        'language_select': 'Выберите язык / Select language:',
        'language_changed': '✅ Язык изменён на Русский',
        
        # Ошибки
        'no_permission': '❌ У вас нет прав для выполнения этой команды.\nТолько администраторы могут использовать эту команду.',
        'error': '❌ Ошибка',
        'usage': 'Использование',
    }
}


def t(key: str, lang: str = 'en', **kwargs) -> str:
    """
    Перевод строки
    
    Args:
        key: ключ перевода
        lang: язык ('en' или 'ru')
        **kwargs: параметры для форматирования (например, n=1 для TP{n})
    """
    translation = TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, key)
    
    # Форматирование параметров
    try:
        return translation.format(**kwargs)
    except:
        return translation


def get_user_lang(telegram_id: str) -> str:
    """Получить язык пользователя"""
    from database.user_preferences import UserPreferenceManager
    return UserPreferenceManager.get_language(telegram_id)

