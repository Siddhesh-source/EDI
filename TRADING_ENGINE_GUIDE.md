# Rule-Based Trading Engine Guide

## Overview

A pure rule-based trading engine with no machine learning. Uses technical indicators, sentiment analysis, and composite market scores to generate trading signals with comprehensive risk management.

## Trading Rules

### BUY Signal Conditions (ALL must be met)

1. **Trend Condition**: `EMA20 > EMA50`
   - Confirms uptrend
   - Momentum is positive

2. **Sentiment Condition**: `SentimentIndex > 0.2`
   - Positive market sentiment
   - News and social media are bullish

3. **Composite Score**: `CMS > 0.3`
   - Overall market conditions favorable
   - Multiple factors align bullish

4. **Event Filter**: No negative event keywords detected
   - No bankruptcy, fraud, lawsuit, etc.
   - Clean news environment

### SELL Signal Conditions (ALL must be met)

1. **Trend Condition**: `EMA20 < EMA50`
   - Confirms downtrend
   - Momentum is negative

2. **Sentiment Condition**: `SentimentIndex < -0.3`
   - Negative market sentiment
   - News and social media are bearish

3. **Composite Score**: `CMS < -0.3`
   - Overall market conditions unfavorable
   - Multiple factors align bearish

4. **Event Shock**: `EventShockFactor < -1`
   - Significant negative event occurred
   - Market reaction expected

## Risk Management

### 1. Fixed Risk Per Trade

```python
risk_per_trade = 1% of account balance
```

- Never risk more than 1% on a single trade
- Protects capital from large losses
- Allows for multiple losing trades without significant drawdown

### 2. ATR-Based Stop Loss

```python
stop_loss_distance = ATR × 2.0
stop_loss_price = entry_price ± stop_loss_distance
```

- Dynamic stop loss based on volatility
- Wider stops in volatile markets
- Tighter stops in calm markets

### 3. Position Sizing Formula

```python
# Calculate risk amount
risk_amount = account_balance × 0.01

# Calculate stop distance
stop_distance = ATR × 2.0

# Calculate shares
shares = risk_amount / stop_distance

# Apply max position size constraint
max_position = account_balance × 0.10  # 10% max
if shares × price > max_position:
    shares = max_position / price
```

### 4. Trailing Stop Loss

```python
# For LONG positions
if current_price > entry_price:
    trailing_stop = current_price × 0.98  # 2% below current

# For SHORT positions
if current_price < entry_price:
    trailing_stop = current_price × 1.02  # 2% above current
```

- Locks in profits as price moves favorably
- Automatically adjusts stop loss
- Prevents giving back large gains

### 5. Take Profit Target

```python
# 2:1 Risk/Reward ratio
take_profit_distance = stop_loss_distance × 2
take_profit_price = entry_price ± take_profit_distance
```

## Trading Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Market Data Input                         │
│  • Price Data (OHLCV)                                       │
│  • Technical Indicators (EMA20, EMA50, ATR)                 │
│  • Sentiment Index (from NLP Engine)                        │
│  • CMS Score (from CMS Engine)                              │
│  • Event Data (from Event Detector)                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Rule-Based Trading Engine                       │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Check BUY Conditions                         │  │
│  │  ✓ EMA20 > EMA50?                                    │  │
│  │  ✓ Sentiment > 0.2?                                  │  │
│  │  ✓ CMS > 0.3?                                        │  │
│  │  ✓ No negative events?                               │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │                                        │
│                     ▼                                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Check SELL Conditions                        │  │
│  │  ✓ EMA20 < EMA50?                                    │  │
│  │  ✓ Sentiment < -0.3?                                 │  │
│  │  ✓ CMS < -0.3?                                       │  │
│  │  ✓ Event Shock < -1?                                 │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │                                        │
│                     ▼                                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Generate Signal                              │  │
│  │  • BUY / SELL / HOLD                                 │  │
│  │  • Calculate Confidence                              │  │
│  │  • Generate Reasons                                  │  │
│  └──────────────────┬───────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Risk Management Engine                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Calculate Position Size                      │  │
│  │  1. Risk Amount = Balance × 1%                       │  │
│  │  2. Stop Distance = ATR × 2.0                        │  │
│  │  3. Shares = Risk / Stop Distance                    │  │
│  │  4. Apply Max Position Constraint (10%)              │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │                                        │
│                     ▼                                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Calculate Stop Loss & Take Profit            │  │
│  │  • Stop Loss = Entry ± (ATR × 2)                     │  │
│  │  • Take Profit = Entry ± (ATR × 4)                   │  │
│  │  • Risk/Reward = 1:2                                 │  │
│  └──────────────────┬───────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Signal Distribution                         │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │    Redis     │    │  PostgreSQL  │    │  Order       │ │
│  │  Streaming   │    │   Storage    │    │  Executor    │ │
│  │              │    │              │    │              │ │
│  │ • Real-time  │    │ • History    │    │ • Execute    │ │
│  │ • Pub/Sub    │    │ • Analytics  │    │ • Monitor    │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Position Management                             │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Monitor Open Positions                       │  │
│  │  • Update trailing stops                             │  │
│  │  • Check stop loss / take profit                     │  │
│  │  • Calculate unrealized P&L                          │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │                                        │
│                     ▼                                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Close Positions                              │  │
│  │  • Stop loss hit                                     │  │
│  │  • Take profit hit                                   │  │
│  │  • Trailing stop hit                                 │  │
│  │  • Opposite signal generated                         │  │
│  └──────────────────┬───────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Performance Tracking                            │
│  • Win rate                                                 │
│  • Profit factor                                            │
│  • Average win/loss                                         │
│  • Sharpe ratio                                             │
│  • Maximum drawdown                                         │
└─────────────────────────────────────────────────────────────┘
```

## Usage Examples

### Basic Signal Generation

```python
from src.trading.rule_engine import (
    RuleBasedTradingEngine,
    MarketData,
    RiskParameters
)
from datetime import datetime

# Initialize risk parameters
risk_params = RiskParameters(
    account_balance=100000,
    risk_per_trade_pct=0.01,  # 1%
    atr_stop_multiplier=2.0,
    trailing_stop_pct=0.02,   # 2%
    max_position_size_pct=0.1  # 10%
)

# Initialize trading engine
engine = RuleBasedTradingEngine(risk_params)

# Prepare market data
market_data = MarketData(
    symbol="AAPL",
    current_price=150.00,
    ema_20=152.00,
    ema_50=148.00,
    atr=3.50,
    sentiment_index=0.35,
    cms_score=0.45,
    event_shock_factor=0.10,
    negative_events=[],
    timestamp=datetime.utcnow()
)

# Generate signal
signal = engine.generate_signal(market_data)

print(f"Signal: {signal.signal_type.value}")
print(f"Confidence: {signal.confidence:.2%}")
print(f"Position Size: {signal.position_size.shares} shares")
print(f"Stop Loss: ${signal.position_size.stop_loss_price:.2f}")
print(f"Take Profit: ${signal.position_size.take_profit_price:.2f}")
print(f"Risk/Reward: {signal.position_size.risk_reward_ratio:.2f}:1")
print(f"\nReasons:")
for reason in signal.reasons:
    print(f"  {reason}")
```

### Integration with Other Systems

```python
from src.nlp.engine import EnhancedNLPEngine
from src.regime.enhanced_detector import EnhancedMarketRegimeDetector
from src.signal.cms_engine import CMSEngine
from src.trading.rule_engine import RuleBasedTradingEngine, MarketData

# Initialize all engines
nlp_engine = EnhancedNLPEngine()
regime_detector = EnhancedMarketRegimeDetector()
cms_engine = CMSEngine()
trading_engine = RuleBasedTradingEngine(risk_params)

# Process data
nlp_output = nlp_engine.process_articles(articles)
regime_output = regime_detector.detect_regime(price_bars, nlp_output.sentiment_index.smoothed_score)
cms_result = cms_engine.compute_cms(components)

# Create market data
market_data = MarketData(
    symbol="AAPL",
    current_price=price_bars[-1].close,
    ema_20=regime_output.inputs.ema_20,
    ema_50=regime_output.inputs.ema_50,
    atr=regime_output.inputs.atr,
    sentiment_index=nlp_output.sentiment_index.smoothed_score,
    cms_score=cms_result.cms_score,
    event_shock_factor=nlp_output.event_shock_factor.total_shock,
    negative_events=nlp_output.detected_events,
    timestamp=datetime.utcnow()
)

# Generate and publish signal
signal = trading_engine.generate_signal(market_data)
trading_engine.publish_to_redis(signal)
trading_engine.store_to_database(signal)
```

### Trailing Stop Calculation

```python
# For an open long position
entry_price = 150.00
current_price = 160.00

trailing_stop = engine.calculate_trailing_stop(
    entry_price=entry_price,
    current_price=current_price,
    is_long=True
)

print(f"Entry: ${entry_price:.2f}")
print(f"Current: ${current_price:.2f}")
print(f"Trailing Stop: ${trailing_stop:.2f}")
print(f"Profit Protected: ${current_price - trailing_stop:.2f}")
```

## Redis Message Format

### Channel: `trading.signals`

```json
{
  "signal_type": "BUY",
  "symbol": "AAPL",
  "price": 150.00,
  "confidence": 0.8234,
  "position_size": {
    "shares": 285,
    "position_value": 42750.00,
    "risk_amount": 1000.00,
    "stop_loss_price": 143.00,
    "take_profit_price": 164.00,
    "risk_reward_ratio": 2.0
  },
  "reasons": [
    "✓ Bullish trend: EMA20 (152.00) > EMA50 (148.00) by 2.70%",
    "✓ Positive sentiment: 0.350 > 0.2",
    "✓ Positive CMS: 0.45 > 0.3",
    "✓ No negative events detected"
  ],
  "risk_params": {
    "account_balance": 100000,
    "risk_per_trade_pct": 0.01,
    "atr_stop_multiplier": 2.0,
    "trailing_stop_pct": 0.02,
    "max_position_size_pct": 0.1
  },
  "market_data": {
    "ema_20": 152.00,
    "ema_50": 148.00,
    "atr": 3.50,
    "sentiment_index": 0.3500,
    "cms_score": 0.45,
    "event_shock_factor": 0.1000,
    "negative_events": []
  },
  "timestamp": "2024-01-15T10:30:00"
}
```

## PostgreSQL Queries

### Get Recent Signals

```sql
SELECT * FROM recent_signals LIMIT 20;
```

### Get Open Positions

```sql
SELECT * FROM open_positions;
```

### Get Trading Performance

```sql
SELECT * FROM trading_performance;
```

### Get Best/Worst Trades

```sql
SELECT * FROM trade_extremes;
```

### Calculate Win Rate

```sql
SELECT
    date,
    winning_trades,
    losing_trades,
    ROUND(
        CAST(winning_trades AS DECIMAL) / 
        NULLIF(winning_trades + losing_trades, 0) * 100,
        2
    ) as win_rate_pct
FROM trading_statistics
WHERE date > CURRENT_DATE - INTERVAL '30 days'
ORDER BY date DESC;
```

## Risk Management Best Practices

### 1. Never Override Risk Rules

- Always respect the 1% risk per trade
- Don't increase position size based on "feeling"
- Stick to the system

### 2. Monitor Correlation

- Don't open multiple positions in correlated assets
- Diversify across sectors
- Limit total exposure

### 3. Review Performance Regularly

- Weekly review of win rate
- Monthly review of profit factor
- Quarterly strategy adjustment

### 4. Respect Stop Losses

- Never move stop loss further away
- Only move stop loss closer (trailing)
- Exit when stop is hit

### 5. Take Profits

- Don't be greedy
- Respect take profit targets
- Use trailing stops to lock in gains

## Performance Metrics

### Win Rate
```
Win Rate = Winning Trades / Total Trades
Target: > 50%
```

### Profit Factor
```
Profit Factor = Gross Profit / Gross Loss
Target: > 1.5
```

### Sharpe Ratio
```
Sharpe Ratio = (Return - Risk Free Rate) / Std Dev of Returns
Target: > 1.0
```

### Maximum Drawdown
```
Max Drawdown = (Peak - Trough) / Peak
Target: < 20%
```

## Conclusion

This rule-based trading engine provides a systematic, disciplined approach to trading without relying on machine learning. The clear rules and comprehensive risk management ensure consistent execution and capital preservation.

Key advantages:
- **Transparent**: Every decision is explainable
- **Consistent**: No emotional trading
- **Risk-Managed**: Capital preservation is priority
- **Backtestable**: Rules can be tested historically
- **Scalable**: Works across multiple symbols
