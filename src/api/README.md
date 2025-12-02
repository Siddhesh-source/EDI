# FastAPI Backend

This is the REST API backend for the Explainable Algorithmic Trading System.

## Features

- **Authentication**: API key-based authentication for all endpoints (except health check)
- **CORS**: Cross-Origin Resource Sharing enabled for frontend integration
- **Rate Limiting**: 100 requests per 60 seconds per IP address
- **Logging**: Comprehensive request/response logging with request IDs
- **Error Handling**: Structured error responses with appropriate HTTP status codes
- **WebSocket**: Real-time signal updates via WebSocket connection

## Endpoints

### Health Check

```
GET /health
```

Returns the health status of the system and its services (database, Redis, signal aggregator).

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00",
  "services": {
    "database": true,
    "redis": true,
    "signal_aggregator": true
  }
}
```

### Current Signal

```
GET /api/v1/signal/current
```

Get the current trading signal with CMS and detailed explanation.

**Headers:**
- `X-API-Key`: Your API key

**Response:**
```json
{
  "signal_type": "buy",
  "cms_score": 75.5,
  "sentiment_component": 30.0,
  "technical_component": 40.0,
  "regime_component": 5.5,
  "confidence": 0.85,
  "explanation": {
    "summary": "BUY signal generated...",
    "sentiment_details": "News sentiment is strongly positive...",
    "technical_details": "RSI indicates oversold conditions...",
    "regime_details": "Market is upward trending...",
    "event_details": "No significant market events...",
    "component_scores": {
      "sentiment": 30.0,
      "technical": 40.0,
      "regime": 5.5,
      "cms": 75.5
    }
  },
  "timestamp": "2024-01-01T12:00:00"
}
```

### Signal History

```
GET /api/v1/signal/history?start=<datetime>&end=<datetime>&limit=<int>
```

Get historical trading signals.

**Query Parameters:**
- `start` (optional): Start datetime (ISO format)
- `end` (optional): End datetime (ISO format)
- `limit` (optional): Maximum number of signals (default: 100)

**Headers:**
- `X-API-Key`: Your API key

**Response:**
```json
[
  {
    "signal_type": "buy",
    "cms_score": 75.5,
    ...
  }
]
```

### Run Backtest

```
POST /api/v1/backtest
```

Run a backtest with the given configuration.

**Headers:**
- `X-API-Key`: Your API key

**Request Body:**
```json
{
  "symbol": "RELIANCE",
  "start_date": "2024-01-01T00:00:00",
  "end_date": "2024-01-31T23:59:59",
  "initial_capital": 100000.0,
  "position_size": 0.1,
  "cms_buy_threshold": 60.0,
  "cms_sell_threshold": -60.0
}
```

**Response:**
```json
{
  "backtest_id": "uuid-here",
  "status": "completed",
  "message": "Backtest completed with 15 trades"
}
```

### Get Backtest Results

```
GET /api/v1/backtest/{backtest_id}
```

Get backtest results by ID.

**Headers:**
- `X-API-Key`: Your API key

**Response:**
```json
{
  "backtest_id": "uuid-here",
  "config": { ... },
  "metrics": {
    "total_return": 0.15,
    "sharpe_ratio": 1.5,
    "max_drawdown": 0.08,
    "win_rate": 0.65,
    "total_trades": 15,
    "avg_trade_duration": 86400
  },
  "trades": [ ... ],
  "equity_curve": [ ... ],
  "created_at": "2024-01-01T12:00:00"
}
```

### Get Orders

```
GET /api/v1/orders?status=<status>&limit=<int>
```

Get orders, optionally filtered by status.

**Query Parameters:**
- `status` (optional): Order status (pending, submitted, filled, cancelled, rejected)
- `limit` (optional): Maximum number of orders (default: 100)

**Headers:**
- `X-API-Key`: Your API key

**Response:**
```json
[
  {
    "order_id": "order-123",
    "symbol": "RELIANCE",
    "order_type": "market",
    "side": "buy",
    "quantity": 10.0,
    "price": null,
    "status": "filled",
    "timestamp": "2024-01-01T12:00:00"
  }
]
```

### WebSocket - Real-time Signals

```
WS /ws/signals
```

Connect to receive real-time trading signal updates.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/signals');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Signal:', data);
};

// Send ping to keep connection alive
ws.send('ping');
```

**Message Format:**
```json
{
  "type": "signal",
  "data": {
    "signal_type": "buy",
    "cms_score": 75.5,
    ...
  }
}
```

## Running the Server

### Development

```bash
python src/api/main.py
```

Or with uvicorn directly:

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Production

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Or with Gunicorn:

```bash
gunicorn src.api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Configuration

Configuration is managed through environment variables (see `.env.example`):

- `API_KEY`: API key for authentication (default: "default_api_key")
- `API_HOST`: Host to bind to (default: "0.0.0.0")
- `API_PORT`: Port to bind to (default: 8000)
- `POSTGRES_HOST`: PostgreSQL host
- `POSTGRES_PORT`: PostgreSQL port
- `POSTGRES_DB`: PostgreSQL database name
- `POSTGRES_USER`: PostgreSQL username
- `POSTGRES_PASSWORD`: PostgreSQL password
- `REDIS_HOST`: Redis host
- `REDIS_PORT`: Redis port
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

## Middleware

### Logging Middleware

Logs all HTTP requests and responses with:
- Request ID
- Method and path
- Client IP
- Response status code
- Processing time

### Error Handling Middleware

Catches exceptions and returns structured error responses:
- `400 Bad Request`: Validation errors
- `403 Forbidden`: Permission denied
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Unexpected errors
- `504 Gateway Timeout`: Request timeout

### Rate Limiting Middleware

Limits requests to 100 per 60 seconds per IP address. Returns:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Remaining requests in window
- `X-RateLimit-Reset`: Timestamp when limit resets

## Testing

Run the test suite:

```bash
pytest tests/test_api.py -v
```

## API Documentation

Interactive API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Architecture

The FastAPI backend:
1. Initializes connections to PostgreSQL, Redis, and C++ indicator engine on startup
2. Starts the signal aggregator to listen for real-time data
3. Serves REST API endpoints for querying signals, running backtests, and managing orders
4. Broadcasts real-time updates to connected WebSocket clients
5. Gracefully shuts down all connections on application exit

## Error Handling

All endpoints return structured error responses:

```json
{
  "error": "Error type",
  "message": "Detailed error message",
  "request_id": "1234567890"
}
```

## Security

- API key authentication required for all endpoints (except health check)
- HTTPS recommended for production
- Rate limiting to prevent abuse
- Input validation using Pydantic models
- SQL injection prevention via SQLAlchemy ORM
- CORS configured for specific origins in production
