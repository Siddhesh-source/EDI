"""Integration tests for sentiment analyzer."""

import pytest
import asyncio
from datetime import datetime
from src.sentiment.analyzer import SentimentAnalyzer
from src.shared.models import Article


class TestSentimentIntegration:
    """Integration tests for sentiment analyzer."""
    
    @pytest.mark.asyncio
    async def test_concurrent_processing(self):
        """Test concurrent article processing."""
        analyzer = SentimentAnalyzer(api_key="test_key")
        
        # Create multiple articles
        articles = [
            Article(
                id=f"test{i}",
                title=f"Article {i}",
                content="Bullish growth positive excellent" if i % 2 == 0 else "Bearish decline negative crisis",
                source="Test Source",
                published_at=datetime.now(),
                symbols=["TEST"]
            )
            for i in range(10)
        ]
        
        # Process concurrently
        sentiments = await analyzer.process_articles_concurrent(articles)
        
        # Verify all articles processed
        assert len(sentiments) == len(articles)
        
        # Verify all scores are valid
        for sentiment in sentiments:
            assert -1.0 <= sentiment.score <= 1.0
            assert 0.0 <= sentiment.confidence <= 1.0
        
        # Verify alternating positive/negative pattern
        for i, sentiment in enumerate(sentiments):
            if i % 2 == 0:
                assert sentiment.score > 0  # Even indices should be positive
            else:
                assert sentiment.score < 0  # Odd indices should be negative
        
        analyzer.close()
    
    def test_negation_handling_comprehensive(self):
        """Test comprehensive negation handling."""
        analyzer = SentimentAnalyzer(api_key="test_key")
        
        test_cases = [
            # (content, expected_sign)
            # Note: negation detection looks at previous 3 words
            ("stock not strong today", -1),  # Negated positive → negative
            ("market not weak now", 1),    # Negated negative → positive
            ("never positive outlook", -1),  # Negated positive → negative
            ("hardly weak performance", 1),      # Negated negative → positive
            ("company isn't bullish", -1),    # Negated positive → negative
            ("not showing decline", 1),  # Negated negative → positive
        ]
        
        for content, expected_sign in test_cases:
            article = Article(
                id="test_negation",
                title="Test",
                content=content,
                source="Test",
                published_at=datetime.now(),
                symbols=["TEST"]
            )
            
            sentiment = analyzer.analyze_sentiment(article)
            
            if expected_sign > 0:
                assert sentiment.score > 0, f"Expected positive for '{content}', got {sentiment.score}"
            else:
                assert sentiment.score < 0, f"Expected negative for '{content}', got {sentiment.score}"
        
        analyzer.close()
    
    def test_mixed_sentiment(self):
        """Test articles with mixed positive and negative keywords."""
        analyzer = SentimentAnalyzer(api_key="test_key")
        
        # Article with equal positive and negative keywords
        article = Article(
            id="mixed",
            title="Mixed Sentiment",
            content="The company shows growth and profit but faces crisis and decline",
            source="Test",
            published_at=datetime.now(),
            symbols=["TEST"]
        )
        
        sentiment = analyzer.analyze_sentiment(article)
        
        # Should be close to neutral
        assert -0.5 <= sentiment.score <= 0.5
        assert sentiment.confidence > 0.0
        
        # Should have both positive and negative keywords
        assert len(sentiment.keywords_positive) > 0
        assert len(sentiment.keywords_negative) > 0
        
        analyzer.close()
    
    def test_cache_functionality(self):
        """Test sentiment caching."""
        analyzer = SentimentAnalyzer(api_key="test_key")
        
        article = Article(
            id="cache_test",
            title="Cache Test",
            content="Positive growth",
            source="Test",
            published_at=datetime.now(),
            symbols=["TEST"]
        )
        
        # Process article
        sentiment = analyzer.process_article(article)
        
        # Check cache
        cached = analyzer.get_cached_sentiment("cache_test")
        assert cached is not None
        assert cached.score == sentiment.score
        assert cached.confidence == sentiment.confidence
        
        analyzer.close()
    
    def test_empty_content_handling(self):
        """Test handling of articles with empty or minimal content."""
        analyzer = SentimentAnalyzer(api_key="test_key")
        
        # Empty content
        article_empty = Article(
            id="empty",
            title="",
            content="",
            source="Test",
            published_at=datetime.now(),
            symbols=["TEST"]
        )
        
        sentiment_empty = analyzer.analyze_sentiment(article_empty)
        assert sentiment_empty.score == 0.0  # Should be neutral
        assert sentiment_empty.confidence < 0.5  # Low confidence
        
        # Minimal content with no keywords
        article_minimal = Article(
            id="minimal",
            title="The company",
            content="The report will be released",
            source="Test",
            published_at=datetime.now(),
            symbols=["TEST"]
        )
        
        sentiment_minimal = analyzer.analyze_sentiment(article_minimal)
        assert sentiment_minimal.score == 0.0  # Should be neutral
        
        analyzer.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
