# Complete PostgreSQL Database Guide for Indian Markets Trading System

## Overview

This is a comprehensive, scalable, and normalized PostgreSQL schema designed for an algorithmic trading system targeting Indian markets (NSE/BSE). The schema supports the entire trading pipeline from news ingestion to order execution.

## Schema Architecture

### 10 Main Components

1. **News & Sentiment Analysis** - Raw news, sentiment scores, event detection
2. **Market Data** - OHLCV prices for Indian stocks
3. **Technical Indicators** - Calculated indicators (EMA, RSI, MACD, etc.)
4. **Composite Market Score (CMS)** - Multi-factor scoring system
5. **Market Regimes** - Bull/bear and volatility classification
6. **Trading Signals** - Rule-based signal generation
7. **Trades & Positions** - Active and historical trades
8. **Backtesting** - Historical strategy validation
9. **Zerodha Integration** - Indian broker API integration
10. **System Tables** - Configuration and statistics

## Table Relationships

```
news_raw
├── sentiment_scores (1:N)
└── events_detected (1:N)

historical_prices
└── indicators (1:1 on symbol+timestamp)

cms_values
└── cms_transitions (1:N)

signals
├── positions (1:1)
└── zerodha_orders (1:N)

positions
├── trades (1:1)
└── zerodha_orders (1:N)

backtest_results
└── backtest_signals (1:N)
```

## API → Database Mapping

### NLP Engine → Database

```python
# News ingestion
POST /api/nlp/process
↓
INSERT INTO news_raw (source, title, content, url, published_at, symbols)
↓
INSERT INTO sentiment_scores (article_id, score, confidence, method)
↓
INSERT INTO events_detected (article_id, event_type, severity, keywords)
```

### Price Data → Database

```python
# Price updates
POST /api/prices/update
↓
INSERT INTO historical_prices (symbol, exchange, open, high, low, close, volume, timestamp)
↓
INSERT INTO indicators (symbol, timestamp, ema_20, ema_50, atr, rsi, macd)
```

### CMS Engine → Database

```python
# CMS calculation
POST /api/cms/calculate
↓
INSERT INTO cms_values (
    symbol, cms_score, sentiment_index, volatility_index,
    trend_strength, event_shock_factor, signal_type, confidence
)
↓
TRIGGER: track_cms_transition() → INSERT INTO cms_transitions
```

### Trading Engine → Database

```python
# Signal generation
POST /api/trading/signal
↓
INSERT INTO signals (
    symbol, signal_type, price, confidence,
    shares, position_value, risk_amount,
    stop_loss_price, take_profit_price
)
↓
TRIGGER: update_trading_stats() → UPDATE trading_statistics
```

### Order Execution → Database

```python
# Place order
POST /api/orders/place
↓
INSERT INTO zerodha_orders (
    order_id, symbol, exchange, transaction_type,
    quantity, price, status
)
↓
UPDATE signals SET executed = TRUE, order_id = ?
↓
INSERT INTO positions (
    symbol, side, entry_price, shares,
    initial_stop_loss, current_stop_loss
)
```

### Trade Completion → Database

```python
# Close position
POST /api/positions/close
↓
UPDATE positions SET status = 'CLOSED', exit_timestamp = NOW()
↓
INSERT INTO trades (
    position_id, symbol, entry_price, exit_price,
    gross_pnl, net_pnl, pnl_pct, hold_duration_seconds
)
↓
UPDATE trading_statistics (daily aggregation)
```

## Redis → Database Synchronization

### Real-time Streaming

```python
# Redis channels → PostgreSQL tables

redis_channel: 'prices.live'
→ INSERT INTO historical_prices

redis_channel: 'sentiment.live'
→ INSERT INTO sentiment_scores

redis_channel: 'cms.live'
→ INSERT INTO cms_values

redis_channel: 'trading.signals'
→ INSERT INTO signals

redis_channel: 'orders.updates'
→ UPDATE zerodha_orders
```

### Synchronization Strategy

1. **Write-Through**: Write to both Redis and PostgreSQL simultaneously
2. **Write-Behind**: Write to Redis first, async batch to PostgreSQL
3. **Read-Through**: Read from Redis cache, fallback to PostgreSQL

```python
# Example: Write-through pattern
def save_cms_score(cms_result, symbol):
    # 1. Publish to Redis (real-time)
    redis_client.publish('cms.live', json.dumps(cms_result.to_dict()))
    
    # 2. Store in PostgreSQL (persistence)
    with db.session() as session:
        session.execute("""
            INSERT INTO cms_values (...)
            VALUES (...)
        """)
        session.commit()
```

## Index Optimization

### High-Performance Indexes

```sql
-- Most frequently queried patterns

-- 1. Symbol + Timestamp (time-series queries)
CREATE INDEX idx_prices_symbol_timestamp ON historical_prices(symbol, timestamp DESC);
CREATE INDEX idx_cms_symbol_timestamp ON cms_values(symbol, timestamp DESC);
CREATE INDEX idx_signals_symbol_timestamp ON signals(symbol, timestamp DESC);

-- 2. Status filtering (active positions/orders)
CREATE INDEX idx_positions_status ON positions(status) WHERE status = 'OPEN';
CREATE INDEX idx_zerodha_status ON zerodha_orders(status) WHERE status IN ('OPEN', 'PENDING');

-- 3. Date-based aggregations
CREATE INDEX idx_trades_exit_timestamp ON trades(exit_timestamp DESC);
CREATE INDEX idx_trading_stats_date ON trading_statistics(date DESC);

-- 4. GIN indexes for array/JSONB columns
CREATE INDEX idx_news_symbols ON news_raw USING GIN (symbols);
CREATE INDEX idx_signals_reasons ON signals USING GIN (reasons);
```

### Partial Indexes

```sql
-- Only index active/relevant data
CREATE INDEX idx_recent_prices ON historical_prices(timestamp)
WHERE timestamp > NOW() - INTERVAL '90 days';

CREATE INDEX idx_open_positions ON positions(symbol)
WHERE status = 'OPEN';
```

## Query Patterns

### Common Queries

#### 1. Get Latest Market Data

```sql
SELECT
    p.symbol,
    p.close as price,
    i.ema_20,
    i.ema_50,
    i.atr,
    i.rsi,
    c.cms_score,
    c.signal_type,
    r.regime_type
FROM historical_prices p
JOIN indicators i ON p.symbol = i.symbol AND p.timestamp = i.timestamp
JOIN cms_values c ON p.symbol = c.symbol AND p.timestamp = c.timestamp
JOIN regimes r ON p.symbol = r.symbol AND p.timestamp = r.timestamp
WHERE p.symbol = 'RELIANCE'
ORDER BY p.timestamp DESC
LIMIT 1;
```

#### 2. Get Trading Signals with Context

```sql
SELECT
    s.symbol,
    s.signal_type,
    s.price,
    s.confidence,
    s.shares,
    s.stop_loss_price,
    s.take_profit_price,
    s.reasons,
    c.cms_score,
    c.sentiment_index,
    r.regime_type
FROM signals s
LEFT JOIN cms_values c ON s.symbol = c.symbol 
    AND c.timestamp = (
        SELECT MAX(timestamp) FROM cms_values 
        WHERE symbol = s.symbol AND timestamp <= s.timestamp
    )
LEFT JOIN regimes r ON s.symbol = r.symbol
    AND r.timestamp = (
        SELECT MAX(timestamp) FROM regimes
        WHERE symbol = s.symbol AND timestamp <= s.timestamp
    )
WHERE s.timestamp > NOW() - INTERVAL '1 day'
ORDER BY s.timestamp DESC;
```

#### 3. Calculate Portfolio Performance

```sql
SELECT
    DATE(exit_timestamp) as date,
    COUNT(*) as trades,
    SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN net_pnl < 0 THEN 1 ELSE 0 END) as losses,
    ROUND(AVG(CASE WHEN net_pnl > 0 THEN net_pnl END), 2) as avg_win,
    ROUND(AVG(CASE WHEN net_pnl < 0 THEN net_pnl END), 2) as avg_loss,
    ROUND(SUM(net_pnl), 2) as total_pnl,
    ROUND(
        SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END)::DECIMAL / COUNT(*) * 100,
        2
    ) as win_rate_pct
FROM trades
WHERE exit_timestamp > NOW() - INTERVAL '30 days'
GROUP BY DATE(exit_timestamp)
ORDER BY date DESC;
```

#### 4. Find Best Performing Symbols

```sql
SELECT
    symbol,
    COUNT(*) as total_trades,
    SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) as wins,
    ROUND(AVG(net_pnl), 2) as avg_pnl,
    ROUND(SUM(net_pnl), 2) as total_pnl,
    ROUND(
        SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END)::DECIMAL / COUNT(*) * 100,
        2
    ) as win_rate_pct
FROM trades
WHERE exit_timestamp > NOW() - INTERVAL '90 days'
GROUP BY symbol
HAVING COUNT(*) >= 5  -- Minimum trades for significance
ORDER BY total_pnl DESC
LIMIT 20;
```

#### 5. Monitor Open Positions

```sql
SELECT
    p.symbol,
    p.side,
    p.entry_price,
    hp.close as current_price,
    p.shares,
    p.current_stop_loss,
    p.take_profit,
    ROUND((hp.close - p.entry_price) * p.shares, 2) as unrealized_pnl,
    ROUND(((hp.close - p.entry_price) / p.entry_price) * 100, 2) as pnl_pct,
    EXTRACT(EPOCH FROM (NOW() - p.entry_timestamp))::INTEGER / 3600 as hours_held
FROM positions p
JOIN LATERAL (
    SELECT close
    FROM historical_prices
    WHERE symbol = p.symbol
    ORDER BY timestamp DESC
    LIMIT 1
) hp ON true
WHERE p.status = 'OPEN'
ORDER BY unrealized_pnl DESC;
```

## Scalability Considerations

### Partitioning Strategy

```sql
-- Partition historical_prices by month
CREATE TABLE historical_prices_2024_01 PARTITION OF historical_prices
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE historical_prices_2024_02 PARTITION OF historical_prices
FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- Automatic partition creation
CREATE OR REPLACE FUNCTION create_monthly_partition()
RETURNS void AS $$
DECLARE
    start_date DATE;
    end_date DATE;
    partition_name TEXT;
BEGIN
    start_date := DATE_TRUNC('month', CURRENT_DATE);
    end_date := start_date + INTERVAL '1 month';
    partition_name := 'historical_prices_' || TO_CHAR(start_date, 'YYYY_MM');
    
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF historical_prices
         FOR VALUES FROM (%L) TO (%L)',
        partition_name, start_date, end_date
    );
END;
$$ LANGUAGE plpgsql;
```

### Archiving Old Data

```sql
-- Archive trades older than 2 years
CREATE TABLE trades_archive (LIKE trades INCLUDING ALL);

INSERT INTO trades_archive
SELECT * FROM trades
WHERE exit_timestamp < NOW() - INTERVAL '2 years';

DELETE FROM trades
WHERE exit_timestamp < NOW() - INTERVAL '2 years';
```

### Connection Pooling

```python
# Use connection pooling for high concurrency
from sqlalchemy.pool import QueuePool

engine = create_engine(
    'postgresql://user:pass@localhost/trading',
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True
)
```

## Backup Strategy

### Daily Backups

```bash
# Full backup
pg_dump -h localhost -U trading_user -d trading_db \
    -F c -b -v -f /backups/trading_$(date +%Y%m%d).backup

# Backup specific tables
pg_dump -h localhost -U trading_user -d trading_db \
    -t trades -t positions -t signals \
    -F c -f /backups/critical_$(date +%Y%m%d).backup
```

### Point-in-Time Recovery

```bash
# Enable WAL archiving in postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'cp %p /archive/%f'

# Restore to specific point
pg_restore -h localhost -U trading_user -d trading_db \
    -t trades /backups/trading_20240115.backup
```

## Monitoring Queries

### Database Health

```sql
-- Table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- Slow queries
SELECT
    query,
    calls,
    total_time,
    mean_time,
    max_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 20;
```

## Best Practices

1. **Always use prepared statements** to prevent SQL injection
2. **Use transactions** for multi-table operations
3. **Batch inserts** for bulk data (use COPY or multi-row INSERT)
4. **Regular VACUUM ANALYZE** for query optimization
5. **Monitor index usage** and drop unused indexes
6. **Use connection pooling** for high concurrency
7. **Implement retry logic** for transient failures
8. **Archive old data** to keep tables lean
9. **Use views** for complex, frequently-used queries
10. **Document schema changes** with migrations

## Conclusion

This schema provides a solid foundation for a production-grade algorithmic trading system targeting Indian markets. It's designed for scalability, performance, and maintainability while supporting the entire trading pipeline from data ingestion to order execution.
