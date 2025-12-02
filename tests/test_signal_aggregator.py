"""Unit tests for the Signal Aggregator."""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from src.signal.aggregator import SignalAggregator
from src.shared.models import (
    AggregatedData, Event, EventType, MarketRegime, RegimeType,
    TechnicalSignals, TechnicalSignalType,
    TradingSignal, TradingSignalType
)


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    client = Mock()
    client.create_subscriber = Mock(return_value=Mock())
    client.publish = Mock(return_value=True)
    return client


@pytest.fixture
def aggregator(mock_redis_client):
    """Create a signal aggregator with default settings."""
    return SignalAggregator(
        redis_client=mock_redis_client,
        weight_sentiment=0.3,
        weight_technical=0.5,
        weight_regime=0.2,
        buy_threshold=60.0,
        sell_threshold=-60.0
    )


@pytest.fixture
def sample_aggregated_data():
    """Create sample aggregated data."""
    return AggregatedData(
        sentiment_score=0.6,
        technical_signals=TechnicalSignals(
            rsi_signal=TechnicalSignalType.OVERSOLD,
            macd_signal=TechnicalSignalType.BULLISH_CROSS,
            bb_signal=TechnicalSignalType.NEUTRAL
        ),
        regime=MarketRegime(
            regime_type=RegimeType.TRENDING_UP,
            confidence=0.8,
            volatility=0.15,
            trend_strength=0.75,
            timestamp=datetime.now()
        ),
        events=[],
        timestamp=datetime.now()
    )


class TestSignalAggregator:
    """Test cases for SignalAggregator."""
    
    def test_initialization(self, aggregator):
        """Test aggregator initialization."""
        assert aggregator.weight_sentiment == 0.3
        assert aggregator.weight_technical == 0.5
        assert aggregator.weight_regime == 0.2
        assert aggregator.buy_threshold == 60.0
        assert aggregator.sell_threshold == -60.0
    
    def test_weight_normalization(self, mock_redis_client):
        """Test that weights are normalized to sum to 1.0."""
        aggregator = SignalAggregator(
            redis_client=mock_redis_client,
            weight_sentiment=0.4,
            weight_technical=0.4,
            weight_regime=0.4  # Sum = 1.2
        )
        
        # Weights should be normalized
        total = aggregator.weight_sentiment + aggregator.weight_technical + aggregator.weight_regime
        assert abs(total - 1.0) < 0.001
    
    def test_normalize_technical_signals_bullish(self, aggregator):
        """Test technical signal normalization for bullish signals."""
        signals = TechnicalSignals(
            rsi_signal=TechnicalSignalType.OVERSOLD,  # +1.0
            macd_signal=TechnicalSignalType.BULLISH_CROSS,  # +1.0
            bb_signal=TechnicalSignalType.LOWER_BREACH  # +1.0
        )
        
        score = aggregator._normalize_technical_signals(signals)
        assert score == 1.0
    
    def test_normalize_technical_signals_bearish(self, aggregator):
        """Test technical signal normalization for bearish signals."""
        signals = TechnicalSignals(
            rsi_signal=TechnicalSignalType.OVERBOUGHT,  # -1.0
            macd_signal=TechnicalSignalType.BEARISH_CROSS,  # -1.0
            bb_signal=TechnicalSignalType.UPPER_BREACH  # -1.0
        )
        
        score = aggregator._normalize_technical_signals(signals)
        assert score == -1.0
    
    def test_normalize_technical_signals_neutral(self, aggregator):
        """Test technical signal normalization for neutral signals."""
        signals = TechnicalSignals(
            rsi_signal=TechnicalSignalType.NEUTRAL,
            macd_signal=TechnicalSignalType.NEUTRAL,
            bb_signal=TechnicalSignalType.NEUTRAL
        )
        
        score = aggregator._normalize_technical_signals(signals)
        assert score == 0.0
    
    def test_normalize_regime_trending_up(self, aggregator):
        """Test regime normalization for trending up."""
        regime = MarketRegime(
            regime_type=RegimeType.TRENDING_UP,
            confidence=0.8,
            volatility=0.15,
            trend_strength=0.75,
            timestamp=datetime.now()
        )
        
        score = aggregator._normalize_regime(regime)
        assert score == 0.8  # 1.0 * 0.8 confidence
    
    def test_normalize_regime_trending_down(self, aggregator):
        """Test regime normalization for trending down."""
        regime = MarketRegime(
            regime_type=RegimeType.TRENDING_DOWN,
            confidence=0.7,
            volatility=0.2,
            trend_strength=0.6,
            timestamp=datetime.now()
        )
        
        score = aggregator._normalize_regime(regime)
        assert score == -0.7  # -1.0 * 0.7 confidence
    
    def test_normalize_regime_ranging(self, aggregator):
        """Test regime normalization for ranging."""
        regime = MarketRegime(
            regime_type=RegimeType.RANGING,
            confidence=0.9,
            volatility=0.1,
            trend_strength=0.2,
            timestamp=datetime.now()
        )
        
        score = aggregator._normalize_regime(regime)
        assert score == 0.0  # 0.0 * 0.9 confidence
    
    def test_compute_cms_bullish(self, aggregator, sample_aggregated_data):
        """Test CMS computation for bullish scenario."""
        cms = aggregator.compute_cms(sample_aggregated_data)
        
        # CMS should be positive and within bounds
        assert -100 <= cms.score <= 100
        assert cms.score > 0  # Should be bullish
        
        # Check components
        assert cms.sentiment_component > 0
        assert cms.technical_component > 0
        assert cms.regime_component > 0
        
        # Check weights
        assert cms.weights['sentiment'] == 0.3
        assert cms.weights['technical'] == 0.5
        assert cms.weights['regime'] == 0.2
    
    def test_compute_cms_bearish(self, aggregator):
        """Test CMS computation for bearish scenario."""
        data = AggregatedData(
            sentiment_score=-0.7,
            technical_signals=TechnicalSignals(
                rsi_signal=TechnicalSignalType.OVERBOUGHT,
                macd_signal=TechnicalSignalType.BEARISH_CROSS,
                bb_signal=TechnicalSignalType.UPPER_BREACH
            ),
            regime=MarketRegime(
                regime_type=RegimeType.TRENDING_DOWN,
                confidence=0.85,
                volatility=0.25,
                trend_strength=0.8,
                timestamp=datetime.now()
            ),
            events=[],
            timestamp=datetime.now()
        )
        
        cms = aggregator.compute_cms(data)
        
        # CMS should be negative and within bounds
        assert -100 <= cms.score <= 100
        assert cms.score < 0  # Should be bearish
    
    def test_generate_signal_buy(self, aggregator, sample_aggregated_data):
        """Test signal generation for BUY signal."""
        signal = aggregator.generate_signal(sample_aggregated_data)
        
        # Should generate BUY signal for bullish data
        assert signal.signal_type == TradingSignalType.BUY
        assert signal.cms.score > 60.0
        assert 0 <= signal.confidence <= 1.0
        
        # Check explanation exists
        assert signal.explanation is not None
        assert len(signal.explanation.summary) > 0
    
    def test_generate_signal_sell(self, aggregator):
        """Test signal generation for SELL signal."""
        data = AggregatedData(
            sentiment_score=-0.8,
            technical_signals=TechnicalSignals(
                rsi_signal=TechnicalSignalType.OVERBOUGHT,
                macd_signal=TechnicalSignalType.BEARISH_CROSS,
                bb_signal=TechnicalSignalType.UPPER_BREACH
            ),
            regime=MarketRegime(
                regime_type=RegimeType.TRENDING_DOWN,
                confidence=0.9,
                volatility=0.3,
                trend_strength=0.85,
                timestamp=datetime.now()
            ),
            events=[],
            timestamp=datetime.now()
        )
        
        signal = aggregator.generate_signal(data)
        
        # Should generate SELL signal for bearish data
        assert signal.signal_type == TradingSignalType.SELL
        assert signal.cms.score < -60.0
    
    def test_generate_signal_hold(self, aggregator):
        """Test signal generation for HOLD signal."""
        data = AggregatedData(
            sentiment_score=0.1,
            technical_signals=TechnicalSignals(
                rsi_signal=TechnicalSignalType.NEUTRAL,
                macd_signal=TechnicalSignalType.NEUTRAL,
                bb_signal=TechnicalSignalType.NEUTRAL
            ),
            regime=MarketRegime(
                regime_type=RegimeType.RANGING,
                confidence=0.7,
                volatility=0.1,
                trend_strength=0.2,
                timestamp=datetime.now()
            ),
            events=[],
            timestamp=datetime.now()
        )
        
        signal = aggregator.generate_signal(data)
        
        # Should generate HOLD signal for neutral data
        assert signal.signal_type == TradingSignalType.HOLD
        assert -60.0 <= signal.cms.score <= 60.0
    
    def test_create_explanation(self, aggregator, sample_aggregated_data):
        """Test explanation generation."""
        cms = aggregator.compute_cms(sample_aggregated_data)
        explanation = aggregator.create_explanation(
            sample_aggregated_data,
            cms,
            TradingSignalType.BUY
        )
        
        # Check all explanation fields are populated
        assert len(explanation.summary) > 0
        assert len(explanation.sentiment_details) > 0
        assert len(explanation.technical_details) > 0
        assert len(explanation.regime_details) > 0
        assert len(explanation.event_details) > 0
        
        # Check component scores
        assert 'sentiment' in explanation.component_scores
        assert 'technical' in explanation.component_scores
        assert 'regime' in explanation.component_scores
        assert 'cms' in explanation.component_scores
    
    def test_explain_sentiment_positive(self, aggregator):
        """Test sentiment explanation for positive sentiment."""
        explanation = aggregator._explain_sentiment(0.7)
        assert 'positive' in explanation.lower()
    
    def test_explain_sentiment_negative(self, aggregator):
        """Test sentiment explanation for negative sentiment."""
        explanation = aggregator._explain_sentiment(-0.7)
        assert 'negative' in explanation.lower()
    
    def test_explain_technical(self, aggregator):
        """Test technical explanation."""
        signals = TechnicalSignals(
            rsi_signal=TechnicalSignalType.OVERSOLD,
            macd_signal=TechnicalSignalType.BULLISH_CROSS,
            bb_signal=TechnicalSignalType.LOWER_BREACH
        )
        
        explanation = aggregator._explain_technical(signals)
        
        # Should mention all indicators
        assert 'rsi' in explanation.lower()
        assert 'macd' in explanation.lower()
        assert 'bollinger' in explanation.lower()
    
    def test_explain_regime(self, aggregator):
        """Test regime explanation."""
        regime = MarketRegime(
            regime_type=RegimeType.TRENDING_UP,
            confidence=0.8,
            volatility=0.15,
            trend_strength=0.75,
            timestamp=datetime.now()
        )
        
        explanation = aggregator._explain_regime(regime)
        
        # Should mention regime type and metrics
        assert 'trending' in explanation.lower() or 'upward' in explanation.lower()
        assert 'confidence' in explanation.lower()
        assert 'volatility' in explanation.lower()
    
    def test_explain_events_no_events(self, aggregator):
        """Test event explanation with no events."""
        explanation = aggregator._explain_events([])
        assert 'no' in explanation.lower() or 'not' in explanation.lower()
    
    def test_explain_events_high_severity(self, aggregator):
        """Test event explanation with high severity events."""
        events = [
            Event(
                id='event-1',
                article_id='article-1',
                event_type=EventType.EARNINGS,
                severity=0.9,
                keywords=['earnings', 'beat'],
                timestamp=datetime.now()
            )
        ]
        
        explanation = aggregator._explain_events(events)
        assert 'high-severity' in explanation.lower() or 'earnings' in explanation.lower()
    
    def test_cms_bounds(self, aggregator):
        """Test that CMS is always within [-100, 100] bounds."""
        # Test with extreme values
        data = AggregatedData(
            sentiment_score=1.0,
            technical_signals=TechnicalSignals(
                rsi_signal=TechnicalSignalType.OVERSOLD,
                macd_signal=TechnicalSignalType.BULLISH_CROSS,
                bb_signal=TechnicalSignalType.LOWER_BREACH
            ),
            regime=MarketRegime(
                regime_type=RegimeType.TRENDING_UP,
                confidence=1.0,
                volatility=0.0,
                trend_strength=1.0,
                timestamp=datetime.now()
            ),
            events=[],
            timestamp=datetime.now()
        )
        
        cms = aggregator.compute_cms(data)
        assert -100 <= cms.score <= 100
    
    def test_confidence_computation(self, aggregator):
        """Test confidence score computation."""
        cms = Mock()
        cms.score = 80.0
        
        regime = MarketRegime(
            regime_type=RegimeType.TRENDING_UP,
            confidence=0.9,
            volatility=0.1,
            trend_strength=0.8,
            timestamp=datetime.now()
        )
        
        confidence = aggregator._compute_confidence(cms, regime)
        
        # Confidence should be in [0, 1]
        assert 0 <= confidence <= 1.0
        
        # Should be relatively high for strong signal and high regime confidence
        assert confidence > 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
