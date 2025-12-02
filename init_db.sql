-- Database initialization script for the trading system

-- Prices table
CREATE TABLE IF NOT EXISTS prices (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open DECIMAL(10, 2),
    high DECIMAL(10, 2),
    low DECIMAL(10, 2),
    close DECIMAL(10, 2),
    volume BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prices_symbol_timestamp ON prices(symbol, timestamp);

-- Articles table
CREATE TABLE IF NOT EXISTS articles (
    id VARCHAR(100) PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT,
    source VARCHAR(100),
    published_at TIMESTAMPTZ NOT NULL,
    symbols TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles(published_at);

-- Sentiment scores table
CREATE TABLE IF NOT EXISTS sentiment_scores (
    id SERIAL PRIMARY KEY,
    article_id VARCHAR(100) REFERENCES articles(id),
    score DECIMAL(3, 2) NOT NULL,
    confidence DECIMAL(3, 2),
    keywords_positive TEXT[],
    keywords_negative TEXT[],
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sentiment_timestamp ON sentiment_scores(timestamp);

-- Events table
CREATE TABLE IF NOT EXISTS events (
    id VARCHAR(100) PRIMARY KEY,
    article_id VARCHAR(100) REFERENCES articles(id),
    event_type VARCHAR(50) NOT NULL,
    severity DECIMAL(3, 2),
    keywords TEXT[],
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_severity ON events(severity);

-- Trading signals table
CREATE TABLE IF NOT EXISTS trading_signals (
    id SERIAL PRIMARY KEY,
    signal_type VARCHAR(10) NOT NULL,
    cms_score DECIMAL(5, 2) NOT NULL,
    sentiment_component DECIMAL(5, 2),
    technical_component DECIMAL(5, 2),
    regime_component DECIMAL(5, 2),
    explanation JSONB,
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON trading_signals(timestamp);
CREATE INDEX IF NOT EXISTS idx_signals_type ON trading_signals(signal_type);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(100) UNIQUE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    order_type VARCHAR(20),
    side VARCHAR(10),
    quantity DECIMAL(10, 2),
    price DECIMAL(10, 2),
    status VARCHAR(20),
    signal_id INTEGER REFERENCES trading_signals(id),
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_timestamp ON orders(timestamp);

-- Backtest results table
CREATE TABLE IF NOT EXISTS backtest_results (
    id VARCHAR(100) PRIMARY KEY,
    config JSONB NOT NULL,
    metrics JSONB NOT NULL,
    trades JSONB NOT NULL,
    equity_curve JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_backtest_created_at ON backtest_results(created_at);
