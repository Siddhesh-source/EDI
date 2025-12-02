-- Composite Market Score (CMS) Database Schema
-- Stores CMS calculations with all components and contributions

-- Main CMS scores table
CREATE TABLE IF NOT EXISTS cms_scores (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    cms_score DECIMAL(6, 2) NOT NULL CHECK (cms_score >= -100 AND cms_score <= 100),
    signal_type VARCHAR(10) NOT NULL CHECK (signal_type IN ('BUY', 'SELL', 'HOLD')),
    confidence DECIMAL(5, 4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    
    -- Input components (normalized)
    sentiment_index DECIMAL(6, 4) NOT NULL CHECK (sentiment_index >= -1 AND sentiment_index <= 1),
    volatility_index DECIMAL(5, 4) NOT NULL CHECK (volatility_index >= 0 AND volatility_index <= 1),
    trend_strength DECIMAL(6, 4) NOT NULL CHECK (trend_strength >= -1 AND trend_strength <= 1),
    event_shock_factor DECIMAL(5, 4) NOT NULL CHECK (event_shock_factor >= 0 AND event_shock_factor <= 1),
    
    -- Weighted contributions (scaled to [-100, 100])
    sentiment_contribution DECIMAL(6, 2),
    volatility_contribution DECIMAL(6, 2),
    trend_contribution DECIMAL(6, 2),
    event_contribution DECIMAL(6, 2),
    
    -- Metadata
    explanation TEXT,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_cms_symbol ON cms_scores(symbol);
CREATE INDEX IF NOT EXISTS idx_cms_timestamp ON cms_scores(timestamp);
CREATE INDEX IF NOT EXISTS idx_cms_signal_type ON cms_scores(signal_type);
CREATE INDEX IF NOT EXISTS idx_cms_score ON cms_scores(cms_score);
CREATE INDEX IF NOT EXISTS idx_cms_symbol_timestamp ON cms_scores(symbol, timestamp DESC);

-- CMS signal transitions table (tracks signal changes)
CREATE TABLE IF NOT EXISTS cms_signal_transitions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    from_signal VARCHAR(10) NOT NULL,
    to_signal VARCHAR(10) NOT NULL,
    from_cms_score DECIMAL(6, 2),
    to_cms_score DECIMAL(6, 2),
    score_change DECIMAL(6, 2),
    duration_seconds INTEGER,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cms_transition_symbol ON cms_signal_transitions(symbol);
CREATE INDEX IF NOT EXISTS idx_cms_transition_timestamp ON cms_signal_transitions(timestamp);
CREATE INDEX IF NOT EXISTS idx_cms_transition_to_signal ON cms_signal_transitions(to_signal);

-- CMS statistics table (daily aggregations)
CREATE TABLE IF NOT EXISTS cms_statistics (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    
    -- Signal distribution
    buy_signals INTEGER DEFAULT 0,
    sell_signals INTEGER DEFAULT 0,
    hold_signals INTEGER DEFAULT 0,
    total_signals INTEGER DEFAULT 0,
    
    -- Score statistics
    avg_cms_score DECIMAL(6, 2),
    max_cms_score DECIMAL(6, 2),
    min_cms_score DECIMAL(6, 2),
    std_cms_score DECIMAL(6, 2),
    
    -- Component averages
    avg_sentiment DECIMAL(6, 4),
    avg_volatility DECIMAL(5, 4),
    avg_trend DECIMAL(6, 4),
    avg_event_shock DECIMAL(5, 4),
    
    -- Confidence metrics
    avg_confidence DECIMAL(5, 4),
    high_confidence_signals INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE (symbol, date)
);

CREATE INDEX IF NOT EXISTS idx_cms_stats_symbol_date ON cms_statistics(symbol, date DESC);

-- Function to automatically track CMS signal transitions
CREATE OR REPLACE FUNCTION track_cms_signal_transition()
RETURNS TRIGGER AS $$
DECLARE
    prev_signal RECORD;
    duration INTEGER;
BEGIN
    -- Get the most recent CMS signal for this symbol (before this insert)
    SELECT signal_type, cms_score, timestamp INTO prev_signal
    FROM cms_scores
    WHERE symbol = NEW.symbol
      AND timestamp < NEW.timestamp
    ORDER BY timestamp DESC
    LIMIT 1;
    
    -- If there was a previous signal and it's different
    IF prev_signal IS NOT NULL AND prev_signal.signal_type != NEW.signal_type THEN
        -- Calculate duration
        duration := EXTRACT(EPOCH FROM (NEW.timestamp - prev_signal.timestamp))::INTEGER;
        
        -- Insert transition record
        INSERT INTO cms_signal_transitions (
            symbol,
            from_signal,
            to_signal,
            from_cms_score,
            to_cms_score,
            score_change,
            duration_seconds,
            timestamp
        ) VALUES (
            NEW.symbol,
            prev_signal.signal_type,
            NEW.signal_type,
            prev_signal.cms_score,
            NEW.cms_score,
            NEW.cms_score - prev_signal.cms_score,
            duration,
            NEW.timestamp
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic transition tracking
DROP TRIGGER IF EXISTS cms_signal_transition_trigger ON cms_scores;
CREATE TRIGGER cms_signal_transition_trigger
    AFTER INSERT ON cms_scores
    FOR EACH ROW
    EXECUTE FUNCTION track_cms_signal_transition();

-- Function to update CMS statistics
CREATE OR REPLACE FUNCTION update_cms_statistics()
RETURNS TRIGGER AS $$
DECLARE
    stat_date DATE;
BEGIN
    stat_date := DATE(NEW.timestamp);
    
    -- Upsert statistics
    INSERT INTO cms_statistics (
        symbol,
        date,
        buy_signals,
        sell_signals,
        hold_signals,
        total_signals,
        avg_cms_score,
        max_cms_score,
        min_cms_score,
        avg_sentiment,
        avg_volatility,
        avg_trend,
        avg_event_shock,
        avg_confidence,
        high_confidence_signals
    ) VALUES (
        NEW.symbol,
        stat_date,
        CASE WHEN NEW.signal_type = 'BUY' THEN 1 ELSE 0 END,
        CASE WHEN NEW.signal_type = 'SELL' THEN 1 ELSE 0 END,
        CASE WHEN NEW.signal_type = 'HOLD' THEN 1 ELSE 0 END,
        1,
        NEW.cms_score,
        NEW.cms_score,
        NEW.cms_score,
        NEW.sentiment_index,
        NEW.volatility_index,
        NEW.trend_strength,
        NEW.event_shock_factor,
        NEW.confidence,
        CASE WHEN NEW.confidence > 0.7 THEN 1 ELSE 0 END
    )
    ON CONFLICT (symbol, date)
    DO UPDATE SET
        buy_signals = cms_statistics.buy_signals + CASE WHEN NEW.signal_type = 'BUY' THEN 1 ELSE 0 END,
        sell_signals = cms_statistics.sell_signals + CASE WHEN NEW.signal_type = 'SELL' THEN 1 ELSE 0 END,
        hold_signals = cms_statistics.hold_signals + CASE WHEN NEW.signal_type = 'HOLD' THEN 1 ELSE 0 END,
        total_signals = cms_statistics.total_signals + 1,
        avg_cms_score = (
            cms_statistics.avg_cms_score * cms_statistics.total_signals + NEW.cms_score
        ) / (cms_statistics.total_signals + 1),
        max_cms_score = GREATEST(cms_statistics.max_cms_score, NEW.cms_score),
        min_cms_score = LEAST(cms_statistics.min_cms_score, NEW.cms_score),
        avg_sentiment = (
            cms_statistics.avg_sentiment * cms_statistics.total_signals + NEW.sentiment_index
        ) / (cms_statistics.total_signals + 1),
        avg_volatility = (
            cms_statistics.avg_volatility * cms_statistics.total_signals + NEW.volatility_index
        ) / (cms_statistics.total_signals + 1),
        avg_trend = (
            cms_statistics.avg_trend * cms_statistics.total_signals + NEW.trend_strength
        ) / (cms_statistics.total_signals + 1),
        avg_event_shock = (
            cms_statistics.avg_event_shock * cms_statistics.total_signals + NEW.event_shock_factor
        ) / (cms_statistics.total_signals + 1),
        avg_confidence = (
            cms_statistics.avg_confidence * cms_statistics.total_signals + NEW.confidence
        ) / (cms_statistics.total_signals + 1),
        high_confidence_signals = cms_statistics.high_confidence_signals + CASE WHEN NEW.confidence > 0.7 THEN 1 ELSE 0 END,
        updated_at = NOW();
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic statistics update
DROP TRIGGER IF EXISTS cms_statistics_trigger ON cms_scores;
CREATE TRIGGER cms_statistics_trigger
    AFTER INSERT ON cms_scores
    FOR EACH ROW
    EXECUTE FUNCTION update_cms_statistics();

-- Useful views

-- Current CMS for each symbol
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
FROM cms_scores
ORDER BY symbol, timestamp DESC;

-- CMS signal distribution
CREATE OR REPLACE VIEW cms_signal_distribution AS
SELECT
    symbol,
    signal_type,
    COUNT(*) as count,
    AVG(cms_score) as avg_score,
    AVG(confidence) as avg_confidence,
    MIN(cms_score) as min_score,
    MAX(cms_score) as max_score
FROM cms_scores
WHERE timestamp > NOW() - INTERVAL '30 days'
GROUP BY symbol, signal_type
ORDER BY symbol, count DESC;

-- Recent CMS transitions
CREATE OR REPLACE VIEW recent_cms_transitions AS
SELECT
    symbol,
    from_signal,
    to_signal,
    from_cms_score,
    to_cms_score,
    score_change,
    duration_seconds,
    ROUND(duration_seconds / 60.0, 2) as duration_minutes,
    timestamp
FROM cms_signal_transitions
WHERE timestamp > NOW() - INTERVAL '7 days'
ORDER BY timestamp DESC;

-- CMS performance metrics
CREATE OR REPLACE VIEW cms_performance AS
SELECT
    symbol,
    DATE(timestamp) as date,
    COUNT(*) as total_signals,
    AVG(cms_score) as avg_score,
    STDDEV(cms_score) as score_volatility,
    AVG(confidence) as avg_confidence,
    COUNT(CASE WHEN signal_type = 'BUY' THEN 1 END) as buy_signals,
    COUNT(CASE WHEN signal_type = 'SELL' THEN 1 END) as sell_signals,
    COUNT(CASE WHEN signal_type = 'HOLD' THEN 1 END) as hold_signals
FROM cms_scores
WHERE timestamp > NOW() - INTERVAL '30 days'
GROUP BY symbol, DATE(timestamp)
ORDER BY symbol, date DESC;

-- Comments for documentation
COMMENT ON TABLE cms_scores IS 'Stores Composite Market Score calculations with all components';
COMMENT ON TABLE cms_signal_transitions IS 'Tracks CMS signal changes and their durations';
COMMENT ON TABLE cms_statistics IS 'Daily aggregated statistics for CMS signals';

COMMENT ON COLUMN cms_scores.cms_score IS 'Composite Market Score, range [-100, 100]';
COMMENT ON COLUMN cms_scores.sentiment_index IS 'Sentiment from NLP engine, range [-1, 1]';
COMMENT ON COLUMN cms_scores.volatility_index IS 'Normalized volatility, range [0, 1]';
COMMENT ON COLUMN cms_scores.trend_strength IS 'Trend strength, range [-1, 1]';
COMMENT ON COLUMN cms_scores.event_shock_factor IS 'Event shock factor, range [0, 1]';
COMMENT ON COLUMN cms_scores.confidence IS 'Signal confidence, range [0, 1]';
