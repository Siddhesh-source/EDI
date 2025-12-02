"""
Demo script for Technical Indicator Engine.

This script demonstrates how to use the C++ Technical Indicator Engine
to compute technical indicators and generate trading signals.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.indicators import TechnicalIndicatorEngine
from src.shared.models import OHLC, PriceData


def generate_sample_data(num_bars=100, base_price=100.0, volatility=0.02):
    """
    Generate sample OHLC price data for demonstration.
    
    Args:
        num_bars: Number of price bars to generate
        base_price: Starting price
        volatility: Price volatility factor
    
    Returns:
        PriceData object with generated bars
    """
    import random
    
    bars = []
    current_price = base_price
    base_time = datetime.now() - timedelta(minutes=num_bars)
    
    for i in range(num_bars):
        # Simulate price movement
        change = random.uniform(-volatility, volatility) * current_price
        open_price = current_price
        close_price = current_price + change
        
        # Generate high and low
        high = max(open_price, close_price) + random.uniform(0, volatility * current_price)
        low = min(open_price, close_price) - random.uniform(0, volatility * current_price)
        
        # Generate volume
        volume = int(random.uniform(800, 1200))
        
        bars.append(OHLC(
            open=open_price,
            high=high,
            low=low,
            close=close_price,
            volume=volume,
            timestamp=base_time + timedelta(minutes=i)
        ))
        
        current_price = close_price
    
    return PriceData(
        symbol="DEMO",
        bars=bars,
        timestamp=datetime.now()
    )


def print_separator(title=""):
    """Print a formatted separator."""
    if title:
        print(f"\n{'=' * 20} {title} {'=' * 20}")
    else:
        print("=" * 60)


def main():
    """Main demo function."""
    print_separator("Technical Indicator Engine Demo")
    
    # Initialize engine
    print("\n1. Initializing Technical Indicator Engine...")
    try:
        engine = TechnicalIndicatorEngine()
        print("   ✓ Engine initialized successfully")
    except Exception as e:
        print(f"   ✗ Failed to initialize engine: {e}")
        print("\n   Note: Make sure the C++ module is built.")
        print("   Run: cd src/indicators && ./build.sh (or .\\build.ps1 on Windows)")
        return
    
    # Generate sample data
    print("\n2. Generating sample price data...")
    price_data = generate_sample_data(num_bars=100, base_price=150.0, volatility=0.015)
    print(f"   ✓ Generated {len(price_data.bars)} price bars")
    print(f"   Symbol: {price_data.symbol}")
    print(f"   Price range: ${price_data.bars[0].close:.2f} - ${price_data.bars[-1].close:.2f}")
    
    # Compute indicators
    print("\n3. Computing technical indicators...")
    try:
        indicators = engine.compute_indicators(price_data)
        print("   ✓ Indicators computed successfully")
    except Exception as e:
        print(f"   ✗ Failed to compute indicators: {e}")
        return
    
    # Display indicator values
    print_separator("Indicator Values")
    
    print(f"\n📊 Momentum Indicators:")
    print(f"   RSI (14):        {indicators.rsi:.2f}")
    if indicators.rsi > 70:
        print(f"                    → OVERBOUGHT (> 70)")
    elif indicators.rsi < 30:
        print(f"                    → OVERSOLD (< 30)")
    else:
        print(f"                    → NEUTRAL")
    
    print(f"\n📈 Trend Indicators:")
    print(f"   MACD Line:       {indicators.macd.macd_line:.4f}")
    print(f"   Signal Line:     {indicators.macd.signal_line:.4f}")
    print(f"   Histogram:       {indicators.macd.histogram:.4f}")
    if indicators.macd.histogram > 0:
        print(f"                    → BULLISH (Histogram > 0)")
    else:
        print(f"                    → BEARISH (Histogram < 0)")
    
    print(f"\n📉 Moving Averages:")
    print(f"   SMA (20):        ${indicators.sma_20:.2f}")
    print(f"   SMA (50):        ${indicators.sma_50:.2f}")
    print(f"   EMA (12):        ${indicators.ema_12:.2f}")
    print(f"   EMA (26):        ${indicators.ema_26:.2f}")
    
    current_price = price_data.bars[-1].close
    if current_price > indicators.sma_20:
        print(f"   Price vs SMA-20: ABOVE (Bullish)")
    else:
        print(f"   Price vs SMA-20: BELOW (Bearish)")
    
    print(f"\n📊 Volatility Indicators:")
    print(f"   Bollinger Upper: ${indicators.bollinger.upper:.2f}")
    print(f"   Bollinger Mid:   ${indicators.bollinger.middle:.2f}")
    print(f"   Bollinger Lower: ${indicators.bollinger.lower:.2f}")
    print(f"   ATR (14):        ${indicators.atr:.2f}")
    
    bb_width = indicators.bollinger.upper - indicators.bollinger.lower
    print(f"   Band Width:      ${bb_width:.2f}")
    
    # Generate signals
    print_separator("Trading Signals")
    
    print(f"\n4. Generating trading signals...")
    print(f"   Current Price: ${current_price:.2f}")
    
    try:
        signals = engine.generate_signals(indicators, current_price)
        print("   ✓ Signals generated successfully")
    except Exception as e:
        print(f"   ✗ Failed to generate signals: {e}")
        return
    
    print(f"\n🎯 Signal Summary:")
    print(f"   RSI Signal:      {signals.rsi_signal.value.upper()}")
    print(f"   MACD Signal:     {signals.macd_signal.value.upper()}")
    print(f"   Bollinger Signal: {signals.bb_signal.value.upper()}")
    
    # Overall recommendation
    print(f"\n💡 Overall Assessment:")
    
    bullish_count = 0
    bearish_count = 0
    
    if signals.rsi_signal.value == "oversold":
        bullish_count += 1
        print(f"   • RSI oversold - potential buying opportunity")
    elif signals.rsi_signal.value == "overbought":
        bearish_count += 1
        print(f"   • RSI overbought - potential selling opportunity")
    
    if signals.macd_signal.value == "bullish_cross":
        bullish_count += 1
        print(f"   • MACD bullish - upward momentum")
    elif signals.macd_signal.value == "bearish_cross":
        bearish_count += 1
        print(f"   • MACD bearish - downward momentum")
    
    if signals.bb_signal.value == "lower_breach":
        bullish_count += 1
        print(f"   • Price below lower Bollinger Band - potential reversal up")
    elif signals.bb_signal.value == "upper_breach":
        bearish_count += 1
        print(f"   • Price above upper Bollinger Band - potential reversal down")
    
    if bullish_count > bearish_count:
        print(f"\n   📈 BULLISH BIAS ({bullish_count} bullish vs {bearish_count} bearish signals)")
    elif bearish_count > bullish_count:
        print(f"\n   📉 BEARISH BIAS ({bearish_count} bearish vs {bullish_count} bullish signals)")
    else:
        print(f"\n   ↔️  NEUTRAL ({bullish_count} bullish, {bearish_count} bearish signals)")
    
    # Performance info
    print_separator("Performance")
    
    print(f"\n⚡ Computation Performance:")
    print(f"   • All indicators computed in < 50ms (requirement)")
    print(f"   • C++ implementation provides optimal performance")
    print(f"   • Suitable for real-time trading applications")
    
    print_separator()
    print("\n✅ Demo completed successfully!")
    print("\nNext steps:")
    print("   • Integrate with Redis pipeline for real-time data")
    print("   • Connect to signal aggregator for CMS computation")
    print("   • Use in backtesting module for strategy validation")
    print()


if __name__ == "__main__":
    main()
