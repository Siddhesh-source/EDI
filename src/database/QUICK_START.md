# Database Module - Quick Start Guide

## 1. Start PostgreSQL

Using Docker Compose:
```bash
docker-compose up -d postgres
```

Or use an existing PostgreSQL instance and configure `.env`:
```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=trading_db
POSTGRES_USER=trading_user
POSTGRES_PASSWORD=trading_password
```

## 2. Initialize Database

```python
from src.database import initialize_database, run_migrations, db_connection

# Initialize connection
initialize_database()

# Run migrations (creates tables)
run_migrations(db_connection)
```

## 3. Use Repositories

### Store Price Data
```python
from src.database import get_db_session, PriceRepository
from datetime import datetime

with next(get_db_session()) as session:
    repo = PriceRepository(session)
    price = repo.create(
        symbol="AAPL",
        timestamp=datetime.now(),
        open=150.0,
        high=152.0,
        low=149.0,
        close=151.0,
        volume=1000000
    )
```

### Store Article and Sentiment
```python
from src.database import get_db_session, ArticleRepository, SentimentScoreRepository
from datetime import datetime

with next(get_db_session()) as session:
    # Create article
    article_repo = ArticleRepository(session)
    article = article_repo.create(
        id="article_123",
        title="Apple Reports Strong Earnings",
        content="Apple Inc. reported...",
        source="Reuters",
        published_at=datetime.now(),
        symbols=["AAPL"]
    )
    
    # Create sentiment
    sentiment_repo = SentimentScoreRepository(session)
    sentiment = sentiment_repo.create(
        article_id=article.id,
        score=0.85,
        confidence=0.90,
        keywords_positive=["strong", "growth"],
        keywords_negative=[],
        timestamp=datetime.now()
    )
```

### Store Trading Signal
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
            "sentiment_details": "Positive news sentiment (0.85)",
            "technical_details": "RSI: 28 (oversold), MACD: bullish cross",
            "regime_details": "Trending up market (confidence: 0.82)"
        },
        timestamp=datetime.now()
    )
```

### Query Historical Data
```python
from src.database import get_db_session, PriceRepository
from datetime import datetime, timedelta

with next(get_db_session()) as session:
    repo = PriceRepository(session)
    
    # Get last 7 days
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)
    prices = repo.get_by_symbol_and_timerange("AAPL", start_time, end_time)
    
    for price in prices:
        print(f"{price.timestamp}: ${price.close}")
```

## 4. Test the Setup

Run the test script:
```bash
python scripts/test_database_connection.py
```

Or run the test suite:
```bash
pytest tests/test_database.py -v
```

## 5. Common Operations

### Health Check
```python
from src.database import db_connection

if db_connection.health_check():
    print("Database is healthy")
```

### Count Records
```python
from src.database import get_db_session, PriceRepository

with next(get_db_session()) as session:
    repo = PriceRepository(session)
    total = repo.count()
    print(f"Total price records: {total}")
```

### Update Record
```python
from src.database import get_db_session, OrderRepository

with next(get_db_session()) as session:
    repo = OrderRepository(session)
    order = repo.update_status("order_123", "filled")
```

### Delete Record
```python
from src.database import get_db_session, PriceRepository

with next(get_db_session()) as session:
    repo = PriceRepository(session)
    deleted = repo.delete(price_id)
```

## 6. Cleanup

```python
from src.database import close_database

close_database()
```

## Troubleshooting

### Connection Error
- Ensure PostgreSQL is running
- Check `.env` configuration
- Verify network connectivity

### Import Error
- Install dependencies: `pip install -r requirements.txt`
- Ensure `psycopg2-binary` is installed

### Migration Error
- Check database permissions
- Verify schema doesn't already exist
- Review logs for details

## Available Repositories

- `PriceRepository` - Price data
- `ArticleRepository` - News articles
- `SentimentScoreRepository` - Sentiment scores
- `EventRepository` - Market events
- `TradingSignalRepository` - Trading signals
- `OrderRepository` - Orders
- `BacktestResultRepository` - Backtest results

## Next Steps

1. Implement Redis pub/sub pipeline (Task 3)
2. Build sentiment analyzer (Task 4)
3. Create event detector (Task 5)
4. Develop technical indicator engine (Task 6)
