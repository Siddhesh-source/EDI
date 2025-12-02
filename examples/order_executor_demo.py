"""Demo script for order executor functionality."""

import asyncio
import logging
import time
from datetime import datetime

from src.executor import OrderExecutor, KiteConnectClient
from src.shared.redis_client import get_redis_client, RedisChannels
from src.shared.logging_config import setup_logging
from src.shared.models import TradingSignalType

# Setup logging
logger = setup_logging(log_level="INFO", component_name="order_executor_demo")


async def demo_order_executor():
    """Demonstrate order executor functionality."""
    logger.info("=== Order Executor Demo ===")
    
    # Initialize Redis client
    redis_client = get_redis_client()
    
    # Check Redis connection
    if not redis_client.ping():
        logger.error("Redis is not available. Please start Redis first.")
        return
    
    logger.info("✓ Connected to Redis")
    
    # Initialize Kite Connect client (will run in simulation mode if not configured)
    kite_client = KiteConnectClient()
    
    # Initialize order executor with auto trading disabled for demo
    executor = OrderExecutor(
        redis_client=redis_client,
        kite_client=kite_client,
        enable_auto_trading=False,  # Disabled for demo
        position_size=10.0,
        max_position_size=100.0,
        max_daily_trades=5
    )
    
    logger.info("✓ Order executor initialized")
    
    # Start executor
    executor.start()
    logger.info("✓ Order executor started, listening for signals")
    
    # Simulate publishing a BUY signal
    logger.info("\n--- Simulating BUY Signal ---")
    buy_signal = {
        'signal_type': 'buy',
        'cms_score': 75.0,
        'sentiment_component': 30.0,
        'technical_component': 50.0,
        'regime_component': 20.0,
        'confidence': 0.85,
        'timestamp': datetime.now().isoformat()
    }
    
    redis_client.publish(RedisChannels.SIGNALS, buy_signal)
    logger.info("Published BUY signal to Redis")
    
    # Wait a bit for processing
    await asyncio.sleep(2)
    
    # Simulate publishing a SELL signal
    logger.info("\n--- Simulating SELL Signal ---")
    sell_signal = {
        'signal_type': 'sell',
        'cms_score': -75.0,
        'sentiment_component': -30.0,
        'technical_component': -50.0,
        'regime_component': -20.0,
        'confidence': 0.80,
        'timestamp': datetime.now().isoformat()
    }
    
    redis_client.publish(RedisChannels.SIGNALS, sell_signal)
    logger.info("Published SELL signal to Redis")
    
    # Wait a bit for processing
    await asyncio.sleep(2)
    
    # Simulate publishing a HOLD signal
    logger.info("\n--- Simulating HOLD Signal ---")
    hold_signal = {
        'signal_type': 'hold',
        'cms_score': 10.0,
        'sentiment_component': 5.0,
        'technical_component': 5.0,
        'regime_component': 0.0,
        'confidence': 0.60,
        'timestamp': datetime.now().isoformat()
    }
    
    redis_client.publish(RedisChannels.SIGNALS, hold_signal)
    logger.info("Published HOLD signal to Redis")
    
    # Wait a bit for processing
    await asyncio.sleep(2)
    
    # Stop executor
    executor.stop()
    logger.info("\n✓ Order executor stopped")
    
    logger.info("\n=== Demo Complete ===")


def demo_manual_order_execution():
    """Demonstrate manual order execution."""
    logger.info("\n=== Manual Order Execution Demo ===")
    
    # Initialize Kite Connect client
    kite_client = KiteConnectClient()
    
    # Initialize Redis client
    redis_client = get_redis_client()
    
    # Initialize order executor
    executor = OrderExecutor(
        redis_client=redis_client,
        kite_client=kite_client,
        enable_auto_trading=True,  # Enable for manual execution
        position_size=10.0
    )
    
    logger.info("✓ Order executor initialized")
    
    # Manually execute a BUY order
    logger.info("\n--- Executing Manual BUY Order ---")
    signal_data = {
        'signal_type': 'buy',
        'cms_score': 75.0,
        'timestamp': datetime.now().isoformat()
    }
    
    order = executor.execute_order(
        signal_type=TradingSignalType.BUY,
        symbol="RELIANCE",
        signal_data=signal_data
    )
    
    if order:
        logger.info(f"✓ Order executed: {order.order_id}")
        
        # Check order status
        logger.info("\n--- Checking Order Status ---")
        status = executor.check_order_status(order.order_id)
        logger.info(f"Order status: {status}")
        
        # Simulate order fill
        logger.info("\n--- Simulating Order Fill ---")
        executor.handle_fill(order.order_id)
        logger.info("✓ Order marked as filled")
    else:
        logger.error("✗ Order execution failed")
    
    logger.info("\n=== Manual Execution Demo Complete ===")


def demo_risk_management():
    """Demonstrate risk management validation."""
    logger.info("\n=== Risk Management Demo ===")
    
    # Initialize Redis client
    redis_client = get_redis_client()
    
    # Initialize order executor with strict limits
    executor = OrderExecutor(
        redis_client=redis_client,
        enable_auto_trading=True,
        position_size=50.0,
        max_position_size=100.0,  # Only allow 2 trades
        max_daily_trades=3
    )
    
    logger.info("✓ Order executor initialized with strict limits")
    logger.info("  - Max position size: 100.0")
    logger.info("  - Max daily trades: 3")
    logger.info("  - Position size per trade: 50.0")
    
    # Test 1: Valid signal
    logger.info("\n--- Test 1: Valid BUY Signal ---")
    try:
        executor.validate_signal(TradingSignalType.BUY, 75.0)
        logger.info("✓ Validation passed")
    except Exception as e:
        logger.error(f"✗ Validation failed: {e}")
    
    # Test 2: Weak BUY signal
    logger.info("\n--- Test 2: Weak BUY Signal (should fail) ---")
    try:
        executor.validate_signal(TradingSignalType.BUY, 50.0)
        logger.info("✓ Validation passed")
    except Exception as e:
        logger.info(f"✓ Validation correctly rejected: {e}")
    
    # Test 3: Valid SELL signal
    logger.info("\n--- Test 3: Valid SELL Signal ---")
    try:
        executor.validate_signal(TradingSignalType.SELL, -75.0)
        logger.info("✓ Validation passed")
    except Exception as e:
        logger.error(f"✗ Validation failed: {e}")
    
    # Test 4: Weak SELL signal
    logger.info("\n--- Test 4: Weak SELL Signal (should fail) ---")
    try:
        executor.validate_signal(TradingSignalType.SELL, -50.0)
        logger.info("✓ Validation passed")
    except Exception as e:
        logger.info(f"✓ Validation correctly rejected: {e}")
    
    logger.info("\n=== Risk Management Demo Complete ===")


if __name__ == "__main__":
    print("Order Executor Demo")
    print("=" * 50)
    print("\nThis demo shows:")
    print("1. Listening for trading signals from Redis")
    print("2. Manual order execution")
    print("3. Risk management validation")
    print("\nNote: Orders will be simulated if Kite Connect is not configured")
    print("=" * 50)
    
    # Run demos
    demo_risk_management()
    demo_manual_order_execution()
    
    # Run async demo
    print("\n" + "=" * 50)
    print("Starting async signal listener demo...")
    print("=" * 50)
    asyncio.run(demo_order_executor())
