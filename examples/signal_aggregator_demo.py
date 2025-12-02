"""Demo script for the Signal Aggregator."""

import asyncio
import logging
import time
from datetime import datetime

from src.shared.redis_client import get_redis_client, RedisChannels
from src.shared.models import EventType, RegimeType, TechnicalSignalType
from src.signal.aggregator import SignalAggregator
from src.shared.logging_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


async def publish_test_data(redis_client):
    """Publish test data to Redis channels to trigger signal generation."""
    
    logger.info("Publishing test sentiment data...")
    redis_client.publish(RedisChannels.SENTIMENT, {
        'article_id': 'test-article-1',
        'score': 0.7,  # Positive sentiment
        'confidence': 0.85,
        'keywords_positive': ['growth', 'profit', 'bullish'],
        'keywords_negative': [],
        'timestamp': datetime.now().isoformat()
    })
    
    await asyncio.sleep(1)
    
    logger.info("Publishing test technical indicators...")
    redis_client.publish(RedisChannels.INDICATORS, {
        'rsi_signal': TechnicalSignalType.OVERSOLD.value,  # Bullish
        'macd_signal': TechnicalSignalType.BULLISH_CROSS.value,  # Bullish
        'bb_signal': TechnicalSignalType.NEUTRAL.value,
        'timestamp': datetime.now().isoformat()
    })
    
    await asyncio.sleep(1)
    
    logger.info("Publishing test market regime...")
    redis_client.publish(RedisChannels.REGIME, {
        'regime_type': RegimeType.TRENDING_UP.value,  # Bullish
        'confidence': 0.8,
        'volatility': 0.15,
        'trend_strength': 0.75,
        'timestamp': datetime.now().isoformat()
    })
    
    await asyncio.sleep(1)
    
    logger.info("Publishing test event...")
    redis_client.publish(RedisChannels.EVENTS, {
        'id': 'event-1',
        'article_id': 'test-article-1',
        'event_type': EventType.EARNINGS.value,
        'severity': 0.8,
        'keywords': ['earnings', 'beat', 'expectations'],
        'timestamp': datetime.now().isoformat()
    })


async def listen_for_signals(redis_client):
    """Listen for generated signals on the signals channel."""
    subscriber = redis_client.create_subscriber()
    
    def signal_handler(channel, data):
        logger.info("=" * 80)
        logger.info("TRADING SIGNAL RECEIVED")
        logger.info("=" * 80)
        logger.info(f"Signal Type: {data['signal_type'].upper()}")
        logger.info(f"CMS Score: {data['cms_score']:.2f}")
        logger.info(f"Confidence: {data['confidence']:.2%}")
        logger.info("")
        logger.info("Component Scores:")
        logger.info(f"  Sentiment: {data['sentiment_component']:.2f}")
        logger.info(f"  Technical: {data['technical_component']:.2f}")
        logger.info(f"  Regime: {data['regime_component']:.2f}")
        logger.info("")
        logger.info("Explanation:")
        logger.info(f"  Summary: {data['explanation']['summary']}")
        logger.info(f"  Sentiment: {data['explanation']['sentiment_details']}")
        logger.info(f"  Technical: {data['explanation']['technical_details']}")
        logger.info(f"  Regime: {data['explanation']['regime_details']}")
        logger.info(f"  Events: {data['explanation']['event_details']}")
        logger.info("=" * 80)
    
    subscriber.subscribe([RedisChannels.SIGNALS], signal_handler)
    
    # Listen for a limited time
    logger.info("Listening for signals...")
    await asyncio.sleep(10)
    
    subscriber.stop()
    subscriber.close()


async def main():
    """Main demo function."""
    logger.info("=" * 80)
    logger.info("Signal Aggregator Demo")
    logger.info("=" * 80)
    
    # Initialize Redis client
    redis_client = get_redis_client()
    
    if not redis_client.ping():
        logger.error("Cannot connect to Redis. Please ensure Redis is running.")
        return
    
    logger.info("Connected to Redis successfully")
    
    # Create signal aggregator
    aggregator = SignalAggregator(
        redis_client=redis_client,
        weight_sentiment=0.3,
        weight_technical=0.5,
        weight_regime=0.2,
        buy_threshold=60.0,
        sell_threshold=-60.0
    )
    
    # Start aggregator
    aggregator.start()
    logger.info("Signal aggregator started")
    
    # Create tasks
    aggregator_task = asyncio.create_task(aggregator.listen())
    signal_listener_task = asyncio.create_task(listen_for_signals(redis_client))
    
    # Wait a bit before publishing data
    await asyncio.sleep(2)
    
    # Publish test data
    await publish_test_data(redis_client)
    
    # Wait for signal listener to finish
    await signal_listener_task
    
    # Stop aggregator
    aggregator.stop()
    logger.info("Signal aggregator stopped")
    
    # Cancel aggregator task
    aggregator_task.cancel()
    try:
        await aggregator_task
    except asyncio.CancelledError:
        pass
    
    logger.info("Demo completed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
