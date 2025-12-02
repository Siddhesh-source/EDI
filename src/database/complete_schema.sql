-- COMPLETE POSTGRESQL SCHEMA FOR INDIAN MARKETS TRADING SYSTEM
-- Scalable, normalized design with optimized indexes
-- Supports: News, Sentiment, Events, Prices, Indicators, CMS, Regimes, Signals, Trades, Backtests, Zerodha Orders

-- ============================================================================
-- PART 1: NEWS AND SENTIMENT ANALYSIS
-- ============================================================================

-- Raw news articles from various sources
CREATE TABLE IF NOT EXISTS news_raw (
    id SERIAL PRIMARY KEY,
    source VARCHAR(100) NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    url TEXT UNIQUE,
    author VARCHAR(200),
    published_at TIMESTAMPTZ NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbols TEXT[],  -- Array of related stock symbols
    language VARCHAR(10) DEFAULT 'en',
    metadata JSONB,  -- Additional source-specific data
    
    -- Indexes
    INDEX idx_news_published (published_at DESC),
    INDEX idx_news_source (source),
    INDEX idx_news_symbols USING GIN (symbols),
    INDEX idx_news_fetched (fetched_at DESC)
);

-- Sentiment scores for news articles
CREATE TABLE IF NOT EXISTS sentiment_scores (
    id SERIAL PRIMARY KEY,
    article_id INTEGER REFERENCES news_raw(id) ON DELETE CASCADE,
    score DECIMAL(6, 4) NOT NULL CHECK (score >= -1 AND score <= 1),
    confidence DECIMAL(5, 4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    method VARCHAR(50) NOT NULL,  -- 'vader', 'finbert', 'custom'
    positive_score DECIMAL(5, 4),
    negative_score DECIMAL(5, 4),
    neutral_score DECIMAL(5, 4),
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_sentiment_article (article_id),
    INDEX idx_sentiment_score (score),
    INDEX idx_sentiment_computed (computed_at DESC)
);

-- Detected events from news
CREATE TABLE IF NOT EXISTS events_detected (
    id SERIAL PRIMARY KEY,
    article_id INTEGER REFERENCES news_raw(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,  -- 'earnings', 'merger', 'regulatory', etc.
    severity DECIMAL(5, 4) NOT NULL CHECK (severity >= 0 AND severity <= 1),
    keywords TEXT[],
    entities JSONB,  -- Named entities (companies, people, locations)
    impact_score DECIMAL(6, 4),  -- Expected market impact
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_events_article (article_id),
    INDEX idx_events_type (event_type),
    INDEX idx_events_severity (severity DESC),
    INDEX idx_events_detected (detected_at DESC)
);

-- ============================================================================
-- PART 2: MARKET DATA
-- ============================================================================

-- Historical OHLCV price data for Indian stocks
CREATE TABLE IF NOT EXISTS historical_prices (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,  -- NSE/BSE symbol
    exchange VARCHAR(10) NOT NULL DEFAULT 'NSE',  -- 'NSE' or 'BSE'
    open DECIMAL(12, 2) NOT NULL,
    high DECIMAL(12, 2) NOT NULL,
    low DECIMAL(12, 2) NOT NULL,
    close DECIMAL(12, 2) NOT NULL,
    volume BIGINT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    timeframe VARCHAR(10) NOT NULL DEFAULT '1D',  -- '1m', '5m', '1h', '1D'
    
    -- Additional Indian market specific fields
    delivery_qty BIGINT,
    delivery_percent DECIMAL(5, 2),
    
    -- Constraints
    UNIQUE (symbol, exchange, timestamp, timeframe),
    CHECK (high >= low),
    CHECK (high >= open),
    CHECK (high >= close),
    CHECK (low <= open),
    CHECK (low <= close),
    
    -- Indexes
    INDEX idx_prices_symbol (symbol),
    INDEX idx_prices_timestamp (timestamp DESC),
    INDEX idx_prices_symbol_timestamp (symbol, timestamp DESC),
    INDEX idx_prices_exchange (exchange)
);

-- Partition by month for better performance
-- CREATE TABLE historical_prices_2024_01 PARTITION OF historical_prices
-- FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- ============================================================================
-- PART 3: TECHNICAL INDICATORS
-- ============================================================================

-- Technical indicators calculated from price data
CREATE TABLE IF NOT EXISTS indicators (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    
    -- Moving Averages
    ema_20 DECIMAL(12, 2),
    ema_50 DECIMAL(12, 2),
    ema_200 DECIMAL(12, 2),
    sma_20 DECIMAL(12, 2),
    sma_50 DECIMAL(12, 2),
    
    -- Volatility
    atr DECIMAL(12, 4),
    bollinger_upper DECIMAL(12, 2),
    bollinger_middle DECIMAL(12, 2),
    bollinger_lower DECIMAL(12, 2),
    
    -- Momentum
    rsi DECIMAL(5, 2),
    macd DECIMAL(12, 4),
    macd_signal DECIMAL(12, 4),
    macd_histogram DECIMAL(12, 4),
    
    -- Volume
    volume_sma_20 BIGINT,
    volume_ratio DECIMAL(8, 4),
    
    -- Trend
    adx DECIMAL(5, 2),
    
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    UNIQUE (symbol, timestamp),
    
    -- Indexes
    INDEX idx_indicators_symbol (symbol),
    INDEX idx_indicators_timestamp (timestamp DESC),
    INDEX idx_indicators_symbol_timestamp (symbol, timestamp DESC)
);


-- ============================================================================
-- PART 4: COMPOSITE MARKET SCORE (CMS)
-- ============================================================================

-- CMS values combining sentiment, volatility, trend, and events
CREATE TABLE IF NOT EXISTS cms_values (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    cms_score DECIMAL(6, 2) NOT NULL CHECK (cms_score >= -100 AND cms_score <= 100),
    
    -- Input components (normalized)
    sentiment_index DECIMAL(6, 4) NOT NULL CHECK (sentiment_index >= -1 AND sentiment_index <= 1),
    volatility_index DECIMAL(5, 4) NOT NULL CHECK (volatility_index >= 0 AND volatility_index <= 1),
    trend_strength DECIMAL(6, 4) NOT NULL CHECK (trend_strength >= -1 AND trend_strength <= 1),
    event_shock_factor DECIMAL(5, 4) NOT NULL CHECK (event_shock_factor >= 0 AND event_shock_factor <= 1),
    
    -- Weighted contributions
    sentiment_contribution DECIMAL(6, 2),
    volatility_contribution DECIMAL(6, 2),
    trend_contribution DECIMAL(6, 2),
    event_contribution DECIMAL(6, 2),
    
    -- Signal and confidence
    signal_type VARCHAR(10) NOT NULL CHECK (signal_type IN ('BUY', 'SELL', 'HOLD')),
    confidence DECIMAL(5, 4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    
    explanation TEXT,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_cms_symbol (symbol),
    INDEX idx_cms_timestamp (timestamp DESC),
    INDEX idx_cms_symbol_timestamp (symbol, timestamp DESC),
    INDEX idx_cms_signal (signal_type),
    INDEX idx_cms_score (cms_score)
);

-- CMS signal transitions (tracks changes)
CREATE TABLE IF NOT EXISTS cms_transitions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    from_signal VARCHAR(10) NOT NULL,
    to_signal VARCHAR(10) NOT NULL,
    from_score DECIMAL(6, 2),
    to_score DECIMAL(6, 2),
    score_change DECIMAL(6, 2),
    duration_seconds INTEGER,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    INDEX idx_cms_trans_symbol (symbol),
    INDEX idx_cms_trans_timestamp (timestamp DESC)
);

-- ============================================================================
-- PART 5: MARKET REGIMES
-- ============================================================================

-- Market regime detection results
CREATE TABLE IF NOT EXISTS regimes (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    regime_type VARCHAR(20) NOT NULL,  -- 'BULL_QUIET', 'BULL_VOLATILE', 'BEAR_QUIET', 'BEAR_VOLATILE'
    confidence DECIMAL(5, 4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    
    -- Regime characteristics
    trend_direction VARCHAR(10),  -- 'UP', 'DOWN', 'SIDEWAYS'
    volatility_level VARCHAR(10),  -- 'LOW', 'MEDIUM', 'HIGH'
    
    -- Supporting metrics
    ema_20 DECIMAL(12, 2),
    ema_50 DECIMAL(12, 2),
    atr DECIMAL(12, 4),
    volatility_percentile DECIMAL(5, 2),
    
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_regimes_symbol (symbol),
    INDEX idx_regimes_timestamp (timestamp DESC),
    INDEX idx_regimes_symbol_timestamp (symbol, timestamp DESC),
    INDEX idx_regimes_type (regime_type)
);

-- ============================================================================
-- PART 6: TRADING SIGNALS
-- ============================================================================

-- Trading signals generated by rule engine
CREATE TABLE IF NOT EXISTS signals (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    signal_type VARCHAR(20) NOT NULL CHECK (signal_type IN ('BUY', 'SELL', 'HOLD', 'CLOSE_LONG', 'CLOSE_SHORT')),
    price DECIMAL(12, 2) NOT NULL,
    confidence DECIMAL(5, 4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    
    -- Position sizing
    shares INTEGER,
    position_value DECIMAL(15, 2),
    risk_amount DECIMAL(15, 2),
    stop_loss_price DECIMAL(12, 2),
    take_profit_price DECIMAL(12, 2),
    risk_reward_ratio DECIMAL(6, 2),
    
    -- Context
    reasons JSONB,
    market_data JSONB,
    
    -- Execution tracking
    executed BOOLEAN DEFAULT FALSE,
    execution_price DECIMAL(12, 2),
    execution_timestamp TIMESTAMPTZ,
    order_id VARCHAR(50),  -- Zerodha order ID
    
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_signals_symbol (symbol),
    INDEX idx_signals_timestamp (timestamp DESC),
    INDEX idx_signals_symbol_timestamp (symbol, timestamp DESC),
    INDEX idx_signals_type (signal_type),
    INDEX idx_signals_executed (executed),
    INDEX idx_signals_order (order_id)
);

-- ============================================================================
-- PART 7: TRADES AND POSITIONS
-- ============================================================================

-- Active positions
CREATE TABLE IF NOT EXISTS positions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    exchange VARCHAR(10) NOT NULL DEFAULT 'NSE',
    side VARCHAR(10) NOT NULL CHECK (side IN ('LONG', 'SHORT')),
    
    -- Entry details
    entry_price DECIMAL(12, 2) NOT NULL,
    shares INTEGER NOT NULL,
    position_value DECIMAL(15, 2) NOT NULL,
    entry_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Risk management
    initial_stop_loss DECIMAL(12, 2) NOT NULL,
    current_stop_loss DECIMAL(12, 2) NOT NULL,
    take_profit DECIMAL(12, 2),
    trailing_stop_enabled BOOLEAN DEFAULT TRUE,
    
    -- P&L tracking
    unrealized_pnl DECIMAL(15, 2) DEFAULT 0,
    realized_pnl DECIMAL(15, 2) DEFAULT 0,
    
    -- Zerodha integration
    zerodha_order_id VARCHAR(50),
    
    -- Status
    status VARCHAR(20) DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'CLOSED', 'STOPPED_OUT')),
    exit_timestamp TIMESTAMPTZ,
    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_positions_symbol (symbol),
    INDEX idx_positions_status (status),
    INDEX idx_positions_entry (entry_timestamp DESC),
    UNIQUE INDEX idx_positions_open_symbol (symbol) WHERE status = 'OPEN'
);

-- Completed trades history
CREATE TABLE IF NOT EXISTS trades (
    id BIGSERIAL PRIMARY KEY,
    position_id INTEGER REFERENCES positions(id),
    symbol VARCHAR(20) NOT NULL,
    exchange VARCHAR(10) NOT NULL DEFAULT 'NSE',
    side VARCHAR(10) NOT NULL CHECK (side IN ('LONG', 'SHORT')),
    
    -- Entry
    entry_price DECIMAL(12, 2) NOT NULL,
    entry_timestamp TIMESTAMPTZ NOT NULL,
    shares INTEGER NOT NULL,
    entry_order_id VARCHAR(50),
    
    -- Exit
    exit_price DECIMAL(12, 2) NOT NULL,
    exit_timestamp TIMESTAMPTZ NOT NULL,
    exit_reason VARCHAR(50),
    exit_order_id VARCHAR(50),
    
    -- P&L
    gross_pnl DECIMAL(15, 2) NOT NULL,
    net_pnl DECIMAL(15, 2) NOT NULL,
    pnl_pct DECIMAL(8, 4) NOT NULL,
    brokerage DECIMAL(10, 2) DEFAULT 0,
    taxes DECIMAL(10, 2) DEFAULT 0,
    
    -- Risk metrics
    initial_stop_loss DECIMAL(12, 2),
    max_adverse_excursion DECIMAL(15, 2),
    max_favorable_excursion DECIMAL(15, 2),
    
    -- Duration
    hold_duration_seconds INTEGER,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_trades_symbol (symbol),
    INDEX idx_trades_exit_timestamp (exit_timestamp DESC),
    INDEX idx_trades_pnl (net_pnl),
    INDEX idx_trades_side (side)
);


-- ============================================================================
-- PART 8: BACKTESTING
-- ============================================================================

-- Backtest configurations and results
CREATE TABLE IF NOT EXISTS backtest_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200),
    description TEXT,
    
    -- Configuration
    symbol VARCHAR(20) NOT NULL,
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ NOT NULL,
    initial_capital DECIMAL(15, 2) NOT NULL,
    position_size_pct DECIMAL(5, 4) NOT NULL,
    
    -- Strategy parameters
    strategy_name VARCHAR(100),
    strategy_params JSONB,
    
    -- Performance metrics
    total_return DECIMAL(10, 4),
    cagr DECIMAL(10, 4),
    sharpe_ratio DECIMAL(8, 4),
    sortino_ratio DECIMAL(8, 4),
    max_drawdown DECIMAL(8, 4),
    win_rate DECIMAL(5, 4),
    profit_factor DECIMAL(8, 4),
    
    -- Trade statistics
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    avg_win DECIMAL(15, 2),
    avg_loss DECIMAL(15, 2),
    largest_win DECIMAL(15, 2),
    largest_loss DECIMAL(15, 2),
    avg_hold_duration_seconds INTEGER,
    
    -- Equity curve (stored as JSONB array)
    equity_curve JSONB,
    drawdown_curve JSONB,
    
    -- Trade log
    trades JSONB,
    
    -- Execution details
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    execution_time_seconds DECIMAL(8, 2),
    
    -- Indexes
    INDEX idx_backtest_symbol (symbol),
    INDEX idx_backtest_executed (executed_at DESC),
    INDEX idx_backtest_sharpe (sharpe_ratio DESC),
    INDEX idx_backtest_return (total_return DESC)
);

-- Backtest signals (for analysis)
CREATE TABLE IF NOT EXISTS backtest_signals (
    id BIGSERIAL PRIMARY KEY,
    backtest_id UUID REFERENCES backtest_results(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    signal_type VARCHAR(20) NOT NULL,
    price DECIMAL(12, 2) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    
    -- Signal context
    cms_score DECIMAL(6, 2),
    sentiment_index DECIMAL(6, 4),
    regime_type VARCHAR(20),
    
    -- Execution
    executed BOOLEAN DEFAULT FALSE,
    
    INDEX idx_backtest_signals_backtest (backtest_id),
    INDEX idx_backtest_signals_timestamp (timestamp)
);

-- ============================================================================
-- PART 9: ZERODHA INTEGRATION (Indian Broker)
-- ============================================================================

-- Zerodha orders
CREATE TABLE IF NOT EXISTS zerodha_orders (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(50) UNIQUE NOT NULL,  -- Zerodha order ID
    exchange_order_id VARCHAR(50),  -- Exchange order ID
    
    -- Order details
    symbol VARCHAR(20) NOT NULL,
    exchange VARCHAR(10) NOT NULL,  -- 'NSE' or 'BSE'
    transaction_type VARCHAR(10) NOT NULL,  -- 'BUY' or 'SELL'
    order_type VARCHAR(20) NOT NULL,  -- 'MARKET', 'LIMIT', 'SL', 'SL-M'
    product VARCHAR(10) NOT NULL,  -- 'CNC', 'MIS', 'NRML'
    
    -- Quantity and price
    quantity INTEGER NOT NULL,
    price DECIMAL(12, 2),
    trigger_price DECIMAL(12, 2),
    disclosed_quantity INTEGER DEFAULT 0,
    
    -- Execution details
    filled_quantity INTEGER DEFAULT 0,
    pending_quantity INTEGER,
    cancelled_quantity INTEGER DEFAULT 0,
    average_price DECIMAL(12, 2),
    
    -- Status
    status VARCHAR(20) NOT NULL,  -- 'OPEN', 'COMPLETE', 'CANCELLED', 'REJECTED'
    status_message TEXT,
    
    -- Timestamps
    order_timestamp TIMESTAMPTZ NOT NULL,
    exchange_timestamp TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Linking
    signal_id BIGINT REFERENCES signals(id),
    position_id INTEGER REFERENCES positions(id),
    
    -- Indexes
    INDEX idx_zerodha_order_id (order_id),
    INDEX idx_zerodha_symbol (symbol),
    INDEX idx_zerodha_status (status),
    INDEX idx_zerodha_timestamp (order_timestamp DESC),
    INDEX idx_zerodha_signal (signal_id),
    INDEX idx_zerodha_position (position_id)
);

-- Zerodha positions (snapshot from broker)
CREATE TABLE IF NOT EXISTS zerodha_positions_snapshot (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    exchange VARCHAR(10) NOT NULL,
    product VARCHAR(10) NOT NULL,
    
    -- Quantity
    quantity INTEGER NOT NULL,
    overnight_quantity INTEGER DEFAULT 0,
    
    -- Prices
    average_price DECIMAL(12, 2) NOT NULL,
    last_price DECIMAL(12, 2) NOT NULL,
    close_price DECIMAL(12, 2),
    
    -- P&L
    pnl DECIMAL(15, 2) NOT NULL,
    day_pnl DECIMAL(15, 2),
    
    -- Snapshot time
    snapshot_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    INDEX idx_zerodha_pos_symbol (symbol),
    INDEX idx_zerodha_pos_snapshot (snapshot_at DESC)
);

-- ============================================================================
-- PART 10: SYSTEM TABLES
-- ============================================================================

-- Trading statistics (daily aggregations)
CREATE TABLE IF NOT EXISTS trading_statistics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    
    -- Signal counts
    total_signals INTEGER DEFAULT 0,
    buy_signals INTEGER DEFAULT 0,
    sell_signals INTEGER DEFAULT 0,
    hold_signals INTEGER DEFAULT 0,
    signals_executed INTEGER DEFAULT 0,
    execution_rate DECIMAL(5, 4),
    
    -- Trade stats
    trades_opened INTEGER DEFAULT 0,
    trades_closed INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    
    -- P&L
    total_pnl DECIMAL(15, 2) DEFAULT 0,
    avg_win DECIMAL(15, 2),
    avg_loss DECIMAL(15, 2),
    win_rate DECIMAL(5, 4),
    profit_factor DECIMAL(8, 4),
    
    -- Risk metrics
    avg_risk_per_trade DECIMAL(15, 2),
    max_drawdown DECIMAL(15, 2),
    sharpe_ratio DECIMAL(8, 4),
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    INDEX idx_trading_stats_date (date DESC)
);

-- System configuration
CREATE TABLE IF NOT EXISTS system_config (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- API rate limits and usage
CREATE TABLE IF NOT EXISTS api_usage (
    id SERIAL PRIMARY KEY,
    api_name VARCHAR(50) NOT NULL,
    endpoint VARCHAR(200),
    requests_count INTEGER DEFAULT 0,
    date DATE NOT NULL,
    hour INTEGER CHECK (hour >= 0 AND hour <= 23),
    
    UNIQUE (api_name, endpoint, date, hour),
    INDEX idx_api_usage_date (date DESC),
    INDEX idx_api_usage_api (api_name)
);


-- ============================================================================
-- TRIGGERS AND FUNCTIONS
-- ============================================================================

-- Function to update CMS transitions
CREATE OR REPLACE FUNCTION track_cms_transition()
RETURNS TRIGGER AS $$
DECLARE
    prev_signal RECORD;
    duration INTEGER;
BEGIN
    SELECT signal_type, cms_score, timestamp INTO prev_signal
    FROM cms_values
    WHERE symbol = NEW.symbol
      AND timestamp < NEW.timestamp
    ORDER BY timestamp DESC
    LIMIT 1;
    
    IF prev_signal IS NOT NULL AND prev_signal.signal_type != NEW.signal_type THEN
        duration := EXTRACT(EPOCH FROM (NEW.timestamp - prev_signal.timestamp))::INTEGER;
        
        INSERT INTO cms_transitions (
            symbol, from_signal, to_signal,
            from_score, to_score, score_change,
            duration_seconds, timestamp
        ) VALUES (
            NEW.symbol, prev_signal.signal_type, NEW.signal_type,
            prev_signal.cms_score, NEW.cms_score,
            NEW.cms_score - prev_signal.cms_score,
            duration, NEW.timestamp
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS cms_transition_trigger ON cms_values;
CREATE TRIGGER cms_transition_trigger
    AFTER INSERT ON cms_values
    FOR EACH ROW
    EXECUTE FUNCTION track_cms_transition();

-- Function to update trading statistics
CREATE OR REPLACE FUNCTION update_trading_stats()
RETURNS TRIGGER AS $$
DECLARE
    stat_date DATE;
BEGIN
    stat_date := DATE(NEW.timestamp);
    
    INSERT INTO trading_statistics (
        date, total_signals, buy_signals, sell_signals, hold_signals, signals_executed
    ) VALUES (
        stat_date,
        1,
        CASE WHEN NEW.signal_type = 'BUY' THEN 1 ELSE 0 END,
        CASE WHEN NEW.signal_type = 'SELL' THEN 1 ELSE 0 END,
        CASE WHEN NEW.signal_type = 'HOLD' THEN 1 ELSE 0 END,
        CASE WHEN NEW.executed THEN 1 ELSE 0 END
    )
    ON CONFLICT (date)
    DO UPDATE SET
        total_signals = trading_statistics.total_signals + 1,
        buy_signals = trading_statistics.buy_signals + CASE WHEN NEW.signal_type = 'BUY' THEN 1 ELSE 0 END,
        sell_signals = trading_statistics.sell_signals + CASE WHEN NEW.signal_type = 'SELL' THEN 1 ELSE 0 END,
        hold_signals = trading_statistics.hold_signals + CASE WHEN NEW.signal_type = 'HOLD' THEN 1 ELSE 0 END,
        signals_executed = trading_statistics.signals_executed + CASE WHEN NEW.executed THEN 1 ELSE 0 END,
        execution_rate = CAST(trading_statistics.signals_executed + CASE WHEN NEW.executed THEN 1 ELSE 0 END AS DECIMAL) / 
                        CAST(trading_statistics.total_signals + 1 AS DECIMAL),
        updated_at = NOW();
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trading_stats_trigger ON signals;
CREATE TRIGGER trading_stats_trigger
    AFTER INSERT ON signals
    FOR EACH ROW
    EXECUTE FUNCTION update_trading_stats();

-- Function to update trailing stops
CREATE OR REPLACE FUNCTION update_trailing_stop()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.trailing_stop_enabled AND NEW.status = 'OPEN' THEN
        IF NEW.side = 'LONG' THEN
            NEW.current_stop_loss := GREATEST(
                NEW.current_stop_loss,
                NEW.entry_price * 0.98
            );
        ELSIF NEW.side = 'SHORT' THEN
            NEW.current_stop_loss := LEAST(
                NEW.current_stop_loss,
                NEW.entry_price * 1.02
            );
        END IF;
    END IF;
    
    NEW.last_updated := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trailing_stop_trigger ON positions;
CREATE TRIGGER trailing_stop_trigger
    BEFORE UPDATE ON positions
    FOR EACH ROW
    EXECUTE FUNCTION update_trailing_stop();

-- ============================================================================
-- USEFUL VIEWS
-- ============================================================================

-- Current market overview
CREATE OR REPLACE VIEW market_overview AS
SELECT DISTINCT ON (symbol)
    symbol,
    close as current_price,
    volume,
    timestamp
FROM historical_prices
ORDER BY symbol, timestamp DESC;

-- Latest CMS for each symbol
CREATE OR REPLACE VIEW current_cms AS
SELECT DISTINCT ON (symbol)
    symbol,
    cms_score,
    signal_type,
    confidence,
    sentiment_index,
    volatility_index,
    trend_strength,
    event_shock_factor,
    timestamp
FROM cms_values
ORDER BY symbol, timestamp DESC;

-- Latest regime for each symbol
CREATE OR REPLACE VIEW current_regimes AS
SELECT DISTINCT ON (symbol)
    symbol,
    regime_type,
    confidence,
    trend_direction,
    volatility_level,
    timestamp
FROM regimes
ORDER BY symbol, timestamp DESC;

-- Open positions summary
CREATE OR REPLACE VIEW open_positions_summary AS
SELECT
    id,
    symbol,
    side,
    entry_price,
    shares,
    position_value,
    current_stop_loss,
    take_profit,
    unrealized_pnl,
    ROUND((unrealized_pnl / position_value) * 100, 2) as pnl_pct,
    entry_timestamp,
    EXTRACT(EPOCH FROM (NOW() - entry_timestamp))::INTEGER as hold_duration_seconds
FROM positions
WHERE status = 'OPEN'
ORDER BY entry_timestamp DESC;

-- Recent signals
CREATE OR REPLACE VIEW recent_signals AS
SELECT
    symbol,
    signal_type,
    price,
    confidence,
    shares,
    position_value,
    risk_amount,
    stop_loss_price,
    take_profit_price,
    executed,
    timestamp
FROM signals
WHERE timestamp > NOW() - INTERVAL '7 days'
ORDER BY timestamp DESC;

-- Trading performance
CREATE OR REPLACE VIEW trading_performance AS
SELECT
    date,
    total_signals,
    buy_signals,
    sell_signals,
    signals_executed,
    ROUND(execution_rate * 100, 2) as execution_rate_pct,
    trades_closed,
    winning_trades,
    losing_trades,
    ROUND(win_rate * 100, 2) as win_rate_pct,
    total_pnl,
    avg_win,
    avg_loss,
    profit_factor,
    sharpe_ratio
FROM trading_statistics
WHERE date > CURRENT_DATE - INTERVAL '30 days'
ORDER BY date DESC;

-- Best and worst trades
CREATE OR REPLACE VIEW trade_extremes AS
(
    SELECT 'Best' as type, *
    FROM trades
    ORDER BY net_pnl DESC
    LIMIT 10
)
UNION ALL
(
    SELECT 'Worst' as type, *
    FROM trades
    ORDER BY net_pnl ASC
    LIMIT 10
);

-- Backtest leaderboard
CREATE OR REPLACE VIEW backtest_leaderboard AS
SELECT
    id,
    name,
    symbol,
    total_return,
    sharpe_ratio,
    max_drawdown,
    win_rate,
    total_trades,
    executed_at
FROM backtest_results
WHERE total_trades > 10  -- Minimum trades for statistical significance
ORDER BY sharpe_ratio DESC
LIMIT 20;

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE news_raw IS 'Raw news articles from various sources';
COMMENT ON TABLE sentiment_scores IS 'Sentiment analysis scores for news articles';
COMMENT ON TABLE events_detected IS 'Detected events from news with severity and impact';
COMMENT ON TABLE historical_prices IS 'OHLCV price data for Indian stocks (NSE/BSE)';
COMMENT ON TABLE indicators IS 'Technical indicators calculated from price data';
COMMENT ON TABLE cms_values IS 'Composite Market Score combining multiple factors';
COMMENT ON TABLE regimes IS 'Market regime detection results';
COMMENT ON TABLE signals IS 'Trading signals generated by rule engine';
COMMENT ON TABLE positions IS 'Currently open trading positions';
COMMENT ON TABLE trades IS 'Historical record of completed trades';
COMMENT ON TABLE backtest_results IS 'Backtesting results with performance metrics';
COMMENT ON TABLE zerodha_orders IS 'Orders placed through Zerodha broker API';
COMMENT ON TABLE trading_statistics IS 'Daily aggregated trading performance metrics';

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- Insert default system configuration
INSERT INTO system_config (key, value, description) VALUES
('risk_per_trade', '0.01', 'Maximum risk per trade as fraction of capital'),
('max_position_size', '0.10', 'Maximum position size as fraction of capital'),
('atr_stop_multiplier', '2.0', 'ATR multiplier for stop loss calculation'),
('trailing_stop_pct', '0.02', 'Trailing stop percentage'),
('cms_buy_threshold', '50.0', 'CMS score threshold for BUY signals'),
('cms_sell_threshold', '-50.0', 'CMS score threshold for SELL signals')
ON CONFLICT (key) DO NOTHING;

-- ============================================================================
-- MAINTENANCE QUERIES
-- ============================================================================

-- Vacuum and analyze for performance
-- Run periodically:
-- VACUUM ANALYZE historical_prices;
-- VACUUM ANALYZE cms_values;
-- VACUUM ANALYZE signals;
-- VACUUM ANALYZE trades;

-- Reindex for optimal performance
-- Run monthly:
-- REINDEX TABLE historical_prices;
-- REINDEX TABLE cms_values;
-- REINDEX TABLE signals;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
