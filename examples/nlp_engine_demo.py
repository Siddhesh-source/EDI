"""
Demo script for Enhanced NLP Engine
Demonstrates Sentiment Index, Event Shock Factor, and complete analysis
"""

import asyncio
import json
from datetime import datetime, timedelta

from src.nlp.engine import EnhancedNLPEngine
from src.shared.models import Article
from src.sentiment.analyzer import SentimentAnalyzer
from src.events.detector import EventDetector


def create_sample_articles():
    """Create sample articles for demonstration."""
    articles = [
        Article(
            id="art1",
            title="Apple Reports Record Q4 Earnings, Beats Expectations",
            content="Apple Inc. announced record-breaking quarterly earnings today, "
                   "surpassing analyst expectations with strong iPhone sales and "
                   "robust growth in services revenue. The company's CEO expressed "
                   "optimism about future prospects.",
            source="Financial Times",
            published_at=datetime.now() - timedelta(hours=2),
            symbols=["AAPL"]
        ),
        Article(
            id="art2",
            title="Tesla Faces Regulatory Investigation Over Safety Concerns",
            content="Tesla is under investigation by federal regulators following "
                   "reports of safety issues with its autonomous driving system. "
                   "The probe could result in significant fines and recalls.",
            source="Reuters",
            published_at=datetime.now() - timedelta(hours=5),
            symbols=["TSLA"]
        ),
        Article(
            id="art3",
            title="Google Announces Major AI Breakthrough",
            content="Google unveiled a groundbreaking artificial intelligence system "
                   "that demonstrates unprecedented capabilities. The innovation "
                   "positions the company as a leader in the AI race.",
            source="TechCrunch",
            published_at=datetime.now() - timedelta(hours=8),
            symbols=["GOOGL"]
        ),
        Article(
            id="art4",
            title="Amazon Expands Cloud Services, Launches New Products",
            content="Amazon Web Services announced the launch of several new cloud "
                   "products aimed at enterprise customers. The expansion strengthens "
                   "Amazon's position in the competitive cloud market.",
            source="Bloomberg",
            published_at=datetime.now() - timedelta(hours=12),
            symbols=["AMZN"]
        ),
        Article(
            id="art5",
            title="Microsoft Faces Antitrust Lawsuit",
            content="Microsoft is facing a major antitrust lawsuit alleging "
                   "anticompetitive practices. Legal experts warn this could "
                   "result in substantial penalties and operational changes.",
            source="Wall Street Journal",
            published_at=datetime.now() - timedelta(hours=18),
            symbols=["MSFT"]
        ),
    ]
    
    return articles


def demo_sentiment_index():
    """Demonstrate Sentiment Index calculation."""
    print("\n" + "="*70)
    print("SENTIMENT INDEX (SI) DEMONSTRATION")
    print("="*70)
    
    # Initialize engine
    engine = EnhancedNLPEngine(window_size=10, decay_hours=24.0)
    
    # Create sample articles
    articles = create_sample_articles()
    
    # Analyze sentiment for each article
    sentiments = []
    for article in articles:
        sentiment = engine.sentiment_analyzer.analyze_sentiment(article)
        sentiments.append(sentiment)
        
        print(f"\nArticle: {article.title[:50]}...")
        print(f"  Score: {sentiment.score:+.2f}")
        print(f"  Confidence: {sentiment.confidence:.2f}")
        print(f"  Positive Keywords: {', '.join(sentiment.keywords_positive[:5])}")
        print(f"  Negative Keywords: {', '.join(sentiment.keywords_negative[:5])}")
    
    # Compute Sentiment Index
    si = engine.compute_sentiment_index(sentiments, use_smoothing=True)
    
    print("\n" + "-"*70)
    print("SENTIMENT INDEX RESULTS:")
    print("-"*70)
    print(f"Raw Score:       {si.raw_score:+.3f}")
    print(f"Weighted Score:  {si.weighted_score:+.3f}")
    print(f"Smoothed Score:  {si.smoothed_score:+.3f}")
    print(f"Confidence:      {si.confidence:.3f}")
    print(f"Article Count:   {si.article_count}")
    print(f"Positive Ratio:  {si.positive_ratio:.1%}")
    print(f"Negative Ratio:  {si.negative_ratio:.1%}")
    print(f"Neutral Ratio:   {si.neutral_ratio:.1%}")
    
    return si


def demo_event_shock_factor():
    """Demonstrate Event Shock Factor calculation."""
    print("\n" + "="*70)
    print("EVENT SHOCK FACTOR (ESF) DEMONSTRATION")
    print("="*70)
    
    # Initialize engine
    engine = EnhancedNLPEngine(high_severity_threshold=0.7)
    
    # Create sample articles
    articles = create_sample_articles()
    
    # Detect events in each article
    all_events = []
    for article in articles:
        events = engine.event_detector.detect_events(article)
        all_events.extend(events)
        
        if events:
            print(f"\nArticle: {article.title[:50]}...")
            for event in events:
                print(f"  Event Type: {event.event_type.value}")
                print(f"  Severity: {event.severity:.2f}")
                print(f"  Keywords: {', '.join(event.keywords[:5])}")
    
    # Compute Event Shock Factor
    esf = engine.compute_event_shock_factor(all_events, apply_recency_decay=True)
    
    print("\n" + "-"*70)
    print("EVENT SHOCK FACTOR RESULTS:")
    print("-"*70)
    print(f"Total Shock:           {esf.total_shock:.3f}")
    print(f"Event Count:           {esf.event_count}")
    print(f"High Severity Count:   {esf.high_severity_count}")
    print(f"Max Severity:          {esf.max_severity:.3f}")
    print(f"Avg Severity:          {esf.avg_severity:.3f}")
    print(f"Recency Factor:        {esf.recency_factor:.3f}")
    print(f"Dominant Event Type:   {esf.dominant_event_type}")
    print("\nEvent Type Distribution:")
    for event_type, count in esf.event_type_distribution.items():
        print(f"  {event_type}: {count}")
    
    return esf


def demo_complete_analysis():
    """Demonstrate complete NLP analysis."""
    print("\n" + "="*70)
    print("COMPLETE NLP ANALYSIS DEMONSTRATION")
    print("="*70)
    
    # Initialize engine
    engine = EnhancedNLPEngine(
        window_size=20,
        decay_hours=24.0,
        high_severity_threshold=0.7
    )
    
    # Create sample articles
    articles = create_sample_articles()
    
    print(f"\nProcessing {len(articles)} articles...")
    
    # Process articles through complete pipeline
    output = engine.process_articles(
        articles,
        use_smoothing=True,
        apply_recency_decay=True
    )
    
    print("\n" + "-"*70)
    print("COMPLETE NLP OUTPUT:")
    print("-"*70)
    
    print(f"\nMarket Mood:  {output.market_mood.upper()}")
    print(f"Risk Level:   {output.risk_level.upper()}")
    
    print(f"\nSentiment Index:")
    print(f"  Smoothed Score: {output.sentiment_index.smoothed_score:+.3f}")
    print(f"  Confidence:     {output.sentiment_index.confidence:.3f}")
    print(f"  Articles:       {output.sentiment_index.article_count}")
    
    print(f"\nEvent Shock Factor:")
    print(f"  Total Shock:    {output.event_shock_factor.total_shock:.3f}")
    print(f"  Events:         {output.event_shock_factor.event_count}")
    print(f"  High Severity:  {output.event_shock_factor.high_severity_count}")
    
    print(f"\nExplanation:")
    print(f"  {output.explanation}")
    
    # Display JSON output
    print("\n" + "-"*70)
    print("JSON OUTPUT (formatted):")
    print("-"*70)
    print(output.to_json(indent=2))
    
    return output


def demo_sliding_window():
    """Demonstrate sliding window smoothing."""
    print("\n" + "="*70)
    print("SLIDING WINDOW SMOOTHING DEMONSTRATION")
    print("="*70)
    
    # Initialize engine with small window for demo
    engine = EnhancedNLPEngine(window_size=5)
    
    # Simulate sentiment scores over time
    import random
    random.seed(42)
    
    print("\nSimulating sentiment scores over time:")
    print("(Showing raw vs smoothed scores)")
    print("\nTime | Raw Score | Smoothed Score")
    print("-" * 40)
    
    for i in range(15):
        # Generate random sentiment with trend
        base_trend = 0.3 * (i / 15)  # Upward trend
        noise = random.uniform(-0.3, 0.3)  # Random noise
        raw_score = base_trend + noise
        raw_score = max(-1.0, min(1.0, raw_score))  # Clamp to [-1, 1]
        
        # Add to window
        engine._sentiment_window.append(raw_score)
        
        # Compute smoothed score
        smoothed_score = engine._compute_ewma(list(engine._sentiment_window))
        
        print(f"{i:4d} | {raw_score:+.3f}     | {smoothed_score:+.3f}")
    
    print("\nNotice how smoothed scores reduce noise while following the trend.")


def demo_recency_decay():
    """Demonstrate temporal decay for events."""
    print("\n" + "="*70)
    print("TEMPORAL DECAY DEMONSTRATION")
    print("="*70)
    
    from src.shared.models import Event, EventType
    
    # Initialize engine
    engine = EnhancedNLPEngine(decay_hours=24.0)
    
    # Create events at different times
    now = datetime.now()
    events = [
        Event(
            id=f"evt{i}",
            article_id=f"art{i}",
            event_type=EventType.EARNINGS,
            severity=0.8,
            keywords=["earnings"],
            timestamp=now - timedelta(hours=hours)
        )
        for i, hours in enumerate([1, 6, 12, 24, 48, 72])
    ]
    
    print("\nEvent Age vs Recency Factor:")
    print("(Shows how older events have less impact)")
    print("\nAge (hours) | Recency Factor")
    print("-" * 35)
    
    for event in events:
        age_hours = (now - event.timestamp).total_seconds() / 3600
        
        # Compute recency factor for single event
        import math
        recency_factor = math.exp(-age_hours / engine.decay_hours)
        
        print(f"{age_hours:11.0f} | {recency_factor:.3f}")
    
    print("\nRecent events (< 24 hours) maintain high impact.")
    print("Older events (> 48 hours) have significantly reduced impact.")


def demo_market_mood_classification():
    """Demonstrate market mood classification."""
    print("\n" + "="*70)
    print("MARKET MOOD CLASSIFICATION DEMONSTRATION")
    print("="*70)
    
    from src.nlp.engine import SentimentIndex, EventShockFactor
    
    # Initialize engine
    engine = EnhancedNLPEngine()
    
    # Test different scenarios
    scenarios = [
        {
            'name': 'Strong Bullish',
            'si_score': 0.7,
            'esf_shock': 0.3
        },
        {
            'name': 'Weak Bullish',
            'si_score': 0.3,
            'esf_shock': 0.2
        },
        {
            'name': 'Neutral',
            'si_score': 0.0,
            'esf_shock': 0.1
        },
        {
            'name': 'Weak Bearish',
            'si_score': -0.3,
            'esf_shock': 0.2
        },
        {
            'name': 'Strong Bearish',
            'si_score': -0.7,
            'esf_shock': 0.4
        },
        {
            'name': 'High Shock Amplification',
            'si_score': 0.4,
            'esf_shock': 0.8
        },
    ]
    
    print("\nScenario Analysis:")
    print("\nScenario                  | SI Score | ESF Shock | Mood     | Risk")
    print("-" * 75)
    
    for scenario in scenarios:
        # Create SI and ESF objects
        si = SentimentIndex(
            raw_score=scenario['si_score'],
            weighted_score=scenario['si_score'],
            smoothed_score=scenario['si_score'],
            confidence=0.8,
            article_count=10,
            positive_ratio=0.5,
            negative_ratio=0.3,
            neutral_ratio=0.2,
            timestamp=datetime.now()
        )
        
        esf = EventShockFactor(
            total_shock=scenario['esf_shock'],
            event_count=5,
            high_severity_count=2,
            event_type_distribution={},
            max_severity=0.8,
            avg_severity=0.6,
            recency_factor=0.9,
            dominant_event_type="earnings",
            timestamp=datetime.now()
        )
        
        # Classify
        mood = engine.classify_market_mood(si, esf)
        risk = engine.assess_risk_level(si, esf)
        
        print(f"{scenario['name']:25} | {scenario['si_score']:+.2f}     | "
              f"{scenario['esf_shock']:.2f}      | {mood:8} | {risk}")


async def main():
    """Run all demonstrations."""
    print("\n" + "="*70)
    print("ENHANCED NLP ENGINE DEMONSTRATION")
    print("="*70)
    print("\nThis demo showcases the key features of the Enhanced NLP Engine:")
    print("1. Sentiment Index (SI) calculation")
    print("2. Event Shock Factor (ESF) computation")
    print("3. Complete NLP analysis pipeline")
    print("4. Sliding window smoothing")
    print("5. Temporal decay for recency weighting")
    print("6. Market mood classification")
    
    # Run demonstrations
    demo_sentiment_index()
    demo_event_shock_factor()
    demo_complete_analysis()
    demo_sliding_window()
    demo_recency_decay()
    demo_market_mood_classification()
    
    print("\n" + "="*70)
    print("DEMONSTRATION COMPLETE")
    print("="*70)
    print("\nThe Enhanced NLP Engine provides:")
    print("✓ Quantitative sentiment metrics (SI)")
    print("✓ Event impact assessment (ESF)")
    print("✓ Noise reduction through smoothing")
    print("✓ Recency weighting for timely signals")
    print("✓ Market mood and risk classification")
    print("✓ Clean JSON output for integration")
    print("\nReady for production use in algorithmic trading!")


if __name__ == "__main__":
    asyncio.run(main())
