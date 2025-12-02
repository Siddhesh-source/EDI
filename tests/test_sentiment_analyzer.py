"""Tests for sentiment analyzer."""

import pytest
from datetime import datetime
from src.sentiment.analyzer import SentimentAnalyzer
from src.shared.models import Article


class TestSentimentAnalyzer:
    """Test suite for SentimentAnalyzer."""
    
    def test_analyze_sentiment_positive(self):
        """Test sentiment analysis with positive article."""
        analyzer = SentimentAnalyzer(api_key="test_key")
        
        article = Article(
            id="test1",
            title="Stock surges on strong earnings beat",
            content="The company reported excellent growth and bullish outlook",
            source="Test Source",
            published_at=datetime.now(),
            symbols=["AAPL"]
        )
        
        sentiment = analyzer.analyze_sentiment(article)
        
        assert sentiment.article_id == "test1"
        assert -1.0 <= sentiment.score <= 1.0
        assert sentiment.score > 0  # Should be positive
        assert 0.0 <= sentiment.confidence <= 1.0
        assert len(sentiment.keywords_positive) > 0
    
    def test_analyze_sentiment_negative(self):
        """Test sentiment analysis with negative article."""
        analyzer = SentimentAnalyzer(api_key="test_key")
        
        article = Article(
            id="test2",
            title="Stock plunges on disappointing results",
            content="The company faces crisis and bearish outlook with weak performance",
            source="Test Source",
            published_at=datetime.now(),
            symbols=["AAPL"]
        )
        
        sentiment = analyzer.analyze_sentiment(article)
        
        assert sentiment.article_id == "test2"
        assert -1.0 <= sentiment.score <= 1.0
        assert sentiment.score < 0  # Should be negative
        assert 0.0 <= sentiment.confidence <= 1.0
        assert len(sentiment.keywords_negative) > 0
    
    def test_analyze_sentiment_neutral(self):
        """Test sentiment analysis with neutral article."""
        analyzer = SentimentAnalyzer(api_key="test_key")
        
        article = Article(
            id="test3",
            title="Company announces quarterly report",
            content="The report will be released next week",
            source="Test Source",
            published_at=datetime.now(),
            symbols=["AAPL"]
        )
        
        sentiment = analyzer.analyze_sentiment(article)
        
        assert sentiment.article_id == "test3"
        assert -1.0 <= sentiment.score <= 1.0
        assert sentiment.score == 0.0  # Should be neutral
        assert 0.0 <= sentiment.confidence <= 1.0
    
    def test_analyze_sentiment_negation(self):
        """Test sentiment analysis with negation handling."""
        analyzer = SentimentAnalyzer(api_key="test_key")
        
        article = Article(
            id="test4",
            title="Stock not performing well",
            content="The company is not showing growth and not beating expectations",
            source="Test Source",
            published_at=datetime.now(),
            symbols=["AAPL"]
        )
        
        sentiment = analyzer.analyze_sentiment(article)
        
        assert sentiment.article_id == "test4"
        assert -1.0 <= sentiment.score <= 1.0
        # "not growth" and "not beat" should be treated as negative
        assert sentiment.score < 0
        assert 0.0 <= sentiment.confidence <= 1.0
    
    def test_sentiment_score_bounds(self):
        """Test that sentiment scores are always within bounds."""
        analyzer = SentimentAnalyzer(api_key="test_key")
        
        # Test with extreme positive content
        article_positive = Article(
            id="test5",
            title="Excellent outstanding stellar impressive",
            content="Bullish surge rally gain profit growth " * 10,
            source="Test Source",
            published_at=datetime.now(),
            symbols=["AAPL"]
        )
        
        sentiment_positive = analyzer.analyze_sentiment(article_positive)
        assert -1.0 <= sentiment_positive.score <= 1.0
        
        # Test with extreme negative content
        article_negative = Article(
            id="test6",
            title="Crisis crash plunge failure",
            content="Bearish decline loss weak poor " * 10,
            source="Test Source",
            published_at=datetime.now(),
            symbols=["AAPL"]
        )
        
        sentiment_negative = analyzer.analyze_sentiment(article_negative)
        assert -1.0 <= sentiment_negative.score <= 1.0
    
    def test_confidence_calculation(self):
        """Test confidence score calculation."""
        analyzer = SentimentAnalyzer(api_key="test_key")
        
        # Article with few keywords should have lower confidence
        article_few = Article(
            id="test7",
            title="Stock rises",
            content="The price increased",
            source="Test Source",
            published_at=datetime.now(),
            symbols=["AAPL"]
        )
        
        sentiment_few = analyzer.analyze_sentiment(article_few)
        
        # Article with many keywords should have higher confidence
        article_many = Article(
            id="test8",
            title="Stock surges on excellent earnings beat",
            content="Strong growth profit rally bullish optimistic positive momentum",
            source="Test Source",
            published_at=datetime.now(),
            symbols=["AAPL"]
        )
        
        sentiment_many = analyzer.analyze_sentiment(article_many)
        
        assert sentiment_many.confidence > sentiment_few.confidence
        assert 0.0 <= sentiment_few.confidence <= 1.0
        assert 0.0 <= sentiment_many.confidence <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
