"""Event detector for identifying significant market events from news articles."""

import hashlib
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Set

from src.shared.models import Article, Event, EventType
from src.shared.redis_client import RedisChannels, get_redis_client
from src.database.connection import get_db_session
from src.database.repositories import EventRepository

logger = logging.getLogger(__name__)


class EventDetector:
    """Keyword-based event detector for market events."""
    
    # Event keyword dictionaries
    EVENT_KEYWORDS: Dict[EventType, Set[str]] = {
        EventType.EARNINGS: {
            'earnings', 'quarterly', 'revenue', 'profit', 'eps', 'guidance',
            'forecast', 'results', 'report', 'beat', 'miss', 'outlook',
            'quarter', 'q1', 'q2', 'q3', 'q4', 'fiscal', 'annual'
        },
        EventType.MERGER: {
            'merger', 'merge', 'merging', 'consolidation', 'combine',
            'joining', 'unification', 'amalgamation'
        },
        EventType.ACQUISITION: {
            'acquisition', 'acquire', 'acquiring', 'takeover', 'buyout',
            'purchase', 'bought', 'deal', 'transaction', 'bid'
        },
        EventType.BANKRUPTCY: {
            'bankruptcy', 'bankrupt', 'insolvency', 'insolvent', 'liquidation',
            'chapter 11', 'chapter 7', 'administration', 'receivership',
            'default', 'debt restructuring'
        },
        EventType.REGULATORY: {
            'regulatory', 'regulation', 'sec', 'fda', 'ftc', 'doj',
            'investigation', 'probe', 'lawsuit', 'litigation', 'fine',
            'penalty', 'settlement', 'compliance', 'violation', 'approval',
            'clearance', 'sanction', 'enforcement'
        },
        EventType.PRODUCT_LAUNCH: {
            'launch', 'release', 'unveil', 'introduce', 'debut', 'announce',
            'new product', 'innovation', 'rollout', 'product line'
        },
        EventType.LEADERSHIP_CHANGE: {
            'ceo', 'cfo', 'coo', 'cto', 'president', 'chairman', 'director',
            'executive', 'resign', 'resignation', 'appoint', 'appointment',
            'hire', 'departure', 'succession', 'leadership', 'management change'
        }
    }
    
    # Severity modifiers - words that increase event severity
    HIGH_SEVERITY_MODIFIERS = {
        'major', 'significant', 'massive', 'huge', 'unprecedented',
        'historic', 'record', 'largest', 'biggest', 'critical',
        'emergency', 'urgent', 'immediate', 'shocking', 'surprise',
        'unexpected', 'dramatic', 'substantial', 'considerable'
    }
    
    # Severity modifiers - words that decrease event severity
    LOW_SEVERITY_MODIFIERS = {
        'minor', 'small', 'slight', 'modest', 'limited', 'minimal',
        'routine', 'expected', 'anticipated', 'planned', 'scheduled'
    }
    
    def __init__(self, high_severity_threshold: float = 0.7):
        """
        Initialize event detector.
        
        Args:
            high_severity_threshold: Threshold for high-priority event alerts
        """
        self.high_severity_threshold = high_severity_threshold
        self.redis_client = get_redis_client()
        
        logger.info(f"Event detector initialized with threshold: {high_severity_threshold}")
    
    def detect_events(self, article: Article) -> List[Event]:
        """
        Detect all events in an article.
        
        Args:
            article: Article to scan for events
            
        Returns:
            List of detected events
        """
        # Combine title and content for analysis
        text = f"{article.title} {article.content}".lower()
        
        # Tokenize into words
        words = set(re.findall(r'\b\w+\b', text))
        
        events = []
        
        # Check for each event type
        for event_type, keywords in self.EVENT_KEYWORDS.items():
            # Find matching keywords
            matched_keywords = words.intersection(keywords)
            
            if matched_keywords:
                # Create event
                event = self._create_event(
                    article=article,
                    event_type=event_type,
                    keywords=list(matched_keywords),
                    text=text
                )
                events.append(event)
                
                logger.debug(
                    f"Detected {event_type.value} event in article {article.id}: "
                    f"severity={event.severity:.2f}, keywords={matched_keywords}"
                )
        
        if events:
            logger.info(f"Detected {len(events)} events in article {article.id}")
        
        return events
    
    def _create_event(
        self,
        article: Article,
        event_type: EventType,
        keywords: List[str],
        text: str
    ) -> Event:
        """
        Create an event with computed severity.
        
        Args:
            article: Source article
            event_type: Type of event detected
            keywords: Matched keywords
            text: Article text (lowercase)
            
        Returns:
            Event object with computed severity
        """
        # Generate unique event ID
        event_id = hashlib.md5(
            f"{article.id}_{event_type.value}_{datetime.now().isoformat()}".encode()
        ).hexdigest()
        
        # Compute severity
        severity = self.compute_severity(event_type, keywords, text)
        
        event = Event(
            id=event_id,
            article_id=article.id,
            event_type=event_type,
            severity=severity,
            keywords=keywords,
            timestamp=datetime.now()
        )
        
        return event
    
    def compute_severity(
        self,
        event_type: EventType,
        keywords: List[str],
        text: str
    ) -> float:
        """
        Compute severity score for an event.
        
        Severity is based on:
        1. Base severity by event type
        2. Number of matching keywords (more = higher severity)
        3. Presence of severity modifiers
        
        Args:
            event_type: Type of event
            keywords: Matched keywords for this event
            text: Article text (lowercase)
            
        Returns:
            Severity score between 0.0 and 1.0
        """
        # Base severity by event type
        base_severity = {
            EventType.EARNINGS: 0.5,
            EventType.MERGER: 0.7,
            EventType.ACQUISITION: 0.7,
            EventType.BANKRUPTCY: 0.9,
            EventType.REGULATORY: 0.6,
            EventType.PRODUCT_LAUNCH: 0.4,
            EventType.LEADERSHIP_CHANGE: 0.5
        }
        
        severity = base_severity.get(event_type, 0.5)
        
        # Adjust based on number of keywords (more keywords = higher confidence/severity)
        keyword_factor = min(len(keywords) / 5.0, 0.2)  # Max +0.2
        severity += keyword_factor
        
        # Check for severity modifiers in text
        text_words = set(re.findall(r'\b\w+\b', text))
        
        high_modifiers = text_words.intersection(self.HIGH_SEVERITY_MODIFIERS)
        low_modifiers = text_words.intersection(self.LOW_SEVERITY_MODIFIERS)
        
        # Adjust severity based on modifiers
        if high_modifiers:
            severity += 0.15 * min(len(high_modifiers), 2)  # Max +0.3
        
        if low_modifiers:
            severity -= 0.1 * min(len(low_modifiers), 2)  # Max -0.2
        
        # Ensure severity is within bounds [0.0, 1.0]
        severity = max(0.0, min(1.0, severity))
        
        return severity
    
    def publish_to_redis(self, event: Event) -> bool:
        """
        Publish event to Redis events channel.
        
        High-severity events (>= threshold) are published as high-priority alerts.
        
        Args:
            event: Event to publish
            
        Returns:
            True if published successfully, False otherwise
        """
        data = {
            'id': event.id,
            'article_id': event.article_id,
            'event_type': event.event_type.value,
            'severity': event.severity,
            'keywords': event.keywords,
            'timestamp': event.timestamp.isoformat(),
            'high_priority': event.severity >= self.high_severity_threshold
        }
        
        success = self.redis_client.publish(RedisChannels.EVENTS, data)
        
        if success:
            priority = "HIGH-PRIORITY" if event.severity >= self.high_severity_threshold else "normal"
            logger.debug(
                f"Published {priority} event to Redis: {event.event_type.value} "
                f"(severity={event.severity:.2f})"
            )
        else:
            logger.warning(f"Failed to publish event to Redis: {event.id}")
        
        return success
    
    def store_event(self, event: Event) -> bool:
        """
        Store event in PostgreSQL.
        
        Args:
            event: Event to store
            
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            with get_db_session() as session:
                event_repo = EventRepository(session)
                
                # Store event
                event_repo.create({
                    'id': event.id,
                    'article_id': event.article_id,
                    'event_type': event.event_type.value,
                    'severity': float(event.severity),
                    'keywords': event.keywords,
                    'timestamp': event.timestamp
                })
                
                session.commit()
                logger.debug(f"Stored event: {event.id}")
                return True
        
        except Exception as e:
            logger.error(f"Error storing event {event.id}: {e}")
            return False
    
    def process_article(self, article: Article) -> List[Event]:
        """
        Process an article: detect events, publish to Redis, store in DB.
        
        Args:
            article: Article to process
            
        Returns:
            List of detected events
        """
        try:
            # Detect events
            events = self.detect_events(article)
            
            # Process each event
            for event in events:
                # Publish to Redis
                self.publish_to_redis(event)
                
                # Store in database
                self.store_event(event)
            
            return events
        
        except Exception as e:
            logger.error(f"Error processing article {article.id} for events: {e}")
            return []
    
    def get_high_severity_events(self, limit: Optional[int] = None) -> List[Event]:
        """
        Get high-severity events from database.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of high-severity events
        """
        try:
            with get_db_session() as session:
                event_repo = EventRepository(session)
                db_events = event_repo.get_high_severity_events(
                    severity_threshold=self.high_severity_threshold,
                    limit=limit
                )
                
                # Convert to Event objects
                events = []
                for db_event in db_events:
                    event = Event(
                        id=db_event.id,
                        article_id=db_event.article_id,
                        event_type=EventType(db_event.event_type),
                        severity=float(db_event.severity),
                        keywords=db_event.keywords,
                        timestamp=db_event.timestamp
                    )
                    events.append(event)
                
                return events
        
        except Exception as e:
            logger.error(f"Error getting high severity events: {e}")
            return []
