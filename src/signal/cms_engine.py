"""
Composite Market Score (CMS) Engine
Combines sentiment, volatility, trend, and events into a single actionable score.

Formula:
CMS = 0.4 × SentimentIndex 
    - 0.3 × VolatilityIndex 
    + 0.2 × TrendStrength 
    + 0.1 × EventShockFactor

Range: [-100, 100]
"""

import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, Optional
import json

from src.shared.redis_client import get_redis_client
from src.database.connection import get_db_session

logger = logging.getLogger(__name__)


@dataclass
class CMSComponents:
    """
    Individual components of the Composite Market Score.
    
    All components are normalized to appropriate ranges before weighting.
    """
    sentiment_index: float      # [-1, 1] from NLP engine
    volatility_index: float     # [0, 1] from regime detector
    trend_strength: float       # [-1, 1] from regime detector
    event_shock_factor: float   # [0, 1] from NLP engine
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return asdict(self)
    
    def validate(self) -> None:
        """Validate component ranges."""
        if not -1 <= self.sentiment_index <= 1:
            raise ValueError(f"sentiment_index must be in [-1, 1], got {self.sentiment_index}")
        if not 0 <= self.volatility_index <= 1:
            raise ValueError(f"volatility_index must be in [0, 1], got {self.volatility_index}")
        if not -1 <= self.trend_strength <= 1:
            raise ValueError(f"trend_strength must be in [-1, 1], got {self.trend_strength}")
        if not 0 <= self.event_shock_factor <= 1:
            raise ValueError(f"event_shock_factor must be in [0, 1], got {self.event_shock_factor}")
 


@
dataclass
class CMSResult:
    """
    Result of CMS calculation.
    """
    cms_score: float                        # Final CMS score [-100, 100]
    signal_type: str                        # 'BUY', 'SELL', or 'HOLD'
    confidence: float                       # Confidence level [0, 1]
    components: CMSComponents               # Input components
    weighted_contributions: Dict[str, float]  # Contribution of each component
    explanation: str                        # Human-readable explanation
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'cms_score': round(self.cms_score, 2),
            'signal_type': self.signal_type,
            'confidence': round(self.confidence, 4),
            'components': self.components.to_dict(),
            'weighted_contributions': {k: round(v, 2) for k, v in self.weighted_contributions.items()},
            'explanation': self.explanation,
            'timestamp': self.timestamp.isoformat()
        }


class CMSEngine:
    """
    Composite Market Score Engine.
    
    Combines multiple market signals into a single actionable score.
    """
    
    # Component weights (must sum to 1.0 in absolute terms)
    SENTIMENT_WEIGHT = 0.4      # 40% - Highest weight (market psychology)
    VOLATILITY_WEIGHT = -0.3    # 30% - Negative (high vol is bearish)
    TREND_WEIGHT = 0.2          # 20% - Confirms direction
    EVENT_WEIGHT = 0.1          # 10% - Amplifies sentiment
    
    def __init__(
        self,
        buy_threshold: float = 50.0,
        sell_threshold: float = -50.0,
        redis_channel: str = "cms.live"
    ):
        """
        Initialize CMS Engine.
        
        Args:
            buy_threshold: CMS score above which to generate BUY signal
            sell_threshold: CMS score below which to generate SELL signal
            redis_channel: Redis channel for publishing CMS updates
        """
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.redis_channel = redis_channel
        
        logger.info(
            f"CMS Engine initialized with thresholds: "
            f"BUY>{buy_threshold}, SELL<{sell_threshold}"
        )
    
    def compute_cms(self, components: CMSComponents) -> CMSResult:
        """
        Compute Composite Market Score from components.
        
        Args:
            components: Normalized input components
            
        Returns:
            CMSResult with score, signal, confidence, and explanation
        """
        # Validate inputs
        components.validate()
        
        # Calculate weighted contributions (scaled to [-100, 100])
        sentiment_contrib = self.SENTIMENT_WEIGHT * components.sentiment_index * 100
        volatility_contrib = self.VOLATILITY_WEIGHT * components.volatility_index * 100
        trend_contrib = self.TREND_WEIGHT * components.trend_strength * 100
        
        # Event contribution amplifies sentiment direction
        if components.sentiment_index >= 0:
            event_contrib = self.EVENT_WEIGHT * components.event_shock_factor * 100
        else:
            event_contrib = -self.EVENT_WEIGHT * components.event_shock_factor * 100
        
        # Sum contributions
        cms_score = sentiment_contrib + volatility_contrib + trend_contrib + event_contrib
        
        # Ensure bounds
        cms_score = max(-100.0, min(100.0, cms_score))
        
        # Generate signal
        if cms_score > self.buy_threshold:
            signal_type = 'BUY'
        elif cms_score < self.sell_threshold:
            signal_type = 'SELL'
        else:
            signal_type = 'HOLD'
        
        # Calculate confidence
        confidence = self._calculate_confidence(components, cms_score)
        
        # Create weighted contributions dict
        weighted_contributions = {
            'sentiment': sentiment_contrib,
            'volatility': volatility_contrib,
            'trend': trend_contrib,
            'event': event_contrib
        }
        
        # Generate explanation
        explanation = self._generate_explanation(
            cms_score, signal_type, weighted_contributions
        )
        
        result = CMSResult(
            cms_score=cms_score,
            signal_type=signal_type,
            confidence=confidence,
            components=components,
            weighted_contributions=weighted_contributions,
            explanation=explanation,
            timestamp=datetime.utcnow()
        )
        
        logger.info(
            f"CMS computed: {cms_score:.2f} ({signal_type}) "
            f"confidence={confidence:.2%}"
        )
        
        return result
    
    def _calculate_confidence(
        self,
        components: CMSComponents,
        cms_score: float
    ) -> float:
        """
        Calculate confidence level for the CMS signal.
        
        Confidence factors:
        1. Signal strength (50%): How far from neutral
        2. Component agreement (30%): How aligned are components
        3. Volatility penalty (20%): Lower confidence in high volatility
        
        Args:
            components: Input components
            cms_score: Calculated CMS score
            
        Returns:
            Confidence level [0, 1]
        """
        # 1. Signal strength: |CMS| / 100
        signal_strength = abs(cms_score) / 100.0
        
        # 2. Component agreement: normalize and check alignment
        # Convert all to same scale (positive = bullish, negative = bearish)
        normalized_components = [
            components.sentiment_index,
            -components.volatility_index,  # Negative because high vol is bearish
            components.trend_strength,
            components.event_shock_factor * (1 if components.sentiment_index >= 0 else -1)
        ]
        
        # Calculate standard deviation (lower = more agreement)
        mean = sum(normalized_components) / len(normalized_components)
        variance = sum((x - mean) ** 2 for x in normalized_components) / len(normalized_components)
        std_dev = variance ** 0.5
        
        # Agreement score (1 - normalized std_dev)
        agreement = max(0.0, 1.0 - std_dev)
        
        # 3. Volatility penalty
        volatility_penalty = 1.0 - components.volatility_index
        
        # Weighted confidence
        confidence = (
            signal_strength * 0.5 +
            agreement * 0.3 +
            volatility_penalty * 0.2
        )
        
        return max(0.0, min(1.0, confidence))
    
    def _generate_explanation(
        self,
        cms_score: float,
        signal_type: str,
        contributions: Dict[str, float]
    ) -> str:
        """
        Generate human-readable explanation of CMS calculation.
        
        Args:
            cms_score: Final CMS score
            signal_type: Generated signal
            contributions: Weighted contributions
            
        Returns:
            Explanation string
        """
        # Find dominant factor
        dominant_factor = max(contributions.items(), key=lambda x: abs(x[1]))
        
        explanation = (
            f"{signal_type} signal generated with CMS of {cms_score:.2f}. "
            f"Sentiment contributes {contributions['sentiment']:+.2f}, "
            f"volatility {contributions['volatility']:+.2f}, "
            f"trend {contributions['trend']:+.2f}, "
            f"events {contributions['event']:+.2f}. "
            f"Dominant factor: {dominant_factor[0]}."
        )
        
        return explanation
    
    def publish_to_redis(self, result: CMSResult, symbol: str) -> None:
        """
        Publish CMS result to Redis.
        
        Args:
            result: CMS calculation result
            symbol: Trading symbol
        """
        try:
            redis_client = get_redis_client()
            
            # Prepare message
            message = result.to_dict()
            message['symbol'] = symbol
            
            # Publish to channel
            redis_client.publish(self.redis_channel, json.dumps(message))
            
            logger.debug(f"Published CMS for {symbol} to Redis: {result.cms_score:.2f}")
            
        except Exception as e:
            logger.error(f"Failed to publish CMS to Redis: {e}")
    
    def store_to_database(self, result: CMSResult, symbol: str) -> None:
        """
        Store CMS result to PostgreSQL.
        
        Args:
            result: CMS calculation result
            symbol: Trading symbol
        """
        try:
            with get_db_session() as session:
                session.execute("""
                    INSERT INTO cms_scores (
                        symbol, cms_score, signal_type, confidence,
                        sentiment_index, volatility_index, trend_strength, event_shock_factor,
                        sentiment_contribution, volatility_contribution,
                        trend_contribution, event_contribution,
                        explanation, timestamp
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    symbol,
                    result.cms_score,
                    result.signal_type,
                    result.confidence,
                    result.components.sentiment_index,
                    result.components.volatility_index,
                    result.components.trend_strength,
                    result.components.event_shock_factor,
                    result.weighted_contributions['sentiment'],
                    result.weighted_contributions['volatility'],
                    result.weighted_contributions['trend'],
                    result.weighted_contributions['event'],
                    result.explanation,
                    result.timestamp
                ))
                session.commit()
                
            logger.debug(f"Stored CMS for {symbol} to database")
            
        except Exception as e:
            logger.error(f"Failed to store CMS to database: {e}")


def compute_cms(
    sentiment_index: float,
    volatility_index: float,
    trend_strength: float,
    event_shock_factor: float,
    buy_threshold: float = 50.0,
    sell_threshold: float = -50.0
) -> CMSResult:
    """
    Convenience function to compute CMS from individual components.
    
    Args:
        sentiment_index: Sentiment score [-1, 1]
        volatility_index: Volatility score [0, 1]
        trend_strength: Trend strength [-1, 1]
        event_shock_factor: Event shock [0, 1]
        buy_threshold: BUY signal threshold
        sell_threshold: SELL signal threshold
        
    Returns:
        CMSResult
    """
    components = CMSComponents(
        sentiment_index=sentiment_index,
        volatility_index=volatility_index,
        trend_strength=trend_strength,
        event_shock_factor=event_shock_factor
    )
    
    engine = CMSEngine(buy_threshold=buy_threshold, sell_threshold=sell_threshold)
    return engine.compute_cms(components)
