# Database Module

This module provides PostgreSQL database connection management, ORM models, and repository pattern implementation for the Explainable Algorithmic Trading System.

## Components

### 1. Connection Management (`connection.py`)

Manages PostgreSQL connections with connection pooling:

```python
from src.database import initialize_database, close_database, get_db_session

# Initialize database connection
initialize_database()

# Use database session
with next(get_db_session()) as session:
    # Perform database operations
    result = session.execute("SELECT 1")
    session.commit()

# Close database connection
close_database()
```

**Features:**
- Connection pooling (10 connections, max 20 overflow)
- Automatic connection recycling (1 hour)
- Pre-ping health checks
- Automatic retry and reconnection
- Context manager for session management

### 2. ORM Models (`models.py`)

SQLAlchemy ORM models for all database tables:

- `Price`: Market price data (OHLCV)
- `Article`: News articles
- `SentimentScore`: Sentiment analysis results
- `Event`: Detected market events
- `TradingSignal`: Generated trading signals
- `Order`: Executed orders
- `BacktestResult`: Backtesting results

### 3. Repository Pattern (`repository.py`, `repositories.py`)

Base repository with CRUD operations and specialized repositories for each table:

```python
from src.database import PriceRepository, get_db_session
from datetime import datetime

with next(get_db_session()) as session:
    repo = PriceRepository(session)
    
    # Create
    price = repo.create(
        symbol="AAPL",
        timestamp=datetime.now(),
        open=150.0,
        high=152.0,
        low=149.0,
        close=151.0,
        volume=1000000
    )
    
    # Read
    price = repo.get_by_id(price.id)
    prices = repo.get_by_symbol_and_timerange("AAPL", start_time, end_time)
    
    # Update
    updated = repo.update(price.id, close=155.0)
    
    # Delete
    repo.delete(price.id)
    
    # Count
    total = repo.count()
```

**Available Repositories:**
- `PriceRepository`: Price data operations
- `ArticleRepository`: Article operations
- `SentimentScoreRepository`: Sentiment score operations
- `EventRepository`: Event operations
- `TradingSignalRepository`: Trading signal operations
- `OrderRepository`: Order operations
- `BacktestResultRepository`: Backtest result operations

### 4. Migrations (`migrations.py`)

Database schema migration utilities:

```python
from src.database import db_connection, run_migrations

# Run migrations
run_migrations(db_connection)
```

**Features:**
- Create all tables from SQLAlchemy models
- Execute SQL files
- Verify schema integrity
- Idempotent operations

## Database Schema

### Tables

1. **prices**: Market price data
   - Columns: id, symbol, timestamp, open, high, low, close, volume
   - Indexes: (symbol, timestamp)

2. **articles**: News articles
   - Columns: id, title, content, source, published_at, symbols
   - Indexes: published_at

3. **sentiment_scores**: Sentiment analysis results
   - Columns: id, article_id, score, confidence, keywords_positive, keywords_negative, timestamp
   - Indexes: timestamp
   - Foreign Key: article_id → articles.id

4. **events**: Market events
   - Columns: id, article_id, event_type, severity, keywords, timestamp
   - Indexes: timestamp, severity
   - Foreign Key: article_id → articles.id

5. **trading_signals**: Trading signals
   - Columns: id, signal_type, cms_score, sentiment_component, technical_component, regime_component, explanation, timestamp
   - Indexes: timestamp, signal_type

6. **orders**: Executed orders
   - Columns: id, order_id, symbol, order_type, side, quantity, price, status, signal_id, timestamp
   - Indexes: status, timestamp
   - Foreign Key: signal_id → trading_signals.id

7. **backtest_results**: Backtesting results
   - Columns: id, config, metrics, trades, equity_curve, created_at
   - Indexes: created_at

## Setup

### Prerequisites

1. PostgreSQL 15+ running (via Docker or locally)
2. Python dependencies installed:
   ```bash
   pip install -r requirements.txt
   ```

### Using Docker Compose

```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Verify services are running
docker-compose ps
```

### Configuration

Set environment variables in `.env`:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=trading_db
POSTGRES_USER=trading_user
POSTGRES_PASSWORD=trading_password
```

### Initialize Database

```python
from src.database import initialize_database, run_migrations, db_connection

# Initialize connection
initialize_database()

# Run migrations
run_migrations(db_connection)
```

Or use the test script:

```bash
python scripts/test_database_connection.py
```

## Testing

Run database tests:

```bash
# Run all database tests
pytest tests/test_database.py -v

# Run specific test class
pytest tests/test_database.py::TestDatabaseConnection -v

# Run specific test
pytest tests/test_database.py::TestRepositories::test_price_repository_create -v
```

## Usage Examples

### Example 1: Store Price Data

```python
from src.database import initialize_database, get_db_session, PriceRepository
from datetime import datetime

initialize_database()

with next(get_db_session()) as session:
    repo = PriceRepository(session)
    
    # Store price data
    price = repo.create(
        symbol="AAPL",
        timestamp=datetime.now(),
        open=150.0,
        high=152.0,
        low=149.0,
        close=151.0,
        volume=1000000
    )
    
    print(f"Stored price: {price.symbol} @ ${price.close}")
```

### Example 2: Query Historical Data

```python
from src.database import get_db_session, PriceRepository
from datetime import datetime, timedelta

with next(get_db_session()) as session:
    repo = PriceRepository(session)
    
    # Get last 7 days of data
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)
    
    prices = repo.get_by_symbol_and_timerange("AAPL", start_time, end_time)
    
    for price in prices:
        print(f"{price.timestamp}: ${price.close}")
```

### Example 3: Store Trading Signal

```python
from src.database import get_db_session, TradingSignalRepository
from datetime import datetime

with next(get_db_session()) as session:
    repo = TradingSignalRepository(session)
    
    signal = repo.create(
        signal_type="buy",
        cms_score=75.5,
        sentiment_component=20.0,
        technical_component=35.5,
        regime_component=20.0,
        explanation={
            "summary": "Strong buy signal",
            "sentiment_details": "Positive news sentiment",
            "technical_details": "RSI oversold, MACD bullish cross",
            "regime_details": "Trending up market"
        },
        timestamp=datetime.now()
    )
    
    print(f"Signal created: {signal.signal_type} with CMS {signal.cms_score}")
```

## Error Handling

The database module implements comprehensive error handling:

- **Connection Failures**: Automatic retry with exponential backoff
- **Transaction Errors**: Automatic rollback on exceptions
- **Query Errors**: Detailed logging with context
- **Pool Exhaustion**: Configurable overflow connections

All errors are logged with appropriate context for debugging.

## Performance Considerations

- **Connection Pooling**: Reuses connections to reduce overhead
- **Indexes**: Optimized for common query patterns
- **Batch Operations**: Use bulk inserts for large datasets
- **Query Optimization**: Use appropriate filters and limits

## Maintenance

### Backup Database

```bash
docker exec trading_postgres pg_dump -U trading_user trading_db > backup.sql
```

### Restore Database

```bash
docker exec -i trading_postgres psql -U trading_user trading_db < backup.sql
```

### Monitor Connections

```python
from src.database import db_connection

# Check pool status
pool = db_connection.engine.pool
print(f"Pool size: {pool.size()}")
print(f"Checked out: {pool.checkedout()}")
```
