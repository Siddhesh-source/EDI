"""Python wrapper for C++ Technical Indicator Engine."""

from typing import List, Any, TYPE_CHECKING
from datetime import datetime
import sys
import os

# Add the indicators directory to the path to find the compiled module
sys.path.insert(0, os.path.dirname(__file__))

try:
    from indicators_engine import (
        TechnicalIndicatorEngine as CppEngine,
        OHLC as CppOHLC,
        PriceData as CppPriceData,
        IndicatorResults as CppIndicatorResults,
        TechnicalSignals as CppTechnicalSignals,
        SignalType as CppSignalType,
    )
    CPP_AVAILABLE = True
except ImportError:
    CPP_AVAILABLE = False
    # Define dummy types for type hints when C++ module is not available
    CppEngine = Any
    CppOHLC = Any
    CppPriceData = Any
    CppIndicatorResults = Any
    CppTechnicalSignals = Any
    CppSignalType = Any
    print("Warning: C++ indicators engine not available, using Python fallback")

from src.shared.models import (
    OHLC,
    PriceData,
    IndicatorResults,
    TechnicalSignals,
    TechnicalSignalType,
    MACDResult,
    BollingerBands,
)


class TechnicalIndicatorEngine:
    """
    Python wrapper for the C++ Technical Indicator Engine.
    
    Provides seamless conversion between Python data models and C++ structures,
    with automatic fallback to Python implementation if C++ module is unavailable.
    """
    
    def __init__(self):
        """Initialize the engine."""
        if CPP_AVAILABLE:
            self._engine = CppEngine()
            self._use_cpp = True
        else:
            self._use_cpp = False
    
    def _convert_ohlc_to_cpp(self, ohlc: OHLC) -> CppOHLC:
        """Convert Python OHLC to C++ OHLC."""
        cpp_ohlc = CppOHLC()
        cpp_ohlc.open = ohlc.open
        cpp_ohlc.high = ohlc.high
        cpp_ohlc.low = ohlc.low
        cpp_ohlc.close = ohlc.close
        cpp_ohlc.volume = ohlc.volume
        cpp_ohlc.timestamp = int(ohlc.timestamp.timestamp())
        return cpp_ohlc
    
    def _convert_price_data_to_cpp(self, price_data: PriceData) -> CppPriceData:
        """Convert Python PriceData to C++ PriceData."""
        cpp_data = CppPriceData()
        cpp_data.symbol = price_data.symbol
        cpp_data.bars = [self._convert_ohlc_to_cpp(bar) for bar in price_data.bars]
        cpp_data.timestamp = int(price_data.timestamp.timestamp())
        return cpp_data
    
    def _convert_cpp_results_to_python(self, cpp_results: CppIndicatorResults) -> IndicatorResults:
        """Convert C++ IndicatorResults to Python IndicatorResults."""
        macd = MACDResult(
            macd_line=cpp_results.macd.macd_line,
            signal_line=cpp_results.macd.signal_line,
            histogram=cpp_results.macd.histogram,
        )
        
        bollinger = BollingerBands(
            upper=cpp_results.bollinger.upper,
            middle=cpp_results.bollinger.middle,
            lower=cpp_results.bollinger.lower,
        )
        
        return IndicatorResults(
            rsi=cpp_results.rsi,
            macd=macd,
            bollinger=bollinger,
            sma_20=cpp_results.sma_20,
            sma_50=cpp_results.sma_50,
            ema_12=cpp_results.ema_12,
            ema_26=cpp_results.ema_26,
            atr=cpp_results.atr,
        )
    
    def _convert_cpp_signal_to_python(self, cpp_signal: CppSignalType) -> TechnicalSignalType:
        """Convert C++ SignalType to Python TechnicalSignalType."""
        signal_map = {
            CppSignalType.OVERBOUGHT: TechnicalSignalType.OVERBOUGHT,
            CppSignalType.OVERSOLD: TechnicalSignalType.OVERSOLD,
            CppSignalType.BULLISH_CROSS: TechnicalSignalType.BULLISH_CROSS,
            CppSignalType.BEARISH_CROSS: TechnicalSignalType.BEARISH_CROSS,
            CppSignalType.UPPER_BREACH: TechnicalSignalType.UPPER_BREACH,
            CppSignalType.LOWER_BREACH: TechnicalSignalType.LOWER_BREACH,
            CppSignalType.NEUTRAL: TechnicalSignalType.NEUTRAL,
        }
        return signal_map[cpp_signal]
    
    def _convert_cpp_signals_to_python(self, cpp_signals: CppTechnicalSignals) -> TechnicalSignals:
        """Convert C++ TechnicalSignals to Python TechnicalSignals."""
        return TechnicalSignals(
            rsi_signal=self._convert_cpp_signal_to_python(cpp_signals.rsi_signal),
            macd_signal=self._convert_cpp_signal_to_python(cpp_signals.macd_signal),
            bb_signal=self._convert_cpp_signal_to_python(cpp_signals.bb_signal),
        )
    
    def compute_indicators(self, price_data: PriceData) -> IndicatorResults:
        """
        Compute all technical indicators for the given price data.
        
        Args:
            price_data: Price data with OHLC bars
            
        Returns:
            IndicatorResults with all computed indicators
            
        Raises:
            ValueError: If insufficient data or invalid input
        """
        if not self._use_cpp:
            return self._compute_indicators_python(price_data)
        
        try:
            cpp_data = self._convert_price_data_to_cpp(price_data)
            cpp_results = self._engine.compute_indicators(cpp_data)
            return self._convert_cpp_results_to_python(cpp_results)
        except Exception as e:
            raise ValueError(f"Failed to compute indicators: {str(e)}")
    
    def generate_signals(self, indicators: IndicatorResults, current_price: float) -> TechnicalSignals:
        """
        Generate trading signals based on indicator values.
        
        Args:
            indicators: Computed indicator results
            current_price: Current market price
            
        Returns:
            TechnicalSignals with RSI, MACD, and Bollinger Band signals
        """
        if not self._use_cpp:
            return self._generate_signals_python(indicators, current_price)
        
        try:
            # Convert Python indicators to C++ format
            cpp_results = CppIndicatorResults()
            cpp_results.rsi = indicators.rsi
            cpp_results.macd.macd_line = indicators.macd.macd_line
            cpp_results.macd.signal_line = indicators.macd.signal_line
            cpp_results.macd.histogram = indicators.macd.histogram
            cpp_results.bollinger.upper = indicators.bollinger.upper
            cpp_results.bollinger.middle = indicators.bollinger.middle
            cpp_results.bollinger.lower = indicators.bollinger.lower
            cpp_results.sma_20 = indicators.sma_20
            cpp_results.sma_50 = indicators.sma_50
            cpp_results.ema_12 = indicators.ema_12
            cpp_results.ema_26 = indicators.ema_26
            cpp_results.atr = indicators.atr
            
            cpp_signals = self._engine.generate_signals(cpp_results, current_price)
            return self._convert_cpp_signals_to_python(cpp_signals)
        except Exception as e:
            raise ValueError(f"Failed to generate signals: {str(e)}")
    
    def _compute_indicators_python(self, price_data: PriceData) -> IndicatorResults:
        """Python fallback implementation for indicator computation."""
        # This is a simplified fallback - in production, you'd implement full Python versions
        raise NotImplementedError("Python fallback not yet implemented. Please build C++ module.")
    
    def _generate_signals_python(self, indicators: IndicatorResults, current_price: float) -> TechnicalSignals:
        """Python fallback implementation for signal generation."""
        # RSI signals
        if indicators.rsi > 70.0:
            rsi_signal = TechnicalSignalType.OVERBOUGHT
        elif indicators.rsi < 30.0:
            rsi_signal = TechnicalSignalType.OVERSOLD
        else:
            rsi_signal = TechnicalSignalType.NEUTRAL
        
        # MACD signals
        if indicators.macd.histogram > 0.0:
            macd_signal = TechnicalSignalType.BULLISH_CROSS
        elif indicators.macd.histogram < 0.0:
            macd_signal = TechnicalSignalType.BEARISH_CROSS
        else:
            macd_signal = TechnicalSignalType.NEUTRAL
        
        # Bollinger Bands signals
        if current_price > indicators.bollinger.upper:
            bb_signal = TechnicalSignalType.UPPER_BREACH
        elif current_price < indicators.bollinger.lower:
            bb_signal = TechnicalSignalType.LOWER_BREACH
        else:
            bb_signal = TechnicalSignalType.NEUTRAL
        
        return TechnicalSignals(
            rsi_signal=rsi_signal,
            macd_signal=macd_signal,
            bb_signal=bb_signal,
        )
