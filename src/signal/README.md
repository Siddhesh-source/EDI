# Signal Aggregator Module

The Signal Aggregator is responsible for computing the Composite Market Score (CMS) and generating trading signals by aggregating data from multiple sources.

## Overview

The Signal Aggregator subscribes to Redis channels for:
- **Sentiment scores** from news analysis
- **Technical indicators** from the C++ engine
- **Market regime** classifications
- **Market events** from news detection

It combines these inputs using configurable weights to compute a CMS score in the range [-100, 100], then generates BUY/SELL/HOLD signals based on configurable thresholds.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Redis Pub/Sub Channels                    │
│  sentiment | events | indicators | regime                   │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Signal Aggregator                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Data Collection (Thread-Safe)                       │  │
│  │  - Latest sentiment score                            │  │
│  │  - Latest technical signals                          │  │
│  │  - Latest market regime                              │  │
│  │  - Recent events (last 10)                           │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│                           ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  CMS Computation                                     │  │
│  │  - Normalize components to [-1, 1]                   │  │
│  │  - Apply configurable weights                        │  │
│  │  - Scale to [-100, 100]                              │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│                           ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Signal Generation                                   │  │
│  │  - CMS > 60: BUY                                     │  │
│  │  - CMS < -60: SELL                                   │  │
│  │  - Otherwise: HOLD                                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│                           ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Explanation Generation                              │  │
│  │  - Detailed component breakdown                      │  │
│  │  - Human-readable descriptions                       │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  Output: Redis signals channel + PostgreSQL storage         │
└─────────────────────────────────────────────────────────────┘
```

## CMS Computation

The Composite Market Score is computed as:

```
CMS = (w_sentiment × sentiment_normalized + 
       w_technical × technical_normalized + 
       w_regime × regime_normalized) × 100
```

Where:
- **w_sentiment** = 0.3 (default, configurable)
- **w_technical** = 0.5 (default, configurable)
- **w_regime** = 0.2 (default, configurable)
- All weights must sum to 1.0

### Component Normalization

**Sentiment Component:**
- Already in [-1, 1] range from sentiment analyzer
- Directly used in CMS computation

**Technical Component:**
- RSI: OVERSOLD → +1.0, OVERBOUGHT → -1.0, NEUTRAL → 0.0
- MACD: BULLISH_CROSS → +1.0, BEARISH_CROSS → -1.0, NEUTRAL → 0.0
- Bollinger Bands: LOWER_BREACH → +1.0, UPPER_BREACH → -1.0, NEUTRAL → 0.0
- Average of all three signals

**Regime Component:**
- TRENDING_UP → +1.0
- TRENDING_DOWN → -1.0
- RANGING → 0.0
- VOLATILE → -0.3
- CALM → +0.2
- Weighted by regime confidence

## Signal Generation Rules

| CMS Range | Signal | Description |
|-----------|--------|-------------|
| > 60 | BUY | Strong bullish signal |
| -60 to 60 | HOLD | Neutral, no clear direction |
| < -60 | SELL | Strong bearish signal |

## Usage

### Basic Usage

```python
from src.shared.redis_client import get_redis_client
from src.signal.aggregator import SignalAggregator

# Initialize Redis client
redis_client = get_redis_client()

# Create aggregator with default settings
aggregator = SignalAggregator(redis_client)

# Start subscribing to channels
aggregator.start()

# Listen for messages (async)
await aggregator.listen()

# Stop when done
aggregator.stop()
```

### Custom Configuration

```python
# Create aggregator with custom weights and thresholds
aggregator = SignalAggregator(
    redis_client=redis_client,
    weight_sentiment=0.4,  # Increase sentiment weight
    weight_technical=0.4,  # Decrease technical weight
    weight_regime=0.2,     # Keep regime weight
    buy_threshold=70.0,    # More conservative buy threshold
    sell_threshold=-70.0   # More conservative sell threshold
)
```

### Manual Signal Generation

```python
from src.shared.models import AggregatedData, TechnicalSignals, MarketRegime

# Create aggregated data
data = AggregatedData(
    sentiment_score=0.6,
    technical_signals=TechnicalSignals(...),
    regime=MarketRegime(...),
    events=[],
    timestamp=datetime.now()
)

# Generate signal
signal = aggregator.generate_signal(data)

print(f"Signal: {signal.signal_type.value}")
print(f"CMS: {signal.cms.score:.2f}")
print(f"Explanation: {signal.explanation.summary}")
```

## Data Flow

1. **Data Collection**: Aggregator subscribes to Redis channels and maintains latest data from each source
2. **Trigger**: When all required data is available, signal generation is triggered
3. **CMS Computation**: Components are normalized and weighted to compute CMS
4. **Signal Generation**: Signal type determined based on CMS and thresholds
5. **Explanation**: Detailed explanation generated with component breakdowns
6. **Publishing**: Signal published to Redis `signals` channel
7. **Storage**: Signal stored in PostgreSQL for historical analysis

## Thread Safety

The aggregator uses thread-safe data structures with locks to handle concurrent updates from multiple Redis channels. All data access is protected by a lock to prevent race conditions.

## Error Handling

- **Missing Data**: Signal generation skipped if any required component is missing
- **Redis Failures**: Errors logged, buffering enabled for reconnection
- **Database Failures**: Errors logged, signal still published to Redis
- **Invalid Data**: Parsing errors logged, invalid messages skipped

## Configuration

Configuration is loaded from environment variables via `src/shared/config.py`:

```bash
# CMS Weights (must sum to 1.0)
CMS_WEIGHT_SENTIMENT=0.3
CMS_WEIGHT_TECHNICAL=0.5
CMS_WEIGHT_REGIME=0.2

# Signal Thresholds
CMS_BUY_THRESHOLD=60.0
CMS_SELL_THRESHOLD=-60.0
```

## Testing

Run the demo script to test the signal aggregator:

```bash
python examples/signal_aggregator_demo.py
```

This will:
1. Start the signal aggregator
2. Publish test data to Redis channels
3. Generate and display a trading signal
4. Show the complete explanation

## Requirements Validation

This implementation satisfies the following requirements:

- **5.1**: Aggregates sentiment, technical, and regime data
- **5.2**: CMS normalized to [-100, 100] range
- **5.3**: BUY signal when CMS > 60
- **5.4**: SELL signal when CMS < -60
- **5.5**: HOLD signal when -60 ≤ CMS ≤ 60
- **5.6**: Detailed explanation with component scores and weights
- **14.1**: Individual component scores included in explanation
- **14.2**: Weights documented in explanation
- **14.3**: Specific technical indicators listed in explanation
- **14.4**: Event type, severity, and keywords included in explanation

## Future Enhancements

- Support for multiple symbols simultaneously
- Historical signal analysis and backtesting integration
- Machine learning-based weight optimization
- Real-time weight adjustment based on market conditions
- Advanced confidence scoring using multiple factors
