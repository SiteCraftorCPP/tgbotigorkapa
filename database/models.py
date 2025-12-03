from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from datetime import datetime
import config

# Используем новый синтаксис SQLAlchemy 2.0 (совместим с Python 3.13)
class Base(DeclarativeBase):
    pass

class Signal(Base):
    __tablename__ = 'signals'
    
    id = Column(Integer, primary_key=True)
    signal_id = Column(String(50), unique=True, nullable=False)
    exchange = Column(String(20), default='XT.com')
    ticker = Column(String(20), nullable=False)
    direction = Column(String(10), nullable=False)  # LONG/SHORT
    
    # Entry/Exit levels
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    stop_loss_breakeven = Column(Float)  # SL после переноса в безубыток
    take_profit_1 = Column(Float, nullable=False)
    take_profit_2 = Column(Float, nullable=False)
    take_profit_3 = Column(Float, nullable=False)
    take_profit_4 = Column(Float, nullable=True)  # Made nullable as it's no longer used
    
    # TP flags
    tp1_hit = Column(Boolean, default=False)
    tp2_hit = Column(Boolean, default=False)
    tp3_hit = Column(Boolean, default=False)
    tp4_hit = Column(Boolean, default=False)
    
    # Risk management
    risk_percent = Column(Float, default=1.0)
    leverage = Column(Integer, default=10)
    position_size = Column(Float)
    
    # AI Score (deprecated - no longer used)
    ai_score = Column(Integer, nullable=True, default=None)
    
    # Result tracking
    status = Column(String(30), default='WAITING')  # WAITING/IN_POSITION/TP1_HIT/TP2_HIT/TP3_HIT/TP4_HIT/STOPPED_OUT/CANCELLED/CLOSED_FULL_TP
    result = Column(String(10))  # WIN/LOSS
    cancellation_reason = Column(Text)  # Причина отмены
    pnl_percent = Column(Float)
    pnl_usdt = Column(Float)
    risk_reward = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime)
    
    # Additional data
    timeframe = Column(String(10))
    timeframe_higher = Column(String(10))  # Старший таймфрейм для подтверждения
    market_cap_rank = Column(Integer)  # Место в ТОП-100
    volume_24h = Column(Float)  # Объём за 24ч
    spread_percent = Column(Float)  # Спред
    atr_value = Column(Float)  # ATR на момент сигнала
    notes = Column(Text)
    activated_at = Column(DateTime)  # Время активации входа
    partial_exits = Column(Text)  # JSON с историей частичных выходов
    
    def __repr__(self):
        return f"<Signal {self.signal_id} {self.ticker} {self.direction}>"


class BotStats(Base):
    __tablename__ = 'bot_stats'
    
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, default=datetime.utcnow)
    
    total_signals = Column(Integer, default=0)
    winning_signals = Column(Integer, default=0)
    losing_signals = Column(Integer, default=0)
    
    total_pnl = Column(Float, default=0.0)
    average_rr = Column(Float, default=0.0)
    winrate = Column(Float, default=0.0)
    
    best_pair = Column(String(20))
    worst_pair = Column(String(20))
    
    def __repr__(self):
        return f"<BotStats {self.date} WR:{self.winrate}%>"


class BotConfig(Base):
    __tablename__ = 'bot_config'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(50), unique=True, nullable=False)
    value = Column(Text, nullable=False)  # Text для поддержки 200+ торговых пар
    description = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<BotConfig {self.key}={self.value}>"


class Admin(Base):
    __tablename__ = 'admins'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String(50), unique=True, nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    added_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<Admin {self.telegram_id} (@{self.username})>"


# Database initialization
# SQLite требует connect_args для внешних ключей
if config.DATABASE_URL.startswith('sqlite'):
    engine = create_engine(config.DATABASE_URL, echo=False, connect_args={'check_same_thread': False})
else:
    engine = create_engine(config.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    """Создание всех таблиц"""
    from database.user_preferences import UserPreference
    
    # Импорт Base из user_preferences для регистрации модели
    UserPreference.metadata.create_all(engine)
    Base.metadata.create_all(engine)
    
    print("OK: База данных инициализирована")
    
    # Инициализация настроек по умолчанию
    _init_default_config()


def _init_default_config():
    """Инициализация настроек по умолчанию"""
    db = SessionLocal()
    try:
        # Проверка наличия настроек
        existing = db.query(BotConfig).first()
        if existing:
            return
        
        # Дефолтные настройки
        defaults = [
            ('bot_enabled', 'true', 'Включение/выключение бота'),
            ('min_ai_score', '70', 'Минимальный AI Score для публикации'),
            ('risk_percent', '1.0', 'Процент риска на сделку'),
            ('default_leverage', '10', 'Плечо по умолчанию'),
            ('trading_pairs', 'BTC/USDT,ETH/USDT,BNB/USDT,SOL/USDT', 'Торгуемые пары'),
            ('timeframes', '1m,5m,15m,1h,4h', 'Таймфреймы для анализа'),
        ]
        
        for key, value, desc in defaults:
            config_item = BotConfig(key=key, value=value, description=desc)
            db.add(config_item)
        
        db.commit()
        print("OK: Настройки по умолчанию созданы")
        
        # Инициализация админов из .env
        _init_default_admins(db)
        
    except Exception as e:
        print(f"ERROR: Ошибка инициализации настроек: {e}")
        db.rollback()
    finally:
        db.close()

def _init_default_admins(db):
    """Инициализация админов из .env"""
    import config
    from .models import Admin
    
    if not config.TELEGRAM_ADMIN_IDS:
        return
    
    for admin_id in config.TELEGRAM_ADMIN_IDS:
        admin_id = admin_id.strip()
        if not admin_id:
            continue
        
        # Проверка существования
        existing = db.query(Admin).filter(Admin.telegram_id == admin_id).first()
        if not existing:
            admin = Admin(
                telegram_id=admin_id,
                is_active=True
            )
            db.add(admin)
            print(f"✅ Админ {admin_id} добавлен из .env")
    
    db.commit()

def get_db():
    """Получение сессии БД"""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

