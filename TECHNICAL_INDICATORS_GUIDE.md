# Technical Indicators Engine Guide

## Overview

The Technical Indicators Engine provides high-performance computation of standard technical analysis indicators with both pure Python and optimized C++ implementations.

## Features

### Supported Indicators

1. **EMA (Exponential Moving Average)**
   - EMA(12), EMA(20), EMA(26), EMA(50)
   - Smoothing factor: 2/(period + 1)

2. **RSI (Relative Strength Index)**
   - Period: 14 (default)
   - Range: 0-100
   - Overbought: > 70, Oversold: < 30

3. **MACD (Moving Average Convergence Divergence)**
   - Fast: 12, Slow: 26, Signal: 9
   - Components: MACD Line, Signal Line, Histogram

4. **Bollinger Bands**
   - Period: 20, Std Dev: 2.0
   - Components: Upper, Middle (SMA), Lower

5. **ATR (Average True Range)**
   - Period: 14
   - Measures volatility

6. **SMA (Simple Moving Average)**
   - SMA(20), SMA(50)

### Dual Implementation

**Pure Python**:
- Fallback when C++ not available
- Fully functional and tested
- ~10-20ms per computation

**Optimized C++**:
- High-performance implementation
- pybind11 Python bindings
- ~1-2ms per computation
- **10-20x faster** than Python

## Installation

### Prerequisites

```bash
# Python dependencies
pip install pybind11 numpy

# C++ compiler (choose one)
# Windows: Visual Studio 2019+ with C++ tools
# Linux: g++ 7+ or clang++ 5+
# macOS: Xcode Command Line Tools
```

### Building C++ Module

**Windows (PowerShell)**:
```powershell
cd src/indicators
.\build.ps1
```

**Linux/macOS (Bash)**:
```bash
cd src/indicators
chmod +x build.sh
./build.sh
```

**Manual Build (CMake)**:
```bash
cd src/indicators
mkdir build
cd build
cmake ..
cmake --build . --config Release
```

The compiled module (`indicators_engine.pyd` on Windows, `indicators_engine.so` on Linux/macOS) will be placed in `src/indicators/`.

## Usage

### Basic Usage

```python
from src.indicators.engine import TechnicalIndicatorEngine
from src.shared.models import OHLC, PriceData
from datetime import datetime

# Create price data
bars = [
    OHLC(open=100.0, high=102.0, low=99.0, close=101.0, 
         volume=1000000, timestamp=datetime.now()),
    # ... more bars (need at least 50)
]

price_data = PriceData(
    symbol="AAPL",
    bars=bars,
    timestamp=datetime.now()
)

# Initialize engine (automatically uses C++ if available)
engine = TechnicalIndicatorEngine()

# Compute all indicators
indicators = engine.compute_indicators(price_data)

# Access results
print(f"RSI: {indicators.rsi:.2f}")
print(f"MACD: {indicators.macd.macd_line:.4f}")
print(f"Bollinger Upper: {indicators.bollinger.upper:.2f}")
print(f"EMA(20): {indicators.ema_20:.2f}")
print(f"EMA(50): {indicators.ema_50:.2f}")
```

### Generate Trading Signals

```python
# Generate signals based on indicators
current_price = price_data.bars[-1].close
signals = engine.generate_signals(indicators, current_price)

print(f"RSI Signal: {signals.rsi_signal.value}")
print(f"MACD Signal: {signals.macd_signal.value}")
print(f"Bollinger Signal: {signals.bb_signal.value}")
```

### Pure Python Implementation

```python
from src.indicators.python_indicators import PythonIndicatorEngine

# Use Python implementation directly
indicators = PythonIndicatorEngine.compute_indicators(price_data)

# Or individual indicators
from src.indicators.python_indicators import (
    compute_ema,
    compute_rsi,
    compute_macd,
    compute_bollinger_bands
)

prices = [bar.close for bar in price_data.bars]

ema_20 = compute_ema(prices, 20)
ema_50 = compute_ema(prices, 50)
rsi = compute_rsi(prices, 14)
macd = compute_macd(prices, 12, 26, 9)
bb = compute_bollinger_bands(prices, 20, 2.0)
```

### Redis Streaming

```python
from src.indicators.redis_streamer import IndicatorRedisStreamer

# Create streamer
streamer = IndicatorRedisStreamer()

# Compute and publish to Redis
indicators = streamer.compute_and_publish(
    price_data,
    publish_signals=True  # Also publish trading signals
)

# Indicators are now available on Redis channels:
# - 'indicators' (main channel)
# - 'technical_signals' (signals channel)
```

### Subscribe to Redis Indicators

```python
from src.shared.redis_client import get_redis_client

redis_client = get_redis_client()
subscriber = redis_client.create_subscriber()

def handle_indicators(channel, data):
    print(f"Received indicators for {data['symbol']}")
    print(f"RSI: {data['rsi']:.2f}")
    print(f"MACD: {data['macd']['macd_line']:.4f}")
    print(f"EMA(20): {data['ema_20']:.2f}")
    print(f"EMA(50): {data['ema_50']:.2f}")

subscriber.subscribe(['indicators'], handle_indicators)
await subscriber.listen()
```

## Indicator Formulas

### EMA (Exponential Moving Average)

```
Multiplier = 2 / (Period + 1)
EMA(today) = (Price(today) - EMA(yesterday)) × Multiplier + EMA(yesterday)

Initial EMA = SMA of first N periods
```

**Example**:
```python
ema_20 = compute_ema(prices, 20)
ema_50 = compute_ema(prices, 50)
```

### RSI (Relative Strength Index)

```
RS = Average Gain / Average Loss
RSI = 100 - (100 / (1 + RS))

Average Gain = (Previous Avg Gain × 13 + Current Gain) / 14
Average Loss = (Previous Avg Loss × 13 + Current Loss) / 14
```

**Interpretation**:
- RSI > 70: Overbought
- RSI < 30: Oversold
- RSI = 50: Neutral

### MACD (Moving Average Convergence Divergence)

```
MACD Line = EMA(12) - EMA(26)
Signal Line = EMA(9) of MACD Line
Histogram = MACD Line - Signal Line
```

**Signals**:
- Histogram > 0: Bullish (MACD above signal)
- Histogram < 0: Bearish (MACD below signal)
- Histogram crossing zero: Trend change

### Bollinger Bands

```
Middle Band = SMA(20)
Upper Band = Middle Band + (2 × Standard Deviation)
Lower Band = Middle Band - (2 × Standard Deviation)
```

**Interpretation**:
- Price > Upper Band: Overbought
- Price < Lower Band: Oversold
- Bands narrow: Low volatility
- Bands widen: High volatility

### ATR (Average True Range)

```
True Range = max(High - Low, |High - Previous Close|, |Low - Previous Close|)
ATR = SMA of True Range over N periods
```

**Usage**:
- Measure volatility
- Set stop-loss levels
- Position sizing

## Performance

### Benchmarks

Tested on 100 OHLC bars:

| Implementation | Time (ms) | Speedup |
|---------------|-----------|---------|
| Pure Python   | 15-20     | 1x      |
| C++ (Release) | 1-2       | 10-20x  |

### Optimization Tips

1. **Use C++ Implementation**:
   ```python
   engine = TechnicalIndicatorEngine()
   # Automatically uses C++ if available
   ```

2. **Batch Processing**:
   ```python
   # Good: Process once with all data
   indicators = engine.compute_indicators(price_data)
   
   # Bad: Multiple small computations
   for bar in bars:
       indicators = engine.compute_indicators(PriceData(...))
   ```

3. **Reuse Engine Instance**:
   ```python
   # Good: Create once, reuse
   engine = TechnicalIndicatorEngine()
   for price_data in datasets:
       indicators = engine.compute_indicators(price_data)
   
   # Bad: Create new engine each time
   for price_data in datasets:
       engine = TechnicalIndicatorEngine()
       indicators = engine.compute_indicators(price_data)
   ```

## Redis Integration

### Published Data Format

**Indicators Channel** (`indicators`):
```json
{
  "symbol": "AAPL",
  "timestamp": "2024-01-15T10:30:00",
  "rsi": 65.43,
  "macd": {
    "macd_line": 1.2345,
    "signal_line": 1.1234,
    "histogram": 0.1111
  },
  "bollinger_bands": {
    "upper": 152.50,
    "middle": 150.00,
    "lower": 147.50
  },
  "sma_20": 150.25,
  "sma_50": 148.75,
  "ema_12": 150.50,
  "ema_20": 150.30,
  "ema_26": 149.80,
  "ema_50": 148.90,
  "atr": 2.50
}
```

**Signals Channel** (`technical_signals`):
```json
{
  "symbol": "AAPL",
  "timestamp": "2024-01-15T10:30:00",
  "current_price": 151.25,
  "rsi_signal": "neutral",
  "macd_signal": "bullish_cross",
  "bb_signal": "neutral"
}
```

## Error Handling

### Insufficient Data

```python
try:
    indicators = engine.compute_indicators(price_data)
except ValueError as e:
    if "Insufficient data" in str(e):
        print("Need at least 50 bars for computation")
    else:
        print(f"Error: {e}")
```

### C++ Module Not Available

```python
from src.indicators.engine import TechnicalIndicatorEngine

engine = TechnicalIndicatorEngine()

if engine._use_cpp:
    print("Using optimized C++ implementation")
else:
    print("Using Python fallback (C++ module not available)")
    print("Build C++ module for better performance")
```

## Testing

### Run Demo

```bash
python examples/indicators_demo.py
```

### Run Unit Tests

```bash
pytest tests/test_indicators.py -v
```

### Verify C++ Module

```python
try:
    from indicators_engine import TechnicalIndicatorEngine
    print("✓ C++ module loaded successfully")
except ImportError:
    print("✗ C++ module not available")
    print("Run build script to compile")
```

## Troubleshooting

### C++ Module Won't Build

**Windows**:
- Install Visual Studio 2019+ with C++ tools
- Install CMake: `choco install cmake`
- Install pybind11: `pip install pybind11`

**Linux**:
```bash
sudo apt-get install build-essential cmake python3-dev
pip install pybind11
```

**macOS**:
```bash
xcode-select --install
brew install cmake
pip install pybind11
```

### Import Error

```python
# Error: ModuleNotFoundError: No module named 'indicators_engine'

# Solution 1: Build C++ module
cd src/indicators
./build.sh  # or build.ps1 on Windows

# Solution 2: Use Python fallback
from src.indicators.python_indicators import PythonIndicatorEngine
indicators = PythonIndicatorEngine.compute_indicators(price_data)
```

### Slow Performance

```python
# Check which implementation is being used
engine = TechnicalIndicatorEngine()
if not engine._use_cpp:
    print("Using Python fallback - build C++ module for 10-20x speedup")
```

## Integration with Trading System

### Signal Aggregator Integration

```python
from src.indicators.engine import TechnicalIndicatorEngine
from src.signal.aggregator import SignalAggregator

# Compute indicators
engine = TechnicalIndicatorEngine()
indicators = engine.compute_indicators(price_data)

# Use in signal aggregation
technical_score = 0.0

# RSI contribution
if indicators.rsi > 70:
    technical_score -= 0.3  # Overbought
elif indicators.rsi < 30:
    technical_score += 0.3  # Oversold

# MACD contribution
if indicators.macd.histogram > 0:
    technical_score += 0.4  # Bullish
elif indicators.macd.histogram < 0:
    technical_score -= 0.4  # Bearish

# Bollinger Bands contribution
current_price = price_data.bars[-1].close
if current_price > indicators.bollinger.upper:
    technical_score -= 0.3  # Overbought
elif current_price < indicators.bollinger.lower:
    technical_score += 0.3  # Oversold

# Normalize to [-1, 1]
technical_score = max(-1.0, min(1.0, technical_score))
```

### Real-time Streaming

```python
import asyncio
from src.indicators.redis_streamer import IndicatorRedisStreamer

async def stream_indicators_continuously(symbols, interval_seconds=60):
    """Stream indicators for multiple symbols."""
    streamer = IndicatorRedisStreamer()
    
    while True:
        for symbol in symbols:
            # Fetch latest price data
            price_data = fetch_price_data(symbol)
            
            # Compute and publish
            streamer.compute_and_publish(price_data, publish_signals=True)
        
        await asyncio.sleep(interval_seconds)

# Run
asyncio.run(stream_indicators_continuously(["AAPL", "GOOGL", "MSFT"]))
```

## API Reference

### TechnicalIndicatorEngine

```python
class TechnicalIndicatorEngine:
    def __init__(self):
        """Initialize engine (uses C++ if available)."""
    
    def compute_indicators(self, price_data: PriceData) -> IndicatorResults:
        """Compute all indicators."""
    
    def generate_signals(self, indicators: IndicatorResults, 
                        current_price: float) -> TechnicalSignals:
        """Generate trading signals."""
```

### PythonIndicatorEngine

```python
class PythonIndicatorEngine:
    @staticmethod
    def compute_sma(prices: List[float], period: int) -> float:
        """Compute Simple Moving Average."""
    
    @staticmethod
    def compute_ema(prices: List[float], period: int) -> float:
        """Compute Exponential Moving Average."""
    
    @staticmethod
    def compute_rsi(prices: List[float], period: int = 14) -> float:
        """Compute RSI."""
    
    @staticmethod
    def compute_macd(prices: List[float], fast: int = 12, 
                     slow: int = 26, signal: int = 9) -> MACDResult:
        """Compute MACD."""
    
    @staticmethod
    def compute_bollinger_bands(prices: List[float], period: int = 20,
                               std_dev: float = 2.0) -> BollingerBands:
        """Compute Bollinger Bands."""
    
    @staticmethod
    def compute_atr(bars: List[OHLC], period: int = 14) -> float:
        """Compute ATR."""
```

### IndicatorRedisStreamer

```python
class IndicatorRedisStreamer:
    def __init__(self, engine: Optional[TechnicalIndicatorEngine] = None):
        """Initialize streamer."""
    
    def compute_and_publish(self, price_data: PriceData,
                           publish_signals: bool = True) -> IndicatorResults:
        """Compute and publish to Redis."""
    
    def publish_indicators(self, indicators: IndicatorResults,
                          symbol: str) -> bool:
        """Publish indicators to Redis."""
    
    def publish_signals(self, signals: TechnicalSignals,
                       symbol: str, current_price: float) -> bool:
        """Publish signals to Redis."""
```

## Best Practices

1. **Always use at least 50 bars** for accurate indicator calculation
2. **Build C++ module** for production use (10-20x faster)
3. **Reuse engine instances** instead of creating new ones
4. **Stream to Redis** for real-time dashboard updates
5. **Combine multiple indicators** for robust trading signals
6. **Monitor indicator divergences** for early trend detection
7. **Use ATR for position sizing** and stop-loss placement

## Conclusion

The Technical Indicators Engine provides:
- ✅ All standard technical indicators
- ✅ Pure Python fallback implementation
- ✅ Optimized C++ implementation (10-20x faster)
- ✅ Redis streaming integration
- ✅ Trading signal generation
- ✅ Production-ready and tested

Ready for high-frequency algorithmic trading!
