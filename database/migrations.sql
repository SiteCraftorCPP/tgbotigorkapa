-- Создание базы данных
-- CREATE DATABASE crypto_signals;

-- Подключение к базе
-- \c crypto_signals;

-- Таблица сигналов
CREATE TABLE IF NOT EXISTS signals (
    id SERIAL PRIMARY KEY,
    signal_id VARCHAR(50) UNIQUE NOT NULL,
    exchange VARCHAR(20) DEFAULT 'XT.com',
    ticker VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL,
    
    entry_price FLOAT NOT NULL,
    stop_loss FLOAT NOT NULL,
    stop_loss_breakeven FLOAT,
    take_profit_1 FLOAT NOT NULL,
    take_profit_2 FLOAT NOT NULL,
    take_profit_3 FLOAT NOT NULL,
    take_profit_4 FLOAT NOT NULL,
    
    tp1_hit BOOLEAN DEFAULT FALSE,
    tp2_hit BOOLEAN DEFAULT FALSE,
    tp3_hit BOOLEAN DEFAULT FALSE,
    tp4_hit BOOLEAN DEFAULT FALSE,
    
    risk_percent FLOAT DEFAULT 1.0,
    leverage INTEGER DEFAULT 10,
    position_size FLOAT,
    
    ai_score INTEGER NOT NULL,
    
    status VARCHAR(30) DEFAULT 'WAITING',
    result VARCHAR(10),
    cancellation_reason TEXT,
    pnl_percent FLOAT,
    pnl_usdt FLOAT,
    risk_reward FLOAT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    
    timeframe VARCHAR(10),
    timeframe_higher VARCHAR(10),
    market_cap_rank INTEGER,
    volume_24h FLOAT,
    spread_percent FLOAT,
    atr_value FLOAT,
    notes TEXT,
    activated_at TIMESTAMP,
    partial_exits TEXT
);

-- Таблица статистики
CREATE TABLE IF NOT EXISTS bot_stats (
    id SERIAL PRIMARY KEY,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    total_signals INTEGER DEFAULT 0,
    winning_signals INTEGER DEFAULT 0,
    losing_signals INTEGER DEFAULT 0,
    
    total_pnl FLOAT DEFAULT 0.0,
    average_rr FLOAT DEFAULT 0.0,
    winrate FLOAT DEFAULT 0.0,
    
    best_pair VARCHAR(20),
    worst_pair VARCHAR(20)
);

-- Таблица конфигурации
CREATE TABLE IF NOT EXISTS bot_config (
    id SERIAL PRIMARY KEY,
    key VARCHAR(50) UNIQUE NOT NULL,
    value VARCHAR(200) NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица администраторов
CREATE TABLE IF NOT EXISTS admins (
    id SERIAL PRIMARY KEY,
    telegram_id VARCHAR(50) UNIQUE NOT NULL,
    username VARCHAR(100),
    first_name VARCHAR(100),
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_signals_ticker ON signals(ticker);
CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status);
CREATE INDEX IF NOT EXISTS idx_signals_created_at ON signals(created_at);
CREATE INDEX IF NOT EXISTS idx_signals_direction ON signals(direction);
CREATE INDEX IF NOT EXISTS idx_admins_telegram_id ON admins(telegram_id);
CREATE INDEX IF NOT EXISTS idx_admins_active ON admins(is_active);

-- Представление для статистики по парам
CREATE OR REPLACE VIEW pair_stats AS
SELECT 
    ticker,
    COUNT(*) as total_signals,
    SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN result = 'LOSS' THEN 1 ELSE 0 END) as losses,
    ROUND(AVG(CASE WHEN result = 'WIN' THEN 1.0 ELSE 0.0 END) * 100, 2) as winrate,
    ROUND(SUM(pnl_percent), 2) as total_pnl,
    ROUND(AVG(ai_score), 2) as avg_ai_score
FROM signals
WHERE status IN ('TP1', 'TP2', 'SL')
GROUP BY ticker
ORDER BY total_pnl DESC;

-- Представление для дневной статистики
CREATE OR REPLACE VIEW daily_stats AS
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_signals,
    SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN result = 'LOSS' THEN 1 ELSE 0 END) as losses,
    ROUND(AVG(CASE WHEN result = 'WIN' THEN 1.0 ELSE 0.0 END) * 100, 2) as winrate,
    ROUND(SUM(pnl_percent), 2) as total_pnl
FROM signals
WHERE status IN ('TP1', 'TP2', 'SL')
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Начальная конфигурация
INSERT INTO bot_config (key, value, description) VALUES
    ('bot_enabled', 'true', 'Включение/выключение бота'),
    ('min_ai_score', '70', 'Минимальный AI Score для публикации'),
    ('risk_percent', '1.0', 'Процент риска на сделку'),
    ('default_leverage', '10', 'Плечо по умолчанию')
ON CONFLICT (key) DO NOTHING;

COMMENT ON TABLE signals IS 'Торговые сигналы';
COMMENT ON TABLE bot_stats IS 'Статистика работы бота';
COMMENT ON TABLE bot_config IS 'Конфигурация бота';
COMMENT ON TABLE admins IS 'Администраторы бота';

-- ВАЖНО: После создания БД добавьте своих админов вручную:
-- INSERT INTO admins (telegram_id, username, first_name) VALUES ('YOUR_TELEGRAM_ID', 'your_username', 'Your Name');
-- INSERT INTO admins (telegram_id, username, first_name) VALUES ('SECOND_ADMIN_ID', 'second_username', 'Second Name');

