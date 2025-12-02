"""
Панель управления фильтрами для Telegram бота
Красивый интерфейс с кнопками для настройки всех параметров фильтрации
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from typing import Dict, List, Optional
import json


class FilterSettings:
    """Хранилище настроек фильтров (в памяти, с возможностью сохранения в БД)"""
    
    # Значения по умолчанию
    DEFAULTS = {
        # === ФИЛЬТРЫ РЫНКА ===
        'top_coins_limit': 200,
        'min_futures_volume': 3_000_000,
        'min_volume_60m_ratio': 1.2,  # %
        'max_spread': 0.18,  # %
        'min_liquidity': 300_000,
        'atr_min': 0.3,  # %
        'atr_max': 3.5,  # %
        'max_atr_deviation': 35,  # %
        'max_candle_body_gap': 1.8,  # %
        'max_high_low_gap': 2.5,  # %
        
        # === BTC/ETH ФИЛЬТРЫ ===
        'btc_max_move_5m': 1.8,  # %
        'btc_max_move_15m': 2.8,  # %
        'btc_max_reversals': 2,
        'btc_pause_minutes': 20,
        'btc_strong_move_1h': 3.0,  # %
        'eth_max_move_15m': 2.5,  # %
        
        # === ВРЕМЕННЫЕ ФИЛЬТРЫ ===
        'time_guard_start': 5,  # минут
        'time_guard_end': 3,  # минут
        'min_hourly_volume': 75,  # %
        
        # === ИНДИКАТОРЫ ===
        'rsi_max_long': 68,
        'rsi_min_short': 32,
        'adx_min': 18,
        'adx_max': 45,
        'min_rr_ratio': 1.8,
        
        # === ТРЕНД И СТРУКТУРА ===
        'max_ema50_distance': 2.0,  # ATR
        'pullback_min': 0.3,  # ATR
        'pullback_max': 0.6,  # ATR
        'min_trend_candles': 3,
        
        # === КАЧЕСТВО СИГНАЛА ===
        'impulse_body_ratio': 60,  # %
        'impulse_avg_multiplier': 1.25,
        'max_dirty_candles': 3,
        'ema50_slope_min': 7,
        'max_bid_ask_imbalance': 35,  # %
        'max_stddev_ratio': 1.25,
        'max_saw_candles': 3,
        
        # === УРОВНИ ===
        'min_level_touches': 2,
        'htf_volume_multiplier': 1.3,
        'min_opposite_distance': 1.4,  # ATR
        'breakout_body_ratio': 55,  # %
        
        # === SL/TP ===
        'sl_tolerance_min': 0.4,  # ATR
        'sl_tolerance_max': 0.6,  # ATR
        'max_sl_distance': 1.6,  # ATR
        'min_sl_liquidity': 90_000,
        'max_ema50_deviation': 2.2,  # ATR
        'tp1_min': 1.0,  # ATR
        'tp1_max': 1.3,  # ATR
        'tp2_min': 2.0,  # ATR
        'tp2_max': 2.6,  # ATR
        
        # === РИСК-МЕНЕДЖМЕНТ ===
        'max_active_signals': 1,
        'cooldown_hours': 1,
        'min_data_candles': 150,
    }
    
    _settings = None
    
    @classmethod
    def get_all(cls) -> Dict:
        """Получить все настройки"""
        if cls._settings is None:
            cls._settings = cls.DEFAULTS.copy()
            cls._load_from_db()
        return cls._settings
    
    @classmethod
    def get(cls, key: str):
        """Получить значение настройки"""
        settings = cls.get_all()
        return settings.get(key, cls.DEFAULTS.get(key))
    
    @classmethod
    def set(cls, key: str, value):
        """Установить значение настройки"""
        if cls._settings is None:
            cls._settings = cls.DEFAULTS.copy()
        cls._settings[key] = value
        cls._save_to_db()
        cls._apply_to_filters()
    
    @classmethod
    def reset_all(cls):
        """Сбросить все настройки к значениям по умолчанию"""
        cls._settings = cls.DEFAULTS.copy()
        cls._save_to_db()
        cls._apply_to_filters()
    
    @classmethod
    def _load_from_db(cls):
        """Загрузить настройки из БД"""
        try:
            from database.models import get_db, BotConfig
            db = get_db()
            try:
                config = db.query(BotConfig).filter(
                    BotConfig.key == 'filter_settings'
                ).first()
                if config and config.value:
                    saved = json.loads(config.value)
                    cls._settings.update(saved)
            finally:
                db.close()
        except Exception as e:
            print(f"[FilterSettings] Error loading from DB: {e}")
    
    @classmethod
    def _save_to_db(cls):
        """Сохранить настройки в БД"""
        try:
            from database.models import get_db, BotConfig
            db = get_db()
            try:
                config = db.query(BotConfig).filter(
                    BotConfig.key == 'filter_settings'
                ).first()
                if config:
                    config.value = json.dumps(cls._settings)
                else:
                    config = BotConfig(
                        key='filter_settings',
                        value=json.dumps(cls._settings)
                    )
                    db.add(config)
                db.commit()
            finally:
                db.close()
        except Exception as e:
            print(f"[FilterSettings] Error saving to DB: {e}")
    
    @classmethod
    def _apply_to_filters(cls):
        """Применить настройки к фильтрам"""
        try:
            from analysis.market_filters import MarketFilters
            from analysis.signal_generator import SignalGenerator
            from analysis.conservative_filters import ConservativeFilters
            
            # Убеждаемся, что настройки загружены
            if cls._settings is None:
                cls._settings = cls.DEFAULTS.copy()
            
            s = cls._settings
            
            # Market Filters
            MarketFilters.TOP_COINS_LIMIT = s['top_coins_limit']
            MarketFilters.MIN_FUTURES_VOLUME_USDT = s['min_futures_volume']
            MarketFilters.MIN_VOLUME_60M_RATIO = s['min_volume_60m_ratio'] / 100
            MarketFilters.MAX_SPREAD_PERCENT = s['max_spread']
            MarketFilters.MIN_LIQUIDITY_USDT = s['min_liquidity']
            MarketFilters.ATR_MIN_PERCENT = s['atr_min']
            MarketFilters.ATR_MAX_PERCENT = s['atr_max']
            MarketFilters.MAX_ATR_DEVIATION = s['max_atr_deviation'] / 100
            MarketFilters.MAX_CANDLE_BODY_PERCENT = s['max_candle_body_gap']
            MarketFilters.MAX_HIGH_LOW_GAP_PERCENT = s['max_high_low_gap']
            
            # BTC/ETH Filters
            MarketFilters.BTC_MAX_MOVE_5M = s['btc_max_move_5m']
            MarketFilters.BTC_MAX_MOVE_15M = s['btc_max_move_15m']
            MarketFilters.BTC_MAX_REVERSALS_30M = s['btc_max_reversals']
            MarketFilters.BTC_PAUSE_MINUTES = s['btc_pause_minutes']
            MarketFilters.BTC_STRONG_MOVE_1H = s['btc_strong_move_1h']
            MarketFilters.ETH_MAX_MOVE_15M = s['eth_max_move_15m']
            
            # Time Filters
            MarketFilters.TIME_GUARD_START_MINUTES = s['time_guard_start']
            MarketFilters.TIME_GUARD_END_MINUTES = s['time_guard_end']
            MarketFilters.MIN_HOURLY_VOLUME_RATIO = s['min_hourly_volume'] / 100
            
            # Indicators
            MarketFilters.RSI_MAX_LONG = s['rsi_max_long']
            MarketFilters.RSI_MIN_SHORT = s['rsi_min_short']
            MarketFilters.ADX_MIN = s['adx_min']
            MarketFilters.ADX_MAX = s['adx_max']
            MarketFilters.MIN_RR_RATIO = s['min_rr_ratio']
            
            # Trend & Structure
            MarketFilters.MAX_EMA50_DISTANCE_ATR = s['max_ema50_distance']
            MarketFilters.PULLBACK_MIN_ATR = s['pullback_min']
            MarketFilters.PULLBACK_MAX_ATR = s['pullback_max']
            MarketFilters.MIN_TREND_CANDLES = s['min_trend_candles']
            
            # Signal Quality
            MarketFilters.IMPULSE_BODY_RATIO = s['impulse_body_ratio'] / 100
            MarketFilters.IMPULSE_AVG_MULTIPLIER = s['impulse_avg_multiplier']
            MarketFilters.MAX_DIRTY_CANDLES = s['max_dirty_candles']
            MarketFilters.EMA50_SLOPE_MIN_CANDLES = s['ema50_slope_min']
            MarketFilters.MAX_BID_ASK_IMBALANCE = s['max_bid_ask_imbalance'] / 100
            MarketFilters.MAX_STDDEV_RATIO = s['max_stddev_ratio']
            MarketFilters.MAX_SAW_CANDLES = s['max_saw_candles']
            
            # Levels
            MarketFilters.MIN_LEVEL_TOUCHES = s['min_level_touches']
            MarketFilters.HTF_VOLUME_MULTIPLIER = s['htf_volume_multiplier']
            MarketFilters.MIN_OPPOSITE_LEVEL_DISTANCE_ATR = s['min_opposite_distance']
            MarketFilters.BREAKOUT_BODY_RATIO = s['breakout_body_ratio'] / 100
            
            # SL/TP
            MarketFilters.SL_TOLERANCE_MIN_ATR = s['sl_tolerance_min']
            MarketFilters.SL_TOLERANCE_MAX_ATR = s['sl_tolerance_max']
            MarketFilters.MAX_SL_DISTANCE_ATR = s['max_sl_distance']
            MarketFilters.MIN_SL_LIQUIDITY_USDT = s['min_sl_liquidity']
            MarketFilters.MAX_EMA50_DEVIATION_ATR = s['max_ema50_deviation']
            MarketFilters.TP1_MIN_ATR = s['tp1_min']
            MarketFilters.TP1_MAX_ATR = s['tp1_max']
            MarketFilters.TP2_MIN_ATR = s['tp2_min']
            MarketFilters.TP2_MAX_ATR = s['tp2_max']
            
            # Signal Generator
            SignalGenerator.MIN_RR_RATIO = s['min_rr_ratio']
            SignalGenerator.SL_TOLERANCE_MIN_ATR = s['sl_tolerance_min']
            SignalGenerator.SL_TOLERANCE_MAX_ATR = s['sl_tolerance_max']
            SignalGenerator.MAX_SL_DISTANCE_ATR = s['max_sl_distance']
            SignalGenerator.MAX_EMA50_DISTANCE_ATR = s['max_ema50_distance']
            SignalGenerator.MAX_EMA50_DEVIATION_ATR = s['max_ema50_deviation']
            SignalGenerator.PULLBACK_MIN_ATR = s['pullback_min']
            SignalGenerator.PULLBACK_MAX_ATR = s['pullback_max']
            SignalGenerator.MIN_TREND_CANDLES = s['min_trend_candles']
            SignalGenerator.IMPULSE_BODY_RATIO = s['impulse_body_ratio'] / 100
            SignalGenerator.TP1_MIN_ATR = s['tp1_min']
            SignalGenerator.TP1_MAX_ATR = s['tp1_max']
            SignalGenerator.TP2_MIN_ATR = s['tp2_min']
            SignalGenerator.TP2_MAX_ATR = s['tp2_max']
            
            # Conservative Filters
            ConservativeFilters.MIN_LEVEL_TOUCHES = s['min_level_touches']
            ConservativeFilters.MIN_HTF_LEVEL_TOUCHES = s['min_level_touches']
            ConservativeFilters.HTF_VOLUME_MULTIPLIER = s['htf_volume_multiplier']
            ConservativeFilters.MIN_OPPOSITE_LEVEL_DISTANCE_ATR = s['min_opposite_distance']
            ConservativeFilters.BREAKOUT_BODY_RATIO = s['breakout_body_ratio'] / 100
            ConservativeFilters.MAX_BID_ASK_IMBALANCE = s['max_bid_ask_imbalance'] / 100
            
            # Risk Manager
            from database.risk_manager import RiskManager
            RiskManager.COOLDOWN_HOURS = s['cooldown_hours']
            RiskManager.MAX_SIGNALS_PER_COIN = s['max_active_signals']
            
            print("[FilterSettings] Applied to all filter classes")
            
        except Exception as e:
            print(f"[FilterSettings] Error applying to filters: {e}")


class FilterPanel:
    """Панель управления фильтрами с красивыми кнопками"""
    
    # Категории фильтров
    CATEGORIES = {
        'market': {
            'name': '📊 Фильтры рынка',
            'emoji': '📊',
            'filters': [
                ('top_coins_limit', 'Топ монет', '', [100, 150, 200, 250, 300]),
                ('min_futures_volume', 'Мин. объём', 'M$', [1, 2, 3, 5, 10]),
                ('min_volume_60m_ratio', 'Объём 60m', '%', [0.8, 1.0, 1.2, 1.5, 2.0]),
                ('max_spread', 'Макс. спред', '%', [0.10, 0.15, 0.18, 0.25, 0.35]),
                ('min_liquidity', 'Мин. ликвидность', 'K$', [100, 200, 300, 500, 1000]),
            ]
        },
        'atr': {
            'name': '📈 ATR волатильность',
            'emoji': '📈',
            'filters': [
                ('atr_min', 'ATR мин', '%', [0.1, 0.2, 0.3, 0.5, 0.8]),
                ('atr_max', 'ATR макс', '%', [2.0, 2.5, 3.0, 3.5, 5.0]),
                ('max_atr_deviation', 'Отклонение ATR', '%', [20, 25, 30, 35, 50]),
                ('max_candle_body_gap', 'Разрыв свечи', '%', [1.0, 1.5, 1.8, 2.5, 3.0]),
                ('max_high_low_gap', 'High/Low разрыв', '%', [1.5, 2.0, 2.5, 3.0, 4.0]),
            ]
        },
        'btc': {
            'name': '₿ BTC/ETH фильтры',
            'emoji': '₿',
            'filters': [
                ('btc_max_move_5m', 'BTC 5m', '%', [1.0, 1.5, 1.8, 2.0, 2.5]),
                ('btc_max_move_15m', 'BTC 15m', '%', [2.0, 2.5, 2.8, 3.0, 4.0]),
                ('btc_max_reversals', 'BTC развороты', '', [1, 2, 3, 4, 5]),
                ('btc_pause_minutes', 'Пауза BTC', 'мин', [10, 15, 20, 30, 60]),
                ('eth_max_move_15m', 'ETH 15m', '%', [1.5, 2.0, 2.5, 3.0, 4.0]),
            ]
        },
        'time': {
            'name': '⏰ Временные фильтры',
            'emoji': '⏰',
            'filters': [
                ('time_guard_start', 'Начало часа', 'мин', [0, 3, 5, 10, 15]),
                ('time_guard_end', 'Конец часа', 'мин', [0, 3, 5, 10, 15]),
                ('min_hourly_volume', 'Мин. час. объём', '%', [50, 60, 75, 85, 100]),
            ]
        },
        'indicators': {
            'name': '📉 Индикаторы',
            'emoji': '📉',
            'filters': [
                ('rsi_max_long', 'RSI макс LONG', '', [60, 65, 68, 70, 75]),
                ('rsi_min_short', 'RSI мин SHORT', '', [25, 30, 32, 35, 40]),
                ('adx_min', 'ADX мин', '', [15, 18, 20, 25, 30]),
                ('adx_max', 'ADX макс', '', [40, 45, 50, 55, 60]),
                ('min_rr_ratio', 'Мин. RR', ':1', [1.2, 1.5, 1.8, 2.0, 2.5]),
            ]
        },
        'trend': {
            'name': '📊 Тренд и структура',
            'emoji': '📊',
            'filters': [
                ('max_ema50_distance', 'EMA50 дистанция', 'ATR', [1.5, 2.0, 2.5, 3.0, 4.0]),
                ('pullback_min', 'Pullback мин', 'ATR', [0.2, 0.3, 0.4, 0.5, 0.6]),
                ('pullback_max', 'Pullback макс', 'ATR', [0.4, 0.5, 0.6, 0.8, 1.0]),
                ('min_trend_candles', 'Мин. тренд свечей', '/4', [2, 3, 4]),
            ]
        },
        'quality': {
            'name': '✨ Качество сигнала',
            'emoji': '✨',
            'filters': [
                ('impulse_body_ratio', 'Импульс тело', '%', [50, 55, 60, 65, 70]),
                ('impulse_avg_multiplier', 'Импульс множитель', 'x', [1.1, 1.2, 1.25, 1.3, 1.5]),
                ('max_dirty_candles', 'Грязные свечи', '/10', [2, 3, 4, 5]),
                ('ema50_slope_min', 'Наклон EMA50', '/10', [5, 6, 7, 8, 9]),
                ('max_bid_ask_imbalance', 'Bid/Ask дисбаланс', '%', [25, 30, 35, 40, 50]),
            ]
        },
        'levels': {
            'name': '📍 Уровни',
            'emoji': '📍',
            'filters': [
                ('min_level_touches', 'Мин. касания', '', [1, 2, 3, 4, 5]),
                ('htf_volume_multiplier', 'HTF объём', 'x', [1.1, 1.2, 1.3, 1.5, 2.0]),
                ('min_opposite_distance', 'До уровня', 'ATR', [1.0, 1.2, 1.4, 1.6, 2.0]),
                ('breakout_body_ratio', 'Пробой тело', '%', [45, 50, 55, 60, 70]),
            ]
        },
        'sltp': {
            'name': '🎯 SL/TP параметры',
            'emoji': '🎯',
            'filters': [
                ('sl_tolerance_min', 'SL допуск мин', 'ATR', [0.2, 0.3, 0.4, 0.5, 0.6]),
                ('sl_tolerance_max', 'SL допуск макс', 'ATR', [0.4, 0.5, 0.6, 0.7, 0.8]),
                ('max_sl_distance', 'Макс. SL', 'ATR', [1.2, 1.4, 1.6, 1.8, 2.0]),
                ('min_sl_liquidity', 'Ликвидность SL', 'K$', [50, 70, 90, 120, 150]),
                ('tp1_min', 'TP1 мин', 'ATR', [0.8, 1.0, 1.2, 1.5, 2.0]),
                ('tp2_min', 'TP2 мин', 'ATR', [1.5, 1.8, 2.0, 2.5, 3.0]),
            ]
        },
        'risk': {
            'name': '⚠️ Риск-менеджмент',
            'emoji': '⚠️',
            'filters': [
                ('max_active_signals', 'Макс. сигналов', '', [1, 2, 3, 5]),
                ('cooldown_hours', 'Cooldown', 'ч', [0.5, 1, 2, 4, 8]),
                ('min_data_candles', 'Мин. свечей', '', [50, 100, 150, 200, 300]),
            ]
        },
    }
    
    @staticmethod
    def get_main_menu() -> InlineKeyboardMarkup:
        """Главное меню панели управления"""
        keyboard = []
        
        # Заголовок
        keyboard.append([InlineKeyboardButton("⚙️ ПАНЕЛЬ УПРАВЛЕНИЯ ФИЛЬТРАМИ", callback_data="noop")])
        keyboard.append([InlineKeyboardButton("─────────────────────", callback_data="noop")])
        
        # Категории по 2 в ряд
        categories = list(FilterPanel.CATEGORIES.items())
        for i in range(0, len(categories), 2):
            row = []
            for j in range(2):
                if i + j < len(categories):
                    cat_id, cat_data = categories[i + j]
                    row.append(InlineKeyboardButton(
                        cat_data['name'],
                        callback_data=f"fp_cat_{cat_id}"
                    ))
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("─────────────────────", callback_data="noop")])
        
        # Дополнительные кнопки
        keyboard.append([
            InlineKeyboardButton("📋 Текущие настройки", callback_data="fp_show_all"),
            InlineKeyboardButton("🔄 Сбросить все", callback_data="fp_reset_confirm")
        ])
        
        keyboard.append([
            InlineKeyboardButton("❌ Закрыть", callback_data="fp_close")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_category_menu(category: str) -> InlineKeyboardMarkup:
        """Меню категории фильтров"""
        cat_data = FilterPanel.CATEGORIES.get(category)
        if not cat_data:
            return FilterPanel.get_main_menu()
        
        keyboard = []
        
        # Заголовок категории
        keyboard.append([InlineKeyboardButton(f"{cat_data['name']}", callback_data="noop")])
        keyboard.append([InlineKeyboardButton("─────────────────────", callback_data="noop")])
        
        # Фильтры категории
        for filter_key, filter_name, unit, values in cat_data['filters']:
            current_value = FilterSettings.get(filter_key)
            
            # Форматирование значения
            if filter_key == 'min_futures_volume':
                display_value = f"{current_value / 1_000_000:.1f}M$"
            elif filter_key == 'min_liquidity':
                display_value = f"{current_value / 1_000:.0f}K$"
            elif filter_key == 'min_sl_liquidity':
                display_value = f"{current_value / 1_000:.0f}K$"
            elif unit:
                display_value = f"{current_value}{unit}"
            else:
                display_value = str(current_value)
            
            keyboard.append([InlineKeyboardButton(
                f"{filter_name}: {display_value}",
                callback_data=f"fp_edit_{category}_{filter_key}"
            )])
        
        keyboard.append([InlineKeyboardButton("─────────────────────", callback_data="noop")])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="fp_main")])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_edit_menu(category: str, filter_key: str) -> InlineKeyboardMarkup:
        """Меню редактирования конкретного фильтра"""
        cat_data = FilterPanel.CATEGORIES.get(category)
        if not cat_data:
            return FilterPanel.get_main_menu()
        
        # Находим фильтр
        filter_data = None
        for f in cat_data['filters']:
            if f[0] == filter_key:
                filter_data = f
                break
        
        if not filter_data:
            return FilterPanel.get_category_menu(category)
        
        filter_key, filter_name, unit, values = filter_data
        current_value = FilterSettings.get(filter_key)
        
        keyboard = []
        
        # Заголовок
        keyboard.append([InlineKeyboardButton(f"✏️ {filter_name}", callback_data="noop")])
        keyboard.append([InlineKeyboardButton(f"Текущее: {current_value}{unit}", callback_data="noop")])
        keyboard.append([InlineKeyboardButton("─────────────────────", callback_data="noop")])
        
        # Кнопки со значениями по 3 в ряд
        for i in range(0, len(values), 3):
            row = []
            for j in range(3):
                if i + j < len(values):
                    val = values[i + j]
                    
                    # Преобразование для отображения
                    if filter_key == 'min_futures_volume':
                        display_val = f"{val}M$"
                        actual_val = val * 1_000_000
                    elif filter_key in ['min_liquidity', 'min_sl_liquidity']:
                        display_val = f"{val}K$"
                        actual_val = val * 1_000
                    else:
                        display_val = f"{val}{unit}"
                        actual_val = val
                    
                    # Отметка текущего значения
                    if actual_val == current_value or val == current_value:
                        display_val = f"✓ {display_val}"
                    
                    row.append(InlineKeyboardButton(
                        display_val,
                        callback_data=f"fp_set_{category}_{filter_key}_{val}"
                    ))
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("─────────────────────", callback_data="noop")])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data=f"fp_cat_{category}")])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_settings_text() -> str:
        """Текст с текущими настройками"""
        s = FilterSettings.get_all()
        
        text = """
📋 *ТЕКУЩИЕ НАСТРОЙКИ ФИЛЬТРОВ*

📊 *Фильтры рынка:*
├ Топ монет: {top_coins_limit}
├ Мин. объём: {min_futures_volume:,.0f}$
├ Объём 60m: {min_volume_60m_ratio}%
├ Макс. спред: {max_spread}%
└ Мин. ликвидность: {min_liquidity:,.0f}$

📈 *ATR волатильность:*
├ ATR: {atr_min}% - {atr_max}%
├ Отклонение ATR: ≤{max_atr_deviation}%
└ Разрывы: ≤{max_candle_body_gap}% / {max_high_low_gap}%

₿ *BTC/ETH фильтры:*
├ BTC 5m/15m: ≤{btc_max_move_5m}% / {btc_max_move_15m}%
├ BTC развороты: ≤{btc_max_reversals}
├ Пауза BTC: {btc_pause_minutes} мин
└ ETH 15m: ≤{eth_max_move_15m}%

⏰ *Временные:*
├ Начало часа: {time_guard_start} мин
├ Конец часа: {time_guard_end} мин
└ Мин. час. объём: {min_hourly_volume}%

📉 *Индикаторы:*
├ RSI LONG: ≤{rsi_max_long}
├ RSI SHORT: ≥{rsi_min_short}
├ ADX: {adx_min} - {adx_max}
└ Мин. RR: {min_rr_ratio}:1

📊 *Тренд и структура:*
├ EMA50 дистанция: ≤{max_ema50_distance} ATR
├ Pullback: {pullback_min}-{pullback_max} ATR
└ Мин. тренд: {min_trend_candles}/4 свечей

🎯 *SL/TP:*
├ SL допуск: {sl_tolerance_min}-{sl_tolerance_max} ATR
├ Макс. SL: ≤{max_sl_distance} ATR
├ TP1: {tp1_min}-{tp1_max} ATR
└ TP2: {tp2_min}-{tp2_max} ATR

⚠️ *Риск-менеджмент:*
├ Макс. сигналов: {max_active_signals}
├ Cooldown: {cooldown_hours} ч
└ Мин. свечей: {min_data_candles}
""".format(**s)
        
        return text.strip()


async def handle_filter_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback-ов панели фильтров"""
    query = update.callback_query
    data = query.data
    
    # Игнорируем noop (не отвечаем на него)
    if data == "noop":
        return
    
    # Закрыть панель
    if data == "fp_close":
        try:
            await query.answer("Панель закрыта")
            await query.message.delete()
        except:
            pass
        return
    
    # Для остальных callback-ов отвечаем
    await query.answer()
    
    # Главное меню
    if data == "fp_main":
        await query.edit_message_text(
            "⚙️ *Панель управления фильтрами*\n\nВыберите категорию для настройки:",
            reply_markup=FilterPanel.get_main_menu(),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Показать все настройки
    if data == "fp_show_all":
        text = FilterPanel.get_settings_text()
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="fp_main")]]
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Подтверждение сброса
    if data == "fp_reset_confirm":
        keyboard = [
            [
                InlineKeyboardButton("✅ Да, сбросить", callback_data="fp_reset_do"),
                InlineKeyboardButton("❌ Отмена", callback_data="fp_main")
            ]
        ]
        await query.edit_message_text(
            "⚠️ *Сбросить все настройки?*\n\nВсе фильтры будут возвращены к значениям по умолчанию.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Выполнить сброс
    if data == "fp_reset_do":
        FilterSettings.reset_all()
        await query.edit_message_text(
            "✅ *Настройки сброшены!*\n\nВсе фильтры возвращены к значениям по умолчанию.",
            reply_markup=FilterPanel.get_main_menu(),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Открыть категорию
    if data.startswith("fp_cat_"):
        try:
            category = data.replace("fp_cat_", "")
            cat_data = FilterPanel.CATEGORIES.get(category)
            if cat_data:
                await query.edit_message_text(
                    f"{cat_data['emoji']} *{cat_data['name']}*\n\nВыберите параметр для настройки:",
                    reply_markup=FilterPanel.get_category_menu(category),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await query.answer("❌ Категория не найдена", show_alert=True)
        except Exception as e:
            await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
        return
    
    # Редактирование фильтра
    if data.startswith("fp_edit_"):
        parts = data.replace("fp_edit_", "").split("_", 1)
        if len(parts) == 2:
            category, filter_key = parts
            await query.edit_message_text(
                "✏️ *Выберите новое значение:*",
                reply_markup=FilterPanel.get_edit_menu(category, filter_key),
                parse_mode=ParseMode.MARKDOWN
            )
        return
    
    # Установка значения
    if data.startswith("fp_set_"):
        try:
            # Формат: fp_set_{category}_{filter_key}_{value}
            # Разбиваем по последнему подчеркиванию (значение может быть числом с точкой)
            data_parts = data.replace("fp_set_", "")
            
            # Ищем последнее подчеркивание перед значением
            # Значение может быть int или float
            last_underscore_idx = data_parts.rfind("_")
            if last_underscore_idx == -1:
                return
            
            prefix = data_parts[:last_underscore_idx]
            value_str = data_parts[last_underscore_idx + 1:]
            
            # Разбиваем prefix на category и filter_key
            first_underscore_idx = prefix.find("_")
            if first_underscore_idx == -1:
                return
            
            category = prefix[:first_underscore_idx]
            filter_key = prefix[first_underscore_idx + 1:]
            
            # Преобразование значения
            try:
                if '.' in value_str:
                    value = float(value_str)
                else:
                    value = int(value_str)
            except (ValueError, TypeError):
                await query.answer("❌ Ошибка: неверное значение", show_alert=True)
                return
            
            # Специальная обработка для некоторых полей
            if filter_key == 'min_futures_volume':
                value = value * 1_000_000
            elif filter_key in ['min_liquidity', 'min_sl_liquidity']:
                value = value * 1_000
            
            # Сохраняем
            FilterSettings.set(filter_key, value)
            
            # Форматируем значение для отображения
            if filter_key == 'min_futures_volume':
                display_value = f"{value / 1_000_000:.1f}M$"
            elif filter_key in ['min_liquidity', 'min_sl_liquidity']:
                display_value = f"{value / 1_000:.0f}K$"
            else:
                display_value = str(value)
            
            await query.edit_message_text(
                f"✅ *Значение обновлено!*\n\n`{filter_key}` = `{display_value}`",
                reply_markup=FilterPanel.get_category_menu(category),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
        return

