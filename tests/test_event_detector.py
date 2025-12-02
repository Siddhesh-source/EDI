"""Unit tests for the Event Detector module."""

import pytest
from datetime import datetime

from src.events import EventDetector
from src.shared.models import Article, EventType


class TestEventDetector:
    """Test suite for EventDetector class."""
    
    @pytest.fixture
    def detector(self):
        """Create event detector instance."""
        return EventDetector(high_severity_threshold=0.7)
    
    @pytest.fixture
    def sample_article(self):
        """Create sample article."""
        return Article(
            id="test_article",
            title="Test Article",
            content="Test content",
            source="Test Source",
            published_at=datetime.now(),
            symbols=["TEST"]
        )
    
    def test_detector_initialization(self, detector):
        """Test detector initializes correctly."""
        assert detector.high_severity_threshold == 0.7
        assert detector.redis_client is not None
    
    def test_earnings_event_detection(self, detector):
        """Test detection of earnings events."""
        article = Article(
            id="earnings_article",
            title="Company Reports Quarterly Earnings",
            content="The company announced quarterly earnings with strong revenue growth.",
            source="Financial Times",
            published_at=datetime.now(),
            symbols=["COMP"]
        )
        
        events = detector.detect_events(article)
        
        assert len(events) > 0
        earnings_events = [e for e in events if e.event_type == EventType.EARNINGS]
        assert len(earnings_events) > 0
        
        event = earnings_events[0]
        assert event.article_id == article.id
        assert 0.0 <= event.severity <= 1.0
        assert len(event.keywords) > 0
    
    def test_merger_event_detection(self, detector):
        """Test detection of merger events."""
        article = Article(
            id="merger_article",
            title="Companies Announce Merger",
            content="Two companies announced plans to merge operations.",
            source="WSJ",
            published_at=datetime.now(),
            symbols=["A", "B"]
        )
        
        events = detector.detect_events(article)
        
        merger_events = [e for e in events if e.event_type == EventType.MERGER]
        assert len(merger_events) > 0
        assert merger_events[0].severity >= 0.7  # Mergers have high base severity
    
    def test_acquisition_event_detection(self, detector):
        """Test detection of acquisition events."""
        article = Article(
            id="acquisition_article",
            title="Company Announces Acquisition",
            content="The company announced plans to acquire a competitor.",
            source="Bloomberg",
            published_at=datetime.now(),
            symbols=["COMP"]
        )
        
        events = detector.detect_events(article)
        
        acquisition_events = [e for e in events if e.event_type == EventType.ACQUISITION]
        assert len(acquisition_events) > 0
    
    def test_bankruptcy_event_detection(self, detector):
        """Test detection of bankruptcy events."""
        article = Article(
            id="bankruptcy_article",
            title="Company Files for Bankruptcy",
            content="The company filed for Chapter 11 bankruptcy protection.",
            source="Reuters",
            published_at=datetime.now(),
            symbols=["CORP"]
        )
        
        events = detector.detect_events(article)
        
        bankruptcy_events = [e for e in events if e.event_type == EventType.BANKRUPTCY]
        assert len(bankruptcy_events) > 0
        assert bankruptcy_events[0].severity >= 0.9  # Bankruptcy has highest base severity
    
    def test_regulatory_event_detection(self, detector):
        """Test detection of regulatory events."""
        article = Article(
            id="regulatory_article",
            title="SEC Launches Investigation",
            content="The SEC announced an investigation into potential violations.",
            source="CNBC",
            published_at=datetime.now(),
            symbols=["CORP"]
        )
        
        events = detector.detect_events(article)
        
        regulatory_events = [e for e in events if e.event_type == EventType.REGULATORY]
        assert len(regulatory_events) > 0
    
    def test_product_launch_event_detection(self, detector):
        """Test detection of product launch events."""
        article = Article(
            id="product_article",
            title="Company Launches New Product Innovation",
            content="The company will launch and unveil a new product line with major innovation today.",
            source="TechCrunch",
            published_at=datetime.now(),
            symbols=["TECH"]
        )
        
        events = detector.detect_events(article)
        
        product_events = [e for e in events if e.event_type == EventType.PRODUCT_LAUNCH]
        assert len(product_events) > 0
    
    def test_leadership_change_event_detection(self, detector):
        """Test detection of leadership change events."""
        article = Article(
            id="leadership_article",
            title="CEO Announces Resignation",
            content="The CEO announced his resignation effective next month.",
            source="WSJ",
            published_at=datetime.now(),
            symbols=["CORP"]
        )
        
        events = detector.detect_events(article)
        
        leadership_events = [e for e in events if e.event_type == EventType.LEADERSHIP_CHANGE]
        assert len(leadership_events) > 0
    
    def test_multiple_events_in_article(self, detector):
        """Test detection of multiple events in a single article."""
        article = Article(
            id="multi_article",
            title="CEO Resigns Amid Regulatory Investigation",
            content="The CEO resigned following an SEC investigation into earnings reports.",
            source="Financial Times",
            published_at=datetime.now(),
            symbols=["CORP"]
        )
        
        events = detector.detect_events(article)
        
        # Should detect multiple event types
        assert len(events) >= 2
        
        event_types = {e.event_type for e in events}
        assert EventType.LEADERSHIP_CHANGE in event_types
        assert EventType.REGULATORY in event_types or EventType.EARNINGS in event_types
    
    def test_severity_bounds(self, detector):
        """Test that severity scores are within bounds [0.0, 1.0]."""
        article = Article(
            id="severity_article",
            title="Major Unprecedented Massive Merger Announced",
            content="In a shocking historic record-breaking deal, companies merge.",
            source="WSJ",
            published_at=datetime.now(),
            symbols=["A", "B"]
        )
        
        events = detector.detect_events(article)
        
        for event in events:
            assert 0.0 <= event.severity <= 1.0
    
    def test_high_severity_modifiers(self, detector):
        """Test that high severity modifiers increase severity."""
        article_high = Article(
            id="high_mod_article",
            title="Major Unprecedented Merger",
            content="A massive historic merger was announced.",
            source="WSJ",
            published_at=datetime.now(),
            symbols=["A", "B"]
        )
        
        article_normal = Article(
            id="normal_article",
            title="Merger Announced",
            content="A merger was announced.",
            source="WSJ",
            published_at=datetime.now(),
            symbols=["C", "D"]
        )
        
        events_high = detector.detect_events(article_high)
        events_normal = detector.detect_events(article_normal)
        
        # High modifier article should have higher severity
        if events_high and events_normal:
            high_severity = max(e.severity for e in events_high if e.event_type == EventType.MERGER)
            normal_severity = max(e.severity for e in events_normal if e.event_type == EventType.MERGER)
            assert high_severity >= normal_severity
    
    def test_low_severity_modifiers(self, detector):
        """Test that low severity modifiers decrease severity."""
        article_low = Article(
            id="low_mod_article",
            title="Minor Routine Merger Expected",
            content="A small planned merger was announced.",
            source="WSJ",
            published_at=datetime.now(),
            symbols=["A", "B"]
        )
        
        article_normal = Article(
            id="normal_article2",
            title="Merger Announced",
            content="A merger was announced.",
            source="WSJ",
            published_at=datetime.now(),
            symbols=["C", "D"]
        )
        
        events_low = detector.detect_events(article_low)
        events_normal = detector.detect_events(article_normal)
        
        # Low modifier article should have lower or equal severity
        if events_low and events_normal:
            low_severity = min(e.severity for e in events_low if e.event_type == EventType.MERGER)
            normal_severity = min(e.severity for e in events_normal if e.event_type == EventType.MERGER)
            assert low_severity <= normal_severity
    
    def test_high_priority_flag(self, detector):
        """Test that high-priority events are flagged correctly."""
        article = Article(
            id="bankruptcy_article2",
            title="Major Company Files for Bankruptcy",
            content="The company filed for bankruptcy.",
            source="Reuters",
            published_at=datetime.now(),
            symbols=["CORP"]
        )
        
        events = detector.detect_events(article)
        
        # Bankruptcy events should be high priority (severity >= 0.7)
        bankruptcy_events = [e for e in events if e.event_type == EventType.BANKRUPTCY]
        assert len(bankruptcy_events) > 0
        assert bankruptcy_events[0].severity >= detector.high_severity_threshold
    
    def test_no_events_in_neutral_article(self, detector):
        """Test that neutral articles with no event keywords return empty list."""
        article = Article(
            id="neutral_article",
            title="Market Commentary",
            content="The market showed mixed performance today with various stocks moving.",
            source="Market Watch",
            published_at=datetime.now(),
            symbols=["SPY"]
        )
        
        events = detector.detect_events(article)
        
        # Should detect no events or very few
        assert len(events) == 0 or all(e.severity < 0.5 for e in events)
    
    def test_event_id_uniqueness(self, detector):
        """Test that each event gets a unique ID."""
        article = Article(
            id="unique_article",
            title="CEO Resigns, Company Reports Earnings",
            content="The CEO resigned and the company reported quarterly earnings.",
            source="WSJ",
            published_at=datetime.now(),
            symbols=["CORP"]
        )
        
        events = detector.detect_events(article)
        
        if len(events) > 1:
            event_ids = [e.id for e in events]
            assert len(event_ids) == len(set(event_ids))  # All IDs should be unique
    
    def test_keyword_extraction(self, detector):
        """Test that keywords are properly extracted."""
        article = Article(
            id="keyword_article",
            title="Company Reports Quarterly Earnings",
            content="The quarterly earnings report showed strong revenue.",
            source="Financial Times",
            published_at=datetime.now(),
            symbols=["COMP"]
        )
        
        events = detector.detect_events(article)
        
        earnings_events = [e for e in events if e.event_type == EventType.EARNINGS]
        assert len(earnings_events) > 0
        
        event = earnings_events[0]
        assert len(event.keywords) > 0
        assert any(kw in ['earnings', 'quarterly', 'revenue', 'report'] for kw in event.keywords)
    
    def test_compute_severity_method(self, detector):
        """Test the compute_severity method directly."""
        keywords = ['earnings', 'quarterly', 'revenue']
        text = "major unprecedented earnings report with strong quarterly revenue"
        
        severity = detector.compute_severity(EventType.EARNINGS, keywords, text)
        
        assert 0.0 <= severity <= 1.0
        assert severity > 0.5  # Should be elevated due to high modifiers
    
    def test_process_article_returns_events(self, detector, sample_article):
        """Test that process_article returns list of events."""
        article = Article(
            id="process_article",
            title="Company Announces Merger",
            content="The company announced a merger with a competitor.",
            source="WSJ",
            published_at=datetime.now(),
            symbols=["COMP"]
        )
        
        events = detector.process_article(article)
        
        assert isinstance(events, list)
        # Note: Redis and DB operations may fail in test environment, but detection should work
        assert len(events) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
