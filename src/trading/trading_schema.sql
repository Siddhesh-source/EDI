-- Trading Signals Database Schema
-- Stores rule-based trading signals with risk management

-- Main trading signals table
CREATE TABLE IF NOT EXISTS trading_signals (
    id SERIAL PRIMARY KEY,
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
    
    -- Metadata
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    executed BOOLEAN DEFAULT FALSE,
    execution_price DECIMAL(12, 2),
    execution_timestamp TIMESTAMPTZ
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_trading_signals_symbol ON trading_signals(symbol);
CREATE INDEX IF NOT EXISTS idx_trading_signals_timestamp ON trading_signals(timestamp);
CREATE INDEX IF NOT EXISTS idx_trading_signals_signal_type ON trading_signals(signal_type);
CREATE INDEX IF NOT EXISTS idx_trading_signals_executed ON trading_signals(executed);
CREATE INDEX IF NOT EXISTS idx_trading_signals_symbol_timestamp ON trading_signals(symbol, timestamp DESC);

-- Positions table (tracks open positions)
CREATE TABLE IF NOT EXISTS positions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('LONG', 'SHORT')),
    entry_price DECIMAL(12, 2) NOT NULL,
    shares INTEGER NOT NULL,
    position_value DECIMAL(15, 2) NOT NULL,
    
    -- Risk management
    initial_stop_loss DECIMAL(12, 2) NOT NULL,
    current_stop_loss DECIMAL(12, 2) NOT NULL,
    take_profit DECIMAL(12, 2),
    trailing_stop_enabled BOOLEAN DEFAULT TRUE,
    
    -- P&L tracking
    unrealized_pnl DECIMAL(15, 2) DEFAULT 0,
    realized_pnl DECIMAL(15, 2) DEFAULT 0,
    
    -- Status
    status VARCHAR(20) DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'CLOSED', 'STOPPED_OUT')),
    
    -- Timestamps
    entry_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    exit_timestamp TIMESTAMPTZ,
    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for positions
CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);
CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
CREATE INDEX IF NOT EXISTS idx_positions_entry_timestamp ON positions(entry_timestamp);
CREATE UNIQUE INDEX IF NOT EXISTS idx_positions_open_symbol ON positions(symbol) WHERE status = 'OPEN';

-- Trade history table (completed trades)
CREATE TABLE IF NOT EXISTS trade_history (
    id SERIAL PRIMARY KEY,
    position_id INTEGER REFERENCES positions(id),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    
    -- Entry
    entry_price DECIMAL(12, 2) NOT NULL,
    entry_timestamp TIMESTAMPTZ NOT NULL,
    shares INTEGER NOT NULL,
    
    -- Exit
    exit_price DECIMAL(12, 2) NOT NULL,
    exit_timestamp TIMESTAMPTZ NOT NULL,
    exit_reason VARCHAR(50),
    
    -- P&L
    gross_pnl DECIMAL(15, 2) NOT NULL,
    net_pnl DECIMAL(15, 2) NOT NULL,
    pnl_pct DECIMAL(8, 4) NOT NULL,
    
    -- Risk metrics
    initial_stop_loss DECIMAL(12, 2),
    max_adverse_excursion DECIMAL(15, 2),
    max_favorable_excursion DECIMAL(15, 2),
    
    -- Duration
    hold_duration_seconds INTEGER,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for trade history
CREATE INDEX IF NOT EXISTS idx_trade_history_symbol ON trade_history(symbol);
CREATE INDEX IF NOT EXISTS idx_trade_history_exit_timestamp ON trade_history(exit_timestamp);
CREATE INDEX IF NOT EXISTS idx_trade_history_pnl ON trade_history(net_pnl);

-- Trading statistics table (daily aggregations)
CREATE TABLE IF NOT EXISTS trading_statistics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    
    -- Signal counts
    total_signals INTEGER DEFAULT 0,
    buy_signals INTEGER DEFAULT 0,
    sell_signals INTEGER DEFAULT 0,
    hold_signals INTEGER DEFAULT 0,
    
    -- Execution stats
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
    
    UNIQUE (date)
);

CREATE INDEX IF NOT EXISTS idx_trading_stats_date ON trading_statistics(date DESC);

-- Function to update position stop loss (trailing)
CREATE OR REPLACE FUNCTION update_trailing_stop()
RETURNS TRIGGER AS $$
BEGIN
    -- Only update if trailing stop is enabled and position is open
    IF NEW.trailing_stop_enabled AND NEW.status = 'OPEN' THEN
        -- For LONG positions
        IF NEW.side = 'LONG' THEN
            -- Calculate new trailing stop (2% below current price)
            NEW.current_stop_loss := GREATEST(
                NEW.current_stop_loss,
                NEW.entry_price * 0.98  -- Never go below 2% of entry
            );
        -- For SHORT positions
        ELSIF NEW.side = 'SHORT' THEN
            -- Calculate new trailing stop (2% above current price)
            NEW.current_stop_loss := LEAST(
                NEW.current_stop_loss,
                NEW.entry_price * 1.02  -- Never go above 2% of entry
            );
        END IF;
    END IF;
    
    NEW.last_updated := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for trailing stop updates
DROP TRIGGER IF EXISTS trailing_stop_trigger ON positions;
CREATE TRIGGER trailing_stop_trigger
    BEFORE UPDATE ON positions
    FOR EACH ROW
    EXECUTE FUNCTION update_trailing_stop();

-- Function to update trading statistics
CREATE OR REPLACE FUNCTION update_trading_statistics()
RETURNS TRIGGER AS $$
DECLARE
    stat_date DATE;
BEGIN
    stat_date := DATE(NEW.timestamp);
    
    -- Upsert statistics
    INSERT INTO trading_statistics (
        date,
        total_signals,
        buy_signals,
        sell_signals,
        hold_signals,
        signals_executed
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

-- Trigger for statistics updates
DROP TRIGGER IF EXISTS trading_statistics_trigger ON trading_signals;
CREATE TRIGGER trading_statistics_trigger
    AFTER INSERT ON trading_signals
    FOR EACH ROW
    EXECUTE FUNCTION update_trading_statistics();

-- Useful views

-- Current open positions
CREATE OR REPLACE VIEW open_positions AS
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
    risk_reward_ratio,
    executed,
    timestamp
FROM trading_signals
WHERE timestamp > NOW() - INTERVAL '7 days'
ORDER BY timestamp DESC;

-- Trading performance summary
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
    FROM trade_history
    ORDER BY net_pnl DESC
    LIMIT 10
)
UNION ALL
(
    SELECT 'Worst' as type, *
    FROM trade_history
    ORDER BY net_pnl ASC
    LIMIT 10
);

-- Comments for documentation
COMMENT ON TABLE trading_signals IS 'Stores all trading signals generated by the rule engine';
COMMENT ON TABLE positions IS 'Tracks currently open positions with risk management';
COMMENT ON TABLE trade_history IS 'Historical record of completed trades';
COMMENT ON TABLE trading_statistics IS 'Daily aggregated trading performance metrics';

COMMENT ON COLUMN trading_signals.confidence IS 'Signal confidence level [0, 1]';
COMMENT ON COLUMN trading_signals.risk_reward_ratio IS 'Expected profit / risk ratio';
COMMENT ON COLUMN positions.trailing_stop_enabled IS 'Whether trailing stop is active';
COMMENT ON COLUMN trade_history.max_adverse_excursion IS 'Largest unrealized loss during trade';
COMMENT ON COLUMN trade_history.max_favorable_excursion IS 'Largest unrealized profit during trade';
