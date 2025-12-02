# Market Regime Detector

The Market Regime Detector classifies current market conditions based on price action analysis. It uses a rolling window of price bars to identify whether the market is trending, ranging, volatile, or calm.

## Features

- **Regime Classification**: Identifies 5 distinct market regimes
  - TRENDING_UP: Strong upward trend
  - TRENDING_DOWN: Strong downward trend
  - RANGING: Sideways/consolidating market
  - VOLATILE: High volatility conditions
  - CALM: Low volatility conditions

- **Confidence Scoring**: Each regime classification includes a confidence score (0.0 to 1.0)

- **Rolling Window Analysis**: Uses the most recent 100 price bars (configurable)

- **Redis Integration**: Publishes regime changes to Redis `regime` channel

- **Database Storage**: Stores regime data in PostgreSQL

## Usage

### Basic Usage

```python
from src.regime import MarketRegimeDetector
from src.shared.models import OHLC
from datetime import datetime

# Initialize detector
detector = MarketRegimeDetector(window_size=100, confidence_threshold=0.6)

# Prepare price data
prices = [
    OHLC(open=100.0, high=102.0, low=99.0, close=101.0, volume=1000, timestamp=datetime.now()),
    # ... more price bars
]

# Detect regime
regime = detector.detect_regime(prices)

print(f"Regime: {regime.regime_type.value}")
print(f"Confidence: {regime.confidence:.2f}")
print(f"Volatility: {regime.volatility:.4f}")
print(f"Trend Strength: {regime.trend_strength:.4f}")
```

### Process Prices (Full Pipeline)

```python
# Process prices: detect, publish to Redis, store in DB
regime = detector.process_prices(prices)
```

### Publish to Redis

```python
# Manually publish regime to Redis
success = detector.publish_to_redis(regime)
```

## Regime Classification Logic

The detector uses three key metrics:

1. **Volatility**: Standard deviation of log returns
   - HIGH_VOLATILITY > 0.03 → VOLATILE regime
   - LOW_VOLATILITY < 0.01 → CALM regime

2. **Trend Strength**: R-squared from linear regression (0.0 to 1.0)
   - STRONG_TREND > 0.5 → TRENDING regime
   - WEAK_TREND < 0.3 → RANGING regime

3. **Trend Direction**: Normalized slope from linear regression
   - Positive → TRENDING_UP
   - Negative → TRENDING_DOWN

### Confidence Threshold

If the confidence score is below the threshold (default: 0.6), the regime defaults to RANGING. This ensures conservative classification when market conditions are ambiguous.

## Configuration

```python
detector = MarketRegimeDetector(
    window_size=100,           # Number of bars to analyze
    confidence_threshold=0.6   # Minimum confidence for classification
)
```

## Requirements

- **Minimum Data**: At least 20 price bars required for regime detection
- **Optimal Data**: 100+ price bars for accurate classification
- **Window Size**: Only the most recent `window_size` bars are used

## Redis Channel

Regime changes are published to the `regime` Redis channel with the following format:

```json
{
    "regime_type": "trending_up",
    "confidence": 0.85,
    "volatility": 0.025,
    "trend_strength": 0.78,
    "timestamp": "2024-01-15T10:30:00"
}
```

## Error Handling

- **Insufficient Data**: Returns default RANGING regime with 0.5 confidence
- **Redis Unavailable**: Logs warning, continues operation
- **Database Errors**: Logs error, continues operation

## Performance

- **Computation Time**: < 10ms for 100 bars
- **Memory Usage**: Minimal (only stores last regime)
- **Redis Latency**: < 10ms for publish operations

## Integration with Trading System

The regime detector integrates with the broader trading system:

1. **Input**: Receives price data from market data feed
2. **Processing**: Analyzes rolling window of prices
3. **Output**: Publishes regime to Redis for signal aggregator
4. **Storage**: Stores regime data for historical analysis

The regime component is used by the Signal Aggregator to adjust trading signals based on market conditions.
