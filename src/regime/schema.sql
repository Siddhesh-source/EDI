-- Market Regime Detection Schema
-- Stores regime classifications with all inputs and outputs

-- Main regimes table
CREATE TABLE IF NOT EXISTS market_regimes (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    regime_type VARCHAR(20) NOT NULL CHECK (regime_type IN ('bull', 'bear', 'neutral', 'panic')),
    confidence DECIMAL(5, 4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    
    -- Input values
    sentiment_index DECIMAL(6, 4) NOT NULL CHECK (sentiment_index >= -1 AND sentiment_index <= 1),
    volatility_index DECIMAL(5, 4) NOT NULL CHECK (volatility_index >= 0 AND volatility_index <= 1),
    trend_strength DECIMAL(6, 4) NOT NULL CHECK (trend_strength >= -1 AND trend_strength <= 1),
    
    -- Regime scores
    bull_score DECIMAL(6, 4),
    bear_score DECIMAL(6, 4),
    neutral_score DECIMAL(6, 4),
    panic_score DECIMAL(6, 4),
    
    -- Metadata
    explanation TEXT,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Indexes for efficient querying
    INDEX idx_regime_symbol (symbol),
    INDEX idx_regime_timestamp (timestamp),
    INDEX idx_regime_type (regime_type),
    INDEX idx_regime_symbol_timestamp (symbol, timestamp DESC)
);

-- Regime transitions table (tracks changes)
CREATE TABLE IF NOT EXISTS regime_transitions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    from_regime VARCHAR(20) NOT NULL,
    to_regime VARCHAR(20) NOT NULL,
    confidence_change DECIMAL(6, 4),
    duration_seconds INTEGER,  -- How long previous regime lasted
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    INDEX idx_transition_symbol (symbol),
    INDEX idx_transition_timestamp (timestamp),
    INDEX idx_transition_to_regime (to_regime)
);

-- Regime statistics table (aggregated metrics)
CREATE TABLE IF NOT EXISTS regime_statistics (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    regime_type VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    
    -- Aggregated metrics
    total_duration_seconds INTEGER,
    occurrence_count INTEGER,
    avg_confidence DECIMAL(5, 4),
    avg_sentiment_index DECIMAL(6, 4),
    avg_volatility_index DECIMAL(5, 4),
    avg_trend_strength DECIMAL(6, 4),
    
    -- Performance metrics (if linked to trades)
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    avg_return DECIMAL(8, 4),
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE (symbol, regime_type, date),
    INDEX idx_stats_symbol_date (symbol, date DESC),
    INDEX idx_stats_regime (regime_type)
);

-- Function to automatically track regime transitions
CREATE OR REPLACE FUNCTION track_regime_transition()
RETURNS TRIGGER AS $$
DECLARE
    prev_regime RECORD;
    duration INTEGER;
BEGIN
    -- Get the most recent regime for this symbol (before this insert)
    SELECT regime_type, timestamp INTO prev_regime
    FROM market_regimes
    WHERE symbol = NEW.symbol
      AND timestamp < NEW.timestamp
    ORDER BY timestamp DESC
    LIMIT 1;
    
    -- If there was a previous regime and it's different
    IF prev_regime IS NOT NULL AND prev_regime.regime_type != NEW.regime_type THEN
        -- Calculate duration
        duration := EXTRACT(EPOCH FROM (NEW.timestamp - prev_regime.timestamp))::INTEGER;
        
        -- Insert transition record
        INSERT INTO regime_transitions (
            symbol,
            from_regime,
            to_regime,
            duration_seconds,
            timestamp
        ) VALUES (
            NEW.symbol,
            prev_regime.regime_type,
            NEW.regime_type,
            duration,
            NEW.timestamp
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic transition tracking
DROP TRIGGER IF EXISTS regime_transition_trigger ON market_regimes;
CREATE TRIGGER regime_transition_trigger
    AFTER INSERT ON market_regimes
    FOR EACH ROW
    EXECUTE FUNCTION track_regime_transition();

-- Function to update regime statistics
CREATE OR REPLACE FUNCTION update_regime_statistics()
RETURNS TRIGGER AS $$
DECLARE
    stat_date DATE;
BEGIN
    stat_date := DATE(NEW.timestamp);
    
    -- Upsert statistics
    INSERT INTO regime_statistics (
        symbol,
        regime_type,
        date,
        total_duration_seconds,
        occurrence_count,
        avg_confidence,
        avg_sentiment_index,
        avg_volatility_index,
        avg_trend_strength
    ) VALUES (
        NEW.symbol,
        NEW.regime_type,
        stat_date,
        0,  -- Will be updated by aggregation
        1,
        NEW.confidence,
        NEW.sentiment_index,
        NEW.volatility_index,
        NEW.trend_strength
    )
    ON CONFLICT (symbol, regime_type, date)
    DO UPDATE SET
        occurrence_count = regime_statistics.occurrence_count + 1,
        avg_confidence = (
            regime_statistics.avg_confidence * regime_statistics.occurrence_count + NEW.confidence
        ) / (regime_statistics.occurrence_count + 1),
        avg_sentiment_index = (
            regime_statistics.avg_sentiment_index * regime_statistics.occurrence_count + NEW.sentiment_index
        ) / (regime_statistics.occurrence_count + 1),
        avg_volatility_index = (
            regime_statistics.avg_volatility_index * regime_statistics.occurrence_count + NEW.volatility_index
        ) / (regime_statistics.occurrence_count + 1),
        avg_trend_strength = (
            regime_statistics.avg_trend_strength * regime_statistics.occurrence_count + NEW.trend_strength
        ) / (regime_statistics.occurrence_count + 1),
        updated_at = NOW();
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic statistics update
DROP TRIGGER IF EXISTS regime_statistics_trigger ON market_regimes;
CREATE TRIGGER regime_statistics_trigger
    AFTER INSERT ON market_regimes
    FOR EACH ROW
    EXECUTE FUNCTION update_regime_statistics();

-- Useful queries

-- Get current regime for a symbol
CREATE OR REPLACE VIEW current_regimes AS
SELECT DISTINCT ON (symbol)
    symbol,
    regime_type,
    confidence,
    sentiment_index,
    volatility_index,
    trend_strength,
    timestamp
FROM market_regimes
ORDER BY symbol, timestamp DESC;

-- Get regime distribution for a symbol
CREATE OR REPLACE VIEW regime_distribution AS
SELECT
    symbol,
    regime_type,
    COUNT(*) as count,
    AVG(confidence) as avg_confidence,
    AVG(sentiment_index) as avg_sentiment,
    AVG(volatility_index) as avg_volatility,
    AVG(trend_strength) as avg_trend
FROM market_regimes
WHERE timestamp > NOW() - INTERVAL '30 days'
GROUP BY symbol, regime_type
ORDER BY symbol, count DESC;

-- Get recent regime transitions
CREATE OR REPLACE VIEW recent_transitions AS
SELECT
    symbol,
    from_regime,
    to_regime,
    duration_seconds,
    ROUND(duration_seconds / 60.0, 2) as duration_minutes,
    timestamp
FROM regime_transitions
WHERE timestamp > NOW() - INTERVAL '7 days'
ORDER BY timestamp DESC;

-- Comments for documentation
COMMENT ON TABLE market_regimes IS 'Stores market regime classifications with inputs and scores';
COMMENT ON TABLE regime_transitions IS 'Tracks regime changes and their durations';
COMMENT ON TABLE regime_statistics IS 'Aggregated daily statistics for each regime type';

COMMENT ON COLUMN market_regimes.sentiment_index IS 'Sentiment from NLP engine, range [-1, 1]';
COMMENT ON COLUMN market_regimes.volatility_index IS 'Normalized volatility (ATR/Price), range [0, 1]';
COMMENT ON COLUMN market_regimes.trend_strength IS 'EMA20-EMA50 slope difference, range [-1, 1]';
COMMENT ON COLUMN market_regimes.confidence IS 'Classification confidence, range [0, 1]';
