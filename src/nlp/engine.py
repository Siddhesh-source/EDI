"""
Enhanced NLP Engine for Trading System
Provides Sentiment Index (SI), Event Shock Factor (ESF), and sliding window smoothing
"""

import logging
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import json

from src.shared.models import Article, SentimentScore, Event
from src.sentiment.analyzer import SentimentAnalyzer
from src.events.detector import EventDetector
from src.shared.redis_client import RedisChannels, get_redis_client
from src.database.connection import get_db_session
from src.database.repositories import SentimentScoreRepository, EventRepository

logger = logging.getLogger(__name__)


@dataclass
class SentimentIndex:
    """
    Sentiment Index (SI) - Aggregated sentiment measure
    
    SI combines raw sentiment scores with confidence weighting
    and temporal decay for a robust sentiment measure.
    """
    raw_score: float  # Raw sentiment score [-1.0, 1.0]
    weighted_score: float  # Confidence-weighted score [-1.0, 1.0]
    smoothed_score: float  # Time-smoothed score [-1.0, 1.0]
    confidence: float  # Overall confidence [0.0, 1.0]
    article_count: int  # Number of articles in calculation
    positive_ratio: float  # Ratio of positive articles [0.0, 1.0]
    negative_ratio: float  # Ratio of negative articles [0.0, 1.0]
    neutral_ratio: float  # Ratio of neutral articles [0.0, 1.0]
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class EventShockFactor:
    """
    Event Shock Factor (ESF) - Measure of event impact
    
    ESF quantifies the potential market impact of detected events
    based on severity, recency, and event type clustering.
    """
    total_shock: float  # Total shock factor [0.0, 1.0]
    event_count: int  # Number of events
    high_severity_count: int  # Number of high-severity events
    event_type_distribution: Dict[str, int]  # Count by event type
    max_severity: float  # Maximum event severity
    avg_severity: float  # Average event severity
    recency_factor: float  # Time decay factor [0.0, 1.0]
    dominant_event_type: Optional[str]  # Most common event type
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class NLPOutput:
    """
    Complete NLP Engine Output
    
    Combines sentiment analysis, event detection, and derived metrics
    into a single comprehensive output structure.
    """
    sentiment_index: SentimentIndex
    event_shock_factor: EventShockFactor
    raw_sentiments: List[Dict]  # Individual sentiment scores
    detected_events: List[Dict]  # Individual events
    market_mood: str  # Overall market mood: bullish/bearish/neutral
    risk_level: str  # Risk level: low/medium/high/critical
    explanation: str  # Human-readable explanation
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'sentiment_index': self.sentiment_index.to_dict(),
            'event_shock_factor': self.event_shock_factor.to_dict(),
            'raw_sentiments': self.raw_sentiments,
            'detected_events': self.detected_events,
            'market_mood': self.market_mood,
            'risk_level': self.risk_level,
            'explanation': self.explanation,
            'timestamp': self.timestamp.isoformat()
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class EnhancedNLPEngine:
    """
    Enhanced NLP Engine with advanced analytics
    
    Features:
    - Sentiment Index (SI) calculation with confidence weighting
    - Event Shock Factor (ESF) computation
    - Sliding window sentiment smoothing
    - Temporal decay for recency weighting
    - Market mood classification
    - Risk level assessment
    """
    
    def __init__(
        self,
        sentiment_analyzer: Optional[SentimentAnalyzer] = None,
        event_detector: Optional[EventDetector] = None,
        window_size: int = 20,  # Number of articles for sliding window
        decay_hours: float = 24.0,  # Hours for temporal decay
        high_severity_threshold: float = 0.7
    ):
        """
        Initialize enhanced NLP engine.
        
        Args:
            sentiment_analyzer: Sentiment analyzer instance
            event_detector: Event detector instance
            window_size: Number of articles for sliding window smoothing
            decay_hours: Hours for temporal decay calculation
            high_severity_threshold: Threshold for high-severity events
        """
        self.sentiment_analyzer = sentiment_analyzer or SentimentAnalyzer()
        self.event_detector = event_detector or EventDetector(high_severity_threshold)
        self.window_size = window_size
        self.decay_hours = decay_hours
        self.high_severity_threshold = high_severity_threshold
        
        # Sliding window for sentiment smoothing
        self._sentiment_window: deque = deque(maxlen=window_size)
        
        # Redis client for publishing
        self.redis_client = get_redis_client()
        
        logger.info(
            f"Enhanced NLP Engine initialized: "
            f"window_size={window_size}, decay_hours={decay_hours}"
        )
    
    def compute_sentiment_index(
        self,
        sentiments: List[SentimentScore],
        use_smoothing: bool = True
    ) -> SentimentIndex:
        """
        Compute Sentiment Index (SI) from sentiment scores.
        
        SI Calculation:
        1. Raw score: Simple average of sentiment scores
        2. Weighted score: Confidence-weighted average
        3. Smoothed score: Sliding window smoothed (if enabled)
        
        Args:
            sentiments: List of sentiment scores
            use_smoothing: Whether to apply sliding window smoothing
            
        Returns:
            SentimentIndex with computed metrics
        """
        if not sentiments:
            return SentimentIndex(
                raw_score=0.0,
                weighted_score=0.0,
                smoothed_score=0.0,
                confidence=0.0,
                article_count=0,
                positive_ratio=0.0,
                negative_ratio=0.0,
                neutral_ratio=0.0,
                timestamp=datetime.now()
            )
        
        # Calculate raw score (simple average)
        raw_score = sum(s.score for s in sentiments) / len(sentiments)
        
        # Calculate weighted score (confidence-weighted average)
        total_weight = sum(s.confidence for s in sentiments)
        if total_weight > 0:
            weighted_score = sum(s.score * s.confidence for s in sentiments) / total_weight
        else:
            weighted_score = raw_score
        
        # Calculate smoothed score using sliding window
        if use_smoothing:
            # Add current weighted score to window
            self._sentiment_window.append(weighted_score)
            # Compute exponentially weighted moving average
            smoothed_score = self._compute_ewma(list(self._sentiment_window))
        else:
            smoothed_score = weighted_score
        
        # Calculate overall confidence
        avg_confidence = sum(s.confidence for s in sentiments) / len(sentiments)
        
        # Calculate sentiment distribution
        positive_count = sum(1 for s in sentiments if s.score > 0.1)
        negative_count = sum(1 for s in sentiments if s.score < -0.1)
        neutral_count = len(sentiments) - positive_count - negative_count
        
        total = len(sentiments)
        positive_ratio = positive_count / total
        negative_ratio = negative_count / total
        neutral_ratio = neutral_count / total
        
        return SentimentIndex(
            raw_score=raw_score,
            weighted_score=weighted_score,
            smoothed_score=smoothed_score,
            confidence=avg_confidence,
            article_count=len(sentiments),
            positive_ratio=positive_ratio,
            negative_ratio=negative_ratio,
            neutral_ratio=neutral_ratio,
            timestamp=datetime.now()
        )
    
    def compute_event_shock_factor(
        self,
        events: List[Event],
        apply_recency_decay: bool = True
    ) -> EventShockFactor:
        """
        Compute Event Shock Factor (ESF) from detected events.
        
        ESF Calculation:
        1. Base shock: Weighted sum of event severities
        2. Recency factor: Temporal decay based on event age
        3. Clustering bonus: Additional impact for multiple events
        
        Args:
            events: List of detected events
            apply_recency_decay: Whether to apply temporal decay
            
        Returns:
            EventShockFactor with computed metrics
        """
        if not events:
            return EventShockFactor(
                total_shock=0.0,
                event_count=0,
                high_severity_count=0,
                event_type_distribution={},
                max_severity=0.0,
                avg_severity=0.0,
                recency_factor=1.0,
                dominant_event_type=None,
                timestamp=datetime.now()
            )
        
        # Calculate event type distribution
        event_type_dist = {}
        for event in events:
            event_type = event.event_type.value
            event_type_dist[event_type] = event_type_dist.get(event_type, 0) + 1
        
        # Find dominant event type
        dominant_event_type = max(event_type_dist, key=event_type_dist.get) if event_type_dist else None
        
        # Calculate severity metrics
        severities = [e.severity for e in events]
        max_severity = max(severities)
        avg_severity = sum(severities) / len(severities)
        high_severity_count = sum(1 for s in severities if s >= self.high_severity_threshold)
        
        # Calculate recency factor (temporal decay)
        if apply_recency_decay:
            recency_factor = self._compute_recency_factor(events)
        else:
            recency_factor = 1.0
        
        # Calculate total shock
        # Base shock: weighted sum of severities
        base_shock = sum(severities) / len(severities)
        
        # Clustering bonus: more events = higher shock
        clustering_bonus = min(len(events) / 10.0, 0.3)  # Max +0.3
        
        # Apply recency factor
        total_shock = min((base_shock + clustering_bonus) * recency_factor, 1.0)
        
        return EventShockFactor(
            total_shock=total_shock,
            event_count=len(events),
            high_severity_count=high_severity_count,
            event_type_distribution=event_type_dist,
            max_severity=max_severity,
            avg_severity=avg_severity,
            recency_factor=recency_factor,
            dominant_event_type=dominant_event_type,
            timestamp=datetime.now()
        )
    
    def _compute_ewma(self, values: List[float], alpha: float = 0.3) -> float:
        """
        Compute Exponentially Weighted Moving Average.
        
        Args:
            values: List of values
            alpha: Smoothing factor [0, 1], higher = more weight on recent
            
        Returns:
            EWMA value
        """
        if not values:
            return 0.0
        
        ewma = values[0]
        for value in values[1:]:
            ewma = alpha * value + (1 - alpha) * ewma
        
        return ewma
    
    def _compute_recency_factor(self, events: List[Event]) -> float:
        """
        Compute recency factor based on event timestamps.
        
        Recent events have higher impact (factor closer to 1.0)
        Older events have lower impact (factor closer to 0.0)
        
        Args:
            events: List of events
            
        Returns:
            Recency factor [0.0, 1.0]
        """
        if not events:
            return 1.0
        
        now = datetime.now()
        
        # Calculate average age of events in hours
        ages = [(now - e.timestamp).total_seconds() / 3600 for e in events]
        avg_age = sum(ages) / len(ages)
        
        # Exponential decay: factor = exp(-age / decay_hours)
        import math
        recency_factor = math.exp(-avg_age / self.decay_hours)
        
        return recency_factor
    
    def classify_market_mood(self, si: SentimentIndex, esf: EventShockFactor) -> str:
        """
        Classify overall market mood based on SI and ESF.
        
        Args:
            si: Sentiment Index
            esf: Event Shock Factor
            
        Returns:
            Market mood: 'bullish', 'bearish', or 'neutral'
        """
        # Use smoothed sentiment score for classification
        score = si.smoothed_score
        
        # Adjust for event shock
        if esf.total_shock > 0.5:
            # High shock can amplify sentiment
            if score > 0:
                score *= (1 + esf.total_shock * 0.5)
            else:
                score *= (1 + esf.total_shock * 0.5)
        
        # Classify
        if score > 0.2:
            return 'bullish'
        elif score < -0.2:
            return 'bearish'
        else:
            return 'neutral'
    
    def assess_risk_level(self, si: SentimentIndex, esf: EventShockFactor) -> str:
        """
        Assess risk level based on SI and ESF.
        
        Args:
            si: Sentiment Index
            esf: Event Shock Factor
            
        Returns:
            Risk level: 'low', 'medium', 'high', or 'critical'
        """
        # Risk factors
        sentiment_volatility = abs(si.smoothed_score)
        event_shock = esf.total_shock
        high_severity_ratio = esf.high_severity_count / max(esf.event_count, 1)
        
        # Compute risk score
        risk_score = (
            sentiment_volatility * 0.3 +
            event_shock * 0.5 +
            high_severity_ratio * 0.2
        )
        
        # Classify risk
        if risk_score < 0.3:
            return 'low'
        elif risk_score < 0.5:
            return 'medium'
        elif risk_score < 0.7:
            return 'high'
        else:
            return 'critical'
    
    def generate_explanation(
        self,
        si: SentimentIndex,
        esf: EventShockFactor,
        market_mood: str,
        risk_level: str
    ) -> str:
        """
        Generate human-readable explanation of NLP analysis.
        
        Args:
            si: Sentiment Index
            esf: Event Shock Factor
            market_mood: Market mood classification
            risk_level: Risk level assessment
            
        Returns:
            Explanation string
        """
        parts = []
        
        # Sentiment explanation
        parts.append(
            f"Market sentiment is {market_mood} with a smoothed score of {si.smoothed_score:.2f}. "
            f"Analysis based on {si.article_count} articles: "
            f"{si.positive_ratio*100:.0f}% positive, "
            f"{si.negative_ratio*100:.0f}% negative, "
            f"{si.neutral_ratio*100:.0f}% neutral."
        )
        
        # Event explanation
        if esf.event_count > 0:
            parts.append(
                f"Detected {esf.event_count} market events with total shock factor of {esf.total_shock:.2f}. "
                f"{esf.high_severity_count} high-severity events identified."
            )
            
            if esf.dominant_event_type:
                parts.append(f"Dominant event type: {esf.dominant_event_type}.")
        else:
            parts.append("No significant market events detected.")
        
        # Risk explanation
        parts.append(f"Overall risk level assessed as {risk_level}.")
        
        return " ".join(parts)
    
    def process_articles(
        self,
        articles: List[Article],
        use_smoothing: bool = True,
        apply_recency_decay: bool = True
    ) -> NLPOutput:
        """
        Process articles through complete NLP pipeline.
        
        Args:
            articles: List of articles to process
            use_smoothing: Whether to apply sliding window smoothing
            apply_recency_decay: Whether to apply temporal decay
            
        Returns:
            Complete NLP output with all metrics
        """
        # Analyze sentiment for all articles
        sentiments = []
        for article in articles:
            sentiment = self.sentiment_analyzer.analyze_sentiment(article)
            sentiments.append(sentiment)
        
        # Detect events in all articles
        all_events = []
        for article in articles:
            events = self.event_detector.detect_events(article)
            all_events.extend(events)
        
        # Compute Sentiment Index
        si = self.compute_sentiment_index(sentiments, use_smoothing)
        
        # Compute Event Shock Factor
        esf = self.compute_event_shock_factor(all_events, apply_recency_decay)
        
        # Classify market mood
        market_mood = self.classify_market_mood(si, esf)
        
        # Assess risk level
        risk_level = self.assess_risk_level(si, esf)
        
        # Generate explanation
        explanation = self.generate_explanation(si, esf, market_mood, risk_level)
        
        # Prepare raw data for output
        raw_sentiments = [
            {
                'article_id': s.article_id,
                'score': s.score,
                'confidence': s.confidence,
                'keywords_positive': s.keywords_positive,
                'keywords_negative': s.keywords_negative,
                'timestamp': s.timestamp.isoformat()
            }
            for s in sentiments
        ]
        
        detected_events = [
            {
                'id': e.id,
                'article_id': e.article_id,
                'event_type': e.event_type.value,
                'severity': e.severity,
                'keywords': e.keywords,
                'timestamp': e.timestamp.isoformat()
            }
            for e in all_events
        ]
        
        # Create output
        output = NLPOutput(
            sentiment_index=si,
            event_shock_factor=esf,
            raw_sentiments=raw_sentiments,
            detected_events=detected_events,
            market_mood=market_mood,
            risk_level=risk_level,
            explanation=explanation,
            timestamp=datetime.now()
        )
        
        logger.info(
            f"NLP processing complete: mood={market_mood}, risk={risk_level}, "
            f"SI={si.smoothed_score:.2f}, ESF={esf.total_shock:.2f}"
        )
        
        return output
    
    def publish_to_redis(self, output: NLPOutput) -> bool:
        """
        Publish NLP output to Redis.
        
        Args:
            output: NLP output to publish
            
        Returns:
            True if published successfully
        """
        try:
            # Publish to dedicated NLP channel
            success = self.redis_client.publish(
                'nlp_output',
                output.to_dict()
            )
            
            if success:
                logger.info("Published NLP output to Redis")
            else:
                logger.warning("Failed to publish NLP output to Redis")
            
            return success
        except Exception as e:
            logger.error(f"Error publishing NLP output: {e}")
            return False
    
    def get_historical_sentiment_index(
        self,
        hours: int = 24,
        symbol: Optional[str] = None
    ) -> List[SentimentIndex]:
        """
        Get historical Sentiment Index values.
        
        Args:
            hours: Hours of history to retrieve
            symbol: Optional symbol filter
            
        Returns:
            List of historical Sentiment Index values
        """
        try:
            with get_db_session() as session:
                repo = SentimentScoreRepository(session)
                
                # Get sentiments from last N hours
                start_time = datetime.now() - timedelta(hours=hours)
                sentiments_data = repo.get_by_timerange(start_time, datetime.now())
                
                # Group by hour and compute SI for each hour
                hourly_si = []
                current_hour_sentiments = []
                current_hour = None
                
                for sent_data in sentiments_data:
                    hour = sent_data.timestamp.replace(minute=0, second=0, microsecond=0)
                    
                    if current_hour is None:
                        current_hour = hour
                    
                    if hour == current_hour:
                        # Convert to SentimentScore object
                        sentiment = SentimentScore(
                            article_id=sent_data.article_id,
                            score=float(sent_data.score),
                            confidence=float(sent_data.confidence),
                            keywords_positive=sent_data.keywords_positive or [],
                            keywords_negative=sent_data.keywords_negative or [],
                            timestamp=sent_data.timestamp
                        )
                        current_hour_sentiments.append(sentiment)
                    else:
                        # Compute SI for completed hour
                        if current_hour_sentiments:
                            si = self.compute_sentiment_index(
                                current_hour_sentiments,
                                use_smoothing=False
                            )
                            hourly_si.append(si)
                        
                        # Start new hour
                        current_hour = hour
                        sentiment = SentimentScore(
                            article_id=sent_data.article_id,
                            score=float(sent_data.score),
                            confidence=float(sent_data.confidence),
                            keywords_positive=sent_data.keywords_positive or [],
                            keywords_negative=sent_data.keywords_negative or [],
                            timestamp=sent_data.timestamp
                        )
                        current_hour_sentiments = [sentiment]
                
                # Process last hour
                if current_hour_sentiments:
                    si = self.compute_sentiment_index(
                        current_hour_sentiments,
                        use_smoothing=False
                    )
                    hourly_si.append(si)
                
                return hourly_si
        
        except Exception as e:
            logger.error(f"Error getting historical sentiment index: {e}")
            return []
