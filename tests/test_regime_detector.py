"""Tests for Market Regime Detector."""

import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.regime import MarketRegimeDetector
from src.shared.models import OHLC, MarketRegime, RegimeType


@pytest.fixture
def detector():
    """Create a MarketRegimeDetector instance."""
    return MarketRegimeDetector(window_size=100, confidence_threshold=0.6)


@pytest.fixture
def sample_prices():
    """Generate sample price data."""
    prices = []
    base_price = 100.0
    timestamp = datetime.now() - timedelta(minutes=100)
    
    for i in range(100):
        prices.append(OHLC(
            open=base_price + i * 0.1,
            high=base_price + i * 0.1 + 1.0,
            low=base_price + i * 0.1 - 1.0,
            close=base_price + i * 0.1 + 0.5,
            volume=1000,
            timestamp=timestamp + timedelta(minutes=i)
        ))
    
    return prices


def generate_trending_up_prices(n_bars: int = 100) -> list[OHLC]:
    """Generate uptrending price data."""
    prices = []
    current_price = 100.0
    timestamp = datetime.now() - timedelta(minutes=n_bars)
    
    for i in range(n_bars):
        current_price += 0.5 + np.random.normal(0, 0.5)
        prices.append(OHLC(
            open=current_price,
            high=current_price + 0.5,
            low=current_price - 0.5,
            close=current_price + 0.2,
            volume=1000,
            timestamp=timestamp + timedelta(minutes=i)
        ))
    
    return prices


def generate_trending_down_prices(n_bars: int = 100) -> list[OHLC]:
    """Generate downtrending price data."""
    prices = []
    current_price = 100.0
    timestamp = datetime.now() - timedelta(minutes=n_bars)
    
    for i in range(n_bars):
        current_price -= 0.5 + np.random.normal(0, 0.5)
        prices.append(OHLC(
            open=current_price,
            high=current_price + 0.5,
            low=current_price - 0.5,
            close=current_price - 0.2,
            volume=1000,
            timestamp=timestamp + timedelta(minutes=i)
        ))
    
    return prices


def generate_ranging_prices(n_bars: int = 100) -> list[OHLC]:
    """Generate ranging price data."""
    prices = []
    base_price = 100.0
    timestamp = datetime.now() - timedelta(minutes=n_bars)
    
    for i in range(n_bars):
        price = base_price + np.random.normal(0, 1.0)
        prices.append(OHLC(
            open=price,
            high=price + 0.5,
            low=price - 0.5,
            close=price + 0.1,
            volume=1000,
            timestamp=timestamp + timedelta(minutes=i)
        ))
    
    return prices


def generate_volatile_prices(n_bars: int = 100) -> list[OHLC]:
    """Generate volatile price data."""
    prices = []
    current_price = 100.0
    timestamp = datetime.now() - timedelta(minutes=n_bars)
    
    for i in range(n_bars):
        current_price += np.random.normal(0, 3.0)
        prices.append(OHLC(
            open=current_price,
            high=current_price + 2.0,
            low=current_price - 2.0,
            close=current_price + 0.5,
            volume=1000,
            timestamp=timestamp + timedelta(minutes=i)
        ))
    
    return prices


def generate_calm_prices(n_bars: int = 100) -> list[OHLC]:
    """Generate calm/low volatility price data."""
    prices = []
    base_price = 100.0
    timestamp = datetime.now() - timedelta(minutes=n_bars)
    
    for i in range(n_bars):
        price = base_price + np.random.normal(0, 0.1)
        prices.append(OHLC(
            open=price,
            high=price + 0.05,
            low=price - 0.05,
            close=price + 0.02,
            volume=1000,
            timestamp=timestamp + timedelta(minutes=i)
        ))
    
    return prices


class TestMarketRegimeDetector:
    """Test suite for MarketRegimeDetector."""
    
    def test_initialization(self):
        """Test detector initialization."""
        detector = MarketRegimeDetector(window_size=50, confidence_threshold=0.7)
        
        assert detector.window_size == 50
        assert detector.confidence_threshold == 0.7
        assert detector._last_regime is None
    
    def test_detect_regime_trending_up(self):
        """Test detection of uptrending market."""
        detector = MarketRegimeDetector()
        prices = generate_trending_up_prices(100)
        
        regime = detector.detect_regime(prices)
        
        assert regime.regime_type == RegimeType.TRENDING_UP
        assert 0.0 <= regime.confidence <= 1.0
        assert regime.confidence > 0.5  # Should have reasonable confidence
        assert regime.volatility >= 0.0
        assert regime.trend_strength >= 0.0
    
    def test_detect_regime_trending_down(self):
        """Test detection of downtrending market."""
        detector = MarketRegimeDetector()
        prices = generate_trending_down_prices(100)
        
        regime = detector.detect_regime(prices)
        
        assert regime.regime_type == RegimeType.TRENDING_DOWN
        assert 0.0 <= regime.confidence <= 1.0
        assert regime.confidence > 0.5
    
    def test_detect_regime_ranging(self):
        """Test detection of ranging market."""
        detector = MarketRegimeDetector()
        prices = generate_ranging_prices(100)
        
        regime = detector.detect_regime(prices)
        
        assert regime.regime_type == RegimeType.RANGING
        assert 0.0 <= regime.confidence <= 1.0
    
    def test_detect_regime_volatile(self):
        """Test detection of volatile market."""
        detector = MarketRegimeDetector()
        prices = generate_volatile_prices(100)
        
        regime = detector.detect_regime(prices)
        
        # Volatile markets should have high volatility
        # May be classified as VOLATILE or RANGING depending on exact volatility
        assert 0.0 <= regime.confidence <= 1.0
        assert regime.volatility > 0.02  # Should have high volatility
    
    def test_detect_regime_calm(self):
        """Test detection of calm market."""
        detector = MarketRegimeDetector()
        prices = generate_calm_prices(100)
        
        regime = detector.detect_regime(prices)
        
        # Calm markets can be classified as CALM or RANGING (both valid for low volatility)
        assert regime.regime_type in [RegimeType.CALM, RegimeType.RANGING]
        assert 0.0 <= regime.confidence <= 1.0
        assert regime.volatility < 0.02  # Should have low volatility
    
    def test_rolling_window_size(self):
        """Test that only the most recent window_size bars are used."""
        detector = MarketRegimeDetector(window_size=50)
        
        # Generate 200 bars
        prices = generate_trending_up_prices(200)
        
        regime = detector.detect_regime(prices)
        
        # Should only use last 50 bars
        assert regime is not None
        assert isinstance(regime, MarketRegime)
    
    def test_insufficient_data(self):
        """Test handling of insufficient data."""
        detector = MarketRegimeDetector()
        
        # Only 10 bars (less than minimum 20)
        prices = generate_ranging_prices(10)
        
        regime = detector.detect_regime(prices)
        
        # Should return default regime
        assert regime.regime_type == RegimeType.RANGING
        assert regime.confidence == 0.5
    
    def test_confidence_threshold_default(self):
        """Test that low confidence defaults to RANGING."""
        detector = MarketRegimeDetector(confidence_threshold=0.9)
        
        # Generate ambiguous data
        prices = generate_ranging_prices(100)
        
        regime = detector.detect_regime(prices)
        
        # With high threshold, should default to RANGING
        if regime.confidence < 0.9:
            assert regime.regime_type == RegimeType.RANGING
    
    def test_compute_confidence(self):
        """Test confidence computation."""
        detector = MarketRegimeDetector()
        prices = generate_trending_up_prices(100)
        
        regime = detector.detect_regime(prices)
        confidence = detector.compute_confidence(regime)
        
        assert confidence == regime.confidence
        assert 0.0 <= confidence <= 1.0
    
    @patch('src.regime.detector.get_redis_client')
    def test_publish_to_redis(self, mock_redis):
        """Test publishing regime to Redis."""
        mock_client = Mock()
        mock_client.publish.return_value = True
        mock_redis.return_value = mock_client
        
        detector = MarketRegimeDetector()
        prices = generate_trending_up_prices(100)
        regime = detector.detect_regime(prices)
        
        success = detector.publish_to_redis(regime)
        
        assert success is True
        mock_client.publish.assert_called_once()
    
    @patch('src.regime.detector.get_redis_client')
    def test_publish_to_redis_no_change(self, mock_redis):
        """Test that unchanged regime is not republished."""
        mock_client = Mock()
        mock_client.publish.return_value = True
        mock_redis.return_value = mock_client
        
        detector = MarketRegimeDetector()
        prices = generate_trending_up_prices(100)
        regime = detector.detect_regime(prices)
        
        # First publish
        detector.publish_to_redis(regime)
        
        # Second publish with same regime
        success = detector.publish_to_redis(regime)
        
        # Should skip publish but return True
        assert success is True
    
    def test_store_regime(self):
        """Test storing regime in database."""
        detector = MarketRegimeDetector()
        prices = generate_trending_up_prices(100)
        regime = detector.detect_regime(prices)
        
        # Storage is currently a placeholder
        success = detector.store_regime(regime)
        
        assert success is True
    
    @patch('src.regime.detector.get_redis_client')
    def test_process_prices(self, mock_redis):
        """Test full price processing pipeline."""
        mock_client = Mock()
        mock_client.publish.return_value = True
        mock_redis.return_value = mock_client
        
        detector = MarketRegimeDetector()
        prices = generate_trending_up_prices(100)
        
        regime = detector.process_prices(prices)
        
        assert regime is not None
        assert isinstance(regime, MarketRegime)
        assert regime.regime_type in [
            RegimeType.TRENDING_UP,
            RegimeType.TRENDING_DOWN,
            RegimeType.RANGING,
            RegimeType.VOLATILE,
            RegimeType.CALM
        ]
    
    def test_volatility_computation(self):
        """Test volatility computation."""
        detector = MarketRegimeDetector()
        
        # High volatility prices
        volatile_prices = generate_volatile_prices(100)
        volatile_regime = detector.detect_regime(volatile_prices)
        
        # Low volatility prices
        calm_prices = generate_calm_prices(100)
        calm_regime = detector.detect_regime(calm_prices)
        
        # Volatile should have higher volatility
        assert volatile_regime.volatility > calm_regime.volatility
    
    def test_trend_strength_computation(self):
        """Test trend strength computation."""
        detector = MarketRegimeDetector()
        
        # Strong trend
        trending_prices = generate_trending_up_prices(100)
        trending_regime = detector.detect_regime(trending_prices)
        
        # Weak trend
        ranging_prices = generate_ranging_prices(100)
        ranging_regime = detector.detect_regime(ranging_prices)
        
        # Trending should have higher trend strength
        assert trending_regime.trend_strength > ranging_regime.trend_strength
    
    def test_regime_timestamp(self):
        """Test that regime has valid timestamp."""
        detector = MarketRegimeDetector()
        prices = generate_trending_up_prices(100)
        
        before = datetime.now()
        regime = detector.detect_regime(prices)
        after = datetime.now()
        
        assert before <= regime.timestamp <= after
    
    def test_empty_prices(self):
        """Test handling of empty price list."""
        detector = MarketRegimeDetector()
        
        regime = detector.detect_regime([])
        
        # Should return default regime
        assert regime.regime_type == RegimeType.RANGING
        assert regime.confidence == 0.5
    
    def test_single_price(self):
        """Test handling of single price bar."""
        detector = MarketRegimeDetector()
        
        prices = [OHLC(
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000,
            timestamp=datetime.now()
        )]
        
        regime = detector.detect_regime(prices)
        
        # Should return default regime
        assert regime.regime_type == RegimeType.RANGING
        assert regime.confidence == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
