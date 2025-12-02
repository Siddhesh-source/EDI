# Backtesting Module

The backtesting module provides historical strategy validation for the explainable algorithmic trading system. It allows you to test trading strategies against historical data to evaluate performance before deploying them in live trading.

## Features

- **Historical Data Retrieval**: Loads price data, sentiment scores, and events from PostgreSQL
- **Chronological Replay**: Replays data in chronological order to prevent look-ahead bias
- **Trade Simulation**: Simulates buy/sell decisions based on CMS thresholds
- **Performance Metrics**: Computes comprehensive metrics including:
  - Total return
  - Sharpe ratio
  - Maximum drawdown
  - Win rate
  - Average trade duration
- **Result Persistence**: Stores backtest results in PostgreSQL for future analysis

## Usage

### Basic Example

```python
from datetime import datetime, timedelta
from src.backtest import BacktestingModule
from src.database.connection import DatabaseConnection
from src.shared.models import BacktestConfig

# Initialize database connection
db_connection = DatabaseConnection()
db_connection.initialize()

# Create backtesting module
backtest_module = BacktestingModule(db_connection)

# Configure backtest
config = BacktestConfig(
    symbol="AAPL",
    start_date=datetime.now() - timedelta(days=90),
    end_date=datetime.now(),
    initial_capital=100000.0,
    position_size=0.1,  # Use 10% of capital per trade
    cms_buy_threshold=60.0,
    cms_sell_threshold=-60.0
)

# Run backtest
result = backtest_module.run_backtest(config)

# Access results
print(f"Total Return: {result.metrics.total_return:.2%}")
print(f"Sharpe Ratio: {result.metrics.sharpe_ratio:.2f}")
print(f"Max Drawdown: {result.metrics.max_drawdown:.2%}")
print(f"Win Rate: {result.metrics.win_rate:.2%}")
print(f"Total Trades: {result.metrics.total_trades}")

# Clean up
db_connection.close()
```

## Configuration Parameters

### BacktestConfig

- **symbol** (str): Stock symbol to backtest (e.g., "AAPL")
- **start_date** (datetime): Start date for historical data
- **end_date** (datetime): End date for historical data
- **initial_capital** (float): Starting capital amount
- **position_size** (float): Fraction of capital to use per trade (0.0 to 1.0)
- **cms_buy_threshold** (float): CMS score above which to generate BUY signals
- **cms_sell_threshold** (float): CMS score below which to generate SELL signals

## Results

### BacktestResult

The backtest returns a `BacktestResult` object containing:

- **backtest_id** (str): Unique identifier for the backtest
- **config** (BacktestConfig): Configuration used for the backtest
- **trades** (List[Trade]): List of all executed trades
- **metrics** (PerformanceMetrics): Performance metrics
- **equity_curve** (List[Tuple[datetime, float]]): Equity over time

### PerformanceMetrics

- **total_return** (float): Total return as a fraction (e.g., 0.15 = 15%)
- **sharpe_ratio** (float): Risk-adjusted return metric (annualized)
- **max_drawdown** (float): Maximum peak-to-trough decline (0.0 to 1.0)
- **win_rate** (float): Percentage of winning trades (0.0 to 1.0)
- **total_trades** (int): Total number of trades executed
- **avg_trade_duration** (timedelta): Average time between entry and exit

### Trade

Each trade record contains:

- **entry_time** (datetime): When the position was opened
- **exit_time** (datetime): When the position was closed
- **entry_price** (float): Price at entry
- **exit_price** (float): Price at exit
- **quantity** (float): Number of shares traded
- **pnl** (float): Profit/loss for the trade
- **signal_type** (TradingSignalType): Type of entry signal (BUY/SELL)

## How It Works

### 1. Data Loading

The module loads historical data from PostgreSQL:
- Price data (OHLC bars)
- Sentiment scores from news analysis
- Detected market events
- Pre-computed trading signals (if available)

### 2. Signal Generation

For each timestamp, the module:
- Uses pre-computed signals if available
- Otherwise, computes a simple CMS score from sentiment and events
- Generates BUY/SELL/HOLD signals based on CMS thresholds

### 3. Trade Simulation

The simulation:
- Processes data chronologically to prevent look-ahead bias
- Opens positions on BUY signals (if no position exists)
- Closes positions on SELL signals (if position exists)
- Tracks equity at each timestamp
- Records all trade details

### 4. Metrics Computation

After simulation, the module computes:
- **Total Return**: (Final Equity - Initial Capital) / Initial Capital
- **Sharpe Ratio**: Risk-adjusted return using daily returns
- **Max Drawdown**: Largest peak-to-trough decline
- **Win Rate**: Percentage of profitable trades
- **Avg Trade Duration**: Mean time between entry and exit

### 5. Result Storage

Results are stored in PostgreSQL for:
- Historical comparison
- Strategy optimization
- Performance tracking

## Important Notes

### Look-Ahead Bias Prevention

The backtesting module ensures chronological data replay:
- Timestamps are sorted before processing
- Only data available at each timestamp is used for decisions
- No future information leaks into past decisions

### Position Management

Current implementation:
- Only long positions (no short selling)
- One position at a time (no pyramiding)
- Full position exit on SELL signals
- Position size based on available capital

### CMS Computation

The simplified CMS used in backtesting:
- Sentiment component: 50% weight
- Event component: 50% weight
- Negative events (bankruptcy, regulatory) decrease score
- Positive events (earnings, merger) increase score
- Score clamped to [-100, 100] range

## Demo Script

Run the demo script to see the backtesting module in action:

```bash
python examples/backtest_demo.py
```

## Testing

Run the test suite:

```bash
pytest tests/test_backtest.py -v
```

## Requirements Validation

This module validates the following requirements:

- **6.1**: Retrieves historical price and news data from PostgreSQL
- **6.2**: Replays data chronologically without look-ahead bias
- **6.3**: Computes performance metrics (return, Sharpe, drawdown, win rate)
- **6.4**: Records trade details (entry/exit prices, holding period, P&L)
- **6.5**: Stores backtest results in PostgreSQL with unique identifier

## Future Enhancements

Potential improvements:
- Support for short positions
- Multiple position sizing strategies
- Transaction cost modeling
- Slippage simulation
- Walk-forward optimization
- Monte Carlo simulation
- Strategy parameter optimization
