"""
Enhanced Market Regime Detection System
Logic-based regime classification using sentiment, volatility, and trend strength.
No ML - pure rule-based logic with mathematical formulas.
"""

import logging
import numpy as np
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum

from src.shared.models import OHLC
from src.shared.redis_client import get_redis_client
from src.database.connection import get_db_session

logger = logging.getLogger(__name__)


class EnhancedRegimeType(Enum):
    """Enhanced market regime types."""
    BULL = "bull"              # Strong uptrend with positive sentiment
    BEAR = "bear"              # Strong downtrend with negative sentiment
    NEUTRAL = "neutral"        # Sideways market, balanced conditions
    PANIC = "panic"            # High volatility with extreme negative sentiment


@dataclass
class RegimeInputs:
    """
    Inputs for regime detection.
    
    All inputs are normalized to [-1, 1] or [0, 1] ranges for consistent weighting.
    """
    sentiment_index: float      # From NLP engine: [-1, 1]
    volatility_index: float     # Normalized volatility: [0, 1]
    trend_strength: float       # EMA slope difference: [-1, 1]
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            'sentiment_index': self.sentiment_index,
            'volatility_index': self.volatility_index,
            'trend_strength': self.trend_strength
        }


@dataclass
class RegimeOutput:
    """
    Output of regime detection.
    
    Contains regime classification, confidence, and all intermediate calculations.
    """
    regime: EnhancedRegimeType
    confidence: float           # [0, 1]
    inputs: RegimeInputs
    scores: Dict[str, float]    # Individual regime scores
    explanation: str            # Human-readable explanation
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'regime': self.regime.value,
            'confidence': self.confidence,
            'inputs': self.inputs.to_dict(),
            'scores': self.scores,
            'explanation': self.explanation,
            'timestamp': self.timestamp.isoformat()
        }


class EnhancedMarketRegimeDetector:
    """
    Enhanced market regime detector using sentiment, volatility, and trend.
    
    Mathematical Formulas:
    =====================
    
    1. Volatility Index (VI):
       VI = normalize(ATR / Price, 0, 0.05)
       where ATR = Average True Range
       
    2. Trend Strength (TS):
       TS = (EMA20 - EMA50) / EMA50
       Normalized to [-1, 1]
       
    3. Sentiment Index (SI):
       From NLP engine, already in [-1, 1]
       
    4. Regime Scores:
       Bull Score = (SI × 0.4) + (TS × 0.4) + ((1 - VI) × 0.2)
       Bear Score = (-SI × 0.4) + (-TS × 0.4) + ((1 - VI) × 0.2)
       Neutral Score = (1 - |SI|) × 0.5 + (1 - |TS|) × 0.3 + ((1 - VI) × 0.2)
       Panic Score = VI × 0.6 + (-SI × 0.4)
       
    5. Regime Selection:
       regime = argmax(Bull, Bear, Neutral, Panic)
       confidence = max_score / sum(all_scores)
    
    Thresholds:
    ===========
    - High Volatility: VI > 0.7
    - Strong Trend: |TS| > 0.3
    - Extreme Sentiment: |SI| > 0.6
    - Panic Trigger: VI > 0.8 AND SI < -0.5
    """
    
    # Regime detection thresholds
    HIGH_VOLATILITY_THRESHOLD = 0.7
    STRONG_TREND_THRESHOLD = 0.3
    EXTREME_SENTIMENT_THRESHOLD = 0.6
    PANIC_VOLATILITY_THRESHOLD = 0.8
    PANIC_SENTIMENT_THRESHOLD = -0.5
    
    # Weighting factors for regime scores
    SENTIMENT_WEIGHT = 0.4
    TREND_WEIGHT = 0.4
    VOLATILITY_WEIGHT = 0.2
    
    def __init__(
        self,
        window_size: int = 100,
        min_confidence: float = 0.4
    ):
        """
        Initialize enhanced regime detector.
        
        Args:
            window_size: Number of bars for calculations
            min_confidence: Minimum confidence threshold
        """
        self.window_size = window_size
        self.min_confidence = min_confidence
        self.redis_client = get_redis_client()
        self._last_regime: Optional[RegimeOutput] = None
        
        logger.info(
            f"Enhanced regime detector initialized: "
            f"window={window_size}, min_confidence={min_confidence}"
        )
    
    def compute_volatility_index(
        self,
        prices: List[OHLC],
        period: int = 14
    ) -> float:
        """
        Compute Volatility Index using ATR.
        
        Formula:
        --------
        ATR = Average True Range over period
        VI = ATR / Current Price
        Normalized to [0, 1] using sigmoid-like function
        
        Args:
            prices: List of OHLC bars
            period: ATR period (default: 14)
            
        Returns:
            Volatility Index in [0, 1]
        """
        if len(prices) < period + 1:
            return 0.5  # Default to medium volatility
        
        # Calculate True Range for each bar
        true_ranges = []
        for i in range(1, len(prices)):
            high_low = prices[i].high - prices[i].low
            high_close = abs(prices[i].high - prices[i-1].close)
            low_close = abs(prices[i].low - prices[i-1].close)
            
            tr = max(high_low, high_close, low_close)
            true_ranges.append(tr)
        
        # Average True Range
        atr = np.mean(true_ranges[-period:])
        
        # Current price
        current_price = prices[-1].close
        
        # Volatility ratio
        volatility_ratio = atr / current_price
        
        # Normalize to [0, 1] using reference range [0, 0.05]
        # VI = 0 means very low volatility
        # VI = 1 means very high volatility
        vi = min(volatility_ratio / 0.05, 1.0)
        
        return float(vi)
    
    def compute_trend_strength(
        self,
        prices: List[OHLC],
        fast_period: int = 20,
        slow_period: int = 50
    ) -> float:
        """
        Compute Trend Strength using EMA slope difference.
        
        Formula:
        --------
        EMA20 = Exponential Moving Average (20 periods)
        EMA50 = Exponential Moving Average (50 periods)
        TS = (EMA20 - EMA50) / EMA50
        
        Normalized to [-1, 1]:
        - TS > 0: Uptrend
        - TS < 0: Downtrend
        - TS ≈ 0: No trend
        
        Args:
            prices: List of OHLC bars
            fast_period: Fast EMA period (default: 20)
            slow_period: Slow EMA period (default: 50)
            
        Returns:
            Trend Strength in [-1, 1]
        """
        if len(prices) < slow_period:
            return 0.0  # No trend
        
        closes = np.array([bar.close for bar in prices])
        
        # Compute EMAs
        ema_fast = self._compute_ema(closes, fast_period)
        ema_slow = self._compute_ema(closes, slow_period)
        
        # Trend strength as percentage difference
        trend_strength = (ema_fast - ema_slow) / ema_slow
        
        # Normalize to [-1, 1] using tanh-like scaling
        # Typical range is [-0.1, 0.1], so we scale by 10
        ts = np.tanh(trend_strength * 10)
        
        return float(ts)
    
    def _compute_ema(self, prices: np.ndarray, period: int) -> float:
        """
        Compute Exponential Moving Average.
        
        Formula:
        --------
        Multiplier = 2 / (period + 1)
        EMA(t) = Price(t) × Multiplier + EMA(t-1) × (1 - Multiplier)
        
        Args:
            prices: Array of prices
            period: EMA period
            
        Returns:
            Current EMA value
        """
        if len(prices) < period:
            return float(np.mean(prices))
        
        # Start with SMA
        ema = np.mean(prices[:period])
        
        # Calculate multiplier
        multiplier = 2.0 / (period + 1.0)
        
        # Calculate EMA
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        
        return float(ema)
    
    def compute_regime_scores(
        self,
        inputs: RegimeInputs
    ) -> Dict[str, float]:
        """
        Compute scores for each regime type.
        
        Formulas:
        ---------
        Bull Score = (SI × 0.4) + (TS × 0.4) + ((1 - VI) × 0.2)
        - Favors positive sentiment, uptrend, low volatility
        
        Bear Score = (-SI × 0.4) + (-TS × 0.4) + ((1 - VI) × 0.2)
        - Favors negative sentiment, downtrend, low volatility
        
        Neutral Score = (1 - |SI|) × 0.5 + (1 - |TS|) × 0.3 + ((1 - VI) × 0.2)
        - Favors neutral sentiment, no trend, low volatility
        
        Panic Score = VI × 0.6 + (-SI × 0.4)
        - Favors high volatility and negative sentiment
        
        Args:
            inputs: RegimeInputs with normalized values
            
        Returns:
            Dictionary of regime scores
        """
        si = inputs.sentiment_index
        ts = inputs.trend_strength
        vi = inputs.volatility_index
        
        # Bull: Positive sentiment + uptrend + low volatility
        bull_score = (
            si * self.SENTIMENT_WEIGHT +
            ts * self.TREND_WEIGHT +
            (1 - vi) * self.VOLATILITY_WEIGHT
        )
        
        # Bear: Negative sentiment + downtrend + low volatility
        bear_score = (
            -si * self.SENTIMENT_WEIGHT +
            -ts * self.TREND_WEIGHT +
            (1 - vi) * self.VOLATILITY_WEIGHT
        )
        
        # Neutral: Balanced sentiment + no trend + low volatility
        neutral_score = (
            (1 - abs(si)) * 0.5 +
            (1 - abs(ts)) * 0.3 +
            (1 - vi) * 0.2
        )
        
        # Panic: High volatility + extreme negative sentiment
        panic_score = (
            vi * 0.6 +
            -si * 0.4
        )
        
        # Normalize scores to [0, 1]
        scores = {
            'bull': max(0.0, bull_score),
            'bear': max(0.0, bear_score),
            'neutral': max(0.0, neutral_score),
            'panic': max(0.0, panic_score)
        }
        
        return scores
    
    def classify_regime(
        self,
        inputs: RegimeInputs
    ) -> Tuple[EnhancedRegimeType, float, Dict[str, float]]:
        """
        Classify market regime based on inputs.
        
        Selection Logic:
        ----------------
        1. Compute scores for all regimes
        2. Select regime with highest score
        3. Confidence = max_score / sum(all_scores)
        4. Apply panic override if conditions met
        
        Panic Override:
        ---------------
        If VI > 0.8 AND SI < -0.5, force PANIC regime
        
        Args:
            inputs: RegimeInputs with normalized values
            
        Returns:
            Tuple of (regime, confidence, scores)
        """
        # Compute regime scores
        scores = self.compute_regime_scores(inputs)
        
        # Check for panic override
        if (inputs.volatility_index > self.PANIC_VOLATILITY_THRESHOLD and
            inputs.sentiment_index < self.PANIC_SENTIMENT_THRESHOLD):
            logger.info("Panic override triggered: high volatility + extreme negative sentiment")
            return EnhancedRegimeType.PANIC, 0.95, scores
        
        # Select regime with highest score
        regime_name = max(scores, key=scores.get)
        max_score = scores[regime_name]
        
        # Calculate confidence
        total_score = sum(scores.values())
        if total_score > 0:
            confidence = max_score / total_score
        else:
            confidence = 0.25  # Equal probability
        
        # Map to enum
        regime_map = {
            'bull': EnhancedRegimeType.BULL,
            'bear': EnhancedRegimeType.BEAR,
            'neutral': EnhancedRegimeType.NEUTRAL,
            'panic': EnhancedRegimeType.PANIC
        }
        
        regime = regime_map[regime_name]
        
        return regime, confidence, scores
    
    def generate_explanation(
        self,
        regime: EnhancedRegimeType,
        inputs: RegimeInputs,
        scores: Dict[str, float]
    ) -> str:
        """
        Generate human-readable explanation of regime classification.
        
        Args:
            regime: Classified regime
            inputs: Input values
            scores: Regime scores
            
        Returns:
            Explanation string
        """
        parts = []
        
        # Regime classification
        parts.append(f"Market regime classified as {regime.value.upper()}.")
        
        # Sentiment analysis
        if inputs.sentiment_index > 0.3:
            parts.append(f"Sentiment is positive ({inputs.sentiment_index:.2f}).")
        elif inputs.sentiment_index < -0.3:
            parts.append(f"Sentiment is negative ({inputs.sentiment_index:.2f}).")
        else:
            parts.append(f"Sentiment is neutral ({inputs.sentiment_index:.2f}).")
        
        # Trend analysis
        if inputs.trend_strength > 0.3:
            parts.append(f"Strong uptrend detected ({inputs.trend_strength:.2f}).")
        elif inputs.trend_strength < -0.3:
            parts.append(f"Strong downtrend detected ({inputs.trend_strength:.2f}).")
        else:
            parts.append(f"No clear trend ({inputs.trend_strength:.2f}).")
        
        # Volatility analysis
        if inputs.volatility_index > 0.7:
            parts.append(f"High volatility ({inputs.volatility_index:.2f}).")
        elif inputs.volatility_index < 0.3:
            parts.append(f"Low volatility ({inputs.volatility_index:.2f}).")
        else:
            parts.append(f"Moderate volatility ({inputs.volatility_index:.2f}).")
        
        # Regime-specific insights
        if regime == EnhancedRegimeType.PANIC:
            parts.append("PANIC conditions: extreme volatility with negative sentiment.")
        
        return " ".join(parts)
    
    def detect_regime(
        self,
        prices: List[OHLC],
        sentiment_index: float
    ) -> RegimeOutput:
        """
        Detect market regime from price data and sentiment.
        
        Args:
            prices: List of OHLC bars
            sentiment_index: Sentiment index from NLP engine [-1, 1]
            
        Returns:
            RegimeOutput with classification and details
        """
        # Compute inputs
        volatility_index = self.compute_volatility_index(prices)
        trend_strength = self.compute_trend_strength(prices)
        
        inputs = RegimeInputs(
            sentiment_index=sentiment_index,
            volatility_index=volatility_index,
            trend_strength=trend_strength
        )
        
        # Classify regime
        regime, confidence, scores = self.classify_regime(inputs)
        
        # Generate explanation
        explanation = self.generate_explanation(regime, inputs, scores)
        
        # Create output
        output = RegimeOutput(
            regime=regime,
            confidence=confidence,
            inputs=inputs,
            scores=scores,
            explanation=explanation,
            timestamp=datetime.now()
        )
        
        logger.info(
            f"Regime detected: {regime.value} "
            f"(confidence={confidence:.2f}, SI={sentiment_index:.2f}, "
            f"VI={volatility_index:.2f}, TS={trend_strength:.2f})"
        )
        
        return output
    
    def publish_to_redis(self, output: RegimeOutput) -> bool:
        """
        Publish regime to Redis 'regime.live' channel.
        
        Args:
            output: RegimeOutput to publish
            
        Returns:
            True if published successfully
        """
        # Check if regime changed significantly
        if self._last_regime is not None:
            if (self._last_regime.regime == output.regime and
                abs(self._last_regime.confidence - output.confidence) < 0.1):
                logger.debug("Regime unchanged, skipping publish")
                return True
        
        data = output.to_dict()
        
        success = self.redis_client.publish('regime.live', data)
        
        if success:
            logger.info(f"Published regime to Redis: {output.regime.value}")
            self._last_regime = output
        else:
            logger.warning("Failed to publish regime to Redis")
        
        return success
    
    def get_trading_signal_adjustment(
        self,
        regime: EnhancedRegimeType
    ) -> Dict[str, float]:
        """
        Get trading signal adjustments based on regime.
        
        Adjustments:
        ------------
        BULL: Favor long positions
        - Position size: +20%
        - Buy threshold: -10 (easier to trigger)
        - Sell threshold: +10 (harder to trigger)
        
        BEAR: Favor short positions or cash
        - Position size: -20%
        - Buy threshold: +10 (harder to trigger)
        - Sell threshold: -10 (easier to trigger)
        
        NEUTRAL: Standard parameters
        - Position size: 0%
        - Thresholds: unchanged
        
        PANIC: Reduce exposure dramatically
        - Position size: -50%
        - Buy threshold: +20 (much harder)
        - Sell threshold: -20 (much easier)
        - Stop loss: tighter (50% of normal)
        
        Args:
            regime: Current market regime
            
        Returns:
            Dictionary of adjustment factors
        """
        adjustments = {
            EnhancedRegimeType.BULL: {
                'position_size_multiplier': 1.2,
                'buy_threshold_adjustment': -10,
                'sell_threshold_adjustment': 10,
                'stop_loss_multiplier': 1.0,
                'take_profit_multiplier': 1.2
            },
            EnhancedRegimeType.BEAR: {
                'position_size_multiplier': 0.8,
                'buy_threshold_adjustment': 10,
                'sell_threshold_adjustment': -10,
                'stop_loss_multiplier': 0.8,
                'take_profit_multiplier': 1.0
            },
            EnhancedRegimeType.NEUTRAL: {
                'position_size_multiplier': 1.0,
                'buy_threshold_adjustment': 0,
                'sell_threshold_adjustment': 0,
                'stop_loss_multiplier': 1.0,
                'take_profit_multiplier': 1.0
            },
            EnhancedRegimeType.PANIC: {
                'position_size_multiplier': 0.5,
                'buy_threshold_adjustment': 20,
                'sell_threshold_adjustment': -20,
                'stop_loss_multiplier': 0.5,
                'take_profit_multiplier': 0.8
            }
        }
        
        return adjustments[regime]
