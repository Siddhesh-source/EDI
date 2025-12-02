"""Signal aggregator for computing Composite Market Score (CMS) and generating trading signals."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict
from threading import Lock

from src.shared.models import (
    AggregatedData, CompositeMarketScore, Event, EventType, Explanation,
    MarketRegime, RegimeType, TradingSignalType,
    TechnicalSignals, TradingSignal, TechnicalSignalType
)
from src.shared.redis_client import RedisChannels, RedisClient, RedisSubscriber
from src.shared.config import settings
from src.database.connection import get_db_session
from src.database.repositories import TradingSignalRepository

logger = logging.getLogger(__name__)


class SignalAggregator:
    """
    Aggregates data from multiple sources and generates trading signals.
    
    Subscribes to Redis channels for sentiment, events, indicators, and regime data.
    Computes Composite Market Score (CMS) and generates BUY/SELL/HOLD signals.
    """
    
    def __init__(
        self,
        redis_client: RedisClient,
        weight_sentiment: float = None,
        weight_technical: float = None,
        weight_regime: float = None,
        buy_threshold: float = None,
        sell_threshold: float = None
    ):
        """
        Initialize signal aggregator.
        
        Args:
            redis_client: Redis client for pub/sub
            weight_sentiment: Weight for sentiment component (default from settings)
            weight_technical: Weight for technical component (default from settings)
            weight_regime: Weight for regime component (default from settings)
            buy_threshold: CMS threshold for BUY signal (default from settings)
            sell_threshold: CMS threshold for SELL signal (default from settings)
        """
        self.redis_client = redis_client
        self.subscriber: Optional[RedisSubscriber] = None
        
        # CMS weights (must sum to 1.0)
        self.weight_sentiment = weight_sentiment or settings.cms_weight_sentiment
        self.weight_technical = weight_technical or settings.cms_weight_technical
        self.weight_regime = weight_regime or settings.cms_weight_regime
        
        # Validate weights sum to 1.0
        total_weight = self.weight_sentiment + self.weight_technical + self.weight_regime
        if abs(total_weight - 1.0) > 0.001:
            logger.warning(f"CMS weights sum to {total_weight}, normalizing to 1.0")
            self.weight_sentiment /= total_weight
            self.weight_technical /= total_weight
            self.weight_regime /= total_weight
        
        # Signal thresholds
        self.buy_threshold = buy_threshold or settings.cms_buy_threshold
        self.sell_threshold = sell_threshold or settings.cms_sell_threshold
        
        # Data storage with thread-safe access
        self._lock = Lock()
        self._latest_sentiment: Optional[float] = None
        self._latest_technical: Optional[TechnicalSignals] = None
        self._latest_regime: Optional[MarketRegime] = None
        self._recent_events: List[Event] = []
        self._max_events = 10  # Keep last 10 events
        
        logger.info(
            f"Signal aggregator initialized with weights: "
            f"sentiment={self.weight_sentiment:.2f}, "
            f"technical={self.weight_technical:.2f}, "
            f"regime={self.weight_regime:.2f}"
        )
    
    def start(self):
        """Start subscribing to Redis channels."""
        self.subscriber = self.redis_client.create_subscriber()
        
        # Subscribe to all relevant channels
        channels = [
            RedisChannels.SENTIMENT,
            RedisChannels.EVENTS,
            RedisChannels.INDICATORS,
            RedisChannels.REGIME
        ]
        
        self.subscriber.subscribe(channels, self._handle_message)
        logger.info(f"Subscribed to channels: {channels}")
    
    async def listen(self):
        """Listen for messages and process them."""
        if self.subscriber is None:
            raise RuntimeError("Aggregator not started. Call start() first.")
        
        await self.subscriber.listen()
    
    def stop(self):
        """Stop listening and cleanup."""
        if self.subscriber:
            self.subscriber.stop()
            self.subscriber.close()
            logger.info("Signal aggregator stopped")
    
    def _handle_message(self, channel: str, data: Dict[str, Any]):
        """
        Handle incoming messages from Redis channels.
        
        Args:
            channel: Channel name
            data: Message data
        """
        try:
            if channel == RedisChannels.SENTIMENT:
                self._handle_sentiment(data)
            elif channel == RedisChannels.EVENTS:
                self._handle_event(data)
            elif channel == RedisChannels.INDICATORS:
                self._handle_indicators(data)
            elif channel == RedisChannels.REGIME:
                self._handle_regime(data)
            
            # After updating data, try to generate a signal
            self._try_generate_signal()
            
        except Exception as e:
            logger.error(f"Error handling message from {channel}: {e}", exc_info=True)
    
    def _handle_sentiment(self, data: Dict[str, Any]):
        """Handle sentiment score update."""
        with self._lock:
            self._latest_sentiment = float(data.get('score', 0.0))
            logger.debug(f"Updated sentiment score: {self._latest_sentiment}")
    
    def _handle_event(self, data: Dict[str, Any]):
        """Handle event detection."""
        with self._lock:
            try:
                event = Event(
                    id=data['id'],
                    article_id=data['article_id'],
                    event_type=EventType(data['event_type']),
                    severity=float(data['severity']),
                    keywords=data['keywords'],
                    timestamp=datetime.fromisoformat(data['timestamp'])
                )
                
                self._recent_events.append(event)
                
                # Keep only recent events
                if len(self._recent_events) > self._max_events:
                    self._recent_events = self._recent_events[-self._max_events:]
                
                logger.debug(f"Added event: {event.event_type.value} (severity={event.severity})")
            except Exception as e:
                logger.error(f"Error parsing event data: {e}")
    
    def _handle_indicators(self, data: Dict[str, Any]):
        """Handle technical indicator update."""
        with self._lock:
            try:
                self._latest_technical = TechnicalSignals(
                    rsi_signal=TechnicalSignalType(data['rsi_signal']),
                    macd_signal=TechnicalSignalType(data['macd_signal']),
                    bb_signal=TechnicalSignalType(data['bb_signal'])
                )
                logger.debug(f"Updated technical signals: {self._latest_technical}")
            except Exception as e:
                logger.error(f"Error parsing technical signals: {e}")
    
    def _handle_regime(self, data: Dict[str, Any]):
        """Handle market regime update."""
        with self._lock:
            try:
                self._latest_regime = MarketRegime(
                    regime_type=RegimeType(data['regime_type']),
                    confidence=float(data['confidence']),
                    volatility=float(data['volatility']),
                    trend_strength=float(data['trend_strength']),
                    timestamp=datetime.fromisoformat(data['timestamp'])
                )
                logger.debug(f"Updated regime: {self._latest_regime.regime_type.value}")
            except Exception as e:
                logger.error(f"Error parsing regime data: {e}")
    
    def _try_generate_signal(self):
        """Try to generate a trading signal if all data is available."""
        with self._lock:
            # Check if we have all required data
            if self._latest_sentiment is None:
                logger.debug("Cannot generate signal: missing sentiment data")
                return
            
            if self._latest_technical is None:
                logger.debug("Cannot generate signal: missing technical data")
                return
            
            if self._latest_regime is None:
                logger.debug("Cannot generate signal: missing regime data")
                return
            
            # Aggregate data
            aggregated = AggregatedData(
                sentiment_score=self._latest_sentiment,
                technical_signals=self._latest_technical,
                regime=self._latest_regime,
                events=self._recent_events.copy(),
                timestamp=datetime.now()
            )
        
        # Generate signal (outside lock to avoid blocking)
        try:
            signal = self.generate_signal(aggregated)
            
            # Publish to Redis
            self._publish_signal(signal)
            
            # Store in database
            self._store_signal(signal)
            
            logger.info(
                f"Generated {signal.signal_type.value.upper()} signal "
                f"(CMS={signal.cms.score:.2f})"
            )
        except Exception as e:
            logger.error(f"Error generating signal: {e}", exc_info=True)
    
    def aggregate_data(self) -> Optional[AggregatedData]:
        """
        Get current aggregated data.
        
        Returns:
            AggregatedData if all components available, None otherwise
        """
        with self._lock:
            if (self._latest_sentiment is None or 
                self._latest_technical is None or 
                self._latest_regime is None):
                return None
            
            return AggregatedData(
                sentiment_score=self._latest_sentiment,
                technical_signals=self._latest_technical,
                regime=self._latest_regime,
                events=self._recent_events.copy(),
                timestamp=datetime.now()
            )
    
    def compute_cms(self, data: AggregatedData) -> CompositeMarketScore:
        """
        Compute Composite Market Score from aggregated data.
        
        Args:
            data: Aggregated data from all sources
            
        Returns:
            CompositeMarketScore with normalized score in [-100, 100]
        """
        # Sentiment component: already in [-1, 1] range
        sentiment_normalized = data.sentiment_score
        
        # Technical component: convert signals to numeric score
        technical_normalized = self._normalize_technical_signals(data.technical_signals)
        
        # Regime component: convert regime to numeric score
        regime_normalized = self._normalize_regime(data.regime)
        
        # Compute weighted CMS
        cms_score = (
            self.weight_sentiment * sentiment_normalized +
            self.weight_technical * technical_normalized +
            self.weight_regime * regime_normalized
        ) * 100  # Scale to [-100, 100]
        
        # Ensure bounds
        cms_score = max(-100.0, min(100.0, cms_score))
        
        return CompositeMarketScore(
            score=cms_score,
            sentiment_component=sentiment_normalized * 100,
            technical_component=technical_normalized * 100,
            regime_component=regime_normalized * 100,
            weights={
                'sentiment': self.weight_sentiment,
                'technical': self.weight_technical,
                'regime': self.weight_regime
            },
            timestamp=datetime.now()
        )
    
    def _normalize_technical_signals(self, signals: TechnicalSignals) -> float:
        """
        Normalize technical signals to [-1, 1] range.
        
        Args:
            signals: Technical signals from indicators
            
        Returns:
            Normalized score in [-1, 1]
        """
        score = 0.0
        count = 0
        
        # RSI signals
        if signals.rsi_signal == TechnicalSignalType.OVERSOLD:
            score += 1.0  # Bullish
            count += 1
        elif signals.rsi_signal == TechnicalSignalType.OVERBOUGHT:
            score -= 1.0  # Bearish
            count += 1
        elif signals.rsi_signal == TechnicalSignalType.NEUTRAL:
            score += 0.0
            count += 1
        
        # MACD signals
        if signals.macd_signal == TechnicalSignalType.BULLISH_CROSS:
            score += 1.0
            count += 1
        elif signals.macd_signal == TechnicalSignalType.BEARISH_CROSS:
            score -= 1.0
            count += 1
        elif signals.macd_signal == TechnicalSignalType.NEUTRAL:
            score += 0.0
            count += 1
        
        # Bollinger Bands signals
        if signals.bb_signal == TechnicalSignalType.LOWER_BREACH:
            score += 1.0  # Bullish (oversold)
            count += 1
        elif signals.bb_signal == TechnicalSignalType.UPPER_BREACH:
            score -= 1.0  # Bearish (overbought)
            count += 1
        elif signals.bb_signal == TechnicalSignalType.NEUTRAL:
            score += 0.0
            count += 1
        
        # Average the signals
        return score / count if count > 0 else 0.0
    
    def _normalize_regime(self, regime: MarketRegime) -> float:
        """
        Normalize market regime to [-1, 1] range.
        
        Args:
            regime: Market regime classification
            
        Returns:
            Normalized score in [-1, 1]
        """
        # Base score from regime type
        regime_scores = {
            RegimeType.TRENDING_UP: 1.0,
            RegimeType.TRENDING_DOWN: -1.0,
            RegimeType.RANGING: 0.0,
            RegimeType.VOLATILE: -0.3,  # Slightly bearish
            RegimeType.CALM: 0.2  # Slightly bullish
        }
        
        base_score = regime_scores.get(regime.regime_type, 0.0)
        
        # Weight by confidence
        return base_score * regime.confidence
    
    def generate_signal(self, data: AggregatedData) -> TradingSignal:
        """
        Generate trading signal from aggregated data.
        
        Args:
            data: Aggregated data from all sources
            
        Returns:
            TradingSignal with type, CMS, and explanation
        """
        # Compute CMS
        cms = self.compute_cms(data)
        
        # Determine signal type based on thresholds
        if cms.score > self.buy_threshold:
            signal_type = TradingSignalType.BUY
        elif cms.score < self.sell_threshold:
            signal_type = TradingSignalType.SELL
        else:
            signal_type = TradingSignalType.HOLD
        
        # Generate explanation
        explanation = self.create_explanation(data, cms, signal_type)
        
        # Compute confidence (based on regime confidence and signal strength)
        confidence = self._compute_confidence(cms, data.regime)
        
        return TradingSignal(
            signal_type=signal_type,
            cms=cms,
            confidence=confidence,
            explanation=explanation,
            timestamp=datetime.now()
        )
    
    def _compute_confidence(self, cms: CompositeMarketScore, regime: MarketRegime) -> float:
        """
        Compute confidence score for the signal.
        
        Args:
            cms: Composite Market Score
            regime: Market regime
            
        Returns:
            Confidence score in [0, 1]
        """
        # Base confidence from CMS strength
        cms_strength = abs(cms.score) / 100.0
        
        # Weight by regime confidence
        confidence = (cms_strength + regime.confidence) / 2.0
        
        return min(1.0, max(0.0, confidence))
    
    def create_explanation(
        self,
        data: AggregatedData,
        cms: CompositeMarketScore,
        signal_type: TradingSignalType
    ) -> Explanation:
        """
        Create detailed explanation for trading signal.
        
        Args:
            data: Aggregated data
            cms: Composite Market Score
            signal_type: Generated signal type
            
        Returns:
            Explanation with detailed breakdown
        """
        # Summary
        summary = (
            f"{signal_type.value.upper()} signal generated with CMS of {cms.score:.2f}. "
            f"Sentiment: {cms.sentiment_component:.2f}, "
            f"Technical: {cms.technical_component:.2f}, "
            f"Regime: {cms.regime_component:.2f}"
        )
        
        # Sentiment details
        sentiment_details = self._explain_sentiment(data.sentiment_score)
        
        # Technical details
        technical_details = self._explain_technical(data.technical_signals)
        
        # Regime details
        regime_details = self._explain_regime(data.regime)
        
        # Event details
        event_details = self._explain_events(data.events)
        
        return Explanation(
            summary=summary,
            sentiment_details=sentiment_details,
            technical_details=technical_details,
            regime_details=regime_details,
            event_details=event_details,
            component_scores={
                'sentiment': cms.sentiment_component,
                'technical': cms.technical_component,
                'regime': cms.regime_component,
                'cms': cms.score
            }
        )
    
    def _explain_sentiment(self, score: float) -> str:
        """Generate explanation for sentiment component."""
        if score > 0.5:
            sentiment = "strongly positive"
        elif score > 0.2:
            sentiment = "moderately positive"
        elif score > -0.2:
            sentiment = "neutral"
        elif score > -0.5:
            sentiment = "moderately negative"
        else:
            sentiment = "strongly negative"
        
        return f"News sentiment is {sentiment} with a score of {score:.2f}"
    
    def _explain_technical(self, signals: TechnicalSignals) -> str:
        """Generate explanation for technical component."""
        details = []
        
        # RSI
        if signals.rsi_signal == TechnicalSignalType.OVERSOLD:
            details.append("RSI indicates oversold conditions (potential buy)")
        elif signals.rsi_signal == TechnicalSignalType.OVERBOUGHT:
            details.append("RSI indicates overbought conditions (potential sell)")
        else:
            details.append("RSI is in neutral territory")
        
        # MACD
        if signals.macd_signal == TechnicalSignalType.BULLISH_CROSS:
            details.append("MACD crossed above signal line (bullish)")
        elif signals.macd_signal == TechnicalSignalType.BEARISH_CROSS:
            details.append("MACD crossed below signal line (bearish)")
        else:
            details.append("MACD shows no clear crossover")
        
        # Bollinger Bands
        if signals.bb_signal == TechnicalSignalType.LOWER_BREACH:
            details.append("Price breached lower Bollinger Band (oversold)")
        elif signals.bb_signal == TechnicalSignalType.UPPER_BREACH:
            details.append("Price breached upper Bollinger Band (overbought)")
        else:
            details.append("Price is within Bollinger Bands")
        
        return ". ".join(details)
    
    def _explain_regime(self, regime: MarketRegime) -> str:
        """Generate explanation for regime component."""
        regime_desc = {
            RegimeType.TRENDING_UP: "upward trending",
            RegimeType.TRENDING_DOWN: "downward trending",
            RegimeType.RANGING: "range-bound",
            RegimeType.VOLATILE: "highly volatile",
            RegimeType.CALM: "calm with low volatility"
        }
        
        desc = regime_desc.get(regime.regime_type, "unknown")
        
        return (
            f"Market is {desc} with {regime.confidence:.1%} confidence. "
            f"Volatility: {regime.volatility:.2f}, "
            f"Trend strength: {regime.trend_strength:.2f}"
        )
    
    def _explain_events(self, events: List[Event]) -> str:
        """Generate explanation for recent events."""
        if not events:
            return "No significant market events detected recently"
        
        high_severity = [e for e in events if e.severity > 0.7]
        
        if high_severity:
            event_types = [e.event_type.value for e in high_severity]
            return (
                f"Detected {len(high_severity)} high-severity event(s): "
                f"{', '.join(event_types)}"
            )
        else:
            return f"Detected {len(events)} low-to-moderate severity event(s)"
    
    def _publish_signal(self, signal: TradingSignal):
        """Publish signal to Redis signals channel."""
        try:
            data = {
                'signal_type': signal.signal_type.value,
                'cms_score': signal.cms.score,
                'sentiment_component': signal.cms.sentiment_component,
                'technical_component': signal.cms.technical_component,
                'regime_component': signal.cms.regime_component,
                'confidence': signal.confidence,
                'explanation': {
                    'summary': signal.explanation.summary,
                    'sentiment_details': signal.explanation.sentiment_details,
                    'technical_details': signal.explanation.technical_details,
                    'regime_details': signal.explanation.regime_details,
                    'event_details': signal.explanation.event_details,
                    'component_scores': signal.explanation.component_scores
                },
                'timestamp': signal.timestamp.isoformat()
            }
            
            self.redis_client.publish(RedisChannels.SIGNALS, data)
            logger.debug(f"Published signal to Redis: {signal.signal_type.value}")
        except Exception as e:
            logger.error(f"Error publishing signal to Redis: {e}")
    
    def _store_signal(self, signal: TradingSignal):
        """Store signal in PostgreSQL database."""
        try:
            with get_db_session() as session:
                repo = TradingSignalRepository(session)
                
                # Convert to database model
                from src.database.models import TradingSignal as DBTradingSignal
                
                db_signal = DBTradingSignal(
                    signal_type=signal.signal_type.value,
                    cms_score=signal.cms.score,
                    sentiment_component=signal.cms.sentiment_component,
                    technical_component=signal.cms.technical_component,
                    regime_component=signal.cms.regime_component,
                    explanation={
                        'summary': signal.explanation.summary,
                        'sentiment_details': signal.explanation.sentiment_details,
                        'technical_details': signal.explanation.technical_details,
                        'regime_details': signal.explanation.regime_details,
                        'event_details': signal.explanation.event_details,
                        'component_scores': signal.explanation.component_scores,
                        'confidence': signal.confidence,
                        'weights': signal.cms.weights
                    },
                    timestamp=signal.timestamp
                )
                
                repo.create(db_signal)
                session.commit()
                logger.debug(f"Stored signal in database: {signal.signal_type.value}")
        except Exception as e:
            logger.error(f"Error storing signal in database: {e}")
