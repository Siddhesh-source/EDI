"""
Rule-Based Trading Engine Demo
Demonstrates signal generation, risk management, and position sizing.
"""

import sys
from datetime import datetime

sys.path.insert(0, '.')

from src.trading.rule_engine import (
    RuleBasedTradingEngine,
    MarketData,
    RiskParameters,
    SignalType
)


def demo_buy_signal():
    """Demonstrate BUY signal generation."""
    print("\n" + "="*70)
    print("BUY SIGNAL DEMONSTRATION")
    print("="*70)
    
    # Initialize risk parameters
    risk_params = RiskParameters(
        account_balance=100000,
        risk_per_trade_pct=0.01,
        atr_stop_multiplier=2.0,
        trailing_stop_pct=0.02,
        max_position_size_pct=0.1
    )
    
    # Initialize engine
    engine = RuleBasedTradingEngine(risk_params)
    
    # Create bullish market data
    market_data = MarketData(
        symbol="AAPL",
        current_price=150.00,
        ema_20=152.00,  # Above EMA50 ✓
        ema_50=148.00,
        atr=3.50,
        sentiment_index=0.35,  # > 0.2 ✓
        cms_score=0.45,  # > 0.3 ✓
        event_shock_factor=0.10,
        negative_events=[],  # No negative events ✓
        timestamp=datetime.utcnow()
    )
    
    print(f"\nMarket Data for {market_data.symbol}:")
    print(f"  Current Price: ${market_data.current_price:.2f}")
    print(f"  EMA20: ${market_data.ema_20:.2f}")
    print(f"  EMA50: ${market_data.ema_50:.2f}")
    print(f"  ATR: ${market_data.atr:.2f}")
    print(f"  Sentiment Index: {market_data.sentiment_index:.3f}")
    print(f"  CMS Score: {market_data.cms_score:.2f}")
    print(f"  Event Shock: {market_data.event_shock_factor:.2f}")
    
    # Generate signal
    signal = engine.generate_signal(market_data)
    
    print(f"\n{'='*70}")
    print(f"SIGNAL GENERATED: {signal.signal_type.value}")
    print(f"{'='*70}")
    print(f"Confidence: {signal.confidence:.2%}")
    
    if signal.position_size:
        print(f"\nPosition Sizing:")
        print(f"  Shares: {signal.position_size.shares}")
        print(f"  Position Value: ${signal.position_size.position_value:,.2f}")
        print(f"  Risk Amount: ${signal.position_size.risk_amount:,.2f}")
        print(f"  Stop Loss: ${signal.position_size.stop_loss_price:.2f}")
        print(f"  Take Profit: ${signal.position_size.take_profit_price:.2f}")
        print(f"  Risk/Reward: {signal.position_size.risk_reward_ratio:.2f}:1")
    
    print(f"\nReasons:")
    for reason in signal.reasons:
        print(f"  {reason}")


def demo_sell_signal():
    """Demonstrate SELL signal generation."""
    print("\n" + "="*70)
    print("SELL SIGNAL DEMONSTRATION")
    print("="*70)
    
    risk_params = RiskParameters(account_balance=100000)
    engine = RuleBasedTradingEngine(risk_params)
    
    # Create bearish market data
    market_data = MarketData(
        symbol="TSLA",
        current_price=200.00,
        ema_20=195.00,  # Below EMA50 ✓
        ema_50=205.00,
        atr=8.00,
        sentiment_index=-0.45,  # < -0.3 ✓
        cms_score=-0.55,  # < -0.3 ✓
        event_shock_factor=-1.5,  # < -1 ✓
        negative_events=["CEO investigation", "Earnings warning"],
        timestamp=datetime.utcnow()
    )
    
    print(f"\nMarket Data for {market_data.symbol}:")
    print(f"  Current Price: ${market_data.current_price:.2f}")
    print(f"  EMA20: ${market_data.ema_20:.2f}")
    print(f"  EMA50: ${market_data.ema_50:.2f}")
    print(f"  ATR: ${market_data.atr:.2f}")
    print(f"  Sentiment Index: {market_data.sentiment_index:.3f}")
    print(f"  CMS Score: {market_data.cms_score:.2f}")
    print(f"  Event Shock: {market_data.event_shock_factor:.2f}")
    print(f"  Negative Events: {market_data.negative_events}")
    
    # Generate signal
    signal = engine.generate_signal(market_data)
    
    print(f"\n{'='*70}")
    print(f"SIGNAL GENERATED: {signal.signal_type.value}")
    print(f"{'='*70}")
    print(f"Confidence: {signal.confidence:.2%}")
    
    if signal.position_size:
        print(f"\nPosition Sizing:")
        print(f"  Shares: {signal.position_size.shares}")
        print(f"  Position Value: ${signal.position_size.position_value:,.2f}")
        print(f"  Risk Amount: ${signal.position_size.risk_amount:,.2f}")
        print(f"  Stop Loss: ${signal.position_size.stop_loss_price:.2f}")
        print(f"  Take Profit: ${signal.position_size.take_profit_price:.2f}")
        print(f"  Risk/Reward: {signal.position_size.risk_reward_ratio:.2f}:1")
    
    print(f"\nReasons:")
    for reason in signal.reasons:
        print(f"  {reason}")


def demo_hold_signal():
    """Demonstrate HOLD signal (conditions not met)."""
    print("\n" + "="*70)
    print("HOLD SIGNAL DEMONSTRATION")
    print("="*70)
    
    risk_params = RiskParameters(account_balance=100000)
    engine = RuleBasedTradingEngine(risk_params)
    
    # Create mixed/neutral market data
    market_data = MarketData(
        symbol="MSFT",
        current_price=350.00,
        ema_20=352.00,  # Above EMA50 ✓
        ema_50=348.00,
        atr=5.00,
        sentiment_index=0.15,  # < 0.2 ✗ (not enough for BUY)
        cms_score=0.25,  # < 0.3 ✗ (not enough for BUY)
        event_shock_factor=0.05,
        negative_events=[],
        timestamp=datetime.utcnow()
    )
    
    print(f"\nMarket Data for {market_data.symbol}:")
    print(f"  Current Price: ${market_data.current_price:.2f}")
    print(f"  EMA20: ${market_data.ema_20:.2f}")
    print(f"  EMA50: ${market_data.ema_50:.2f}")
    print(f"  ATR: ${market_data.atr:.2f}")
    print(f"  Sentiment Index: {market_data.sentiment_index:.3f}")
    print(f"  CMS Score: {market_data.cms_score:.2f}")
    print(f"  Event Shock: {market_data.event_shock_factor:.2f}")
    
    # Generate signal
    signal = engine.generate_signal(market_data)
    
    print(f"\n{'='*70}")
    print(f"SIGNAL GENERATED: {signal.signal_type.value}")
    print(f"{'='*70}")
    print(f"Confidence: {signal.confidence:.2%}")
    
    print(f"\nReasons:")
    for reason in signal.reasons:
        print(f"  {reason}")


def demo_trailing_stop():
    """Demonstrate trailing stop calculation."""
    print("\n" + "="*70)
    print("TRAILING STOP DEMONSTRATION")
    print("="*70)
    
    risk_params = RiskParameters(account_balance=100000)
    engine = RuleBasedTradingEngine(risk_params)
    
    # Long position example
    entry_price = 150.00
    prices = [150.00, 152.00, 155.00, 160.00, 158.00]
    
    print(f"\nLONG Position:")
    print(f"Entry Price: ${entry_price:.2f}")
    print(f"\nPrice Movement and Trailing Stop:")
    print(f"{'Current Price':>15} {'Trailing Stop':>15} {'Profit Protected':>18}")
    print("-" * 50)
    
    for price in prices:
        trailing_stop = engine.calculate_trailing_stop(
            entry_price=entry_price,
            current_price=price,
            is_long=True
        )
        profit_protected = price - trailing_stop
        print(f"${price:>14.2f} ${trailing_stop:>14.2f} ${profit_protected:>17.2f}")
    
    # Short position example
    print(f"\nSHORT Position:")
    entry_price = 200.00
    prices = [200.00, 198.00, 195.00, 190.00, 192.00]
    
    print(f"Entry Price: ${entry_price:.2f}")
    print(f"\nPrice Movement and Trailing Stop:")
    print(f"{'Current Price':>15} {'Trailing Stop':>15} {'Profit Protected':>18}")
    print("-" * 50)
    
    for price in prices:
        trailing_stop = engine.calculate_trailing_stop(
            entry_price=entry_price,
            current_price=price,
            is_long=False
        )
        profit_protected = trailing_stop - price
        print(f"${price:>14.2f} ${trailing_stop:>14.2f} ${profit_protected:>17.2f}")


def demo_position_sizing():
    """Demonstrate position sizing with different account sizes and volatility."""
    print("\n" + "="*70)
    print("POSITION SIZING DEMONSTRATION")
    print("="*70)
    
    account_sizes = [10000, 50000, 100000, 500000]
    entry_price = 150.00
    atr_values = [2.00, 3.50, 5.00, 8.00]
    
    print(f"\nEntry Price: ${entry_price:.2f}")
    print(f"Risk Per Trade: 1%")
    print(f"ATR Multiplier: 2.0")
    print(f"Max Position Size: 10% of account")
    
    for account_balance in account_sizes:
        print(f"\n{'='*70}")
        print(f"Account Balance: ${account_balance:,}")
        print(f"{'='*70}")
        print(f"{'ATR':>8} {'Risk $':>12} {'Shares':>10} {'Position $':>15} {'Stop Loss':>12}")
        print("-" * 70)
        
        for atr in atr_values:
            risk_params = RiskParameters(account_balance=account_balance)
            engine = RuleBasedTradingEngine(risk_params)
            
            position_size = engine._calculate_position_size(
                entry_price=entry_price,
                atr=atr,
                is_long=True
            )
            
            print(
                f"${atr:>7.2f} "
                f"${position_size.risk_amount:>11,.2f} "
                f"{position_size.shares:>10,} "
                f"${position_size.position_value:>14,.2f} "
                f"${position_size.stop_loss_price:>11.2f}"
            )


def demo_risk_scenarios():
    """Demonstrate different risk scenarios."""
    print("\n" + "="*70)
    print("RISK SCENARIO ANALYSIS")
    print("="*70)
    
    scenarios = [
        {
            'name': 'Conservative (Low Volatility)',
            'atr': 2.00,
            'description': 'Stable stock, tight stops'
        },
        {
            'name': 'Moderate (Normal Volatility)',
            'atr': 3.50,
            'description': 'Average volatility'
        },
        {
            'name': 'Aggressive (High Volatility)',
            'atr': 5.00,
            'description': 'Volatile stock, wider stops'
        },
        {
            'name': 'Extreme (Very High Volatility)',
            'atr': 8.00,
            'description': 'Highly volatile, very wide stops'
        }
    ]
    
    account_balance = 100000
    entry_price = 150.00
    
    print(f"\nAccount Balance: ${account_balance:,}")
    print(f"Entry Price: ${entry_price:.2f}")
    print(f"Risk Per Trade: 1% (${account_balance * 0.01:,.2f})")
    
    for scenario in scenarios:
        print(f"\n{'-'*70}")
        print(f"Scenario: {scenario['name']}")
        print(f"Description: {scenario['description']}")
        print(f"{'-'*70}")
        
        risk_params = RiskParameters(account_balance=account_balance)
        engine = RuleBasedTradingEngine(risk_params)
        
        position_size = engine._calculate_position_size(
            entry_price=entry_price,
            atr=scenario['atr'],
            is_long=True
        )
        
        print(f"ATR: ${scenario['atr']:.2f}")
        print(f"Stop Distance: ${scenario['atr'] * 2:.2f}")
        print(f"Shares: {position_size.shares:,}")
        print(f"Position Value: ${position_size.position_value:,.2f}")
        print(f"Position % of Account: {(position_size.position_value / account_balance) * 100:.1f}%")
        print(f"Stop Loss: ${position_size.stop_loss_price:.2f}")
        print(f"Take Profit: ${position_size.take_profit_price:.2f}")
        print(f"Risk Amount: ${position_size.risk_amount:,.2f}")
        print(f"Potential Profit: ${(position_size.take_profit_price - entry_price) * position_size.shares:,.2f}")
        print(f"Risk/Reward: {position_size.risk_reward_ratio:.2f}:1")


def main():
    """Run all demonstrations."""
    print("\n" + "="*70)
    print("RULE-BASED TRADING ENGINE DEMONSTRATION")
    print("="*70)
    print("\nNo ML - Pure Rule-Based Logic with Risk Management")
    
    # Run all demos
    demo_buy_signal()
    demo_sell_signal()
    demo_hold_signal()
    demo_trailing_stop()
    demo_position_sizing()
    demo_risk_scenarios()
    
    print("\n" + "="*70)
    print("DEMONSTRATION COMPLETE")
    print("="*70)
    print("\nKey Features Demonstrated:")
    print("✓ BUY/SELL/HOLD signal generation")
    print("✓ Rule-based condition checking")
    print("✓ Position sizing with 1% risk")
    print("✓ ATR-based dynamic stop loss")
    print("✓ Trailing stop loss calculation")
    print("✓ 2:1 Risk/Reward ratio")
    print("✓ Maximum position size constraints")
    print("✓ Confidence scoring")
    print("✓ Detailed reasoning for every signal")
    print("\nReady for production trading!")


if __name__ == "__main__":
    main()
