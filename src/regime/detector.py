"""Market regime detector for classifying market conditions."""

import logging
import numpy as np
from datetime import datetime
from typing import List, Optional

from src.shared.models import OHLC, MarketRegime, RegimeType
from src.shared.redis_client import RedisChannels, get_redis_client
from src.database.connection import get_db_session

logger = logging.getLogger(__name__)


class MarketRegimeDetector:
    """Detector for classifying market regimes based on price action."""
    
    def __init__(self, window_size: int = 100, confidence_threshold: float = 0.6):
        """
        Initialize market regime detector.
        
        Args:
            window_size: Number of price bars to analyze (default: 100)
            confidence_threshold: Minimum confidence for regime classification (default: 0.6)
        """
        self.window_size = window_size
        self.confidence_threshold = confidence_threshold
        self.redis_client = get_redis_client()
        self._last_regime: Optional[MarketRegime] = None
        
        logger.info(
            f"Market regime detector initialized: window={window_size}, "
            f"confidence_threshold={confidence_threshold}"
        )
    
    def detect_regime(self, prices: List[OHLC]) -> MarketRegime:
        """
        Detect market regime from price data.
        
        Args:
            prices: List of OHLC price bars
            
        Returns:
            MarketRegime with classification and confidence
        """
        # Use only the most recent window_size bars
        if len(prices) > self.window_size:
            prices = prices[-self.window_size:]
        
        if len(prices) < 20:
            logger.warning(f"Insufficient data for regime detection: {len(prices)} bars")
            return self._create_default_regime()
        
        # Extract close prices
        closes = np.array([bar.close for bar in prices])
        highs = np.array([bar.high for bar in prices])
        lows = np.array([bar.low for bar in prices])
        
        # Compute metrics
        volatility = self._compute_volatility(closes)
        trend_strength = self._compute_trend_strength(closes)
        trend_direction = self._compute_trend_direction(closes)
        
        # Classify regime
        regime_type, confidence = self._classify_regime(
            volatility=volatility,
            trend_strength=trend_strength,
            trend_direction=trend_direction
        )
        
        # Apply confidence threshold
        if confidence < self.confidence_threshold:
            logger.debug(
                f"Low confidence ({confidence:.2f}), defaulting to RANGING regime"
            )
            regime_type = RegimeType.RANGING
        
        regime = MarketRegime(
            regime_type=regime_type,
            confidence=confidence,
            volatility=volatility,
            trend_strength=trend_strength,
            timestamp=datetime.now()
        )
        
        logger.debug(
            f"Detected regime: {regime_type.value} "
            f"(confidence={confidence:.2f}, volatility={volatility:.4f}, "
            f"trend_strength={trend_strength:.4f})"
        )
        
        return regime
    
    def _compute_volatility(self, closes: np.ndarray) -> float:
        """
        Compute volatility using standard deviation of returns.
        
        Args:
            closes: Array of closing prices
            
        Returns:
            Volatility measure (normalized)
        """
        if len(closes) < 2:
            return 0.0
        
        # Compute log returns
        returns = np.diff(np.log(closes))
        
        # Standard deviation of returns
        volatility = np.std(returns)
        
        return float(volatility)
    
    def _compute_trend_strength(self, closes: np.ndarray) -> float:
        """
        Compute trend strength using linear regression R-squared.
        
        Args:
            closes: Array of closing prices
            
        Returns:
            Trend strength between 0.0 (no trend) and 1.0 (strong trend)
        """
        if len(closes) < 2:
            return 0.0
        
        # Linear regression
        x = np.arange(len(closes))
        
        # Compute correlation coefficient
        correlation = np.corrcoef(x, closes)[0, 1]
        
        # R-squared (coefficient of determination)
        r_squared = correlation ** 2
        
        return float(r_squared)
    
    def _compute_trend_direction(self, closes: np.ndarray) -> float:
        """
        Compute trend direction using linear regression slope.
        
        Args:
            closes: Array of closing prices
            
        Returns:
            Positive for uptrend, negative for downtrend, near zero for no trend
        """
        if len(closes) < 2:
            return 0.0
        
        # Linear regression
        x = np.arange(len(closes))
        
        # Compute slope
        slope = np.polyfit(x, closes, 1)[0]
        
        # Normalize by mean price
        normalized_slope = slope / np.mean(closes)
        
        return float(normalized_slope)
    
    def _classify_regime(
        self,
        volatility: float,
        trend_strength: float,
        trend_direction: float
    ) -> tuple[RegimeType, float]:
        """
        Classify market regime based on computed metrics.
        
        Classification logic:
        - VOLATILE: High volatility (> 0.03)
        - CALM: Low volatility (< 0.01)
        - TRENDING_UP: Strong upward trend (trend_strength > 0.5, direction > 0)
        - TRENDING_DOWN: Strong downward trend (trend_strength > 0.5, direction < 0)
        - RANGING: Weak trend (trend_strength < 0.3)
        
        Args:
            volatility: Volatility measure
            trend_strength: Trend strength (0-1)
            trend_direction: Trend direction (positive/negative)
            
        Returns:
            Tuple of (RegimeType, confidence)
        """
        # Thresholds
        HIGH_VOLATILITY = 0.03
        LOW_VOLATILITY = 0.01
        STRONG_TREND = 0.5
        WEAK_TREND = 0.3
        
        # Initialize scores for each regime
        scores = {
            RegimeType.VOLATILE: 0.0,
            RegimeType.CALM: 0.0,
            RegimeType.TRENDING_UP: 0.0,
            RegimeType.TRENDING_DOWN: 0.0,
            RegimeType.RANGING: 0.0
        }
        
        # Volatility-based regimes
        if volatility > HIGH_VOLATILITY:
            scores[RegimeType.VOLATILE] = min(volatility / HIGH_VOLATILITY, 1.0)
        elif volatility < LOW_VOLATILITY:
            scores[RegimeType.CALM] = 1.0 - (volatility / LOW_VOLATILITY)
        
        # Trend-based regimes
        if trend_strength > STRONG_TREND:
            if trend_direction > 0:
                scores[RegimeType.TRENDING_UP] = trend_strength
            else:
                scores[RegimeType.TRENDING_DOWN] = trend_strength
        elif trend_strength < WEAK_TREND:
            scores[RegimeType.RANGING] = 1.0 - trend_strength
        
        # If no clear regime, default to ranging
        if all(score < 0.3 for score in scores.values()):
            scores[RegimeType.RANGING] = 0.5
        
        # Select regime with highest score
        regime_type = max(scores, key=scores.get)
        confidence = scores[regime_type]
        
        # Ensure confidence is in valid range
        confidence = max(0.0, min(1.0, confidence))
        
        return regime_type, confidence
    
    def _create_default_regime(self) -> MarketRegime:
        """
        Create default regime (RANGING with low confidence).
        
        Returns:
            Default MarketRegime
        """
        return MarketRegime(
            regime_type=RegimeType.RANGING,
            confidence=0.5,
            volatility=0.0,
            trend_strength=0.0,
            timestamp=datetime.now()
        )
    
    def compute_confidence(self, regime: MarketRegime) -> float:
        """
        Compute confidence score for a regime.
        
        Note: Confidence is already computed during classification.
        This method is provided for API compatibility.
        
        Args:
            regime: MarketRegime to compute confidence for
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        return regime.confidence
    
    def publish_to_redis(self, regime: MarketRegime) -> bool:
        """
        Publish regime to Redis regime channel.
        
        Only publishes if regime has changed from last published regime.
        
        Args:
            regime: MarketRegime to publish
            
        Returns:
            True if published successfully, False otherwise
        """
        # Check if regime has changed
        if self._last_regime is not None:
            if (self._last_regime.regime_type == regime.regime_type and
                abs(self._last_regime.confidence - regime.confidence) < 0.1):
                logger.debug("Regime unchanged, skipping publish")
                return True
        
        data = {
            'regime_type': regime.regime_type.value,
            'confidence': regime.confidence,
            'volatility': regime.volatility,
            'trend_strength': regime.trend_strength,
            'timestamp': regime.timestamp.isoformat()
        }
        
        success = self.redis_client.publish(RedisChannels.REGIME, data)
        
        if success:
            logger.info(
                f"Published regime change to Redis: {regime.regime_type.value} "
                f"(confidence={regime.confidence:.2f})"
            )
            self._last_regime = regime
        else:
            logger.warning(f"Failed to publish regime to Redis")
        
        return success
    
    def store_regime(self, regime: MarketRegime, symbol: str = "DEFAULT") -> bool:
        """
        Store regime data in PostgreSQL.
        
        Note: Current schema doesn't have a dedicated regimes table.
        This stores regime as part of trading signals or can be extended.
        
        Args:
            regime: MarketRegime to store
            symbol: Trading symbol (for future use)
            
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            # For now, we'll log that storage would happen here
            # In a full implementation, we'd add a regimes table to the schema
            logger.debug(
                f"Regime storage: {regime.regime_type.value} "
                f"(confidence={regime.confidence:.2f})"
            )
            return True
        
        except Exception as e:
            logger.error(f"Error storing regime: {e}")
            return False
    
    def process_prices(self, prices: List[OHLC]) -> MarketRegime:
        """
        Process price data: detect regime, publish to Redis, store in DB.
        
        Args:
            prices: List of OHLC price bars
            
        Returns:
            Detected MarketRegime
        """
        try:
            # Detect regime
            regime = self.detect_regime(prices)
            
            # Publish to Redis (only if changed)
            self.publish_to_redis(regime)
            
            # Store in database
            self.store_regime(regime)
            
            return regime
        
        except Exception as e:
            logger.error(f"Error processing prices for regime detection: {e}")
            return self._create_default_regime()
