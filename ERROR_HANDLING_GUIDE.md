# Comprehensive Error Handling Guide

## Overview

The trading system implements comprehensive error handling with circuit breaker patterns, graceful degradation, retry logic, and operation queuing to ensure system resilience and reliability.

## Key Components

### 1. Circuit Breakers

Circuit breakers prevent cascading failures by stopping requests to failing services and allowing them time to recover.

**States:**
- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Service is failing, requests are rejected
- **HALF_OPEN**: Testing if service has recovered

**Configuration:**
```python
from src.shared.error_handling import get_circuit_breaker

# Get or create a circuit breaker
breaker = get_circuit_breaker(
    name="service_name",
    failure_threshold=5,  # Open after 5 failures
    recovery_timeout=60.0,  # Wait 60s before testing recovery
    expected_exception=Exception
)

# Use circuit breaker
try:
    result = breaker.call(risky_function, arg1, arg2)
except CircuitBreakerOpenError:
    # Handle circuit open - service unavailable
    pass
```

**Active Circuit Breakers:**
- `postgresql`: Database operations
- `redis`: Redis pub/sub operations
- `newsapi`: NewsAPI service calls
- `kite_connect`: Kite Connect API calls

### 2. Graceful Degradation

The system continues operating with reduced functionality when services are unavailable.

**Features:**
- Service availability tracking
- Fallback data management
- Stale data detection

**Example:**
```python
from src.shared.error_handling import get_degradation_manager

degradation_manager = get_degradation_manager()

# Mark service unavailable
degradation_manager.mark_service_unavailable("newsapi")

# Set fallback data
degradation_manager.set_fallback_data("newsapi", cached_sentiment_data)

# Check if service is available
if not degradation_manager.is_service_available("newsapi"):
    # Use fallback data
    data = degradation_manager.get_fallback_data("newsapi")
```

**Degradation Behaviors:**

| Service | Degradation Behavior |
|---------|---------------------|
| NewsAPI | Use cached sentiment data, mark as stale |
| Redis | Buffer messages locally, replay on reconnection |
| PostgreSQL | Queue write operations, retry with backoff |
| Kite Connect | Disable auto-trading, alert user |

### 3. Retry Logic with Exponential Backoff

Automatic retry for transient failures with exponential backoff.

**Decorator Usage:**
```python
from src.shared.error_handling import retry_with_backoff

@retry_with_backoff(
    max_attempts=3,
    base_delay=1.0,
    max_delay=60.0,
    exceptions=(ConnectionError, TimeoutError)
)
def unreliable_operation():
    # Operation that might fail transiently
    pass
```

**Manual Usage:**
```python
from src.shared.error_handling import RetryPolicy

policy = RetryPolicy(max_attempts=3, base_delay=1.0)

for attempt in range(policy.max_attempts):
    try:
        result = risky_operation()
        break
    except Exception as e:
        if attempt < policy.max_attempts - 1:
            delay = policy.get_delay(attempt)
            time.sleep(delay)
```

### 4. Operation Queuing

Queue operations when services are unavailable for later execution.

**Database Write Queue:**
```python
from src.database.connection import db_connection

# Queue a write operation
def write_operation():
    with db_connection.get_session() as session:
        # Perform database write
        pass

# Queue if database is unavailable
if not db_connection.health_check():
    db_connection.queue_write_operation(write_operation)

# Process queued operations when database recovers
processed = db_connection.process_queued_operations(max_operations=100)
```

**Redis Message Buffer:**
```python
from src.shared.redis_client import get_redis_client

redis_client = get_redis_client()

# Enable buffering when Redis is unavailable
redis_client.publisher.enable_buffering()

# Messages are automatically buffered
redis_client.publish("channel", data)

# Replay buffered messages after reconnection
replayed = redis_client.publisher.replay_buffer()
```

### 5. Structured Error Logging

All errors are logged with structured format including timestamp, component, error type, and context.

**Usage:**
```python
from src.shared.error_handling import ErrorLogger

error_logger = ErrorLogger("component_name")

try:
    risky_operation()
except Exception as e:
    error_logger.log_error(
        e,
        context={
            'action': 'operation_name',
            'additional_info': 'value'
        }
    )
```

**Log Format:**
```
timestamp=2024-01-01T12:00:00.000000 | level=ERROR | component=sentiment_analyzer | message=Error message | exception=Traceback... | context={'action': 'fetch_news'}
```

## Service-Specific Error Handling

### NewsAPI Service

**Error Scenarios:**
1. API key invalid/expired
2. Rate limit exceeded
3. Network timeout
4. Service unavailable

**Handling:**
- Circuit breaker opens after 3 failures
- System uses cached sentiment data
- Data marked as stale with timestamp
- Alert logged when cache > 1 hour old
- Recovery timeout: 5 minutes

**Code:**
```python
# In sentiment analyzer
try:
    articles = self.client.get_everything(...)
except NewsAPIException as e:
    error_logger.log_error(e, {'action': 'fetch_news'})
    self._handle_newsapi_unavailable()
    self._circuit_breaker._on_failure()
```

### Redis Pipeline

**Error Scenarios:**
1. Connection lost
2. Network timeout
3. Memory full
4. Authentication failure

**Handling:**
- Messages buffered locally (max 1000)
- Automatic reconnection with exponential backoff
- Buffered messages replayed on reconnection
- Old messages (> 5 min) dropped
- Max reconnection attempts: 5

**Code:**
```python
# Automatic in RedisPublisher
def publish(self, channel, data):
    try:
        self.redis_client.publish(channel, message)
    except (ConnectionError, TimeoutError) as e:
        if self._buffer_enabled:
            self._buffer.append((channel, data, time.time()))
```

### PostgreSQL Database

**Error Scenarios:**
1. Connection pool exhausted
2. Network timeout
3. Query timeout
4. Deadlock

**Handling:**
- Write operations queued (max 10,000)
- Retry with exponential backoff
- Circuit breaker opens after 5 failures
- Queued operations processed on recovery
- Recovery timeout: 30 seconds

**Code:**
```python
# In database connection
def _commit_with_retry(self, session, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            self._circuit_breaker.call(session.commit)
            return
        except (OperationalError, DatabaseError) as e:
            if attempt < max_attempts - 1:
                delay = 1.0 * (2 ** attempt)
                time.sleep(delay)
```

### Kite Connect API

**Error Scenarios:**
1. Authentication failure
2. Order rejection
3. Rate limit exceeded
4. Market closed
5. Network timeout

**Handling:**
- Circuit breaker opens after 3 failures
- Automatic trading disabled immediately
- Critical alert logged
- User notified via dashboard
- Recovery timeout: 60 seconds

**Code:**
```python
# In order executor
def _handle_execution_error(self, error):
    if isinstance(error, CircuitBreakerOpenError):
        self.enable_auto_trading = False
        self._degradation_manager.mark_service_unavailable("kite_connect")
        logger.critical("AUTOMATIC TRADING DISABLED")
```

## Monitoring and Alerts

### Health Check Endpoints

**Basic Health Check:**
```bash
GET /health
```

**Detailed Health Check:**
```bash
GET /health/detailed
# Requires API key
# Returns: circuit breaker states, service availability, warnings, errors
```

**Circuit Breaker Status:**
```bash
GET /health/circuit-breakers
# Returns: state, failure count, last failure time for all breakers
```

**Service Status:**
```bash
GET /health/services
# Returns: availability, fallback data status, data age
```

**Active Alerts:**
```bash
GET /health/alerts
# Returns: list of warnings and errors
```

**Database Queue Stats:**
```bash
GET /health/database/queue
# Returns: queue size, dropped count
```

### System Health Monitor

```python
from src.shared.monitoring import get_health_monitor

health_monitor = get_health_monitor()

# Get comprehensive status
status = health_monitor.get_health_status()

# Check if system is healthy
is_healthy = health_monitor.is_system_healthy()

# Get active alerts
alerts = health_monitor.get_alerts()

# Log health status
health_monitor.log_health_status()
```

## Best Practices

### 1. Always Use Circuit Breakers for External Services

```python
# Good
breaker = get_circuit_breaker("external_service")
result = breaker.call(external_api_call, params)

# Bad
result = external_api_call(params)  # No protection
```

### 2. Log Errors with Context

```python
# Good
error_logger.log_error(e, {'action': 'fetch_data', 'symbol': 'AAPL'})

# Bad
logger.error(f"Error: {e}")  # Missing context
```

### 3. Handle Circuit Breaker Open State

```python
try:
    result = breaker.call(operation)
except CircuitBreakerOpenError:
    # Use fallback or queue operation
    result = get_fallback_data()
```

### 4. Queue Critical Operations

```python
# For database writes
if not db_connection.health_check():
    db_connection.queue_write_operation(write_func, *args)
else:
    write_func(*args)
```

### 5. Monitor Service Health

```python
# Periodic health checks
async def health_check_loop():
    while True:
        health_monitor.log_health_status()
        await asyncio.sleep(60)  # Every minute
```

## Configuration

### Environment Variables

```bash
# Circuit Breaker Settings
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60

# Retry Settings
RETRY_MAX_ATTEMPTS=3
RETRY_BASE_DELAY=1.0
RETRY_MAX_DELAY=60.0

# Queue Settings
DB_WRITE_QUEUE_MAX_SIZE=10000
REDIS_BUFFER_MAX_SIZE=1000

# Logging
LOG_LEVEL=INFO
STRUCTURED_LOGGING=true
```

### Tuning Guidelines

**Circuit Breaker Thresholds:**
- Critical services (Kite Connect): 3 failures
- Infrastructure (Redis, PostgreSQL): 5 failures
- External APIs (NewsAPI): 3 failures

**Recovery Timeouts:**
- Fast recovery (Redis): 30 seconds
- Normal recovery (PostgreSQL): 30 seconds
- Slow recovery (NewsAPI): 5 minutes
- Critical services (Kite Connect): 60 seconds

**Queue Sizes:**
- Database writes: 10,000 operations
- Redis messages: 1,000 messages
- Message age limit: 5 minutes

## Troubleshooting

### Circuit Breaker Stuck Open

**Symptoms:** Service appears healthy but circuit breaker remains open

**Solution:**
```python
from src.shared.error_handling import get_circuit_breaker

breaker = get_circuit_breaker("service_name")
breaker.reset()  # Manually reset
```

### Queue Filling Up

**Symptoms:** Database queue size growing, operations not processing

**Solution:**
```python
from src.database.connection import db_connection

# Check queue stats
stats = db_connection.get_queue_stats()

# Process queued operations
processed = db_connection.process_queued_operations(max_operations=1000)

# If database is healthy but queue not processing
db_connection.enable_queue_processing()
```

### Stale Fallback Data

**Symptoms:** System using old cached data

**Solution:**
```python
from src.shared.error_handling import get_degradation_manager

degradation_manager = get_degradation_manager()

# Check data age
age = degradation_manager.get_data_age("service_name")

# Force service check
if service_is_actually_available():
    degradation_manager.mark_service_available("service_name")
```

### All Services Degraded

**Symptoms:** Multiple circuit breakers open, system in degraded mode

**Solution:**
1. Check network connectivity
2. Verify service credentials
3. Check service status pages
4. Review logs for root cause
5. Manually reset circuit breakers if services recovered

```bash
# Check detailed health
curl -H "X-API-Key: your-key" http://localhost:8000/health/detailed

# Check circuit breakers
curl -H "X-API-Key: your-key" http://localhost:8000/health/circuit-breakers
```

## Testing Error Handling

### Simulate Service Failures

```python
# Simulate NewsAPI failure
from src.sentiment.analyzer import SentimentAnalyzer

analyzer = SentimentAnalyzer(api_key="invalid_key")
articles = analyzer.fetch_news(["AAPL"])  # Will fail and trigger degradation

# Simulate Redis failure
from src.shared.redis_client import get_redis_client

redis_client = get_redis_client()
redis_client.client.connection_pool.disconnect()  # Force disconnect

# Simulate database failure
from src.database.connection import db_connection

db_connection.close()  # Close connection
```

### Verify Circuit Breaker Behavior

```python
from src.shared.error_handling import get_circuit_breaker, CircuitBreakerOpenError

breaker = get_circuit_breaker("test_service")

# Trigger failures
for i in range(6):
    try:
        breaker.call(lambda: 1/0)  # Always fails
    except:
        pass

# Verify circuit is open
assert breaker.state == CircuitState.OPEN

# Verify calls are rejected
try:
    breaker.call(lambda: "success")
    assert False, "Should have raised CircuitBreakerOpenError"
except CircuitBreakerOpenError:
    pass  # Expected
```

## Performance Impact

**Circuit Breakers:** < 1ms overhead per call
**Error Logging:** < 5ms per log entry
**Queue Operations:** < 1ms per enqueue/dequeue
**Health Checks:** < 10ms per check

The error handling system adds minimal overhead while providing significant reliability improvements.
