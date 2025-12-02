"""
Market Regime Detection System Demo
Demonstrates logic-based regime classification with sentiment, volatility, and trend.
"""

import sys
import random
from datetime import datetime, timedelta

sys.path.insert(0, '.')

from src.regime.enhanced_detector import (
    EnhancedMarketRegimeDetector,
    EnhancedRegimeType,
    RegimeInputs
)
from src.shared.models import OHLC


def generate_sample_prices(scenario: str, num_bars: int = 100) -> list:
    """Generate sample price data for different scenarios."""
    prices = []
    base_price = 150.0
    current_time = datetime.now() - timedelta(days=num_bars)
    
    random.seed(42)
    
    for i in range(num_bars):
        if scenario == "bull":
            # Uptrend with low volatility
            trend = i * 0.5
            noise = random.uniform(-1, 1)
            current_price = base_price + trend + noise
        
        elif scenario == "bear":
            # Downtrend with moderate volatility
            trend = -i * 0.4
            noise = random.uniform(-2, 2)
            current_price = base_price + trend + noise
        
        elif scenario == "neutral":
            # Sideways with low volatility
            noise = random.uniform(-2, 2)
            current_price = base_price + noise
        
        elif scenario == "panic":
            # High volatility with downtrend
            trend = -i * 0.3
            noise = random.uniform(-5, 5)
            current_price = base_price + trend + noise
        
        else:
            current_price = base_price
        
        # Generate OHLC
        open_price = current_price * random.uniform(0.99, 1.01)
        close_price = current_price * random.uniform(0.99, 1.01)
        high_price = max(open_price, close_price) * random.uniform(1.0, 1.02)
        low_price = min(open_price, close_price) * random.uniform(0.98, 1.0)
        
        bar = OHLC(
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=int(random.uniform(1000000, 5000000)),
            timestamp=current_time + timedelta(days=i)
        )
        prices.append(bar)
    
    return prices


def demo_regime_detection():
    """Demonstrate regime detection for different scenarios."""
    print("\n" + "="*70)
    print("MARKET REGIME DETECTION SYSTEM DEMO")
    print("="*70)
    
    detector = EnhancedMarketRegimeDetector(window_size=100, min_confidence=0.4)
    
    scenarios = [
        {
            'name': 'Bull Market',
            'prices': generate_sample_prices('bull', 100),
            'sentiment': 0.65,  # Positive sentiment
            'description': 'Strong uptrend with positive sentiment'
        },
        {
            'name': 'Bear Market',
            'prices': generate_sample_prices('bear', 100),
            'sentiment': -0.55,  # Negative sentiment
            'description': 'Downtrend with negative sentiment'
        },
        {
            'name': 'Neutral Market',
            'prices': generate_sample_prices('neutral', 100),
            'sentiment': 0.05,  # Neutral sentiment
            'description': 'Sideways market with balanced sentiment'
        },
        {
            'name': 'Panic Market',
            'prices': generate_sample_prices('panic', 100),
            'sentiment': -0.80,  # Very negative sentiment
            'description': 'High volatility with extreme negative sentiment'
        }
    ]
    
    for scenario in scenarios:
        print("\n" + "-"*70)
        print(f"SCENARIO: {scenario['name']}")
        print(f"Description: {scenario['description']}")
        print("-"*70)
        
        # Detect regime
        output = detector.detect_regime(scenario['prices'], scenario['sentiment'])
        
        # Display results
        print(f"\nDetected Regime: {output.regime.value.upper()}")
        print(f"Confidence: {output.confidence:.2%}")
        
        print(f"\nInput Values:")
        print(f"  Sentiment Index:  {output.inputs.sentiment_index:+.3f}")
        print(f"  Volatility Index: {output.inputs.volatility_index:.3f}")
        print(f"  Trend Strength:   {output.inputs.trend_strength:+.3f}")
        
        print(f"\nRegime Scores:")
        for regime, score in output.scores.items():
            print(f"  {regime.capitalize():8s}: {score:.3f}")
        
        print(f"\nExplanation:")
        print(f"  {output.explanation}")
        
        # Get trading adjustments
        adjustments = detector.get_trading_signal_adjustment(output.regime)
        
        print(f"\nTrading Adjustments:")
        print(f"  Position Size: {adjustments['position_size_multiplier']:.0%}")
        print(f"  Buy Threshold: {adjustments['buy_threshold_adjustment']:+d}")
        print(f"  Sell Threshold: {adjustments['sell_threshold_adjustment']:+d}")
        print(f"  Stop Loss: {adjustments['stop_loss_multiplier']:.0%}")
        print(f"  Take Profit: {adjustments['take_profit_multiplier']:.0%}")


def demo_mathematical_formulas():
    """Demonstrate the mathematical formulas."""
    print("\n" + "="*70)
    print("MATHEMATICAL FORMULAS DEMONSTRATION")
    print("="*70)
    
    # Example inputs
    si = 0.50  # Positive sentiment
    vi = 0.30  # Moderate volatility
    ts = 0.40  # Uptrend
    
    print(f"\nExample Inputs:")
    print(f"  Sentiment Index (SI): {si:+.2f}")
    print(f"  Volatility Index (VI): {vi:.2f}")
    print(f"  Trend Strength (TS): {ts:+.2f}")
    
    # Calculate scores
    print(f"\nScore Calculations:")
    
    bull_score = si * 0.4 + ts * 0.4 + (1 - vi) * 0.2
    print(f"\nBull Score:")
    print(f"  = SI × 0.4 + TS × 0.4 + (1 - VI) × 0.2")
    print(f"  = {si} × 0.4 + {ts} × 0.4 + (1 - {vi}) × 0.2")
    print(f"  = {si * 0.4:.3f} + {ts * 0.4:.3f} + {(1-vi) * 0.2:.3f}")
    print(f"  = {bull_score:.3f}")
    
    bear_score = -si * 0.4 + (-ts) * 0.4 + (1 - vi) * 0.2
    print(f"\nBear Score:")
    print(f"  = -SI × 0.4 + (-TS) × 0.4 + (1 - VI) × 0.2")
    print(f"  = {-si} × 0.4 + {-ts} × 0.4 + (1 - {vi}) × 0.2")
    print(f"  = {-si * 0.4:.3f} + {-ts * 0.4:.3f} + {(1-vi) * 0.2:.3f}")
    print(f"  = {bear_score:.3f}")
    
    neutral_score = (1 - abs(si)) * 0.5 + (1 - abs(ts)) * 0.3 + (1 - vi) * 0.2
    print(f"\nNeutral Score:")
    print(f"  = (1 - |SI|) × 0.5 + (1 - |TS|) × 0.3 + (1 - VI) × 0.2")
    print(f"  = (1 - {abs(si)}) × 0.5 + (1 - {abs(ts)}) × 0.3 + (1 - {vi}) × 0.2")
    print(f"  = {(1-abs(si)) * 0.5:.3f} + {(1-abs(ts)) * 0.3:.3f} + {(1-vi) * 0.2:.3f}")
    print(f"  = {neutral_score:.3f}")
    
    panic_score = vi * 0.6 + (-si) * 0.4
    print(f"\nPanic Score:")
    print(f"  = VI × 0.6 + (-SI) × 0.4")
    print(f"  = {vi} × 0.6 + {-si} × 0.4")
    print(f"  = {vi * 0.6:.3f} + {-si * 0.4:.3f}")
    print(f"  = {panic_score:.3f}")
    
    # Regime selection
    scores = {
        'Bull': bull_score,
        'Bear': bear_score,
        'Neutral': neutral_score,
        'Panic': panic_score
    }
    
    max_regime = max(scores, key=scores.get)
    max_score = scores[max_regime]
    total_score = sum(scores.values())
    confidence = max_score / total_score
    
    print(f"\nRegime Selection:")
    print(f"  Highest Score: {max_regime} ({max_score:.3f})")
    print(f"  Total Score: {total_score:.3f}")
    print(f"  Confidence: {max_score:.3f} / {total_score:.3f} = {confidence:.2%}")


def demo_panic_override():
    """Demonstrate panic override logic."""
    print("\n" + "="*70)
    print("PANIC OVERRIDE DEMONSTRATION")
    print("="*70)
    
    print("\nPanic Override Conditions:")
    print("  IF Volatility Index > 0.8 AND Sentiment Index < -0.5")
    print("  THEN Force PANIC regime with 95% confidence")
    
    test_cases = [
        {'vi': 0.85, 'si': -0.70, 'should_trigger': True},
        {'vi': 0.85, 'si': -0.30, 'should_trigger': False},
        {'vi': 0.60, 'si': -0.70, 'should_trigger': False},
        {'vi': 0.90, 'si': -0.80, 'should_trigger': True},
    ]
    
    print("\nTest Cases:")
    for i, case in enumerate(test_cases, 1):
        vi = case['vi']
        si = case['si']
        should_trigger = case['should_trigger']
        
        triggers = vi > 0.8 and si < -0.5
        
        print(f"\n  Case {i}:")
        print(f"    VI = {vi:.2f}, SI = {si:.2f}")
        print(f"    VI > 0.8? {vi > 0.8}")
        print(f"    SI < -0.5? {si < -0.5}")
        print(f"    Panic Override: {'YES' if triggers else 'NO'}")
        print(f"    Expected: {'YES' if should_trigger else 'NO'}")
        print(f"    Result: {'✓ PASS' if triggers == should_trigger else '✗ FAIL'}")


def demo_trading_adjustments():
    """Demonstrate how regimes affect trading."""
    print("\n" + "="*70)
    print("TRADING ADJUSTMENTS DEMONSTRATION")
    print("="*70)
    
    base_position = 10000
    base_buy_threshold = 60
    base_sell_threshold = -60
    
    detector = EnhancedMarketRegimeDetector()
    
    regimes = [
        EnhancedRegimeType.BULL,
        EnhancedRegimeType.BEAR,
        EnhancedRegimeType.NEUTRAL,
        EnhancedRegimeType.PANIC
    ]
    
    print(f"\nBase Parameters:")
    print(f"  Position Size: ${base_position:,}")
    print(f"  Buy Threshold: {base_buy_threshold}")
    print(f"  Sell Threshold: {base_sell_threshold}")
    
    for regime in regimes:
        adj = detector.get_trading_signal_adjustment(regime)
        
        adjusted_position = base_position * adj['position_size_multiplier']
        adjusted_buy = base_buy_threshold + adj['buy_threshold_adjustment']
        adjusted_sell = base_sell_threshold + adj['sell_threshold_adjustment']
        
        print(f"\n{regime.value.upper()} Regime:")
        print(f"  Position Size: ${adjusted_position:,.0f} ({adj['position_size_multiplier']:.0%})")
        print(f"  Buy Threshold: {adjusted_buy} ({adj['buy_threshold_adjustment']:+d})")
        print(f"  Sell Threshold: {adjusted_sell} ({adj['sell_threshold_adjustment']:+d})")
        print(f"  Stop Loss: {adj['stop_loss_multiplier']:.0%} of base")
        print(f"  Take Profit: {adj['take_profit_multiplier']:.0%} of base")


def main():
    """Run all demonstrations."""
    print("\n" + "="*70)
    print("ENHANCED MARKET REGIME DETECTION SYSTEM")
    print("Logic-Based Classification (No ML)")
    print("="*70)
    
    demo_regime_detection()
    demo_mathematical_formulas()
    demo_panic_override()
    demo_trading_adjustments()
    
    print("\n" + "="*70)
    print("DEMONSTRATION COMPLETE")
    print("="*70)
    print("\nKey Features:")
    print("✓ Four regime types: Bull, Bear, Neutral, Panic")
    print("✓ Clear mathematical formulas")
    print("✓ Sentiment + Volatility + Trend integration")
    print("✓ Panic override for extreme conditions")
    print("✓ Trading signal adjustments per regime")
    print("✓ PostgreSQL schema with automatic tracking")
    print("✓ Redis streaming for real-time updates")
    print("\nReady for production trading!")


if __name__ == "__main__":
    main()
