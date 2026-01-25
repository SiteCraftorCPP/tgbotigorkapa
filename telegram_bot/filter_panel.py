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
    
    # Версия миграций настроек, чтобы не перетирать вручную выставленные значения
    MIGRATION_VERSION = 6

    # Значения по умолчанию
    DEFAULTS = {
        # === ФИЛЬТРЫ РЫНКА ===
        'top_coins_limit': 300,
        'min_futures_volume': 3_000_000,
        'min_volume_60m_ratio': 1.2,  # %
        'max_spread': 0.35,  # %
        'max_avg_spread_15m': 0.35,  # % (1h средний спред)
        'min_liquidity': 300_000,
        'funding_rate_min': -0.08,  # %
        'funding_rate_max': 0.08,  # %
        'max_oi_change_15m': 35.0,  # % (1h изменение OI)
        'min_contract_age_days': 10,
        'atr_min': 1.5,  # %
        'atr_max': 9.0,  # %
        'max_atr_deviation': 35,  # %
        'max_candle_body_gap': 5.0,  # %
        'max_high_low_gap': 7.0,  # %
        
        # === BTC/ETH ФИЛЬТРЫ ===
        'btc_max_move_1h': 4.5,  # %
        'btc_max_reversals': 1,
        'btc_pause_minutes': 35,
        'btc_strong_move_1h': 3.0,  # %
        'eth_max_move_1h': 4.0,  # %
        
        # === ВРЕМЕННЫЕ ФИЛЬТРЫ ===
        'time_guard_start': 0,  # минут
        'time_guard_end': 0,  # минут
        'min_hourly_volume': 60,  # %
        
        # === ИНДИКАТОРЫ ===
        'rsi_max_long': 70,
        'rsi_min_short': 30,
        'adx_min': 20,
        'adx_max': 55,
        # (RR управляется логикой MEGABOT, не настраивается здесь)
        
        # === ТРЕНД И СТРУКТУРА ===
        'max_ema50_distance': 2.5,  # ATR
        'pullback_min': 0.3,  # ATR
        'pullback_max': 1.0,  # ATR
        'min_trend_candles': 0.333,  # 1 из 3 свечей (0.333) или N из 4
        'trend_neutral_threshold': 20,  # Порог нейтральности тренда (score)
        'trend_strong_threshold': 35,  # Порог сильного тренда H1 (score)
        
        # === КАЧЕСТВО СИГНАЛА ===
        'impulse_body_ratio': 43,  # % (синхронизировано с SignalGenerator)
        'impulse_avg_multiplier': 1.05,
        'max_dirty_candles': 4,
        'ema50_slope_min': 6,
        'max_bid_ask_imbalance': 40,  # %
        'max_stddev_ratio': 1.35,
        'max_saw_candles': 4,
        'signal_volume_multiplier': 1.03,  # Объём импульсной свечи ≥ 1.03× среднего за 40 свечей
        'volume_contraction_ratio': 0.9,  # Откат на пониженном объёме < 90% среднего
        'pattern_check_enabled': True,  # Включить проверку паттерна
        
        # === УРОВНИ ===
        'min_level_touches': 2,
        'htf_volume_multiplier': 1.3,
        'min_opposite_distance': 1.8,  # ATR
        'breakout_body_ratio': 55,  # %
    }
    
    _settings = None
    
    @classmethod
    def get_all(cls, force_reload: bool = False) -> Dict:
        """Получить все настройки (гарантированно актуальные из БД)"""
        if cls._settings is None or force_reload:
            cls._settings = cls.DEFAULTS.copy()
            cls._load_from_db()
            
            # При первом запуске: если baseline нет, сохраняем текущие значения как baseline
            if cls._load_baseline_from_db() is None:
                baseline = cls._settings.copy()
                cls._save_baseline_to_db(baseline)
        
        return cls._settings
    
    @classmethod
    def get(cls, key: str):
        """Получить значение настройки"""
        settings = cls.get_all()
        return settings.get(key, cls.DEFAULTS.get(key))
    
    @classmethod
    def set(cls, key: str, value):
        """Установить значение настройки"""
        from utils.logger import log_info
        
        # Загружаем актуальные настройки
        if cls._settings is None:
            cls._settings = cls.DEFAULTS.copy()
            cls._load_from_db()
        
        old_value = cls._settings.get(key)
        cls._settings[key] = value
        
        # Сохраняем в БД
        cls._save_to_db()
        
        # Сбрасываем кэш и применяем (применение перезагрузит из БД)
        cls._settings = None
        cls._apply_to_filters()
        
        log_info(f"[FilterSettings] 🔄 Updated {key}: {old_value} → {value} (saved to DB and applied)")
    
    @classmethod
    def reset_all(cls):
        """Сбросить все настройки к базовым значениям из БД"""
        from utils.logger import log_info
        
        # Загружаем базовые значения из БД
        baseline = cls._load_baseline_from_db()
        if not baseline:
            # Если baseline нет, используем текущие значения как baseline
            baseline = cls.get_all(force_reload=True).copy()
            cls._save_baseline_to_db(baseline)
            log_info("[FilterSettings] Baseline created from current settings")
        
        # Применяем базовые значения
        cls._settings = baseline.copy()
        cls._save_to_db()  # Сохраняем как текущие настройки
        cls._apply_to_filters()
        log_info("[FilterSettings] Settings reset to baseline values")
    
    @classmethod
    def save_current_as_baseline(cls):
        """Сохранить текущие настройки как базовые (для сброса)"""
        from utils.logger import log_info
        current = cls.get_all(force_reload=True).copy()
        cls._save_baseline_to_db(current)
        log_info("[FilterSettings] Current settings saved as baseline")
    
    @classmethod
    def _load_baseline_from_db(cls) -> Optional[Dict]:
        """Загрузить базовые настройки из БД"""
        try:
            from database.models import SessionLocal, BotConfig
            db = SessionLocal()
            try:
                config = db.query(BotConfig).filter(
                    BotConfig.key == 'filter_settings_baseline'
                ).first()
                if config and config.value:
                    return json.loads(config.value)
            finally:
                db.close()
        except Exception as e:
            print(f"[FilterSettings] Error loading baseline from DB: {e}")
        return None
    
    @classmethod
    def _save_baseline_to_db(cls, settings: Dict):
        """Сохранить базовые настройки в БД"""
        try:
            from database.models import SessionLocal, BotConfig
            db = SessionLocal()
            try:
                config = db.query(BotConfig).filter(
                    BotConfig.key == 'filter_settings_baseline'
                ).first()
                if config:
                    config.value = json.dumps(settings)
                else:
                    config = BotConfig(
                        key='filter_settings_baseline',
                        value=json.dumps(settings)
                    )
                    db.add(config)
                db.commit()
            finally:
                db.close()
        except Exception as e:
            print(f"[FilterSettings] Error saving baseline to DB: {e}")
    
    @classmethod
    def reset_to_current(cls):
        """
        Сбросить к актуальным сохранённым значениям (перечитать из БД)
        без отката к дефолтным настройкам.
        """
        cls._settings = None
        cls.get_all(force_reload=True)
        cls._apply_to_filters()
    
    @classmethod
    def _load_from_db(cls):
        """Загрузить настройки из БД"""
        try:
            from database.models import SessionLocal, BotConfig
            db = SessionLocal()
            try:
                config = db.query(BotConfig).filter(
                    BotConfig.key == 'filter_settings'
                ).first()
                if config and config.value:
                    saved = json.loads(config.value)
                    # Удаляем удаленные настройки риск-менеджмента (если они есть в БД)
                    saved.pop('max_active_signals', None)
                    saved.pop('cooldown_hours', None)
                    saved.pop('min_data_candles', None)
                    cls._settings.update(saved)
                    
                    # Авто-обновление легаси-значений до новых целевых фильтров
                    if cls._apply_legacy_migrations():
                        cls._save_to_db()
            finally:
                db.close()
        except Exception as e:
            print(f"[FilterSettings] Error loading from DB: {e}")
    
    @classmethod
    def _apply_legacy_migrations(cls) -> bool:
        """
        Подтягиваем старые значения фильтров к новым требованиям,
        чтобы текущие настройки соответствовали обновлённым лимитам.
        """
        changed = False

        # Пропускаем миграции, если уже применена актуальная версия
        current_version = cls._settings.get('_migration_version', 0)
        if current_version >= cls.MIGRATION_VERSION:
            return False
        
        # Мягкие миграции: заполняем только отсутствующие или явно устаревшие значения,
        # не перетирая то, что админ выставил вручную.
        def ensure_default(key: str, target):
            nonlocal changed
            if key not in cls._settings:
                cls._settings[key] = target
                changed = True

        # Минимальный порог ATR мин — только если в сохранённых настройках он ниже 1.0
        atr_min = cls._settings.get('atr_min')
        if atr_min is None or atr_min < 1.0:
            cls._settings['atr_min'] = 1.0
            changed = True

        # Базовые значения для новых ключей (не трогаем, если ключ уже есть)
        target_defaults = {
            # Рынок
            'min_futures_volume': 3_000_000,
            'min_volume_60m_ratio': 1.2,
            'min_liquidity': 300_000,
            'max_spread': 0.35,
            'max_avg_spread_15m': 0.35,  # теперь 1h средний спред
            'funding_rate_min': -0.08,
            'funding_rate_max': 0.08,
            'max_oi_change_15m': 35.0,  # теперь 1h изменение OI
            'min_contract_age_days': 10,
            # Время
            'time_guard_start': 0,
            'time_guard_end': 0,
            'min_hourly_volume': 60,
            # ATR/структура
            'atr_min': 1.5,
            'atr_max': 9.0,
            'max_ema50_distance': 2.5,
            'pullback_min': 0.3,
            'min_opposite_distance': 1.8,
            'max_candle_body_gap': 5.0,
            'max_high_low_gap': 7.0,
            'trend_neutral_threshold': 20,
            'trend_strong_threshold': 35,
            # Уровни
            'htf_volume_multiplier': 1.3,
            'breakout_body_ratio': 55,
            # Индикаторы
            'rsi_max_long': 70,
            'rsi_min_short': 30,
            'adx_min': 20,
            'adx_max': 55,
            # BTC/ETH
            'btc_strong_move_1h': 3.0,
            'btc_max_move_1h': 4.5,
            'btc_max_reversals': 1,
            'btc_pause_minutes': 35,
            'eth_max_move_1h': 4.0,
            # Качество
            'impulse_body_ratio': 43,
            'impulse_avg_multiplier': 1.05,
            'max_dirty_candles': 4,
            'ema50_slope_min': 6,
            'max_bid_ask_imbalance': 40,
            'max_stddev_ratio': 1.35,
            'max_saw_candles': 4,
            'volume_contraction_ratio': 0.9,
            'pattern_check_enabled': True,
            'signal_volume_multiplier': 1.03,  # Объём импульсной свечи ≥ 1.03× среднего за 40 свечей
        }
        for key, target in target_defaults.items():
            ensure_default(key, target)

        # Точечные обновления старых базовых значений → новые целевые
        if cls._settings.get('max_avg_spread_15m') == 0.30:
            cls._settings['max_avg_spread_15m'] = 0.35
            changed = True
        if cls._settings.get('max_oi_change_15m') == 25.0:
            cls._settings['max_oi_change_15m'] = 35.0
            changed = True
        # ATR диапазон
        if cls._settings.get('atr_min', 0) < 1.5:
            cls._settings['atr_min'] = 1.5
            changed = True
        if cls._settings.get('atr_max', 0) < 9.0:
            cls._settings['atr_max'] = 9.0
            changed = True
        # Разрывы
        if cls._settings.get('max_candle_body_gap', 0) < 5.0:
            cls._settings['max_candle_body_gap'] = 5.0
            changed = True
        if cls._settings.get('max_high_low_gap', 0) < 7.0:
            cls._settings['max_high_low_gap'] = 7.0
            changed = True
        # ADX минимум
        if cls._settings.get('adx_min', 0) < 20:
            cls._settings['adx_min'] = 20
            changed = True
        # BTC/ETH пороги обновляем до новых целевых (жёстко)
        if cls._settings.get('btc_max_move_1h') != 4.5:
            cls._settings['btc_max_move_1h'] = 4.5
            changed = True
        if cls._settings.get('btc_pause_minutes') != 35:
            cls._settings['btc_pause_minutes'] = 35
            changed = True
        if cls._settings.get('eth_max_move_1h') != 4.0:
            cls._settings['eth_max_move_1h'] = 4.0
            changed = True

        # Структура/уровни обновляем до новых целевых значений, если стоят старые дефолты
        if cls._settings.get('max_ema50_distance') == 3.0:
            cls._settings['max_ema50_distance'] = 2.5
            changed = True
        if cls._settings.get('htf_volume_multiplier') == 1.2:
            cls._settings['htf_volume_multiplier'] = 1.3
            changed = True
        if cls._settings.get('breakout_body_ratio') == 50:
            cls._settings['breakout_body_ratio'] = 55
            changed = True

        # Версия 6: жёсткое применение новых значений для логики 1H
        if current_version < 6:
            cls._settings['max_ema50_distance'] = 2.5
            cls._settings['htf_volume_multiplier'] = 1.3
            cls._settings['breakout_body_ratio'] = 55
            changed = True
        
        # Обновление объёма импульсной/сигнальной свечи на 1.03 (принудительно)
        current_volume = cls._settings.get('signal_volume_multiplier')
        if current_volume != 1.03:
            cls._settings['signal_volume_multiplier'] = 1.03
            changed = True
        
        # Обновление импульсных фильтров (принудительно)
        if cls._settings.get('impulse_body_ratio') != 43:
            cls._settings['impulse_body_ratio'] = 43
            changed = True
        if cls._settings.get('impulse_avg_multiplier') != 1.05:
            cls._settings['impulse_avg_multiplier'] = 1.05
            changed = True

        # Фиксируем версию миграции, чтобы не применять её повторно
        if current_version < cls.MIGRATION_VERSION:
            cls._settings['_migration_version'] = cls.MIGRATION_VERSION
            changed = True

        return changed
    
    @classmethod
    def _save_to_db(cls):
        """Сохранить настройки в БД"""
        try:
            from database.models import SessionLocal, BotConfig
            db = SessionLocal()
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
        """Применить настройки к фильтрам МГНОВЕННО"""
        try:
            from analysis.market_filters import MarketFilters
            from analysis.signal_generator import SignalGenerator
            from analysis.conservative_filters import ConservativeFilters
            from analysis.multi_timeframe import MultiTimeframeAnalysis
            
            # Сбрасываем кэш, чтобы подтянулись свежие данные из БД
            cls._settings = None 
            s = cls.get_all()
            
            # --- РЫНОК ---
            MarketFilters.TOP_COINS_LIMIT = s['top_coins_limit']
            MarketFilters.MIN_FUTURES_VOLUME_USDT = s['min_futures_volume']
            MarketFilters.MAX_SPREAD_PERCENT = s['max_spread']
            
            # --- ТРЕНД (MultiTimeframe) ---
            MultiTimeframeAnalysis.TREND_NEUTRAL_THRESHOLD = s.get('trend_neutral_threshold', 20)
            MultiTimeframeAnalysis.TREND_STRONG_THRESHOLD = s.get('trend_strong_threshold', 35)
            
            # --- КАЧЕСТВО ---
            MarketFilters.EMA50_SLOPE_MIN_CANDLES = s.get('ema50_slope_min', 6)
            
            # --- ГЕНЕРАТОР (Теперь параметры не статические, а берутся при создании объекта) ---
            # Мы обновили SignalGenerator.__init__, так что он сам подхватит s
            
            from utils.logger import log_info
            log_info(f"[FilterSettings] ✅ Applied {len(s)} settings to bot engine")
            
        except Exception as e:
            from utils.logger import log_error
            log_error(f"[FilterSettings] ❌ Sync error: {e}", "apply_filters")


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
            ('min_volume_60m_ratio', 'Объём 1h', '%', [0.8, 1.0, 1.2, 1.5, 2.0]),
                ('max_spread', 'Макс. спред', '%', [0.10, 0.15, 0.18, 0.25, 0.35]),
            ('max_avg_spread_15m', 'Средний спред 1h', '%', [0.20, 0.25, 0.30, 0.32, 0.35]),
                ('min_liquidity', 'Мин. ликвидность', 'K$', [100, 200, 300, 500, 1000]),
                ('funding_rate_min', 'Funding Rate мин', '%', [-0.10, -0.08, -0.06, -0.04, -0.02]),
                ('funding_rate_max', 'Funding Rate макс', '%', [0.02, 0.04, 0.06, 0.08, 0.10]),
            ('max_oi_change_15m', 'Изменение OI 1h', '%', [15, 20, 25, 30, 35]),
                ('min_contract_age_days', 'Возраст контракта', 'дн', [10, 15, 20, 25, 30]),
            ]
        },
        'atr': {
            'name': '📈 ATR волатильность',
            'emoji': '📈',
            'filters': [
                ('atr_min', 'ATR мин', '%', [1.0, 1.2, 1.5, 2.0, 3.0]),
                ('atr_max', 'ATR макс', '%', [5.0, 6.0, 7.0, 8.0, 9.0]),
                ('max_atr_deviation', 'Отклонение ATR', '%', [20, 25, 30, 35, 50]),
                ('max_candle_body_gap', 'Разрыв свечи', '%', [2.5, 3.0, 4.0, 5.0, 6.0]),
                ('max_high_low_gap', 'High/Low разрыв', '%', [3.0, 4.0, 5.0, 6.0, 7.0]),
            ]
        },
        'btc': {
            'name': '₿ BTC/ETH фильтры',
            'emoji': '₿',
            'filters': [
                ('btc_max_move_1h', 'BTC 1h движение', '%', [2.0, 2.5, 3.0, 3.5, 4.5]),
                ('btc_max_reversals', 'BTC 1h развороты', '', [1, 2, 3]),
                ('btc_pause_minutes', 'Пауза BTC (1h импульс)', 'мин', [10, 20, 25, 30, 35]),
                ('btc_strong_move_1h', 'BTC импульс 1h порог', '%', [2.5, 3.0, 3.5, 4.0, 4.5]),
                ('eth_max_move_1h', 'ETH 1h движение', '%', [3.0, 3.5, 4.0, 4.5]),
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
            ('adx_min', 'ADX мин', '', [18, 20, 22, 25, 30]),
                ('adx_max', 'ADX макс', '', [40, 45, 50, 55, 60]),
            ]
        },
        'trend': {
            'name': '📊 Тренд и структура',
            'emoji': '📊',
            'filters': [
                ('max_ema50_distance', 'EMA50 дистанция (1H)', ' ATR', [1.5, 2.0, 2.5, 3.0, 4.0, 5.0]),
                ('pullback_min', 'Pullback мин (1H)', ' ATR', [0.3, 0.4, 0.5, 0.6, 0.8]),
                ('pullback_max', 'Pullback макс (1H)', ' ATR', [0.8, 0.9, 1.0, 1.1, 1.2]),
                ('min_trend_candles', 'Мин. тренд свечей', '/4', [0.333, 1, 2, 3, 4]),
                ('trend_neutral_threshold', 'Порог нейтральности', ' score', [15, 20, 25, 30, 35]),
                ('trend_strong_threshold', 'Порог сильного тренда', ' score', [30, 35, 40, 45, 50]),
            ]
        },
        'quality': {
            'name': '✨ Качество сигнала',
            'emoji': '✨',
            'filters': [
                ('impulse_body_ratio', 'Импульс тело', '%', [40, 43, 45, 50, 55, 60, 65, 70]),
                ('impulse_avg_multiplier', 'Импульс множитель', 'x', [1.05, 1.1, 1.15, 1.2, 1.25, 1.3, 1.5]),
                ('max_dirty_candles', 'Грязные свечи', '/10', [2, 3, 4, 5]),
                ('ema50_slope_min', 'Наклон EMA50', '/10', [5, 6, 7, 8, 9]),
                ('max_bid_ask_imbalance', 'Bid/Ask дисбаланс', '%', [25, 30, 35, 40, 50]),
                ('max_stddev_ratio', 'StdDev отношение', 'x', [1.0, 1.15, 1.25, 1.35, 1.5]),
                ('max_saw_candles', 'Пила-свечи', '/12', [2, 3, 4, 5]),
                ('volume_contraction_ratio', 'Volume contraction', 'x', [0.6, 0.7, 0.8, 0.9, 1.0]),
                ('pattern_check_enabled', 'Проверка паттерна', '', [True, False]),
            ]
        },
        'levels': {
            'name': '📍 Уровни',
            'emoji': '📍',
            'filters': [
                ('min_level_touches', 'Мин. касания (HTF 1H)', '', [1, 2, 3, 4, 5]),
                ('htf_volume_multiplier', 'HTF объём (1H)', 'x', [1.1, 1.2, 1.3, 1.5, 2.0]),
                ('min_opposite_distance', 'До уровня', 'ATR', [1.2, 1.4, 1.6, 1.8, 2.0]),
                ('breakout_body_ratio', 'Пробой тело (1H)', '%', [45, 50, 55, 60, 70]),
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
            InlineKeyboardButton("📋 Текущие настройки", callback_data="fp_show_all")
        ])
        keyboard.append([
            InlineKeyboardButton("🔄 Сбросить к базовым", callback_data="fp_reset_confirm"),
            InlineKeyboardButton("💾 Сохранить как базовые", callback_data="fp_save_baseline_confirm")
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
            elif filter_key in ['funding_rate_min', 'funding_rate_max']:
                display_value = f"{current_value}%"
            elif filter_key == 'min_contract_age_days':
                display_value = f"{current_value}дн"
            elif filter_key == 'pattern_check_enabled':
                display_value = "ВКЛ" if current_value else "ВЫКЛ"
            elif filter_key == 'min_trend_candles':
                # Специальное форматирование для min_trend_candles
                if abs(current_value - 0.333) < 0.001:
                    display_value = "1/3"
                else:
                    display_value = f"{int(current_value)}/4"
            elif filter_key in ['max_ema50_distance', 'pullback_min', 'pullback_max', 'min_opposite_distance']:
                # Для ATR значений показываем с одним знаком после запятой
                display_value = f"{current_value:.1f}{unit}"
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
        
        # Форматирование текущего значения для отображения
        if filter_key in ['max_ema50_distance', 'pullback_min', 'pullback_max', 'min_opposite_distance']:
            current_display = f"{current_value:.1f}{unit}"
        elif filter_key == 'min_futures_volume':
            current_display = f"{current_value / 1_000_000:.1f}M$"
        elif filter_key in ['min_liquidity']:
            current_display = f"{current_value / 1_000:.0f}K$"
        elif filter_key in ['funding_rate_min', 'funding_rate_max']:
            current_display = f"{current_value}%"
        elif filter_key == 'min_contract_age_days':
            current_display = f"{current_value}дн"
        elif filter_key == 'pattern_check_enabled':
            current_display = "ВКЛ" if current_value else "ВЫКЛ"
        elif filter_key == 'min_trend_candles':
            # Специальное форматирование для min_trend_candles
            if abs(current_value - 0.333) < 0.001:
                current_display = "1/3"
            else:
                current_display = f"{int(current_value)}/4"
        elif unit:
            current_display = f"{current_value}{unit}"
        else:
            current_display = str(current_value)
        
        keyboard.append([InlineKeyboardButton(f"Текущее: {current_display}", callback_data="noop")])
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
                    elif filter_key in ['min_liquidity']:
                        display_val = f"{val}K$"
                        actual_val = val * 1_000
                    elif filter_key in ['funding_rate_min', 'funding_rate_max']:
                        display_val = f"{val}%"
                        actual_val = val
                    elif filter_key == 'min_contract_age_days':
                        display_val = f"{val}дн"
                        actual_val = val
                    elif filter_key == 'pattern_check_enabled':
                        display_val = "ВКЛ" if val else "ВЫКЛ"
                        actual_val = val
                    elif filter_key == 'min_trend_candles':
                        # Специальное форматирование для min_trend_candles
                        if abs(val - 0.333) < 0.001:
                            display_val = "1/3"
                        else:
                            display_val = f"{int(val)}/4"
                        actual_val = val
                    else:
                        display_val = f"{val}{unit}"
                        actual_val = val
                    
                    # Отметка текущего значения (с учетом погрешности для float)
                    is_match = False
                    if isinstance(current_value, float) and isinstance(actual_val, float):
                        is_match = abs(actual_val - current_value) < 0.001
                    elif isinstance(current_value, float) and isinstance(val, (int, float)):
                        is_match = abs(val - current_value) < 0.001
                    else:
                        is_match = (actual_val == current_value or val == current_value)
                    
                    if is_match:
                        display_val = f"✓ {display_val}"
                    
                    # Для boolean значений передаем как строку
                    if isinstance(val, bool):
                        callback_val = "True" if val else "False"
                    else:
                        callback_val = str(val)
                    
                    row.append(InlineKeyboardButton(
                        display_val,
                        callback_data=f"fp_set_{category}_{filter_key}_{callback_val}"
                    ))
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("─────────────────────", callback_data="noop")])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data=f"fp_cat_{category}")])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_settings_text() -> str:
        """Текст с текущими настройками"""
        # ВСЕГДА загружаем актуальные настройки из БД (не используем кэш)
        # Сбрасываем кэш и загружаем заново, чтобы гарантировать актуальность
        FilterSettings._settings = FilterSettings.DEFAULTS.copy()
        FilterSettings._load_from_db()
        s = FilterSettings._settings.copy()  # Копия для форматирования
        
        # Удаляем удаленные настройки риск-менеджмента из словаря (если они есть)
        s.pop('max_active_signals', None)
        s.pop('cooldown_hours', None)
        s.pop('min_data_candles', None)
        s.pop('_migration_version', None)
        
        # Вычисляем значения для форматирования
        pattern_status = 'ВКЛ' if s.get('pattern_check_enabled', True) else 'ВЫКЛ'
        
        # Форматируем значения для отображения (как в категориях)
        min_futures_volume_display = f"{s['min_futures_volume'] / 1_000_000:.1f}M$"
        min_liquidity_display = f"{s['min_liquidity'] / 1_000:.0f}K$"
        
        # Форматирование для min_trend_candles
        min_trend_candles_value = s.get('min_trend_candles', 3)
        if abs(min_trend_candles_value - 0.333) < 0.001:
            min_trend_candles_display = "1/3"
        else:
            min_trend_candles_display = f"{int(min_trend_candles_value)}/4"
        
        text = """
📋 *ТЕКУЩИЕ НАСТРОЙКИ ФИЛЬТРОВ*

📊 *Фильтры рынка:*
├ Топ монет: {top_coins_limit}
├ Мин. объём: {min_futures_volume_display}
├ Объём 1h: {min_volume_60m_ratio}%
├ Макс. спред: {max_spread}%
├ Средний спред 1h: ≤{max_avg_spread_15m}%
├ Мин. ликвидность: {min_liquidity_display}
├ Funding Rate: {funding_rate_min}% до {funding_rate_max}%
├ Изменение OI 1h: ≤{max_oi_change_15m}%
└ Возраст контракта: ≥{min_contract_age_days} дней

📈 *ATR волатильность:*
├ ATR: {atr_min}% - {atr_max}% (1h)
├ Отклонение ATR: ≤{max_atr_deviation}%
└ Разрывы: ≤{max_candle_body_gap}% / {max_high_low_gap}%

₿ *BTC/ETH фильтры:*
├ BTC 1h движение: ≤{btc_max_move_1h}%
├ BTC 1h импульс против сигнала: запрещён
├ BTC 1h разворотные паттерны: ≤{btc_max_reversals} (мягкая проверка)
├ BTC состояние: StdDev ≤ 1.4× (не фаза высокой волатильности)
├ Пауза после резкого движения BTC (1h): {btc_pause_minutes} мин
└ ETH 1h движение: ≤{eth_max_move_1h}%

⏰ *Временные:*
├ Начало часа: {time_guard_start} мин
├ Конец часа: {time_guard_end} мин
└ Мин. час. объём: {min_hourly_volume}%

📉 *Индикаторы:*
├ RSI LONG: ≤{rsi_max_long}
├ RSI SHORT: ≥{rsi_min_short}
└ ADX: {adx_min} - {adx_max}

📊 *Тренд и структура:*
├ EMA50 дистанция: ≤{max_ema50_distance:.1f} ATR
├ Pullback: {pullback_min:.1f}-{pullback_max:.1f} ATR
├ Мин. тренд: {min_trend_candles_display} свечей
├ Порог нейтральности: {trend_neutral_threshold} score
├ Порог сильного тренда: {trend_strong_threshold} score
└ Структура: HH+HL (LONG) / LL+LH (SHORT) желательна (мягкая проверка)

📍 *Уровни:*
├ Мин. касания: {min_level_touches}
├ HTF объём: ≥{htf_volume_multiplier}× среднего
├ До противоположного уровня: ≥{min_opposite_distance:.1f} ATR
└ Пробой тело: ≥{breakout_body_ratio}%

✨ *Качество сигнала:*
├ Импульс тело: {impulse_body_ratio}%
├ Импульс множитель: {impulse_avg_multiplier}x
├ Грязные свечи: ≤{max_dirty_candles}/10
├ Наклон EMA50: ≥{ema50_slope_min}/10
├ Bid/Ask дисбаланс: ≤{max_bid_ask_imbalance}%
├ StdDev отношение: ≤{max_stddev_ratio}x
├ Пила-свечи: ≤{max_saw_candles}/12
├ Volume contraction: <{volume_contraction_ratio}x среднего
└ Паттерн: {pattern_status}

📋 *ЛОГИЧЕСКИЕ ФИЛЬТРЫ (TF = 1H):*

🔄 *Тренд и структура:*
├ Запрет входа против тренда H1
├ Для лонга: HH или HL желательны (мягкая проверка)
└ Для шорта: LL или LH желательны (мягкая проверка)

🎯 *Сигнал • Вход (1H):*
├ Сигнал формируется только при полной валидности всех фильтров
├ Тип сигнала: лонг/шорт строго по направлению тренда и структуры
├ Сигнал подаётся только после закрытия сигнальной свечи (1H)
├ Свеча сигнала: тело ≥ 60% и ≤ 1.8× среднего тела за 20 свечей (1H)
├ Объём импульсной свечи: ≥{signal_volume_multiplier}× среднего за 40 свечей (1H)
├ Структурное подтверждение обязательно (HH+HL для лонга / LL+LH для шорта) (1H)
├ Минимальная дистанция между HL и предыдущим HL ≥ 1.0 ATR (1H)
├ Минимальная дистанция между LH и предыдущим LH ≥ 1.0 ATR (1H)
├ Pullback перед сигналом в диапазоне 0.3–1.0 ATR (1H)
├ EMA50 направлена в сторону сигнала; отклонение ≤ 2.5 ATR (1H)
├ Уровень подтверждён минимум 2 касаниями (HTF — объём ≥ 1.3× среднего) (1H)
├ Пробой уровня: тело ≥ 55% свечи относительно уровня (1H)
├ Структура должна оставаться интактной (1H)
├ Сигнал не подаётся при нарушении структуры в момент формирования
├ Сигнал не подаётся, если область за ключевым уровнем по ликвидности заведомо "дырявая" (по внутренним метрикам MEGABOT)
├ Сигнал отменяется при обратном импульсе (тело ≥ 1.3× среднего за 20 свечей) (1H)
└ Повторный сигнал возможен только после обновления структуры и нового паттерна (1H)

📊 *ВСЕГО ФИЛЬТРОВ: 63*
├ Настраиваемых: 47
└ Логических: 16
""".format(
            **s, 
            pattern_status=pattern_status,
            min_futures_volume_display=min_futures_volume_display,
            min_liquidity_display=min_liquidity_display,
            min_trend_candles_display=min_trend_candles_display
        )
        
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
        try:
            await query.edit_message_text(
                "⚙️ *Панель управления фильтрами*\n\nВыберите категорию для настройки:",
                reply_markup=FilterPanel.get_main_menu(),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            from utils.logger import log_error
            log_error(f"Error in fp_main callback: {str(e)}", "filter_panel")
            await query.answer("Ошибка при возврате в главное меню", show_alert=True)
        return
    
    # Показать все настройки
    if data == "fp_show_all":
        # Принудительно обновляем настройки из БД перед отображением
        FilterSettings._settings = None  # Сбрасываем кэш
        text = FilterPanel.get_settings_text()
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="fp_main")]]
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Подтверждение сброса к базовым значениям
    if data == "fp_reset_confirm":
        keyboard = [
            [
                InlineKeyboardButton("✅ Да, сбросить", callback_data="fp_reset_do"),
                InlineKeyboardButton("❌ Отмена", callback_data="fp_main")
            ]
        ]
        await query.edit_message_text(
            "⚠️ *Сбросить к базовым значениям?*\n\nВсе текущие настройки будут заменены на базовые значения, сохранённые в БД.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Выполнить сброс к базовым
    if data == "fp_reset_do":
        FilterSettings.reset_all()
        await query.edit_message_text(
            "✅ *Сброс выполнен!*\n\nВсе настройки сброшены к базовым значениям из БД.",
            reply_markup=FilterPanel.get_main_menu(),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Подтверждение сохранения текущих как базовых
    if data == "fp_save_baseline_confirm":
        keyboard = [
            [
                InlineKeyboardButton("✅ Да, сохранить", callback_data="fp_save_baseline_do"),
                InlineKeyboardButton("❌ Отмена", callback_data="fp_main")
            ]
        ]
        await query.edit_message_text(
            "💾 *Сохранить текущие настройки как базовые?*\n\nТекущие значения будут сохранены как базовые для кнопки сброса.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Выполнить сохранение текущих как базовых
    if data == "fp_save_baseline_do":
        FilterSettings.save_current_as_baseline()
        await query.edit_message_text(
            "✅ *Сохранено!*\n\nТекущие настройки сохранены как базовые для сброса.",
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
                # Обработка boolean значений
                if value_str.lower() == 'true':
                    value = True
                elif value_str.lower() == 'false':
                    value = False
                elif '.' in value_str:
                    value = float(value_str)
                else:
                    value = int(value_str)
            except (ValueError, TypeError):
                await query.answer("❌ Ошибка: неверное значение", show_alert=True)
                return
            
            # Специальная обработка для некоторых полей
            if filter_key == 'min_futures_volume':
                value = value * 1_000_000
            elif filter_key in ['min_liquidity']:
                value = value * 1_000
            elif filter_key in ['funding_rate_min', 'funding_rate_max']:
                # Значение уже в процентах, оставляем как есть
                pass
            
            # Сохраняем
            FilterSettings.set(filter_key, value)
            
            # Форматируем значение для отображения
            if filter_key == 'min_futures_volume':
                display_value = f"{value / 1_000_000:.1f}M$"
            elif filter_key in ['min_liquidity']:
                display_value = f"{value / 1_000:.0f}K$"
            else:
                display_value = str(value)
            
            # Обновляем меню категории, чтобы показать новое значение
            await query.edit_message_text(
                f"✅ *Значение обновлено!*\n\n`{filter_key}` = `{display_value}`\n\nНастройка применена автоматически и будет использоваться для новых сигналов.",
                reply_markup=FilterPanel.get_category_menu(category),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
        return

