"""Demo script for Market Regime Detector."""

import sys
import os
import numpy as np
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.regime import MarketRegimeDetector
from src.shared.models import OHLC, RegimeType
from src.shared.logging_config import setup_logging


def generate_trending_up_prices(n_bars: int = 100, base_price: float = 100.0) -> list[OHLC]:
    """Generate synthetic uptrending price data."""
    prices = []
    current_price = base_price
    timestamp = datetime.now() - timedelta(minutes=n_bars)
    
    for i in range(n_bars):
        # Upward trend with some noise
        trend = 0.5  # Upward drift
        noise = np.random.normal(0, 1.0)
        current_price += trend + noise
        
        # Generate OHLC
        open_price = current_price
        high = open_price + abs(np.random.normal(0, 0.5))
        low = open_price - abs(np.random.normal(0, 0.5))
        close = np.random.uniform(low, high)
        volume = int(np.random.uniform(1000, 10000))
        
        prices.append(OHLC(
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
            timestamp=timestamp + timedelta(minutes=i)
        ))
    
    return prices


def generate_trending_down_prices(n_bars: int = 100, base_price: float = 100.0) -> list[OHLC]:
    """Generate synthetic downtrending price data."""
    prices = []
    current_price = base_price
    timestamp = datetime.now() - timedelta(minutes=n_bars)
    
    for i in range(n_bars):
        # Downward trend with some noise
        trend = -0.5  # Downward drift
        noise = np.random.normal(0, 1.0)
        current_price += trend + noise
        
        # Generate OHLC
        open_price = current_price
        high = open_price + abs(np.random.normal(0, 0.5))
        low = open_price - abs(np.random.normal(0, 0.5))
        close = np.random.uniform(low, high)
        volume = int(np.random.uniform(1000, 10000))
        
        prices.append(OHLC(
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
            timestamp=timestamp + timedelta(minutes=i)
        ))
    
    return prices


def generate_ranging_prices(n_bars: int = 100, base_price: float = 100.0) -> list[OHLC]:
    """Generate synthetic ranging/sideways price data."""
    prices = []
    current_price = base_price
    timestamp = datetime.now() - timedelta(minutes=n_bars)
    
    for i in range(n_bars):
        # Mean-reverting behavior
        mean_reversion = (base_price - current_price) * 0.1
        noise = np.random.normal(0, 1.0)
        current_price += mean_reversion + noise
        
        # Generate OHLC
        open_price = current_price
        high = open_price + abs(np.random.normal(0, 0.5))
        low = open_price - abs(np.random.normal(0, 0.5))
        close = np.random.uniform(low, high)
        volume = int(np.random.uniform(1000, 10000))
        
        prices.append(OHLC(
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
            timestamp=timestamp + timedelta(minutes=i)
        ))
    
    return prices


def generate_volatile_prices(n_bars: int = 100, base_price: float = 100.0) -> list[OHLC]:
    """Generate synthetic volatile price data."""
    prices = []
    current_price = base_price
    timestamp = datetime.now() - timedelta(minutes=n_bars)
    
    for i in range(n_bars):
        # High volatility
        noise = np.random.normal(0, 3.0)  # Large noise
        current_price += noise
        
        # Generate OHLC with wide ranges
        open_price = current_price
        high = open_price + abs(np.random.normal(0, 2.0))
        low = open_price - abs(np.random.normal(0, 2.0))
        close = np.random.uniform(low, high)
        volume = int(np.random.uniform(1000, 10000))
        
        prices.append(OHLC(
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
            timestamp=timestamp + timedelta(minutes=i)
        ))
    
    return prices


def generate_calm_prices(n_bars: int = 100, base_price: float = 100.0) -> list[OHLC]:
    """Generate synthetic calm/low volatility price data."""
    prices = []
    current_price = base_price
    timestamp = datetime.now() - timedelta(minutes=n_bars)
    
    for i in range(n_bars):
        # Very low volatility
        noise = np.random.normal(0, 0.1)  # Small noise
        current_price += noise
        
        # Generate OHLC with tight ranges
        open_price = current_price
        high = open_price + abs(np.random.normal(0, 0.1))
        low = open_price - abs(np.random.normal(0, 0.1))
        close = np.random.uniform(low, high)
        volume = int(np.random.uniform(1000, 10000))
        
        prices.append(OHLC(
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
            timestamp=timestamp + timedelta(minutes=i)
        ))
    
    return prices


def demo_regime_detection():
    """Demonstrate regime detection on different market conditions."""
    print("=" * 80)
    print("Market Regime Detector Demo")
    print("=" * 80)
    print()
    
    # Initialize detector
    detector = MarketRegimeDetector(window_size=100, confidence_threshold=0.6)
    
    # Test scenarios
    scenarios = [
        ("Trending Up", generate_trending_up_prices()),
        ("Trending Down", generate_trending_down_prices()),
        ("Ranging/Sideways", generate_ranging_prices()),
        ("Volatile", generate_volatile_prices()),
        ("Calm", generate_calm_prices()),
    ]
    
    for scenario_name, prices in scenarios:
        print(f"\n{scenario_name} Market")
        print("-" * 40)
        
        # Detect regime
        regime = detector.detect_regime(prices)
        
        print(f"Detected Regime: {regime.regime_type.value.upper()}")
        print(f"Confidence: {regime.confidence:.2f}")
        print(f"Volatility: {regime.volatility:.4f}")
        print(f"Trend Strength: {regime.trend_strength:.4f}")
        
        # Show price statistics
        closes = [bar.close for bar in prices]
        print(f"\nPrice Statistics:")
        print(f"  Start Price: ${closes[0]:.2f}")
        print(f"  End Price: ${closes[-1]:.2f}")
        print(f"  Change: {((closes[-1] - closes[0]) / closes[0] * 100):.2f}%")
        print(f"  Min: ${min(closes):.2f}")
        print(f"  Max: ${max(closes):.2f}")
    
    print("\n" + "=" * 80)
    print("Demo Complete")
    print("=" * 80)


def demo_rolling_window():
    """Demonstrate rolling window regime detection."""
    print("\n" + "=" * 80)
    print("Rolling Window Regime Detection Demo")
    print("=" * 80)
    print()
    
    # Initialize detector
    detector = MarketRegimeDetector(window_size=50, confidence_threshold=0.6)
    
    # Generate a market that transitions from trending up to ranging
    print("Simulating market transition: Trending Up → Ranging")
    print("-" * 40)
    
    # First 100 bars: trending up
    trending_prices = generate_trending_up_prices(n_bars=100, base_price=100.0)
    
    # Next 100 bars: ranging (starting from last price)
    last_price = trending_prices[-1].close
    ranging_prices = generate_ranging_prices(n_bars=100, base_price=last_price)
    
    # Combine
    all_prices = trending_prices + ranging_prices
    
    # Detect regime at different points
    checkpoints = [50, 100, 150, 200]
    
    for checkpoint in checkpoints:
        prices_slice = all_prices[:checkpoint]
        regime = detector.detect_regime(prices_slice)
        
        print(f"\nAfter {checkpoint} bars:")
        print(f"  Regime: {regime.regime_type.value.upper()}")
        print(f"  Confidence: {regime.confidence:.2f}")
        print(f"  Volatility: {regime.volatility:.4f}")
        print(f"  Trend Strength: {regime.trend_strength:.4f}")
    
    print("\n" + "=" * 80)


def demo_confidence_threshold():
    """Demonstrate confidence threshold behavior."""
    print("\n" + "=" * 80)
    print("Confidence Threshold Demo")
    print("=" * 80)
    print()
    
    # Generate ambiguous market data
    prices = generate_ranging_prices(n_bars=100, base_price=100.0)
    
    # Add some weak trend
    for i, bar in enumerate(prices):
        prices[i] = OHLC(
            open=bar.open + i * 0.05,
            high=bar.high + i * 0.05,
            low=bar.low + i * 0.05,
            close=bar.close + i * 0.05,
            volume=bar.volume,
            timestamp=bar.timestamp
        )
    
    print("Testing different confidence thresholds on ambiguous market data:")
    print("-" * 40)
    
    thresholds = [0.3, 0.5, 0.6, 0.8]
    
    for threshold in thresholds:
        detector = MarketRegimeDetector(window_size=100, confidence_threshold=threshold)
        regime = detector.detect_regime(prices)
        
        print(f"\nThreshold: {threshold:.1f}")
        print(f"  Detected Regime: {regime.regime_type.value.upper()}")
        print(f"  Confidence: {regime.confidence:.2f}")
        print(f"  Applied Default: {'Yes' if regime.confidence < threshold else 'No'}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    # Setup logging
    setup_logging()
    
    # Run demos
    demo_regime_detection()
    demo_rolling_window()
    demo_confidence_threshold()
    
    print("\nNote: Redis publishing and database storage are disabled in demo mode.")
    print("To enable, ensure Redis and PostgreSQL are running and configured.")
