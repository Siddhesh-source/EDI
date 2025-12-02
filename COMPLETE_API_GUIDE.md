# Complete FastAPI Backend Guide

## Overview

Comprehensive FastAPI backend for algorithmic trading system with Indian markets support (NSE/BSE) via Zerodha Kite Connect.

## Architecture

```
FastAPI Application
├── News & Sentiment Endpoints
├── CMS (Composite Market Score) Endpoints
├── Regime Detection Endpoints
├── Trading Signals Endpoints
├── Backtesting Endpoints
├── Zerodha Authentication Endpoints
└── Trading Execution Endpoints
```

## Base URL

```
http://localhost:8000
```

## API Endpoints

### 1. Health Check

**GET** `/health`

Check API health and service status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00",
  "services": {
    "nlp_engine": "active",
    "cms_engine": "active",
    "regime_detector": "active",
    "redis": "connected",
    "zerodha": "authenticated"
  }
}
```

### 2. News & Sentiment

#### Analyze Sentiment

**POST** `/news/sentiment`

Analyze sentiment for news articles.

**Request Body:**
```json
{
  "articles": [
    {
      "source": "Economic Times",
      "title": "Reliance Industries reports strong Q4 earnings",
      "content": "Full article content...",
      "url": "https://example.com/article",
      "author": "John Doe",
      "published_at": "2024-01-15T10:00:00",
      "symbols": ["RELIANCE"]
    }
  ]
}
```

**Response:**
```json
{
  "sentiment_index": 0.65,
  "confidence": 0.85,
  "article_sentiments": [
    {
      "score": 0.70,
      "confidence": 0.88,
      "positive": 0.75,
      "negative": 0.05,
      "neutral": 0.20
    }
  ],
  "detected_events": [
    {
      "type": "EARNINGS",
      "severity": 0.8,
      "keywords": ["earnings", "profit", "growth"]
    }
  ],
  "event_shock_factor": 0.15
}
```

#### Stream Live Sentiment

**GET** `/sentiment/live`

Server-Sent Events stream for real-time sentiment updates.

**Response:** (SSE stream)
```
data: {"sentiment_index": 0.65, "confidence": 0.85, "timestamp": "2024-01-15T10:30:00"}

data: {"sentiment_index": 0.68, "confidence": 0.87, "timestamp": "2024-01-15T10:31:00"}
```

### 3. Composite Market Score (CMS)

#### Calculate CMS

**POST** `/cms/calculate`

Calculate Composite Market Score.

**Request Body:**
```json
{
  "symbol": "RELIANCE",
  "sentiment_index": 0.65,
  "volatility_index": 0.25,
  "trend_strength": 0.40,
  "event_shock_factor": 0.15
}
```

**Response:**
```json
{
  "cms_score": 46.00,
  "signal_type": "HOLD",
  "confidence": 0.7432,
  "components": {
    "sentiment_index": 0.65,
    "volatility_index": 0.25,
    "trend_strength": 0.40,
    "event_shock_factor": 0.15
  },
  "weighted_contributions": {
    "sentiment": 26.00,
    "volatility": -7.50,
    "trend": 8.00,
    "event": 1.50
  },
  "explanation": "HOLD signal generated with CMS of 46.00...",
  "timestamp": "2024-01-15T10:30:00"
}
```

#### Stream Live CMS

**GET** `/cms/live`

Server-Sent Events stream for real-time CMS updates.

#### Get CMS History

**GET** `/cms/history/{symbol}?days=7`

Get historical CMS values.

**Response:**
```json
{
  "symbol": "RELIANCE",
  "history": [
    {
      "cms_score": 46.00,
      "signal_type": "HOLD",
      "confidence": 0.7432,
      "timestamp": "2024-01-15T10:30:00"
    }
  ]
}
```

### 4. Market Regime

#### Stream Live Regime

**GET** `/regime/live`

Server-Sent Events stream for real-time regime updates.

### 5. Trading Signals

#### Stream Live Signals

**GET** `/signals/live`

Server-Sent Events stream for real-time trading signals.

#### Get Signal History

**GET** `/signals/history/{symbol}?days=7`

Get historical trading signals.

**Response:**
```json
{
  "symbol": "RELIANCE",
  "signals": [
    {
      "signal_type": "BUY",
      "price": 2450.50,
      "confidence": 0.82,
      "shares": 40,
      "position_value": 98020.00,
      "risk_amount": 1000.00,
      "stop_loss_price": 2425.50,
      "take_profit_price": 2500.50,
      "executed": true,
      "timestamp": "2024-01-15T10:30:00"
    }
  ]
}
```

### 6. Backtesting

#### Run Backtest

**POST** `/backtest/run`

Run a backtest (executes in background).

**Request Body:**
```json
{
  "symbol": "RELIANCE",
  "start_date": "2023-01-01T00:00:00",
  "end_date": "2023-12-31T23:59:59",
  "initial_capital": 100000,
  "position_size_pct": 0.1,
  "strategy_params": {
    "cms_buy_threshold": 50,
    "cms_sell_threshold": -50
  }
}
```

**Response:**
```json
{
  "message": "Backtest started",
  "symbol": "RELIANCE",
  "start_date": "2023-01-01T00:00:00",
  "end_date": "2023-12-31T23:59:59"
}
```

#### Get Backtest Results

**GET** `/backtest/results?symbol=RELIANCE&limit=10`

Get backtest results.

**Response:**
```json
{
  "results": [
    {
      "id": "uuid-here",
      "name": "RELIANCE Backtest",
      "symbol": "RELIANCE",
      "total_return": 0.2534,
      "cagr": 0.2534,
      "sharpe_ratio": 1.85,
      "sortino_ratio": 2.12,
      "max_drawdown": 0.1234,
      "win_rate": 0.6250,
      "profit_factor": 2.15,
      "total_trades": 48,
      "executed_at": "2024-01-15T10:30:00"
    }
  ]
}
```

#### Get Backtest Detail

**GET** `/backtest/result/{backtest_id}`

Get detailed backtest result with equity curve and trades.

### 7. Zerodha Authentication

#### Initialize Authentication

**POST** `/zerodha/auth/init`

Initialize Zerodha authentication.

**Request Body:**
```json
{
  "api_key": "your_api_key",
  "api_secret": "your_api_secret"
}
```

**Response:**
```json
{
  "login_url": "https://kite.zerodha.com/connect/login?api_key=...",
  "message": "Please visit the login URL and authorize the application"
}
```

#### Complete Authentication

**POST** `/zerodha/auth/complete`

Complete authentication with request token.

**Request Body:**
```json
{
  "api_key": "your_api_key",
  "api_secret": "your_api_secret",
  "request_token": "token_from_callback"
}
```

**Response:**
```json
{
  "message": "Authentication successful",
  "user_id": "AB1234",
  "user_name": "John Doe",
  "email": "john@example.com"
}
```

### 8. Trading Execution

#### Execute Trade

**POST** `/trade/execute`

Place an order through Zerodha.

**Request Body:**
```json
{
  "symbol": "RELIANCE",
  "exchange": "NSE",
  "transaction_type": "BUY",
  "quantity": 10,
  "order_type": "MARKET",
  "product": "CNC",
  "price": null,
  "trigger_price": null,
  "tag": "algo_trade_001"
}
```

**Response:**
```json
{
  "order_id": "240115000123456",
  "status": "COMPLETE",
  "message": "Order placed successfully"
}
```

#### Get Trade Status

**GET** `/trade/status/{order_id}`

Get status of a specific order.

**Response:**
```json
{
  "order_id": "240115000123456",
  "status": "COMPLETE",
  "filled_quantity": 10,
  "pending_quantity": 0,
  "average_price": 2450.50,
  "order_timestamp": "2024-01-15T10:30:00",
  "exchange_timestamp": "2024-01-15T10:30:05"
}
```

#### Get Trade Logs

**GET** `/trade/logs?symbol=RELIANCE&days=7&limit=50`

Get trade execution logs.

**Response:**
```json
{
  "logs": [
    {
      "order_id": "240115000123456",
      "symbol": "RELIANCE",
      "exchange": "NSE",
      "transaction_type": "BUY",
      "order_type": "MARKET",
      "quantity": 10,
      "price": null,
      "filled_quantity": 10,
      "average_price": 2450.50,
      "status": "COMPLETE",
      "order_timestamp": "2024-01-15T10:30:00"
    }
  ]
}
```

#### Modify Order

**PUT** `/trade/modify/{order_id}`

Modify an existing order.

**Query Parameters:**
- `quantity`: New quantity (optional)
- `price`: New price (optional)
- `order_type`: New order type (optional)
- `trigger_price`: New trigger price (optional)

**Response:**
```json
{
  "message": "Order modified successfully",
  "order_id": "240115000123456"
}
```

#### Cancel Order

**DELETE** `/trade/cancel/{order_id}`

Cancel an existing order.

**Response:**
```json
{
  "message": "Order cancelled successfully",
  "order_id": "240115000123456"
}
```

#### Get Holdings

**GET** `/trade/holdings`

Get current holdings from Zerodha.

**Response:**
```json
{
  "holdings": [
    {
      "tradingsymbol": "RELIANCE",
      "exchange": "NSE",
      "quantity": 100,
      "average_price": 2400.00,
      "last_price": 2450.50,
      "pnl": 5050.00
    }
  ]
}
```

#### Get Positions

**GET** `/trade/positions`

Get current positions from Zerodha.

**Response:**
```json
{
  "positions": {
    "net": [
      {
        "tradingsymbol": "RELIANCE",
        "exchange": "NSE",
        "product": "CNC",
        "quantity": 10,
        "average_price": 2450.50,
        "last_price": 2455.00,
        "pnl": 45.00
      }
    ],
    "day": []
  }
}
```

#### Get Margins

**GET** `/trade/margins`

Get margin details from Zerodha.

**Response:**
```json
{
  "margins": {
    "equity": {
      "enabled": true,
      "net": 50000.00,
      "available": {
        "adhoc_margin": 0,
        "cash": 50000.00,
        "collateral": 0,
        "intraday_payin": 0
      },
      "utilised": {
        "debits": 0,
        "exposure": 0,
        "m2m_realised": 0,
        "m2m_unrealised": 0,
        "option_premium": 0,
        "payout": 0,
        "span": 0,
        "holding_sales": 0,
        "turnover": 0
      }
    }
  }
}
```

## Redis Streaming Channels

### 1. Price Updates
**Channel:** `price.live`

```json
{
  "symbol": "RELIANCE",
  "price": 2450.50,
  "volume": 1234567,
  "timestamp": "2024-01-15T10:30:00"
}
```

### 2. Sentiment Updates
**Channel:** `news.sentiment.live`

```json
{
  "sentiment_index": 0.65,
  "confidence": 0.85,
  "article_count": 5,
  "timestamp": "2024-01-15T10:30:00"
}
```

### 3. Event Updates
**Channel:** `events.live`

```json
{
  "event_type": "EARNINGS",
  "severity": 0.8,
  "symbols": ["RELIANCE"],
  "timestamp": "2024-01-15T10:30:00"
}
```

### 4. CMS Updates
**Channel:** `cms.live`

```json
{
  "symbol": "RELIANCE",
  "cms_score": 46.00,
  "signal_type": "HOLD",
  "confidence": 0.7432,
  "timestamp": "2024-01-15T10:30:00"
}
```

### 5. Signal Updates
**Channel:** `signals.live`

```json
{
  "symbol": "RELIANCE",
  "signal_type": "BUY",
  "price": 2450.50,
  "confidence": 0.82,
  "timestamp": "2024-01-15T10:30:00"
}
```

### 6. Trade Updates
**Channel:** `trades.live`

```json
{
  "order_id": "240115000123456",
  "symbol": "RELIANCE",
  "transaction_type": "BUY",
  "quantity": 10,
  "status": "COMPLETE",
  "timestamp": "2024-01-15T10:30:00"
}
```

### 7. Order Updates
**Channel:** `orders.updates`

```json
{
  "order_id": "240115000123456",
  "symbol": "RELIANCE",
  "status": "COMPLETE",
  "filled_quantity": 10,
  "average_price": 2450.50,
  "timestamp": "2024-01-15T10:30:00"
}
```

## Error Handling

All endpoints return standard HTTP status codes:

- `200`: Success
- `400`: Bad Request
- `401`: Unauthorized (Zerodha not authenticated)
- `404`: Not Found
- `500`: Internal Server Error

**Error Response Format:**
```json
{
  "detail": "Error message here"
}
```

## Retry Logic

The Zerodha client implements automatic retry logic:
- **Max Retries:** 3
- **Retry Delay:** Exponential backoff (1s, 2s, 3s)
- **Retryable Errors:** Network errors, temporary failures
- **Non-Retryable:** Token errors, permission errors

## Rate Limiting

Zerodha API has rate limits:
- **Order Placement:** 10 requests/second
- **Order Modification:** 10 requests/second
- **Market Data:** 3 requests/second
- **Historical Data:** 3 requests/second

The API automatically handles rate limiting with retry logic.

## Running the API

### Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run with uvicorn
uvicorn src.api.complete_api:app --reload --host 0.0.0.0 --port 8000
```

### Production

```bash
# Run with gunicorn + uvicorn workers
gunicorn src.api.complete_api:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120
```

### Docker

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "src.api.complete_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/trading

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Zerodha (optional, can be set via API)
ZERODHA_API_KEY=your_api_key
ZERODHA_API_SECRET=your_api_secret

# Logging
LOG_LEVEL=INFO
```

## Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=src tests/

# Test specific endpoint
pytest tests/test_api.py::test_health_check
```

## API Documentation

Interactive API documentation is available at:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Conclusion

This complete FastAPI backend provides a production-ready foundation for algorithmic trading with comprehensive error handling, retry logic, Redis streaming, and full Zerodha integration for Indian markets.
