# Database Architecture

## Overview

The database module implements a layered architecture with connection pooling, ORM models, and repository pattern for clean data access.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Application Layer                           │
│  (FastAPI, Sentiment Analyzer, Event Detector, etc.)           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Uses
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Repository Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │    Price     │  │   Article    │  │   Signal     │         │
│  │  Repository  │  │  Repository  │  │  Repository  │  ...    │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
│  - CRUD operations                                              │
│  - Specialized queries                                          │
│  - Business logic encapsulation                                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Uses
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ORM Layer                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │    Price     │  │   Article    │  │   Signal     │         │
│  │    Model     │  │    Model     │  │    Model     │  ...    │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
│  - SQLAlchemy ORM models                                        │
│  - Relationships and constraints                                │
│  - Type definitions                                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Uses
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Connection Layer                               │
│  ┌──────────────────────────────────────────────────┐          │
│  │         DatabaseConnection                        │          │
│  │  - Connection pooling (10 base, 20 overflow)    │          │
│  │  - Session management                            │          │
│  │  - Health checks                                 │          │
│  │  - Error handling                                │          │
│  └──────────────────────────────────────────────────┘          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Connects to
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   PostgreSQL Database                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │    prices    │  │   articles   │  │   signals    │         │
│  │    table     │  │    table     │  │    table     │  ...    │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
│  - 7 tables with indexes                                        │
│  - Foreign key constraints                                      │
│  - JSONB for flexible data                                      │
└─────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### 1. Connection Layer (`connection.py`)

**Responsibilities:**
- Manage database connections
- Implement connection pooling
- Provide session management
- Handle connection errors
- Monitor connection health

**Key Classes:**
- `DatabaseConnection`: Main connection manager

**Key Functions:**
- `initialize_database()`: Setup connection
- `close_database()`: Cleanup connections
- `get_db_session()`: Get session context manager

### 2. ORM Layer (`models.py`)

**Responsibilities:**
- Define database schema
- Map Python objects to tables
- Define relationships
- Enforce constraints

**Models:**
- `Price`: OHLCV price data
- `Article`: News articles
- `SentimentScore`: Sentiment analysis
- `Event`: Market events
- `TradingSignal`: Trading signals
- `Order`: Executed orders
- `BacktestResult`: Backtest results

### 3. Repository Layer (`repository.py`, `repositories.py`)

**Responsibilities:**
- Abstract data access
- Provide CRUD operations
- Implement business queries
- Handle transactions

**Base Repository:**
- `BaseRepository[T]`: Generic CRUD operations

**Specialized Repositories:**
- `PriceRepository`: Price-specific queries
- `ArticleRepository`: Article-specific queries
- `SentimentScoreRepository`: Sentiment queries
- `EventRepository`: Event queries
- `TradingSignalRepository`: Signal queries
- `OrderRepository`: Order queries
- `BacktestResultRepository`: Backtest queries

### 4. Migration Layer (`migrations.py`)

**Responsibilities:**
- Create database schema
- Execute SQL scripts
- Verify schema integrity
- Handle schema updates

**Key Classes:**
- `DatabaseMigration`: Migration manager

**Key Functions:**
- `run_migrations()`: Execute migrations

## Data Flow

### Write Operation
```
Application
    ↓
Repository.create(data)
    ↓
ORM Model instantiation
    ↓
Session.add(model)
    ↓
Session.flush()
    ↓
Connection Pool
    ↓
PostgreSQL INSERT
```

### Read Operation
```
Application
    ↓
Repository.get_by_id(id)
    ↓
Session.query(Model).filter(...)
    ↓
Connection Pool
    ↓
PostgreSQL SELECT
    ↓
ORM Model instantiation
    ↓
Return to Application
```

## Database Schema

### Entity Relationship Diagram

```
┌─────────────┐
│   Article   │
│─────────────│
│ id (PK)     │◄─────┐
│ title       │      │
│ content     │      │
│ source      │      │
│ published_at│      │
│ symbols[]   │      │
└─────────────┘      │
                     │
        ┌────────────┴────────────┐
        │                         │
        │                         │
┌───────▼──────┐         ┌────────▼──────┐
│ SentimentScore│         │     Event     │
│──────────────│         │───────────────│
│ id (PK)      │         │ id (PK)       │
│ article_id(FK)│         │ article_id(FK)│
│ score        │         │ event_type    │
│ confidence   │         │ severity      │
│ keywords_pos[]│         │ keywords[]    │
│ keywords_neg[]│         │ timestamp     │
│ timestamp    │         └───────────────┘
└──────────────┘

┌─────────────┐
│    Price    │
│─────────────│
│ id (PK)     │
│ symbol      │
│ timestamp   │
│ open        │
│ high        │
│ low         │
│ close       │
│ volume      │
└─────────────┘

┌──────────────┐
│TradingSignal │
│──────────────│
│ id (PK)      │◄─────┐
│ signal_type  │      │
│ cms_score    │      │
│ sentiment_   │      │
│   component  │      │
│ technical_   │      │
│   component  │      │
│ regime_      │      │
│   component  │      │
│ explanation  │      │
│ timestamp    │      │
└──────────────┘      │
                      │
                ┌─────▼──────┐
                │   Order    │
                │────────────│
                │ id (PK)    │
                │ order_id   │
                │ symbol     │
                │ order_type │
                │ side       │
                │ quantity   │
                │ price      │
                │ status     │
                │ signal_id(FK)│
                │ timestamp  │
                └────────────┘

┌──────────────┐
│BacktestResult│
│──────────────│
│ id (PK)      │
│ config       │
│ metrics      │
│ trades       │
│ equity_curve │
│ created_at   │
└──────────────┘
```

## Connection Pooling

### Pool Configuration

```python
Engine Configuration:
├── pool_size: 10          # Base connections
├── max_overflow: 20       # Additional connections
├── pool_timeout: 30       # Wait time (seconds)
├── pool_recycle: 3600     # Recycle after 1 hour
└── pool_pre_ping: True    # Verify before use
```

### Pool Lifecycle

```
Application Start
    ↓
initialize_database()
    ↓
Create Engine with Pool
    ↓
┌─────────────────────────┐
│   Connection Pool       │
│  ┌───┐ ┌───┐ ┌───┐     │
│  │ 1 │ │ 2 │ │ 3 │ ... │  (10 base connections)
│  └───┘ └───┘ └───┘     │
└─────────────────────────┘
    ↓
Request Session
    ↓
Checkout Connection
    ↓
Execute Query
    ↓
Return Connection
    ↓
Application Shutdown
    ↓
close_database()
    ↓
Dispose Pool
```

## Error Handling

### Error Flow

```
Application Request
    ↓
Try: Repository Operation
    ↓
Try: Session Operation
    ↓
Try: Database Query
    ↓
[Error Occurs]
    ↓
Session Rollback
    ↓
Log Error with Context
    ↓
Raise Exception
    ↓
Application Error Handler
```

### Error Types

1. **Connection Errors**: Pool exhaustion, network issues
2. **Transaction Errors**: Constraint violations, deadlocks
3. **Query Errors**: Invalid SQL, missing tables
4. **Data Errors**: Type mismatches, null violations

## Performance Optimization

### Indexes

```sql
-- Price queries
CREATE INDEX idx_prices_symbol_timestamp ON prices(symbol, timestamp);

-- Article queries
CREATE INDEX idx_articles_published_at ON articles(published_at);

-- Sentiment queries
CREATE INDEX idx_sentiment_timestamp ON sentiment_scores(timestamp);

-- Event queries
CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_events_severity ON events(severity);

-- Signal queries
CREATE INDEX idx_signals_timestamp ON trading_signals(timestamp);
CREATE INDEX idx_signals_type ON trading_signals(signal_type);

-- Order queries
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_timestamp ON orders(timestamp);

-- Backtest queries
CREATE INDEX idx_backtest_created_at ON backtest_results(created_at);
```

### Query Optimization

1. **Use Indexes**: Filter on indexed columns
2. **Limit Results**: Use pagination for large datasets
3. **Batch Operations**: Bulk inserts for multiple records
4. **Connection Reuse**: Leverage connection pooling
5. **Prepared Statements**: SQLAlchemy handles this automatically

## Security

### Best Practices

1. **Parameterized Queries**: SQLAlchemy ORM prevents SQL injection
2. **Connection Encryption**: Use SSL for production
3. **Credential Management**: Store in environment variables
4. **Least Privilege**: Database user has minimal permissions
5. **Connection Limits**: Pool size prevents resource exhaustion

## Monitoring

### Health Checks

```python
from src.database import db_connection

# Check connection health
healthy = db_connection.health_check()

# Check pool status
pool = db_connection.engine.pool
print(f"Pool size: {pool.size()}")
print(f"Checked out: {pool.checkedout()}")
```

### Logging

All database operations are logged with:
- Timestamp
- Component name
- Operation type
- Error details (if applicable)
- Execution context

## Testing Strategy

### Unit Tests
- Connection management
- Session lifecycle
- Repository CRUD operations
- Error handling

### Integration Tests
- End-to-end data flow
- Transaction management
- Concurrent operations
- Performance benchmarks

### Test Database
- Use separate test database
- Reset schema between tests
- Mock external dependencies
- Verify data integrity
