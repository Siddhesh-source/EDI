"""Demo script for sentiment analyzer."""

import asyncio
import logging
from datetime import datetime

from src.sentiment.analyzer import SentimentAnalyzer
from src.shared.models import Article
from src.shared.logging_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


async def demo_sentiment_analysis():
    """Demonstrate sentiment analysis functionality."""
    
    # Initialize analyzer (without API key for demo)
    analyzer = SentimentAnalyzer(api_key=None)
    
    # Create sample articles
    articles = [
        Article(
            id="demo1",
            title="Tech Stock Surges on Strong Earnings Beat",
            content="The company reported excellent quarterly results with revenue "
                   "growth exceeding expectations. Analysts are bullish on the stock "
                   "with optimistic outlook for continued expansion.",
            source="Demo News",
            published_at=datetime.now(),
            symbols=["TECH"]
        ),
        Article(
            id="demo2",
            title="Market Concerns Rise as Economic Data Disappoints",
            content="Weak economic indicators have raised concerns among investors. "
                   "The bearish sentiment is reflected in declining market confidence "
                   "and fears of potential recession.",
            source="Demo News",
            published_at=datetime.now(),
            symbols=["SPY"]
        ),
        Article(
            id="demo3",
            title="Company Announces New Product Launch",
            content="The company unveiled its latest innovation at the annual conference. "
                   "The breakthrough technology represents a significant milestone and "
                   "demonstrates strong commitment to growth.",
            source="Demo News",
            published_at=datetime.now(),
            symbols=["INNO"]
        ),
        Article(
            id="demo4",
            title="Stock Not Performing Well Despite Positive News",
            content="The stock is not showing the expected gains. Investors are not "
                   "confident about the outlook despite recent positive developments.",
            source="Demo News",
            published_at=datetime.now(),
            symbols=["UNDER"]
        )
    ]
    
    print("\n" + "="*80)
    print("SENTIMENT ANALYSIS DEMO")
    print("="*80 + "\n")
    
    # Process articles concurrently
    sentiments = await analyzer.process_articles_concurrent(articles)
    
    # Display results
    for article, sentiment in zip(articles, sentiments):
        print(f"\nArticle: {article.title}")
        print(f"Symbol: {article.symbols[0]}")
        print(f"Content: {article.content[:100]}...")
        print(f"\nSentiment Analysis:")
        print(f"  Score: {sentiment.score:.3f} (range: -1.0 to +1.0)")
        print(f"  Confidence: {sentiment.confidence:.3f}")
        print(f"  Positive Keywords: {', '.join(sentiment.keywords_positive[:5])}")
        print(f"  Negative Keywords: {', '.join(sentiment.keywords_negative[:5])}")
        
        # Interpret sentiment
        if sentiment.score > 0.3:
            interpretation = "POSITIVE 📈"
        elif sentiment.score < -0.3:
            interpretation = "NEGATIVE 📉"
        else:
            interpretation = "NEUTRAL ➡️"
        
        print(f"  Interpretation: {interpretation}")
        print("-" * 80)
    
    # Cleanup
    analyzer.close()
    
    print("\nDemo completed successfully!")


if __name__ == "__main__":
    asyncio.run(demo_sentiment_analysis())
