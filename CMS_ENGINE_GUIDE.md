# Composite Market Score (CMS) Engine Guide

## Overview

The Composite Market Score (CMS) Engine combines sentiment, volatility, trend, and event data into a single actionable trading score. It provides clear buy/sell/hold signals with confidence levels and detailed explanations.

## Mathematical Formula

### Core Formula

```
CMS = 0.4 × SentimentIndex 
    - 0.3 × VolatilityIndex 
    + 0.2 × TrendStrength 
    + 0.1 × EventShockFactor
```

**Final Score Range**: [-100, 100]

### Component Explanations

#### 1. Sentiment Index (SI) - Weight: 0.4 (40%)

**Source**: NLP Engine sentiment analysis  
**Range**: [-1, 1]  
**Interpretation**:
- SI > 0.6: Very positive sentiment
- SI > 0.2: Positive sentiment
- -0.2 < SI < 0.2: Neutral sentiment
- SI < -0.2: Negative sentiment
- SI < -0.6: Very negative sentiment

**Impact on CMS**:
- Positive sentiment increases CMS (bullish)
- Negative sentiment decreases CMS (bearish)
- Highest weight because sentiment drives market psychology

#### 2. Volatility Index (VI) - Weight: -0.3 (30%, negative)

**Source**: Regime detector (ATR-based)  
**Range**: [0, 1]  
**Interpretation**:
- VI > 0.8: Extreme volatility
- VI > 0.6: High volatility
- 0.3 < VI < 0.6: Moderate volatility
- VI < 0.3: Low volatility

**Impact on CMS**:
- High volatility decreases CMS (bearish, risky)
- Low volatility increases CMS (bullish, stable)
- Negative weight because volatility represents uncertainty

#### 3. Trend Strength (TS) - Weight: 0.2 (20%)

**Source**: Regime detector (EMA20 vs EMA50)  
**Range**: [-1, 1]  
**Interpretation**:
- TS > 0.5: Strong uptrend
- TS > 0.2: Moderate uptrend
- -0.2 < TS < 0.2: No clear trend
- TS < -0.2: Moderate downtrend
- TS < -0.5: Strong downtrend

**Impact on CMS**:
- Uptrend increases CMS (bullish)
- Downtrend decreases CMS (bearish)
- Moderate weight because trend confirms direction

#### 4. Event Shock Factor (ESF) - Weight: 0.1 (10%)

**Source**: NLP Engine event detection  
**Range**: [0, 1]  
**Interpretation**:
- ESF > 0.8: Extreme event impact
- ESF > 0.6: High event impact
- 0.3 < ESF < 0.6: Moderate event impact
- ESF < 0.3: Low event impact

**Impact on CMS**:
- Amplifies existing sentiment direction
- If sentiment is positive: ESF increases CMS
- If sentiment is negative: ESF decreases CMS
- Lowest weight because events are often temporary

## Normalization Strategies

### Input Normalization

All inputs must be normalized to their expected ranges before CMS calculation:

#### Sentiment Index Normalization
```python
# Already normalized by NLP engine to [-1, 1]
sentiment_normalized = sentiment_raw  # No additional normalization needed
```

#### Volatility Index Normalization
```python
# From ATR calculation
atr = compute_atr(price_bars, period=14)
current_price = price_bars[-1].close
volatility_ratio = atr / current_price

# Normalize to [0, 1] using reference range
volatility_normalized = min(volatility_ratio / 0.05, 1.0)
```

#### Trend Strength Normalization
```python
# From EMA difference
ema_20 = compute_ema(prices, 20)
ema_50 = compute_ema(prices, 50)
trend_ratio = (ema_20 - ema_50) / ema_50

# Normalize to [-1, 1] using tanh scaling
import math
trend_normalized = math.tanh(trend_ratio * 10)
```

#### Event Shock Factor Normalization
```python
# Already normalized by NLP engine to [0, 1]
event_normalized = event_shock_raw  # No additional normalization needed
```

### Output Scaling

```python
# CMS calculation produces value in approximately [-1, 1]
cms_raw = (
    0.4 * sentiment_index +
    -0.3 * volatility_index +
    0.2 * trend_strength +
    0.1 * event_shock_factor
)

# Scale to [-100, 100] for interpretability
cms_final = cms_raw * 100
cms_final = max(-100, min(100, cms_final))  # Ensure bounds
```

## Signal Generation Logic

### Threshold-Based Signals

```python
if cms_score > 50:
    signal = 'BUY'
elif cms_score < -50:
    signal = 'SELL'
else:
    signal = 'HOLD'
```

### Threshold Rationale

**BUY Threshold (50)**:
- Requires strong positive sentiment (SI > 0.5) OR
- Moderate positive sentiment + low volatility + uptrend
- High confidence in bullish conditions

**SELL Threshold (-50)**:
- Requires strong negative sentiment (SI < -0.5) OR
- Moderate negative sentiment + high volatility + downtrend
- High confidence in bearish conditions

**HOLD Range [-50, 50]**:
- Mixed signals or insufficient conviction
- Neutral sentiment with moderate volatility
- Conflicting indicators

### Confidence Calculation

```python
def compute_confidence(components, cms_score):
    # Signal strength: how far from neutral
    signal_strength = abs(cms_score) / 100.0
    
    # Component agreement: how aligned are components
    normalized_components = [
        components.sentiment_index,
        -components.volatility_index,  # Negative because high vol is bearish
        components.trend_strength,
        components.event_shock_factor * (1 if components.sentiment_index > 0 else -1)
    ]
    
    mean = sum(normalized_components) / len(normalized_components)
    variance = sum((x - mean) ** 2 for x in normalized_components) / len(normalized_components)
    std_dev = variance ** 0.5
    agreement = 1.0 - std_dev
    
    # Volatility penalty: high volatility reduces confidence
    volatility_penalty = 1.0 - components.volatility_index
    
    # Weighted confidence
    confidence = (
        signal_strength * 0.5 +
        agreement * 0.3 +
        volatility_penalty * 0.2
    )
    
    return max(0.0, min(1.0, confidence))
```

## Usage Examples

### Basic CMS Calculation

```python
from src.signal.cms_engine import CMSEngine, CMSComponents

# Initialize engine
engine = CMSEngine(buy_threshold=50, sell_threshold=-50)

# Prepare components
components = CMSComponents(
    sentiment_index=0.65,      # Positive sentiment
    volatility_index=0.25,     # Low volatility
    trend_strength=0.40,       # Moderate uptrend
    event_shock_factor=0.15    # Low event impact
)

# Compute CMS
result = engine.compute_cms(components)

print(f"CMS Score: {result.cms_score:.2f}")
print(f"Signal: {result.signal_type}")
print(f"Confidence: {result.confidence:.2%}")
print(f"Explanation: {result.explanation}")
```

### Integration with Other Systems

```python
from src.nlp.engine import EnhancedNLPEngine
from src.regime.enhanced_detector import EnhancedMarketRegimeDetector
from src.signal.cms_engine import CMSEngine, CMSComponents

# Initialize engines
nlp_engine = EnhancedNLPEngine()
regime_detector = EnhancedMarketRegimeDetector()
cms_engine = CMSEngine()

# Process articles and price data
nlp_output = nlp_engine.process_articles(articles)
regime_output = regime_detector.detect_regime(price_bars, nlp_output.sentiment_index.smoothed_score)

# Create CMS components
components = CMSComponents(
    sentiment_index=nlp_output.sentiment_index.smoothed_score,
    volatility_index=regime_output.inputs.volatility_index,
    trend_strength=regime_output.inputs.trend_strength,
    event_shock_factor=nlp_output.event_shock_factor.total_shock
)

# Compute CMS
cms_result = cms_engine.compute_cms(components)

# Publish to Redis and store in database
cms_engine.publish_to_redis(cms_result, symbol="AAPL")
cms_engine.store_to_database(cms_result, symbol="AAPL")
```

### Convenience Function

```python
from src.signal.cms_engine import compute_cms

# Direct calculation
result = compute_cms(
    sentiment_index=0.45,
    volatility_index=0.30,
    trend_strength=0.25,
    event_shock_factor=0.20
)

print(f"CMS: {result.cms_score:.2f} ({result.signal_type})")
```

## Redis Publishing Format

### Channel: `cms.live`

```json
{
  "symbol": "AAPL",
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
  "explanation": "HOLD signal generated with CMS of 46.00. Sentiment contributes +26.00, volatility -7.50, trend +8.00, events +1.50. Dominant factor: sentiment.",
  "timestamp": "2024-01-15T10:30:00"
}
```

### Subscribe to CMS Updates

```python
from src.shared.redis_client import get_redis_client
import json

redis_client = get_redis_client()
pubsub = redis_client.pubsub()
pubsub.subscribe(['cms.live'])

for message in pubsub.listen():
    if message['type'] == 'message':
        data = json.loads(message['data'])
        print(f"CMS Update for {data['symbol']}:")
        print(f"  Score: {data['cms_score']:.2f}")
        print(f"  Signal: {data['signal_type']}")
        print(f"  Confidence: {data['confidence']:.2%}")
        
        # Check for strong signals
        if abs(data['cms_score']) > 80:
            print(f"  🚨 STRONG {data['signal_type']} SIGNAL!")
```

## PostgreSQL Storage

### Query CMS Data

```sql
-- Get current CMS for all symbols
SELECT * FROM current_cms;

-- Get CMS history for a symbol
SELECT cms_score, signal_type, confidence, timestamp
FROM cms_scores
WHERE symbol = 'AAPL'
ORDER BY timestamp DESC
LIMIT 100;

-- Get signal distribution
SELECT * FROM cms_signal_distribution WHERE symbol = 'AAPL';

-- Get recent signal transitions
SELECT * FROM recent_cms_transitions WHERE symbol = 'AAPL';

-- Get performance metrics
SELECT * FROM cms_performance WHERE symbol = 'AAPL';
```

## Integration with Trading System

### Position Sizing Based on CMS

```python
def calculate_position_size(base_size, cms_score, confidence):
    # Base multiplier from CMS score
    if cms_score > 80:
        cms_multiplier = 1.5  # Strong signal
    elif cms_score > 60:
        cms_multiplier = 1.2  # Moderate signal
    elif cms_score > 40:
        cms_multiplier = 1.0  # Weak signal
    elif cms_score > -40:
        cms_multiplier = 0.5  # Neutral/hold
    elif cms_score > -60:
        cms_multiplier = 0.3  # Weak negative
    elif cms_score > -80:
        cms_multiplier = 0.1  # Moderate negative
    else:
        cms_multiplier = 0.0  # Strong negative
    
    # Confidence adjustment
    confidence_multiplier = 0.5 + (confidence * 0.5)  # [0.5, 1.0]
    
    # Final position size
    position_size = base_size * cms_multiplier * confidence_multiplier
    
    return position_size
```

## Best Practices

1. **Regular Calibration**: Backtest and adjust thresholds based on historical performance
2. **Confidence Filtering**: Only act on signals with confidence > 0.6
3. **Component Validation**: Ensure all inputs are properly normalized
4. **Regime Integration**: Adjust CMS interpretation based on market regime
5. **Risk Management**: Always use stop losses and position sizing
6. **Monitoring**: Track CMS performance and component contributions

## Conclusion

The CMS Engine provides a comprehensive, explainable scoring system that combines multiple market factors into actionable trading signals. Its mathematical foundation ensures consistent, reproducible results while detailed explanations maintain transparency in decision-making.
