from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import config

Base = declarative_base()

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
    take_profit_1 = Column(Float, nullable=False)
    take_profit_2 = Column(Float, nullable=False)
    
    # Risk management
    risk_percent = Column(Float, default=1.0)
    leverage = Column(Integer, default=10)
    position_size = Column(Float)
    
    # AI Score
    ai_score = Column(Integer, nullable=False)
    
    # Result tracking
    status = Column(String(20), default='ACTIVE')  # ACTIVE/TP1/TP2/SL/CANCELLED
    result = Column(String(10))  # WIN/LOSS
    pnl_percent = Column(Float)
    pnl_usdt = Column(Float)
    risk_reward = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime)
    
    # Additional data
    timeframe = Column(String(10))
    notes = Column(Text)
    
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
    value = Column(String(200), nullable=False)
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
engine = create_engine(config.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    """Создание всех таблиц"""
    Base.metadata.create_all(engine)
    print("✅ База данных инициализирована")
    
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
        print("✅ Настройки по умолчанию созданы")
        
    except Exception as e:
        print(f"⚠️ Ошибка инициализации настроек: {e}")
        db.rollback()
    finally:
        db.close()

def get_db():
    """Получение сессии БД"""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

