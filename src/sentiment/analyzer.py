"""NewsAPI sentiment analyzer with rule-based NLP."""

import asyncio
import hashlib
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import List, Optional, Set

from newsapi import NewsApiClient
from newsapi.newsapi_exception import NewsAPIException

from src.shared.config import settings
from src.shared.models import Article, SentimentScore
from src.shared.redis_client import RedisChannels, get_redis_client
from src.database.connection import get_db_session
from src.database.repositories import ArticleRepository, SentimentScoreRepository

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """NewsAPI sentiment analyzer with rule-based sentiment analysis."""
    
    # Positive keywords dictionary
    POSITIVE_KEYWORDS = {
        'bullish', 'surge', 'soar', 'rally', 'gain', 'profit', 'growth', 'rise',
        'increase', 'positive', 'strong', 'beat', 'exceed', 'outperform', 'success',
        'breakthrough', 'innovation', 'expansion', 'upgrade', 'optimistic', 'boom',
        'record', 'high', 'advance', 'improve', 'recovery', 'momentum', 'upbeat',
        'confident', 'opportunity', 'win', 'achievement', 'milestone', 'robust',
        'stellar', 'impressive', 'excellent', 'outstanding', 'favorable'
    }
    
    # Negative keywords dictionary
    NEGATIVE_KEYWORDS = {
        'bearish', 'plunge', 'crash', 'fall', 'loss', 'decline', 'drop', 'weak',
        'decrease', 'negative', 'miss', 'underperform', 'failure', 'concern',
        'risk', 'threat', 'warning', 'downgrade', 'pessimistic', 'recession',
        'low', 'slump', 'worsen', 'deteriorate', 'crisis', 'struggle', 'trouble',
        'uncertain', 'volatile', 'fear', 'anxiety', 'disappointing', 'poor',
        'weak', 'challenging', 'difficult', 'problematic', 'unfavorable'
    }
    
    # Negation words
    NEGATION_WORDS = {
        'not', 'no', 'never', 'neither', 'nobody', 'nothing', 'nowhere',
        'none', 'hardly', 'scarcely', 'barely', 'doesn', 'isn',
        'wasn', 'shouldn', 'wouldn', 'couldn', 'won',
        'can', 'don', 'didn', 'haven', 'hasn', 'hadn'
    }
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        max_workers: int = 5,
        cache_hours: int = 24
    ):
        """
        Initialize sentiment analyzer.
        
        Args:
            api_key: NewsAPI key (defaults to settings)
            max_workers: Maximum concurrent workers for article processing
            cache_hours: Hours to cache sentiment data when NewsAPI unavailable
        """
        self.api_key = api_key or settings.newsapi_key
        if not self.api_key:
            logger.warning("NewsAPI key not configured, analyzer will not fetch articles")
            self.client = None
        else:
            self.client = NewsApiClient(api_key=self.api_key)
        
        self.max_workers = max_workers
        self.cache_hours = cache_hours
        self.redis_client = get_redis_client()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._cached_sentiment: dict = {}
        self._last_fetch_time: Optional[datetime] = None
        
        logger.info(f"Sentiment analyzer initialized with {max_workers} workers")
    
    def fetch_news(
        self,
        symbols: List[str],
        lookback_hours: int = 24,
        language: str = 'en'
    ) -> List[Article]:
        """
        Fetch financial news articles from NewsAPI.
        
        Args:
            symbols: List of stock symbols to search for
            lookback_hours: Hours to look back for articles
            language: Article language
            
        Returns:
            List of Article objects
        """
        if not self.client:
            logger.error("NewsAPI client not initialized")
            return []
        
        articles = []
        from_date = datetime.now() - timedelta(hours=lookback_hours)
        
        try:
            # Build query from symbols
            query = ' OR '.join(symbols)
            
            # Fetch articles
            response = self.client.get_everything(
                q=query,
                from_param=from_date.isoformat(),
                language=language,
                sort_by='publishedAt',
                page_size=100
            )
            
            if response['status'] == 'ok':
                for article_data in response['articles']:
                    # Generate unique ID from URL
                    article_id = hashlib.md5(
                        article_data['url'].encode()
                    ).hexdigest()
                    
                    # Parse published date
                    published_at = datetime.fromisoformat(
                        article_data['publishedAt'].replace('Z', '+00:00')
                    )
                    
                    # Extract content
                    content = article_data.get('description', '') or ''
                    if article_data.get('content'):
                        content += ' ' + article_data['content']
                    
                    article = Article(
                        id=article_id,
                        title=article_data['title'],
                        content=content,
                        source=article_data['source']['name'],
                        published_at=published_at,
                        symbols=symbols
                    )
                    articles.append(article)
                
                logger.info(f"Fetched {len(articles)} articles for symbols: {symbols}")
                self._last_fetch_time = datetime.now()
            else:
                logger.warning(f"NewsAPI returned non-ok status: {response['status']}")
        
        except NewsAPIException as e:
            logger.error(f"NewsAPI error: {e}")
            # Mark service as unavailable
            self._handle_newsapi_unavailable()
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
        
        return articles
    
    def analyze_sentiment(self, article: Article) -> SentimentScore:
        """
        Analyze sentiment of an article using rule-based NLP.
        
        Args:
            article: Article to analyze
            
        Returns:
            SentimentScore with score between -1.0 and +1.0
        """
        # Combine title and content for analysis
        text = f"{article.title} {article.content}".lower()
        
        # Tokenize into words
        words = re.findall(r'\b\w+\b', text)
        
        # Track sentiment with negation handling
        positive_count = 0
        negative_count = 0
        keywords_positive = []
        keywords_negative = []
        
        # Sliding window for negation detection (3 words)
        for i, word in enumerate(words):
            # Check for negation in previous 3 words
            negated = False
            for j in range(max(0, i - 3), i):
                if words[j] in self.NEGATION_WORDS:
                    negated = True
                    break
            
            # Check if word is a sentiment keyword
            if word in self.POSITIVE_KEYWORDS:
                if negated:
                    # Negated positive becomes negative
                    negative_count += 1
                    keywords_negative.append(f"not {word}")
                else:
                    positive_count += 1
                    keywords_positive.append(word)
            
            elif word in self.NEGATIVE_KEYWORDS:
                if negated:
                    # Negated negative becomes positive
                    positive_count += 1
                    keywords_positive.append(f"not {word}")
                else:
                    negative_count += 1
                    keywords_negative.append(word)
        
        # Calculate sentiment score
        total_keywords = positive_count + negative_count
        
        if total_keywords == 0:
            # Neutral sentiment
            score = 0.0
            confidence = 0.3  # Low confidence for neutral
        else:
            # Score between -1.0 and +1.0
            score = (positive_count - negative_count) / total_keywords
            
            # Confidence based on number of keywords found
            # More keywords = higher confidence
            confidence = min(1.0, total_keywords / 10.0)
        
        # Ensure score is within bounds
        score = max(-1.0, min(1.0, score))
        confidence = max(0.0, min(1.0, confidence))
        
        sentiment = SentimentScore(
            article_id=article.id,
            score=score,
            confidence=confidence,
            keywords_positive=list(set(keywords_positive)),
            keywords_negative=list(set(keywords_negative)),
            timestamp=datetime.now()
        )
        
        logger.debug(
            f"Analyzed sentiment for article {article.id}: "
            f"score={score:.2f}, confidence={confidence:.2f}"
        )
        
        return sentiment
    
    def publish_to_redis(self, sentiment: SentimentScore) -> bool:
        """
        Publish sentiment score to Redis sentiment channel.
        
        Args:
            sentiment: Sentiment score to publish
            
        Returns:
            True if published successfully, False otherwise
        """
        data = {
            'article_id': sentiment.article_id,
            'score': sentiment.score,
            'confidence': sentiment.confidence,
            'keywords_positive': sentiment.keywords_positive,
            'keywords_negative': sentiment.keywords_negative,
            'timestamp': sentiment.timestamp.isoformat()
        }
        
        success = self.redis_client.publish(RedisChannels.SENTIMENT, data)
        
        if success:
            logger.debug(f"Published sentiment to Redis: {sentiment.article_id}")
        else:
            logger.warning(f"Failed to publish sentiment to Redis: {sentiment.article_id}")
        
        return success
    
    def store_article_and_sentiment(
        self,
        article: Article,
        sentiment: SentimentScore
    ) -> bool:
        """
        Store article and sentiment score in PostgreSQL.
        
        Args:
            article: Article to store
            sentiment: Sentiment score to store
            
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            with get_db_session() as session:
                article_repo = ArticleRepository(session)
                sentiment_repo = SentimentScoreRepository(session)
                
                # Check if article already exists
                existing_article = article_repo.get_by_id(article.id)
                if not existing_article:
                    # Store article
                    article_repo.create({
                        'id': article.id,
                        'title': article.title,
                        'content': article.content,
                        'source': article.source,
                        'published_at': article.published_at,
                        'symbols': article.symbols
                    })
                    logger.debug(f"Stored article: {article.id}")
                
                # Store sentiment score
                sentiment_repo.create({
                    'article_id': sentiment.article_id,
                    'score': float(sentiment.score),
                    'confidence': float(sentiment.confidence),
                    'keywords_positive': sentiment.keywords_positive,
                    'keywords_negative': sentiment.keywords_negative,
                    'timestamp': sentiment.timestamp
                })
                logger.debug(f"Stored sentiment: {sentiment.article_id}")
                
                session.commit()
                return True
        
        except Exception as e:
            logger.error(f"Error storing article and sentiment: {e}")
            return False
    
    def process_article(self, article: Article) -> Optional[SentimentScore]:
        """
        Process a single article: analyze sentiment, publish to Redis, store in DB.
        
        Args:
            article: Article to process
            
        Returns:
            SentimentScore if successful, None otherwise
        """
        try:
            # Analyze sentiment
            sentiment = self.analyze_sentiment(article)
            
            # Publish to Redis
            self.publish_to_redis(sentiment)
            
            # Store in database
            self.store_article_and_sentiment(article, sentiment)
            
            # Cache sentiment
            self._cached_sentiment[article.id] = sentiment
            
            return sentiment
        
        except Exception as e:
            logger.error(f"Error processing article {article.id}: {e}")
            return None
    
    async def process_articles_concurrent(
        self,
        articles: List[Article]
    ) -> List[SentimentScore]:
        """
        Process multiple articles concurrently.
        
        Args:
            articles: List of articles to process
            
        Returns:
            List of sentiment scores
        """
        if not articles:
            return []
        
        logger.info(f"Processing {len(articles)} articles concurrently")
        
        # Process articles in parallel using thread pool
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(self._executor, self.process_article, article)
            for article in articles
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Filter out None results
        sentiments = [s for s in results if s is not None]
        
        logger.info(f"Successfully processed {len(sentiments)}/{len(articles)} articles")
        
        return sentiments
    
    def _handle_newsapi_unavailable(self):
        """Handle NewsAPI service unavailability."""
        logger.warning("NewsAPI service unavailable, using cached sentiment data")
        
        # Mark cached data as stale
        if self._last_fetch_time:
            age = datetime.now() - self._last_fetch_time
            logger.info(f"Using cached sentiment data (age: {age})")
        else:
            logger.warning("No cached sentiment data available")
    
    def get_cached_sentiment(self, article_id: str) -> Optional[SentimentScore]:
        """
        Get cached sentiment score for an article.
        
        Args:
            article_id: Article ID
            
        Returns:
            Cached sentiment score or None
        """
        return self._cached_sentiment.get(article_id)
    
    def is_cache_stale(self) -> bool:
        """
        Check if cached sentiment data is stale.
        
        Returns:
            True if cache is older than cache_hours, False otherwise
        """
        if not self._last_fetch_time:
            return True
        
        age = datetime.now() - self._last_fetch_time
        return age > timedelta(hours=self.cache_hours)
    
    async def run(
        self,
        symbols: List[str],
        lookback_hours: int = 24,
        interval_minutes: int = 15
    ):
        """
        Run sentiment analyzer continuously.
        
        Args:
            symbols: List of stock symbols to monitor
            lookback_hours: Hours to look back for articles
            interval_minutes: Minutes between fetch cycles
        """
        logger.info(
            f"Starting sentiment analyzer for symbols: {symbols}, "
            f"interval: {interval_minutes} minutes"
        )
        
        while True:
            try:
                # Fetch news articles
                articles = self.fetch_news(symbols, lookback_hours)
                
                # Process articles concurrently
                if articles:
                    await self.process_articles_concurrent(articles)
                else:
                    logger.info("No new articles to process")
                
                # Wait for next cycle
                await asyncio.sleep(interval_minutes * 60)
            
            except Exception as e:
                logger.error(f"Error in sentiment analyzer run loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    def close(self):
        """Cleanup resources."""
        self._executor.shutdown(wait=True)
        logger.info("Sentiment analyzer closed")
