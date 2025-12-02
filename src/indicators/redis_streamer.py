"""
Redis streaming integration for technical indicators.
Publishes indicator results to Redis for real-time consumption.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any

from src.shared.models import IndicatorResults, TechnicalSignals, PriceData
from src.shared.redis_client import RedisChannels, get_redis_client
from src.indicators.engine import TechnicalIndicatorEngine

logger = logging.getLogger(__name__)


class IndicatorRedisStreamer:
    """
    Streams technical indicator results to Redis.
    
    Publishes computed indicators to Redis channels for real-time
    consumption by signal aggregators and dashboards.
    """
    
    def __init__(self, engine: Optional[TechnicalIndicatorEngine] = None):
        """
        Initialize Redis streamer.
        
        Args:
            engine: Technical indicator engine (creates new if None)
        """
        self.engine = engine or TechnicalIndicatorEngine()
        self.redis_client = get_redis_client()
        logger.info("Indicator Redis streamer initialized")
    
    def compute_and_publish(
        self,
        price_data: PriceData,
        publish_signals: bool = True
    ) -> IndicatorResults:
        """
        Compute indicators and publish to Redis.
        
        Args:
            price_data: Price data with OHLC bars
            publish_signals: Whether to also publish trading signals
            
        Returns:
            Computed indicator results
        """
        try:
            # Compute indicators
            indicators = self.engine.compute_indicators(price_data)
            
            # Publish indicators
            self.publish_indicators(indicators, price_data.symbol)
            
            # Optionally publish signals
            if publish_signals and price_data.bars:
                current_price = price_data.bars[-1].close
                signals = self.engine.generate_signals(indicators, current_price)
                self.publish_signals(signals, price_data.symbol, current_price)
            
            logger.debug(f"Published indicators for {price_data.symbol}")
            return indicators
        
        except Exception as e:
            logger.error(f"Failed to compute and publish indicators: {e}")
            raise
    
    def publish_indicators(
        self,
        indicators: IndicatorResults,
        symbol: str,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Publish indicator results to Redis.
        
        Args:
            indicators: Computed indicator results
            symbol: Stock symbol
            timestamp: Timestamp (defaults to now)
            
        Returns:
            True if published successfully
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        data = {
            'symbol': symbol,
            'timestamp': timestamp.isoformat(),
            'rsi': indicators.rsi,
            'macd': {
                'macd_line': indicators.macd.macd_line,
                'signal_line': indicators.macd.signal_line,
                'histogram': indicators.macd.histogram
            },
            'bollinger_bands': {
                'upper': indicators.bollinger.upper,
                'middle': indicators.bollinger.middle,
                'lower': indicators.bollinger.lower
            },
            'sma_20': indicators.sma_20,
            'sma_50': indicators.sma_50,
            'ema_12': indicators.ema_12,
            'ema_26': indicators.ema_26,
            'atr': indicators.atr
        }
        
        # Add EMA 20/50 if available
        if hasattr(indicators, 'ema_20'):
            data['ema_20'] = indicators.ema_20
        if hasattr(indicators, 'ema_50'):
            data['ema_50'] = indicators.ema_50
        
        success = self.redis_client.publish(RedisChannels.INDICATORS, data)
        
        if success:
            logger.debug(f"Published indicators for {symbol} to Redis")
        else:
            logger.warning(f"Failed to publish indicators for {symbol} to Redis")
        
        return success
    
    def publish_signals(
        self,
        signals: TechnicalSignals,
        symbol: str,
        current_price: float,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Publish trading signals to Redis.
        
        Args:
            signals: Generated trading signals
            symbol: Stock symbol
            current_price: Current market price
            timestamp: Timestamp (defaults to now)
            
        Returns:
            True if published successfully
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        data = {
            'symbol': symbol,
            'timestamp': timestamp.isoformat(),
            'current_price': current_price,
            'rsi_signal': signals.rsi_signal.value,
            'macd_signal': signals.macd_signal.value,
            'bb_signal': signals.bb_signal.value
        }
        
        # Publish to signals channel (can be consumed by signal aggregator)
        success = self.redis_client.publish('technical_signals', data)
        
        if success:
            logger.debug(f"Published signals for {symbol} to Redis")
        else:
            logger.warning(f"Failed to publish signals for {symbol} to Redis")
        
        return success
    
    def publish_individual_indicator(
        self,
        indicator_name: str,
        value: Any,
        symbol: str,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Publish a single indicator value to Redis.
        
        Useful for streaming individual indicators as they're computed.
        
        Args:
            indicator_name: Name of the indicator (e.g., 'rsi', 'macd')
            value: Indicator value
            symbol: Stock symbol
            timestamp: Timestamp (defaults to now)
            
        Returns:
            True if published successfully
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        data = {
            'symbol': symbol,
            'timestamp': timestamp.isoformat(),
            'indicator': indicator_name,
            'value': value
        }
        
        channel = f"indicator_{indicator_name}"
        success = self.redis_client.publish(channel, data)
        
        if success:
            logger.debug(f"Published {indicator_name} for {symbol} to Redis")
        else:
            logger.warning(f"Failed to publish {indicator_name} for {symbol} to Redis")
        
        return success
    
    def get_indicator_summary(self, indicators: IndicatorResults) -> Dict[str, Any]:
        """
        Get a summary of indicator values for logging/display.
        
        Args:
            indicators: Computed indicator results
            
        Returns:
            Dictionary with indicator summary
        """
        return {
            'rsi': f"{indicators.rsi:.2f}",
            'macd_histogram': f"{indicators.macd.histogram:.4f}",
            'bb_position': self._get_bb_position(indicators),
            'sma_20': f"{indicators.sma_20:.2f}",
            'sma_50': f"{indicators.sma_50:.2f}",
            'atr': f"{indicators.atr:.2f}"
        }
    
    def _get_bb_position(self, indicators: IndicatorResults) -> str:
        """Get Bollinger Band position description."""
        bb = indicators.bollinger
        width = bb.upper - bb.lower
        if width == 0:
            return "neutral"
        
        # Estimate position based on middle band
        if bb.middle > (bb.upper + bb.lower) / 2:
            return "upper_half"
        else:
            return "lower_half"


# Convenience function
def stream_indicators_to_redis(
    price_data: PriceData,
    publish_signals: bool = True
) -> IndicatorResults:
    """
    Convenience function to compute and stream indicators to Redis.
    
    Args:
        price_data: Price data with OHLC bars
        publish_signals: Whether to also publish trading signals
        
    Returns:
        Computed indicator results
    """
    streamer = IndicatorRedisStreamer()
    return streamer.compute_and_publish(price_data, publish_signals)
