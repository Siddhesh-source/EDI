# Sentiment Analysis Module

This module implements a NewsAPI-based sentiment analyzer with rule-based NLP for financial news articles.

## Features

- **NewsAPI Integration**: Fetches real-time financial news articles
- **Rule-Based Sentiment Analysis**: Uses keyword dictionaries for sentiment scoring
- **Negation Handling**: Properly handles negation words (e.g., "not good" → negative)
- **Concurrent Processing**: Processes multiple articles in parallel using ThreadPoolExecutor
- **Redis Publishing**: Publishes sentiment scores to Redis pub/sub pipeline
- **PostgreSQL Storage**: Stores articles and sentiment scores for historical analysis
- **Graceful Degradation**: Continues operating with cached data when NewsAPI is unavailable

## Architecture

### SentimentAnalyzer Class

The main class that orchestrates sentiment analysis:

```python
from src.sentiment import SentimentAnalyzer

analyzer = SentimentAnalyzer(
    api_key="your_newsapi_key",
    max_workers=5,
    cache_hours=24
)
```

### Key Methods

#### `fetch_news(symbols, lookback_hours=24)`
Fetches financial news articles from NewsAPI for specified stock symbols.

**Parameters:**
- `symbols`: List of stock symbols to search for
- `lookback_hours`: Hours to look back for articles (default: 24)

**Returns:** List of `Article` objects

#### `analyze_sentiment(article)`
Analyzes sentiment of an article using rule-based NLP.

**Parameters:**
- `article`: Article object to analyze

**Returns:** `SentimentScore` with score between -1.0 (negative) and +1.0 (positive)

#### `process_articles_concurrent(articles)`
Processes multiple articles concurrently.

**Parameters:**
- `articles`: List of articles to process

**Returns:** List of `SentimentScore` objects

#### `run(symbols, lookback_hours=24, interval_minutes=15)`
Runs sentiment analyzer continuously in a loop.

**Parameters:**
- `symbols`: List of stock symbols to monitor
- `lookback_hours`: Hours to look back for articles
- `interval_minutes`: Minutes between fetch cycles

## Sentiment Analysis Algorithm

### Keyword Dictionaries

**Positive Keywords:**
- bullish, surge, soar, rally, gain, profit, growth, rise, increase, positive, strong, beat, exceed, outperform, success, breakthrough, innovation, expansion, upgrade, optimistic, boom, record, high, advance, improve, recovery, momentum, upbeat, confident, opportunity, win, achievement, milestone, robust, stellar, impressive, excellent, outstanding, favorable

**Negative Keywords:**
- bearish, plunge, crash, fall, loss, decline, drop, weak, decrease, negative, miss, underperform, failure, concern, risk, threat, warning, downgrade, pessimistic, recession, low, slump, worsen, deteriorate, crisis, struggle, trouble, uncertain, volatile, fear, anxiety, disappointing, poor, challenging, difficult, problematic, unfavorable

**Negation Words:**
- not, no, never, neither, nobody, nothing, nowhere, none, hardly, scarcely, barely, doesn't, isn't, wasn't, shouldn't, wouldn't, couldn't, won't, can't, don't, didn't, haven't, hasn't, hadn't

### Scoring Algorithm

1. **Tokenization**: Text is split into words
2. **Negation Detection**: Sliding window of 3 words checks for negation
3. **Keyword Matching**: Each word is checked against positive/negative dictionaries
4. **Negation Handling**: Negated positive becomes negative, negated negative becomes positive
5. **Score Calculation**: `(positive_count - negative_count) / total_keywords`
6. **Confidence Calculation**: Based on number of keywords found (more keywords = higher confidence)

### Score Interpretation

- **Score > 0.3**: Positive sentiment 📈
- **Score < -0.3**: Negative sentiment 📉
- **-0.3 ≤ Score ≤ 0.3**: Neutral sentiment ➡️

## Usage Examples

### Basic Usage

```python
import asyncio
from datetime import datetime
from src.sentiment import SentimentAnalyzer
from src.shared.models import Article

# Initialize analyzer
analyzer = SentimentAnalyzer(api_key="your_newsapi_key")

# Create article
article = Article(
    id="article1",
    title="Stock surges on strong earnings",
    content="The company reported excellent growth...",
    source="Financial Times",
    published_at=datetime.now(),
    symbols=["AAPL"]
)

# Analyze sentiment
sentiment = analyzer.analyze_sentiment(article)
print(f"Score: {sentiment.score:.2f}")
print(f"Confidence: {sentiment.confidence:.2f}")
```

### Concurrent Processing

```python
import asyncio

# Fetch and process articles
articles = analyzer.fetch_news(["AAPL", "GOOGL", "MSFT"], lookback_hours=24)
sentiments = await analyzer.process_articles_concurrent(articles)

for sentiment in sentiments:
    print(f"Article {sentiment.article_id}: {sentiment.score:.2f}")
```

### Continuous Monitoring

```python
import asyncio

# Run continuously
await analyzer.run(
    symbols=["AAPL", "GOOGL", "MSFT"],
    lookback_hours=24,
    interval_minutes=15
)
```

## Data Flow

```
NewsAPI → fetch_news() → Articles
    ↓
analyze_sentiment() → SentimentScore
    ↓
    ├─→ publish_to_redis() → Redis 'sentiment' channel
    └─→ store_article_and_sentiment() → PostgreSQL
```

## Error Handling

### NewsAPI Unavailability
- System continues with cached sentiment data
- Cached data marked as "stale" with timestamp
- Periodic retry attempts with exponential backoff
- Alert logged when service down > 5 minutes

### Redis Unavailability
- Messages buffered locally (max 1000)
- Automatic reconnection with exponential backoff
- Buffered messages replayed upon reconnection

### Database Unavailability
- Write operations continue to be attempted
- Errors logged for debugging
- System continues processing new articles

## Configuration

Configuration is managed through environment variables (see `.env.example`):

```bash
# NewsAPI Configuration
NEWSAPI_KEY=your_newsapi_key_here

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=trading_db
POSTGRES_USER=trading_user
POSTGRES_PASSWORD=trading_password
```

## Testing

Run unit tests:

```bash
pytest tests/test_sentiment_analyzer.py -v
```

Run demo:

```bash
python examples/sentiment_analyzer_demo.py
```

## Requirements

- Python 3.10+
- newsapi-python
- redis
- psycopg2-binary
- sqlalchemy

See `requirements.txt` for complete list.

## Performance

- **Sentiment Analysis**: < 5 seconds per article (Requirement 1.1)
- **Concurrent Processing**: Processes N articles in < N × single_article_time
- **Redis Publishing**: < 10 milliseconds per message
- **Database Storage**: < 100 milliseconds per record

## Correctness Properties

This implementation satisfies the following correctness properties:

- **Property 1**: Sentiment scores are always within [-1.0, 1.0] range
- **Property 2**: All processed articles have sentiment published to Redis
- **Property 3**: Concurrent processing is faster than sequential processing

## Future Enhancements

- Machine learning-based sentiment analysis
- Multi-language support
- Entity recognition for company/product mentions
- Sentiment trend analysis over time
- Integration with additional news sources
