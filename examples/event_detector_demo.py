"""Demo script for the Event Detector module."""

import asyncio
import logging
from datetime import datetime

from src.events import EventDetector
from src.shared.models import Article
from src.shared.logging_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


def demo_basic_detection():
    """Demonstrate basic event detection."""
    print("\n" + "="*80)
    print("DEMO 1: Basic Event Detection")
    print("="*80 + "\n")
    
    # Initialize detector
    detector = EventDetector(high_severity_threshold=0.7)
    
    # Sample articles with different event types
    articles = [
        Article(
            id="article1",
            title="Tech Giant Reports Record Quarterly Earnings",
            content="The company announced record quarterly earnings, beating analyst expectations "
                   "with revenue of $50 billion and EPS of $2.50. The strong results were driven "
                   "by robust demand across all product lines.",
            source="Financial Times",
            published_at=datetime.now(),
            symbols=["TECH"]
        ),
        Article(
            id="article2",
            title="Major Merger Announced: Company A to Acquire Company B",
            content="In a massive $10 billion deal, Company A announced plans to acquire Company B. "
                   "The acquisition is expected to create significant synergies and market leadership.",
            source="Wall Street Journal",
            published_at=datetime.now(),
            symbols=["CMPA", "CMPB"]
        ),
        Article(
            id="article3",
            title="Retail Chain Files for Bankruptcy",
            content="The struggling retail chain filed for Chapter 11 bankruptcy protection today, "
                   "citing mounting debt and declining sales. The company will liquidate all stores.",
            source="Reuters",
            published_at=datetime.now(),
            symbols=["RETAIL"]
        ),
        Article(
            id="article4",
            title="FDA Approves New Drug After Regulatory Review",
            content="Following a comprehensive regulatory review, the FDA has granted approval for "
                   "the new drug. This clearance opens up a significant market opportunity.",
            source="Bloomberg",
            published_at=datetime.now(),
            symbols=["PHARMA"]
        ),
        Article(
            id="article5",
            title="CEO Announces Resignation, New Leadership Appointed",
            content="The company's CEO announced his resignation today. The board has appointed "
                   "a new president who will take over executive leadership next month.",
            source="CNBC",
            published_at=datetime.now(),
            symbols=["CORP"]
        )
    ]
    
    # Process each article
    for article in articles:
        print(f"\nArticle: {article.title}")
        print(f"Source: {article.source}")
        print("-" * 80)
        
        events = detector.detect_events(article)
        
        if events:
            for event in events:
                priority = "🔴 HIGH PRIORITY" if event.severity >= 0.7 else "🟢 Normal"
                print(f"\n  {priority}")
                print(f"  Event Type: {event.event_type.value.upper()}")
                print(f"  Severity: {event.severity:.2f}")
                print(f"  Keywords: {', '.join(event.keywords)}")
        else:
            print("  No events detected")


def demo_multiple_events():
    """Demonstrate detection of multiple events in a single article."""
    print("\n" + "="*80)
    print("DEMO 2: Multiple Events in Single Article")
    print("="*80 + "\n")
    
    detector = EventDetector()
    
    # Article with multiple events
    article = Article(
        id="article_multi",
        title="Major Corporate Shakeup: CEO Resigns Amid Regulatory Investigation",
        content="In a shocking development, the CEO announced his resignation today following "
               "an SEC investigation into accounting practices. The company also reported "
               "disappointing quarterly earnings, missing analyst expectations. The board "
               "has appointed an interim president while searching for permanent leadership.",
        source="Financial Times",
        published_at=datetime.now(),
        symbols=["CORP"]
    )
    
    print(f"Article: {article.title}")
    print("-" * 80)
    
    events = detector.detect_events(article)
    
    print(f"\nDetected {len(events)} events:\n")
    
    for i, event in enumerate(events, 1):
        priority = "🔴 HIGH" if event.severity >= 0.7 else "🟢 Normal"
        print(f"{i}. {event.event_type.value.upper()} ({priority})")
        print(f"   Severity: {event.severity:.2f}")
        print(f"   Keywords: {', '.join(event.keywords)}")
        print()


def demo_severity_modifiers():
    """Demonstrate how severity modifiers affect event severity."""
    print("\n" + "="*80)
    print("DEMO 3: Severity Modifiers")
    print("="*80 + "\n")
    
    detector = EventDetector()
    
    # Same event type with different modifiers
    articles = [
        Article(
            id="article_high",
            title="Major Unprecedented Merger Shocks Industry",
            content="In a massive and historic deal, the largest merger in industry history was announced.",
            source="WSJ",
            published_at=datetime.now(),
            symbols=["A", "B"]
        ),
        Article(
            id="article_normal",
            title="Companies Announce Merger",
            content="Two companies announced plans to merge operations.",
            source="WSJ",
            published_at=datetime.now(),
            symbols=["C", "D"]
        ),
        Article(
            id="article_low",
            title="Minor Routine Merger Expected",
            content="A small planned merger was announced as expected.",
            source="WSJ",
            published_at=datetime.now(),
            symbols=["E", "F"]
        )
    ]
    
    for article in articles:
        events = detector.detect_events(article)
        if events:
            event = events[0]  # Get first event
            print(f"Article: {article.title}")
            print(f"Severity: {event.severity:.2f}")
            print(f"Keywords: {', '.join(event.keywords)}")
            print()


def demo_high_severity_query():
    """Demonstrate querying high-severity events from database."""
    print("\n" + "="*80)
    print("DEMO 4: High-Severity Event Query")
    print("="*80 + "\n")
    
    detector = EventDetector(high_severity_threshold=0.7)
    
    # First, create some events
    articles = [
        Article(
            id="article_bankruptcy",
            title="Major Corporation Files for Bankruptcy",
            content="In a shocking move, the major corporation filed for Chapter 11 bankruptcy.",
            source="Reuters",
            published_at=datetime.now(),
            symbols=["CORP"]
        ),
        Article(
            id="article_product",
            title="Company Launches New Product",
            content="The company unveiled a new product line today.",
            source="TechCrunch",
            published_at=datetime.now(),
            symbols=["TECH"]
        )
    ]
    
    print("Processing articles and storing events...\n")
    
    for article in articles:
        events = detector.process_article(article)
        for event in events:
            print(f"Stored: {event.event_type.value} (severity: {event.severity:.2f})")
    
    print("\n" + "-" * 80)
    print("Querying high-severity events (>= 0.7)...\n")
    
    high_severity_events = detector.get_high_severity_events(limit=10)
    
    if high_severity_events:
        for event in high_severity_events:
            print(f"🔴 {event.event_type.value.upper()}")
            print(f"   Severity: {event.severity:.2f}")
            print(f"   Article ID: {event.article_id}")
            print(f"   Timestamp: {event.timestamp}")
            print()
    else:
        print("No high-severity events found in database.")


def demo_redis_publishing():
    """Demonstrate Redis publishing for events."""
    print("\n" + "="*80)
    print("DEMO 5: Redis Publishing")
    print("="*80 + "\n")
    
    detector = EventDetector(high_severity_threshold=0.7)
    
    article = Article(
        id="article_redis",
        title="Massive Acquisition Deal Announced",
        content="In a record-breaking $50 billion acquisition, Company A will acquire Company B.",
        source="Bloomberg",
        published_at=datetime.now(),
        symbols=["CMPA", "CMPB"]
    )
    
    print(f"Article: {article.title}\n")
    
    events = detector.detect_events(article)
    
    for event in events:
        print(f"Event: {event.event_type.value}")
        print(f"Severity: {event.severity:.2f}")
        print(f"High Priority: {event.severity >= detector.high_severity_threshold}")
        
        # Publish to Redis
        success = detector.publish_to_redis(event)
        
        if success:
            print("✓ Published to Redis 'events' channel")
        else:
            print("✗ Failed to publish to Redis")
        print()


def main():
    """Run all demos."""
    print("\n" + "="*80)
    print("EVENT DETECTOR DEMONSTRATION")
    print("="*80)
    
    try:
        # Run demos
        demo_basic_detection()
        demo_multiple_events()
        demo_severity_modifiers()
        demo_high_severity_query()
        demo_redis_publishing()
        
        print("\n" + "="*80)
        print("DEMO COMPLETE")
        print("="*80 + "\n")
        
    except Exception as e:
        logger.error(f"Error in demo: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
