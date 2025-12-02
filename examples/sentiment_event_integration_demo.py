"""Demo script showing integration between Sentiment Analyzer and Event Detector."""

import logging
from datetime import datetime

from src.sentiment import SentimentAnalyzer
from src.events import EventDetector
from src.shared.models import Article
from src.shared.logging_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


def demo_integrated_analysis():
    """Demonstrate integrated sentiment and event analysis."""
    print("\n" + "="*80)
    print("INTEGRATED SENTIMENT AND EVENT ANALYSIS")
    print("="*80 + "\n")
    
    # Initialize both analyzers
    sentiment_analyzer = SentimentAnalyzer()
    event_detector = EventDetector(high_severity_threshold=0.7)
    
    # Sample article with both sentiment and events
    article = Article(
        id="integrated_article",
        title="Tech Giant Reports Record Earnings, Announces Major Acquisition",
        content="In a bullish announcement, the tech giant reported record quarterly earnings, "
               "beating analyst expectations with strong revenue growth. The company also "
               "unveiled plans for a massive $10 billion acquisition of a leading AI startup, "
               "signaling confidence in future innovation. Investors reacted positively to "
               "the excellent results and strategic expansion.",
        source="Financial Times",
        published_at=datetime.now(),
        symbols=["TECH"]
    )
    
    print(f"Article: {article.title}")
    print(f"Source: {article.source}")
    print("\n" + "-" * 80 + "\n")
    
    # Analyze sentiment
    print("SENTIMENT ANALYSIS:")
    sentiment = sentiment_analyzer.analyze_sentiment(article)
    
    sentiment_label = "POSITIVE" if sentiment.score > 0.2 else "NEGATIVE" if sentiment.score < -0.2 else "NEUTRAL"
    print(f"  Score: {sentiment.score:.2f} ({sentiment_label})")
    print(f"  Confidence: {sentiment.confidence:.2f}")
    print(f"  Positive Keywords: {', '.join(sentiment.keywords_positive[:5])}")
    print(f"  Negative Keywords: {', '.join(sentiment.keywords_negative[:5]) if sentiment.keywords_negative else 'None'}")
    
    print("\n" + "-" * 80 + "\n")
    
    # Detect events
    print("EVENT DETECTION:")
    events = event_detector.detect_events(article)
    
    if events:
        for i, event in enumerate(events, 1):
            priority = "🔴 HIGH PRIORITY" if event.severity >= 0.7 else "🟢 Normal"
            print(f"\n  Event {i}: {event.event_type.value.upper()} ({priority})")
            print(f"    Severity: {event.severity:.2f}")
            print(f"    Keywords: {', '.join(event.keywords)}")
    else:
        print("  No events detected")
    
    print("\n" + "-" * 80 + "\n")
    
    # Combined analysis
    print("COMBINED ANALYSIS:")
    print(f"  Overall Sentiment: {sentiment_label} ({sentiment.score:.2f})")
    print(f"  Number of Events: {len(events)}")
    print(f"  High-Priority Events: {sum(1 for e in events if e.severity >= 0.7)}")
    
    # Trading signal suggestion (simplified)
    if sentiment.score > 0.3 and any(e.event_type.value in ['earnings', 'acquisition'] for e in events):
        signal = "🟢 BULLISH - Positive sentiment with favorable events"
    elif sentiment.score < -0.3 and any(e.event_type.value in ['bankruptcy', 'regulatory'] for e in events):
        signal = "🔴 BEARISH - Negative sentiment with concerning events"
    else:
        signal = "🟡 NEUTRAL - Mixed signals"
    
    print(f"  Suggested Signal: {signal}")


def demo_multiple_articles():
    """Demonstrate processing multiple articles."""
    print("\n" + "="*80)
    print("PROCESSING MULTIPLE ARTICLES")
    print("="*80 + "\n")
    
    sentiment_analyzer = SentimentAnalyzer()
    event_detector = EventDetector()
    
    articles = [
        Article(
            id="article1",
            title="Company Reports Strong Earnings Growth",
            content="The company delivered excellent quarterly results with robust revenue growth.",
            source="WSJ",
            published_at=datetime.now(),
            symbols=["COMP"]
        ),
        Article(
            id="article2",
            title="Regulatory Investigation Announced",
            content="Federal regulators launched an investigation into potential violations.",
            source="Reuters",
            published_at=datetime.now(),
            symbols=["CORP"]
        ),
        Article(
            id="article3",
            title="CEO Steps Down Amid Controversy",
            content="The CEO announced resignation following disappointing performance.",
            source="Bloomberg",
            published_at=datetime.now(),
            symbols=["FIRM"]
        )
    ]
    
    results = []
    
    for article in articles:
        sentiment = sentiment_analyzer.analyze_sentiment(article)
        events = event_detector.detect_events(article)
        
        results.append({
            'title': article.title,
            'sentiment': sentiment.score,
            'events': len(events),
            'high_severity': sum(1 for e in events if e.severity >= 0.7)
        })
    
    # Display summary
    print(f"{'Title':<50} {'Sentiment':<12} {'Events':<8} {'High-Sev':<10}")
    print("-" * 80)
    
    for result in results:
        sentiment_str = f"{result['sentiment']:+.2f}"
        print(f"{result['title'][:48]:<50} {sentiment_str:<12} {result['events']:<8} {result['high_severity']:<10}")


def main():
    """Run all demos."""
    try:
        demo_integrated_analysis()
        demo_multiple_articles()
        
        print("\n" + "="*80)
        print("INTEGRATION DEMO COMPLETE")
        print("="*80 + "\n")
        
    except Exception as e:
        logger.error(f"Error in demo: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
