"""Unit tests for Technical Indicator Engine."""

import pytest
from datetime import datetime, timedelta
from src.shared.models import OHLC, PriceData, TechnicalSignalType
from src.indicators import TechnicalIndicatorEngine


@pytest.fixture
def sample_price_data():
    """Create sample price data for testing."""
    base_time = datetime.now()
    bars = []
    
    # Generate 100 bars with realistic price movement
    base_price = 100.0
    for i in range(100):
        # Simulate some price movement
        open_price = base_price + (i % 5) - 2
        high = open_price + 2.0
        low = open_price - 1.5
        close = open_price + (i % 3) - 1
        
        bars.append(OHLC(
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=1000 + i * 10,
            timestamp=base_time + timedelta(minutes=i)
        ))
        
        base_price = close
    
    return PriceData(
        symbol="TEST",
        bars=bars,
        timestamp=datetime.now()
    )


@pytest.fixture
def engine():
    """Create engine instance."""
    return TechnicalIndicatorEngine()


class TestTechnicalIndicatorEngine:
    """Test suite for Technical Indicator Engine."""
    
    def test_engine_initialization(self, engine):
        """Test that engine initializes correctly."""
        assert engine is not None
    
    def test_compute_indicators_basic(self, engine, sample_price_data):
        """Test basic indicator computation."""
        try:
            indicators = engine.compute_indicators(sample_price_data)
            
            # Verify all indicators are computed
            assert indicators.rsi is not None
            assert indicators.macd is not None
            assert indicators.bollinger is not None
            assert indicators.sma_20 is not None
            assert indicators.sma_50 is not None
            assert indicators.ema_12 is not None
            assert indicators.ema_26 is not None
            assert indicators.atr is not None
            
            # Verify RSI is in valid range
            assert 0 <= indicators.rsi <= 100
            
            # Verify Bollinger Bands ordering
            assert indicators.bollinger.upper > indicators.bollinger.middle
            assert indicators.bollinger.middle > indicators.bollinger.lower
            
            # Verify ATR is positive
            assert indicators.atr > 0
            
        except NotImplementedError:
            pytest.skip("C++ module not built, skipping test")
    
    def test_rsi_calculation(self, engine, sample_price_data):
        """Test RSI calculation with known data."""
        try:
            indicators = engine.compute_indicators(sample_price_data)
            
            # RSI should be between 0 and 100
            assert 0 <= indicators.rsi <= 100
            
        except NotImplementedError:
            pytest.skip("C++ module not built, skipping test")
    
    def test_macd_calculation(self, engine, sample_price_data):
        """Test MACD calculation."""
        try:
            indicators = engine.compute_indicators(sample_price_data)
            
            # MACD components should exist
            assert indicators.macd.macd_line is not None
            assert indicators.macd.signal_line is not None
            assert indicators.macd.histogram is not None
            
            # Histogram should equal macd_line - signal_line (approximately)
            expected_histogram = indicators.macd.macd_line - indicators.macd.signal_line
            assert abs(indicators.macd.histogram - expected_histogram) < 0.01
            
        except NotImplementedError:
            pytest.skip("C++ module not built, skipping test")
    
    def test_bollinger_bands_calculation(self, engine, sample_price_data):
        """Test Bollinger Bands calculation."""
        try:
            indicators = engine.compute_indicators(sample_price_data)
            
            # Bands should be properly ordered
            assert indicators.bollinger.upper > indicators.bollinger.middle
            assert indicators.bollinger.middle > indicators.bollinger.lower
            
            # Middle band should be close to SMA-20
            assert abs(indicators.bollinger.middle - indicators.sma_20) < 0.01
            
        except NotImplementedError:
            pytest.skip("C++ module not built, skipping test")
    
    def test_moving_averages(self, engine, sample_price_data):
        """Test SMA and EMA calculations."""
        try:
            indicators = engine.compute_indicators(sample_price_data)
            
            # All moving averages should be positive
            assert indicators.sma_20 > 0
            assert indicators.sma_50 > 0
            assert indicators.ema_12 > 0
            assert indicators.ema_26 > 0
            
            # EMA-12 should be more responsive than EMA-26
            # (This is a general property, not always true for specific data)
            
        except NotImplementedError:
            pytest.skip("C++ module not built, skipping test")
    
    def test_atr_calculation(self, engine, sample_price_data):
        """Test ATR calculation."""
        try:
            indicators = engine.compute_indicators(sample_price_data)
            
            # ATR should be positive
            assert indicators.atr > 0
            
        except NotImplementedError:
            pytest.skip("C++ module not built, skipping test")
    
    def test_generate_signals_rsi_overbought(self, engine, sample_price_data):
        """Test RSI overbought signal generation."""
        try:
            indicators = engine.compute_indicators(sample_price_data)
            
            # Manually set RSI to overbought
            indicators.rsi = 75.0
            
            current_price = sample_price_data.bars[-1].close
            signals = engine.generate_signals(indicators, current_price)
            
            assert signals.rsi_signal == TechnicalSignalType.OVERBOUGHT
            
        except NotImplementedError:
            pytest.skip("C++ module not built, skipping test")
    
    def test_generate_signals_rsi_oversold(self, engine, sample_price_data):
        """Test RSI oversold signal generation."""
        try:
            indicators = engine.compute_indicators(sample_price_data)
            
            # Manually set RSI to oversold
            indicators.rsi = 25.0
            
            current_price = sample_price_data.bars[-1].close
            signals = engine.generate_signals(indicators, current_price)
            
            assert signals.rsi_signal == TechnicalSignalType.OVERSOLD
            
        except NotImplementedError:
            pytest.skip("C++ module not built, skipping test")
    
    def test_generate_signals_bollinger_breach(self, engine, sample_price_data):
        """Test Bollinger Bands breach signal generation."""
        try:
            indicators = engine.compute_indicators(sample_price_data)
            
            # Test upper breach
            upper_price = indicators.bollinger.upper + 1.0
            signals = engine.generate_signals(indicators, upper_price)
            assert signals.bb_signal == TechnicalSignalType.UPPER_BREACH
            
            # Test lower breach
            lower_price = indicators.bollinger.lower - 1.0
            signals = engine.generate_signals(indicators, lower_price)
            assert signals.bb_signal == TechnicalSignalType.LOWER_BREACH
            
            # Test neutral
            neutral_price = indicators.bollinger.middle
            signals = engine.generate_signals(indicators, neutral_price)
            assert signals.bb_signal == TechnicalSignalType.NEUTRAL
            
        except NotImplementedError:
            pytest.skip("C++ module not built, skipping test")
    
    def test_insufficient_data_error(self, engine):
        """Test that insufficient data raises an error."""
        # Create price data with only 10 bars (need 50+)
        bars = []
        base_time = datetime.now()
        for i in range(10):
            bars.append(OHLC(
                open=100.0,
                high=102.0,
                low=99.0,
                close=101.0,
                volume=1000,
                timestamp=base_time + timedelta(minutes=i)
            ))
        
        price_data = PriceData(
            symbol="TEST",
            bars=bars,
            timestamp=datetime.now()
        )
        
        try:
            with pytest.raises(ValueError, match="Insufficient data"):
                engine.compute_indicators(price_data)
        except NotImplementedError:
            pytest.skip("C++ module not built, skipping test")
    
    def test_empty_data_error(self, engine):
        """Test that empty data raises an error."""
        price_data = PriceData(
            symbol="TEST",
            bars=[],
            timestamp=datetime.now()
        )
        
        try:
            with pytest.raises(ValueError, match="Empty price data"):
                engine.compute_indicators(price_data)
        except NotImplementedError:
            pytest.skip("C++ module not built, skipping test")


class TestIndicatorBounds:
    """Test indicator value bounds and constraints."""
    
    def test_rsi_bounds(self, engine, sample_price_data):
        """Test that RSI stays within [0, 100] bounds."""
        try:
            indicators = engine.compute_indicators(sample_price_data)
            assert 0 <= indicators.rsi <= 100
        except NotImplementedError:
            pytest.skip("C++ module not built, skipping test")
    
    def test_bollinger_bands_ordering(self, engine, sample_price_data):
        """Test that Bollinger Bands maintain proper ordering."""
        try:
            indicators = engine.compute_indicators(sample_price_data)
            assert indicators.bollinger.lower < indicators.bollinger.middle < indicators.bollinger.upper
        except NotImplementedError:
            pytest.skip("C++ module not built, skipping test")
    
    def test_atr_positive(self, engine, sample_price_data):
        """Test that ATR is always positive."""
        try:
            indicators = engine.compute_indicators(sample_price_data)
            assert indicators.atr > 0
        except NotImplementedError:
            pytest.skip("C++ module not built, skipping test")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
