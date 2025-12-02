# Order Executor Module

## Overview

The Order Executor module provides automated trading capabilities through integration with Zerodha's Kite Connect API. It subscribes to trading signals from Redis, validates them against risk management rules, executes orders, and tracks their status.

## Features

- **Automated Order Execution**: Subscribes to trading signals and automatically executes orders
- **Risk Management**: Validates signals against configurable risk rules before execution
- **Order Tracking**: Monitors order status and updates database records
- **Error Handling**: Gracefully handles API failures and disables auto-trading when necessary
- **Simulation Mode**: Runs in simulation mode when Kite Connect credentials are not configured

## Components

### KiteConnectClient

Wrapper around the Kite Connect API that handles:
- Authentication and connection management
- Order placement (market and limit orders)
- Order status tracking
- Order cancellation
- Simulation mode for testing without live API

### OrderExecutor

Main executor class that:
- Subscribes to Redis signals channel
- Validates signals against risk management rules
- Executes orders through KiteConnectClient
- Stores orders in PostgreSQL database
- Tracks daily trade counts and position sizes
- Handles order fill notifications

## Usage

### Basic Setup

```python
from src.executor import OrderExecutor, KiteConnectClient
from src.shared.redis_client import get_redis_client

# Initialize Redis client
redis_client = get_redis_client()

# Initialize Kite Connect client
kite_client = KiteConnectClient(
    api_key="your_api_key",
    api_secret="your_api_secret",
    access_token="your_access_token"
)

# Initialize order executor
executor = OrderExecutor(
    redis_client=redis_client,
    kite_client=kite_client,
    enable_auto_trading=True,
    position_size=1000.0,
    max_position_size=10000.0,
    max_daily_trades=10
)

# Start listening for signals
executor.start()
await executor.listen()
```

### Manual Order Execution

```python
from src.shared.models import TradingSignalType

# Execute a manual order
order = executor.execute_order(
    signal_type=TradingSignalType.BUY,
    symbol="RELIANCE",
    signal_data={'cms_score': 75.0, 'timestamp': datetime.now().isoformat()}
)

# Check order status
status = executor.check_order_status(order.order_id)

# Handle order fill
executor.handle_fill(order.order_id)
```

### Risk Management Validation

```python
from src.executor import RiskManagementError

try:
    executor.validate_signal(TradingSignalType.BUY, cms_score=75.0)
    print("Signal validation passed")
except RiskManagementError as e:
    print(f"Signal rejected: {e}")
```

## Configuration

Configure the order executor through environment variables or settings:

```python
# In .env file
KITE_API_KEY=your_api_key
KITE_API_SECRET=your_api_secret
KITE_ACCESS_TOKEN=your_access_token
ENABLE_AUTO_TRADING=false
POSITION_SIZE=1000.0
```

## Risk Management Rules

The executor validates signals against the following rules:

1. **Daily Trade Limit**: Maximum number of trades per day (default: 10)
2. **Position Size Limit**: Maximum total position size (default: 10,000)
3. **CMS Score Threshold**: 
   - BUY signals must have CMS > 60
   - SELL signals must have CMS < -60
4. **Auto-Trading Flag**: Must be enabled for automatic execution

## Error Handling

The executor implements comprehensive error handling:

- **Kite Connect API Failures**: Automatically disables auto-trading and logs critical alerts
- **Redis Connection Issues**: Buffers messages and retries with exponential backoff
- **Database Failures**: Logs errors but continues operation
- **Validation Failures**: Logs warnings and skips order execution

## Database Integration

Orders are automatically stored in PostgreSQL with the following information:
- Order ID from broker
- Symbol, quantity, price
- Order type and side
- Status (PENDING, SUBMITTED, FILLED, CANCELLED, REJECTED)
- Timestamp
- Associated signal ID

## Simulation Mode

When Kite Connect credentials are not configured, the executor runs in simulation mode:
- Generates simulated order IDs
- Logs order actions without actual execution
- Returns simulated order status
- Useful for testing and development

## Demo

Run the demo script to see the executor in action:

```bash
python examples/order_executor_demo.py
```

The demo shows:
1. Listening for trading signals from Redis
2. Manual order execution
3. Risk management validation
4. Order status tracking

## Requirements

- Redis (for pub/sub messaging)
- PostgreSQL (for order storage)
- kiteconnect Python package (optional, for live trading)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Trading Signals                          │
│                    (Redis Channel)                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Order Executor                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  1. Receive Signal                                    │  │
│  │  2. Validate Against Risk Rules                      │  │
│  │  3. Execute Order via Kite Connect                   │  │
│  │  4. Store Order in Database                          │  │
│  │  5. Track Order Status                               │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────┬───────────────────────────┬────────────────────┘
             │                           │
             ▼                           ▼
┌────────────────────────┐  ┌──────────────────────────────┐
│   Kite Connect API     │  │   PostgreSQL Database        │
│   (Order Execution)    │  │   (Order Storage)            │
└────────────────────────┘  └──────────────────────────────┘
```

## Validation Requirements

The implementation satisfies the following requirements from the design document:

- **Requirement 11.1**: Validates signals against risk management rules before execution
- **Requirement 11.2**: Uses Kite Connect API to submit orders with symbol, quantity, and order type
- **Requirement 11.3**: Stores order ID and status in PostgreSQL database
- **Requirement 11.4**: Updates order status when filled
- **Requirement 11.5**: Handles Kite Connect API errors and disables auto-trading on failure
