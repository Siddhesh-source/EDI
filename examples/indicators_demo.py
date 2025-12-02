"""
Comprehensive demo of Technical Indicator Engine.
Demonstrates both Python and C++ implementations with Redis streaming.
"""

import sys
import time
from datetime import datetime, timedelta
from typing import List
import random

# Add parent directory to path
sys.path.insert(0, '.')

from src.shared.models import OHLC, PriceData
from src.indicators.engine import TechnicalIndicatorEngine
from src.indicators.python_indicators import PythonIndicatorEngine
from src.indicators.redis_streamer import IndicatorRedisStreamer


def generate_sample_price_data(
    symbol: str = "AAPL",
    num_bars: int = 100,
    base_price: float = 150.0
) -> PriceData:
    """
    Generate sample OHLC price data for demonstration.
    
    Args:
        symbol: Stock symbol
        num_bars: Number of bars to generate
        base_price: Starting price
        
    Returns:
        PriceData with generated bars
    """
    bars = []
    current_price = base_price
    current_time = datetime.now() - timedelta(days=num_bars)
    
    random.seed(42)  # For reproducibility
    
    for i in range(num_bars):
        # Generate realistic OHLC data
        change_percent = random.uniform(-0.03, 0.03)  # ±3% daily change
        current_price *= (1 + change_percent)
        
        open_price = current_price * random.uniform(0.99, 1.01)
        close_price = current_price * random.uniform(0.99, 1.01)
        high_price = max(open_price, close_price) * random.uniform(1.0, 1.02)
        low_price = min(open_price, close_price) * random.uniform(0.98, 1.0)
        volume = int(random.uniform(1000000, 5000000))
        
        bar = OHLC(
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
            timestamp=current_time + timedelta(days=i)
        )
        bars.append(bar)
    
    return PriceData(
        symbol=symbol,
        bars=bars,
        timestamp=datetime.now()
    )


def demo_python_implementation():
    """Demonstrate pure Python implementation."""
    print("\n" + "="*70)
    print("PURE PYTHON IMPLEMENTATION DEMO")
    print("="*70)
    
    # Generate sample data
    price_data = generate_sample_price_data("AAPL", 100, 150.0)
    print(f"\nGenerated {len(price_data.bars)} bars for {price_data.symbol}")
    print(f"Price range: ${price_data.bars[0].close:.2f} - ${price_data.bars[-1].close:.2f}")
    
    # Compute indicators using Python
    print("\nComputing indicators using pure Python...")
    start_time = time.time()
    
    indicators = PythonIndicatorEngine.compute_indicators(price_data)
    
    elapsed = (time.time() - start_time) * 1000  # Convert to ms
    
    print(f"Computation time: {elapsed:.2f}ms")
    print("\nIndicator Results:")
    print(f"  RSI(14):           {indicators.rsi:.2f}")
    print(f"  MACD Line:         {indicators.macd.macd_line:.4f}")
    print(f"  MACD Signal:       {indicators.macd.signal_line:.4f}")
    print(f"  MACD Histogram:    {indicators.macd.histogram:.4f}")
    print(f"  Bollinger Upper:   ${indicators.bollinger.upper:.2f}")
    print(f"  Bollinger Middle:  ${indicators.bollinger.middle:.2f}")
    print(f"  Bollinger Lower:   ${indicators.bollinger.lower:.2f}")
    print(f"  SMA(20):           ${indicators.sma_20:.2f}")
    print(f"  SMA(50):           ${indicators.sma_50:.2f}")
    print(f"  EMA(12):           ${indicators.ema_12:.2f}")
    print(f"  EMA(20):           ${indicators.ema_20:.2f}")
    print(f"  EMA(26):           ${indicators.ema_26:.2f}")
    print(f"  EMA(50):           ${indicators.ema_50:.2f}")
    print(f"  ATR(14):           ${indicators.atr:.2f}")
    
    # Generate signals
    current_price = price_data.bars[-1].close
    signals = PythonIndicatorEngine.generate_signals(indicators, current_price)
    
    print(f"\nTrading Signals (Current Price: ${current_price:.2f}):")
    print(f"  RSI Signal:        {signals.rsi_signal.value}")
    print(f"  MACD Signal:       {signals.macd_signal.value}")
    print(f"  Bollinger Signal:  {signals.bb_signal.value}")
    
    return indicators, signals


def demo_cpp_implementation():
    """Demonstrate C++ implementation (if available)."""
    print("\n" + "="*70)
    print("C++ IMPLEMENTATION DEMO")
    print("="*70)
    
    # Generate sample data
    price_data = generate_sample_price_data("GOOGL", 100, 2800.0)
    print(f"\nGenerated {len(price_data.bars)} bars for {price_data.symbol}")
    print(f"Price range: ${price_data.bars[0].close:.2f} - ${price_data.bars[-1].close:.2f}")
    
    # Create engine (will use C++ if available)
    engine = TechnicalIndicatorEngine()
    
    if engine._use_cpp:
        print("\n✓ Using optimized C++ implementation")
    else:
        print("\n⚠ C++ module not available, using Python fallback")
    
    # Compute indicators
    print("\nComputing indicators...")
    start_time = time.time()
    
    indicators = engine.compute_indicators(price_data)
    
    elapsed = (time.time() - start_time) * 1000  # Convert to ms
    
    print(f"Computation time: {elapsed:.2f}ms")
    print("\nIndicator Results:")
    print(f"  RSI(14):           {indicators.rsi:.2f}")
    print(f"  MACD Line:         {indicators.macd.macd_line:.4f}")
    print(f"  MACD Signal:       {indicators.macd.signal_line:.4f}")
    print(f"  MACD Histogram:    {indicators.macd.histogram:.4f}")
    print(f"  Bollinger Upper:   ${indicators.bollinger.upper:.2f}")
    print(f"  Bollinger Middle:  ${indicators.bollinger.middle:.2f}")
    print(f"  Bollinger Lower:   ${indicators.bollinger.lower:.2f}")
    print(f"  SMA(20):           ${indicators.sma_20:.2f}")
    print(f"  SMA(50):           ${indicators.sma_50:.2f}")
    print(f"  EMA(12):           ${indicators.ema_12:.2f}")
    print(f"  EMA(26):           ${indicators.ema_26:.2f}")
    print(f"  ATR(14):           ${indicators.atr:.2f}")
    
    # Generate signals
    current_price = price_data.bars[-1].close
    signals = engine.generate_signals(indicators, current_price)
    
    print(f"\nTrading Signals (Current Price: ${current_price:.2f}):")
    print(f"  RSI Signal:        {signals.rsi_signal.value}")
    print(f"  MACD Signal:       {signals.macd_signal.value}")
    print(f"  Bollinger Signal:  {signals.bb_signal.value}")
    
    return indicators, signals


def demo_redis_streaming():
    """Demonstrate Redis streaming integration."""
    print("\n" + "="*70)
    print("REDIS STREAMING DEMO")
    print("="*70)
    
    # Generate sample data
    price_data = generate_sample_price_data("TSLA", 100, 700.0)
    print(f"\nGenerated {len(price_data.bars)} bars for {price_data.symbol}")
    
    # Create streamer
    streamer = IndicatorRedisStreamer()
    
    print("\nComputing indicators and streaming to Redis...")
    
    try:
        # Compute and publish
        indicators = streamer.compute_and_publish(price_data, publish_signals=True)
        
        print("✓ Successfully published to Redis channels:")
        print("  - indicators (main channel)")
        print("  - technical_signals (signals channel)")
        
        # Show summary
        summary = streamer.get_indicator_summary(indicators)
        print("\nIndicator Summary:")
        for key, value in summary.items():
            print(f"  {key}: {value}")
        
    except Exception as e:
        print(f"✗ Redis streaming failed: {e}")
        print("  (Make sure Redis is running)")


def demo_performance_comparison():
    """Compare Python vs C++ performance."""
    print("\n" + "="*70)
    print("PERFORMANCE COMPARISON")
    print("="*70)
    
    # Generate larger dataset
    price_data = generate_sample_price_data("MSFT", 200, 300.0)
    print(f"\nTesting with {len(price_data.bars)} bars")
    
    # Test Python implementation
    print("\nPython Implementation:")
    python_times = []
    for i in range(5):
        start = time.time()
        PythonIndicatorEngine.compute_indicators(price_data)
        elapsed = (time.time() - start) * 1000
        python_times.append(elapsed)
        print(f"  Run {i+1}: {elapsed:.2f}ms")
    
    avg_python = sum(python_times) / len(python_times)
    print(f"  Average: {avg_python:.2f}ms")
    
    # Test C++ implementation (if available)
    engine = TechnicalIndicatorEngine()
    if engine._use_cpp:
        print("\nC++ Implementation:")
        cpp_times = []
        for i in range(5):
            start = time.time()
            engine.compute_indicators(price_data)
            elapsed = (time.time() - start) * 1000
            cpp_times.append(elapsed)
            print(f"  Run {i+1}: {elapsed:.2f}ms")
        
        avg_cpp = sum(cpp_times) / len(cpp_times)
        print(f"  Average: {avg_cpp:.2f}ms")
        
        speedup = avg_python / avg_cpp
        print(f"\nSpeedup: {speedup:.2f}x faster with C++")
    else:
        print("\nC++ implementation not available for comparison")


def demo_individual_indicators():
    """Demonstrate individual indicator calculations."""
    print("\n" + "="*70)
    print("INDIVIDUAL INDICATOR CALCULATIONS")
    print("="*70)
    
    # Generate sample prices
    prices = [100 + i * 0.5 + random.uniform(-2, 2) for i in range(50)]
    print(f"\nGenerated {len(prices)} price points")
    print(f"Price range: ${min(prices):.2f} - ${max(prices):.2f}")
    
    # Calculate individual indicators
    print("\nCalculating individual indicators:")
    
    # SMA
    sma_20 = PythonIndicatorEngine.compute_sma(prices, 20)
    print(f"  SMA(20):  ${sma_20:.2f}")
    
    # EMA
    ema_20 = PythonIndicatorEngine.compute_ema(prices, 20)
    ema_50 = PythonIndicatorEngine.compute_ema(prices, 50)
    print(f"  EMA(20):  ${ema_20:.2f}")
    print(f"  EMA(50):  ${ema_50:.2f}")
    
    # RSI
    rsi = PythonIndicatorEngine.compute_rsi(prices, 14)
    print(f"  RSI(14):  {rsi:.2f}")
    
    # MACD
    macd = PythonIndicatorEngine.compute_macd(prices, 12, 26, 9)
    print(f"  MACD:     {macd.macd_line:.4f}")
    print(f"  Signal:   {macd.signal_line:.4f}")
    print(f"  Histogram: {macd.histogram:.4f}")
    
    # Bollinger Bands
    bb = PythonIndicatorEngine.compute_bollinger_bands(prices, 20, 2.0)
    print(f"  BB Upper: ${bb.upper:.2f}")
    print(f"  BB Middle: ${bb.middle:.2f}")
    print(f"  BB Lower: ${bb.lower:.2f}")


def main():
    """Run all demonstrations."""
    print("\n" + "="*70)
    print("TECHNICAL INDICATOR ENGINE DEMONSTRATION")
    print("="*70)
    print("\nThis demo showcases:")
    print("1. Pure Python implementation")
    print("2. Optimized C++ implementation (if available)")
    print("3. Redis streaming integration")
    print("4. Performance comparison")
    print("5. Individual indicator calculations")
    
    # Run demos
    demo_python_implementation()
    demo_cpp_implementation()
    demo_redis_streaming()
    demo_performance_comparison()
    demo_individual_indicators()
    
    print("\n" + "="*70)
    print("DEMONSTRATION COMPLETE")
    print("="*70)
    print("\nKey Features:")
    print("✓ Pure Python fallback implementation")
    print("✓ Optimized C++ implementation with pybind11")
    print("✓ Redis streaming for real-time data")
    print("✓ All standard technical indicators")
    print("✓ Trading signal generation")
    print("✓ High performance and accuracy")
    print("\nReady for production use!")


if __name__ == "__main__":
    main()
