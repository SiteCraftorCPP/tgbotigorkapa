"""
Мультиязычность для бота
"""

TRANSLATIONS = {
    'en': {
        # Команды
        'cmd_start': """
📊 Available commands:
/stats - Overall statistics
/today - Today's statistics
/week - Weekly statistics
/language - Change language
""",
        'cmd_start_admin': """
📊 Public commands:
/stats - Overall statistics
/today - Today's statistics
/week - Weekly statistics
/language - Change language

⚙️ Admin commands:
/enable - Enable bot
/disable - Disable bot

🗄️ Database:
/dbstats - Database statistics
/cleanup - Clean old signals

⚙️ Filter Control Panel:
/filters - Open filter control panel
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
        'use_commands': """Use /filters panel to manage all settings""",
        
        'bot_enabled': '✅ Bot enabled',
        'bot_disabled': '⏸ Bot disabled',
        
        # Языки
        'language_select': 'Select language / Выберите язык:',
        'language_changed': '✅ Language changed to English',
        
        # Ошибки
        'no_permission': '❌ You don\'t have permission for this command.\nOnly administrators can use this command.',
        'error': '❌ Error',
        'usage': 'Usage',
        'error_number': '❌ Error: specify a number from {min} to {max}',
        'error_invalid': '❌ Error: invalid value',
        'cannot_remove_last_admin': '❌ Cannot remove the last admin!',
        
        # Команды настроек
        'current_pairs': '📊 Current pairs: {pairs}',
        'pairs_help': 'To change pairs, send:\n`/setpairs BTC/USDT ETH/USDT SOL/USDT`\n\nExample:\n`/setpairs BTC/USDT ETH/USDT`',
        'current_timeframes': '⏰ Current timeframes: {timeframes}',
        'timeframes_help': 'To change timeframes, send:\n`/settimeframes 5m 15m 1h 4h`\n\nExample:\n`/settimeframes 1m 5m 1h`',
        'pairs_updated': '✅ Trading pairs updated:\n{pairs}',
        'timeframes_updated': '✅ Timeframes updated:\n{timeframes}',
        'pairs_changed': '⚙️ Pairs changed: {pairs}',
        'timeframes_changed': '⚙️ Timeframes changed: {timeframes}',
        
        # Админы
        'add_admin_usage': 'Usage:\n`/addadmin USER_ID`\n\nTo get ID, ask user to write @username_to_id_bot',
        'remove_admin_usage': 'Usage:\n`/remove_admin USER_ID`',
        'admin_added': '✅ Admin {id} added',
        'admin_removed': '✅ Admin {id} removed',
        'new_admin_added': '👥 New admin added: {id}',
        'admin_removed_msg': '👥 Admin removed: {id}',
        'no_admins': '📝 No active admins',
        'admin_list': '👥 *Administrators list:*\n\n',
        'admin_item': '• {name} ({username})\n  ID: `{id}`\n\n',
        'no_username': 'no username',
        'no_name': 'no name',
        
        # Статистика (дополнительные)
        'stats_total': '📈 Total signals: {count}',
        'stats_profitable': '✅ Profitable: {count}',
        'stats_unprofitable': '❌ Unprofitable: {count}',
        'stats_winrate': '💹 Winrate: *{winrate:.1f}%*',
        'stats_pnl': '💰 Total PnL: *{pnl:+.2f}%*',
        'stats_avg_rr': '📊 Avg RR: *{rr:.2f}*',
        'today_total': '📈 Total signals: {count}',
        'today_active': '🟢 Active: {count}',
        'week_total': '📈 Total signals: {count}',
        'week_pnl': '💰 PnL: *{pnl:+.2f}%*',
        
        # Конфигурация
        'config_title': '⚙️ *Current Bot Settings*',
        'config_status': '🤖 Status: {status}',
        'config_trading': '📊 *Trading:*',
        'config_pairs': '• Pairs: {pairs}',
        'config_timeframes': '• Timeframes: {timeframes}',
        'config_params': '🎯 *Parameters:*',
    },
    
    'ru': {
        # Команды
        'cmd_start': """
📊 Доступные команды:
/stats - Общая статистика
/today - Статистика за сегодня
/week - Статистика за неделю
/language - Сменить язык
""",
        'cmd_start_admin': """
📊 Публичные команды:
/stats - Общая статистика
/today - Статистика за сегодня
/week - Статистика за неделю
/language - Сменить язык

⚙️ Админ-команды:
/enable - Включить бота
/disable - Выключить бота

🗄️ База данных:
/dbstats - Статистика БД
/cleanup - Очистка старых сигналов

⚙️ Панель управления фильтрами:
/filters - Открыть панель управления
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
        'use_commands': """Используйте панель /filters для управления всеми настройками""",
        
        'bot_enabled': '✅ Бот включен',
        'bot_disabled': '⏸ Бот выключен',
        
        # Языки
        'language_select': 'Выберите язык / Select language:',
        'language_changed': '✅ Язык изменён на Русский',
        
        # Ошибки
        'no_permission': '❌ У вас нет прав для выполнения этой команды.\nТолько администраторы могут использовать эту команду.',
        'error': '❌ Ошибка',
        'usage': 'Использование',
        'error_number': '❌ Ошибка: укажите число от {min} до {max}',
        'error_invalid': '❌ Ошибка: неверное значение',
        'cannot_remove_last_admin': '❌ Нельзя удалить последнего админа!',
        
        # Команды настроек
        'current_pairs': '📊 Текущие пары: {pairs}',
        'pairs_help': 'Чтобы изменить пары, отправьте:\n`/setpairs BTC/USDT ETH/USDT SOL/USDT`\n\nПример:\n`/setpairs BTC/USDT ETH/USDT`',
        'current_timeframes': '⏰ Текущие таймфреймы: {timeframes}',
        'timeframes_help': 'Чтобы изменить таймфреймы, отправьте:\n`/settimeframes 5m 15m 1h 4h`\n\nПример:\n`/settimeframes 1m 5m 1h`',
        'pairs_updated': '✅ Торгуемые пары обновлены:\n{pairs}',
        'timeframes_updated': '✅ Таймфреймы обновлены:\n{timeframes}',
        'pairs_changed': '⚙️ Пары изменены: {pairs}',
        'timeframes_changed': '⚙️ Таймфреймы изменены: {timeframes}',
        
        # Админы
        'add_admin_usage': 'Использование:\n`/addadmin USER_ID`\n\nЧтобы узнать ID, попросите пользователя написать @username_to_id_bot',
        'remove_admin_usage': 'Использование:\n`/remove_admin USER_ID`',
        'admin_added': '✅ Админ {id} добавлен',
        'admin_removed': '✅ Админ {id} удалён',
        'new_admin_added': '👥 Новый админ добавлен: {id}',
        'admin_removed_msg': '👥 Админ удалён: {id}',
        'no_admins': '📝 Нет активных админов',
        'admin_list': '👥 *Список администраторов:*\n\n',
        'admin_item': '• {name} ({username})\n  ID: `{id}`\n\n',
        'no_username': 'нет username',
        'no_name': 'нет имени',
        
        # Статистика (дополнительные)
        'stats_total': '📈 Всего сигналов: {count}',
        'stats_profitable': '✅ Прибыльных: {count}',
        'stats_unprofitable': '❌ Убыточных: {count}',
        'stats_winrate': '💹 Winrate: *{winrate:.1f}%*',
        'stats_pnl': '💰 Общий PnL: *{pnl:+.2f}%*',
        'stats_avg_rr': '📊 Средний RR: *{rr:.2f}*',
        'today_total': '📈 Всего сигналов: {count}',
        'today_active': '🟢 Активных: {count}',
        'week_total': '📈 Всего сигналов: {count}',
        'week_pnl': '💰 PnL: *{pnl:+.2f}%*',
        
        # Конфигурация
        'config_title': '⚙️ *Текущие настройки бота*',
        'config_status': '🤖 Статус: {status}',
        'config_trading': '📊 *Торговля:*',
        'config_pairs': '• Пары: {pairs}',
        'config_timeframes': '• Таймфреймы: {timeframes}',
        'config_params': '🎯 *Параметры:*',
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

