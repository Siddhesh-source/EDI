"""
Pure Python implementation of technical indicators.
Fallback when C++ module is not available.
Optimized for correctness over speed.
"""

import math
from typing import List, Tuple
from dataclasses import dataclass

from src.shared.models import (
    OHLC,
    PriceData,
    IndicatorResults,
    TechnicalSignals,
    TechnicalSignalType,
    MACDResult,
    BollingerBands,
)


class PythonIndicatorEngine:
    """
    Pure Python implementation of technical indicators.
    
    This serves as a fallback when the C++ module is not available.
    All calculations follow standard technical analysis formulas.
    """
    
    @staticmethod
    def compute_sma(prices: List[float], period: int) -> float:
        """
        Compute Simple Moving Average.
        
        SMA = (P1 + P2 + ... + Pn) / n
        
        Args:
            prices: List of prices
            period: Number of periods
            
        Returns:
            SMA value
        """
        if len(prices) < period:
            raise ValueError(f"Insufficient data: need {period} prices, got {len(prices)}")
        
        recent_prices = prices[-period:]
        return sum(recent_prices) / period
    
    @staticmethod
    def compute_ema(prices: List[float], period: int) -> float:
        """
        Compute Exponential Moving Average.
        
        EMA = Price(t) × k + EMA(y) × (1 − k)
        where k = 2 / (period + 1)
        
        Args:
            prices: List of prices
            period: Number of periods
            
        Returns:
            EMA value
        """
        if len(prices) < period:
            raise ValueError(f"Insufficient data: need {period} prices, got {len(prices)}")
        
        # Start with SMA as initial EMA
        ema = sum(prices[:period]) / period
        
        # Calculate multiplier
        multiplier = 2.0 / (period + 1.0)
        
        # Calculate EMA for remaining prices
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    @staticmethod
    def compute_rsi(prices: List[float], period: int = 14) -> float:
        """
        Compute Relative Strength Index.
        
        RSI = 100 - (100 / (1 + RS))
        where RS = Average Gain / Average Loss
        
        Args:
            prices: List of prices
            period: RSI period (default: 14)
            
        Returns:
            RSI value (0-100)
        """
        if len(prices) < period + 1:
            raise ValueError(f"Insufficient data: need {period + 1} prices, got {len(prices)}")
        
        # Calculate price changes
        changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        # Separate gains and losses
        gains = [max(change, 0.0) for change in changes]
        losses = [abs(min(change, 0.0)) for change in changes]
        
        # Calculate initial average gain and loss
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        # Calculate smoothed averages for remaining periods
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        # Calculate RSI
        if avg_loss == 0.0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
        
        return rsi
    
    @staticmethod
    def compute_macd(
        prices: List[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> MACDResult:
        """
        Compute MACD (Moving Average Convergence Divergence).
        
        MACD Line = EMA(12) - EMA(26)
        Signal Line = EMA(9) of MACD Line
        Histogram = MACD Line - Signal Line
        
        Args:
            prices: List of prices
            fast_period: Fast EMA period (default: 12)
            slow_period: Slow EMA period (default: 26)
            signal_period: Signal line EMA period (default: 9)
            
        Returns:
            MACDResult with macd_line, signal_line, and histogram
        """
        if len(prices) < slow_period + signal_period:
            raise ValueError(
                f"Insufficient data: need {slow_period + signal_period} prices, "
                f"got {len(prices)}"
            )
        
        # Calculate fast and slow EMAs
        fast_ema = PythonIndicatorEngine.compute_ema(prices, fast_period)
        slow_ema = PythonIndicatorEngine.compute_ema(prices, slow_period)
        
        # MACD line
        macd_line = fast_ema - slow_ema
        
        # Build MACD history for signal line
        macd_history = []
        for i in range(slow_period, len(prices) + 1):
            subset = prices[:i]
            f_ema = PythonIndicatorEngine.compute_ema(subset, fast_period)
            s_ema = PythonIndicatorEngine.compute_ema(subset, slow_period)
            macd_history.append(f_ema - s_ema)
        
        # Signal line (EMA of MACD)
        if len(macd_history) >= signal_period:
            signal_line = PythonIndicatorEngine.compute_ema(macd_history, signal_period)
        else:
            signal_line = macd_line
        
        # Histogram
        histogram = macd_line - signal_line
        
        return MACDResult(
            macd_line=macd_line,
            signal_line=signal_line,
            histogram=histogram
        )
    
    @staticmethod
    def compute_bollinger_bands(
        prices: List[float],
        period: int = 20,
        std_dev: float = 2.0
    ) -> BollingerBands:
        """
        Compute Bollinger Bands.
        
        Middle Band = SMA(20)
        Upper Band = Middle Band + (2 × Standard Deviation)
        Lower Band = Middle Band - (2 × Standard Deviation)
        
        Args:
            prices: List of prices
            period: Period for SMA (default: 20)
            std_dev: Number of standard deviations (default: 2.0)
            
        Returns:
            BollingerBands with upper, middle, and lower bands
        """
        if len(prices) < period:
            raise ValueError(f"Insufficient data: need {period} prices, got {len(prices)}")
        
        # Middle band (SMA)
        middle = PythonIndicatorEngine.compute_sma(prices, period)
        
        # Calculate standard deviation
        recent_prices = prices[-period:]
        variance = sum((p - middle) ** 2 for p in recent_prices) / period
        std = math.sqrt(variance)
        
        # Upper and lower bands
        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)
        
        return BollingerBands(
            upper=upper,
            middle=middle,
            lower=lower
        )
    
    @staticmethod
    def compute_atr(bars: List[OHLC], period: int = 14) -> float:
        """
        Compute Average True Range.
        
        True Range = max(High - Low, |High - Previous Close|, |Low - Previous Close|)
        ATR = SMA of True Range
        
        Args:
            bars: List of OHLC bars
            period: ATR period (default: 14)
            
        Returns:
            ATR value
        """
        if len(bars) < period + 1:
            raise ValueError(f"Insufficient data: need {period + 1} bars, got {len(bars)}")
        
        # Calculate true ranges
        true_ranges = []
        for i in range(1, len(bars)):
            high_low = bars[i].high - bars[i].low
            high_close = abs(bars[i].high - bars[i-1].close)
            low_close = abs(bars[i].low - bars[i-1].close)
            
            tr = max(high_low, high_close, low_close)
            true_ranges.append(tr)
        
        # ATR is SMA of true ranges
        return PythonIndicatorEngine.compute_sma(true_ranges, period)
    
    @staticmethod
    def compute_indicators(price_data: PriceData) -> IndicatorResults:
        """
        Compute all technical indicators.
        
        Args:
            price_data: Price data with OHLC bars
            
        Returns:
            IndicatorResults with all computed indicators
        """
        if not price_data.bars:
            raise ValueError("Empty price data")
        
        if len(price_data.bars) < 50:
            raise ValueError(f"Insufficient data: need at least 50 bars, got {len(price_data.bars)}")
        
        # Extract close prices
        closes = [bar.close for bar in price_data.bars]
        
        # Compute all indicators
        rsi = PythonIndicatorEngine.compute_rsi(closes, 14)
        macd = PythonIndicatorEngine.compute_macd(closes, 12, 26, 9)
        bollinger = PythonIndicatorEngine.compute_bollinger_bands(closes, 20, 2.0)
        sma_20 = PythonIndicatorEngine.compute_sma(closes, 20)
        sma_50 = PythonIndicatorEngine.compute_sma(closes, 50)
        ema_12 = PythonIndicatorEngine.compute_ema(closes, 12)
        ema_20 = PythonIndicatorEngine.compute_ema(closes, 20)
        ema_26 = PythonIndicatorEngine.compute_ema(closes, 26)
        ema_50 = PythonIndicatorEngine.compute_ema(closes, 50)
        atr = PythonIndicatorEngine.compute_atr(price_data.bars, 14)
        
        return IndicatorResults(
            rsi=rsi,
            macd=macd,
            bollinger=bollinger,
            sma_20=sma_20,
            sma_50=sma_50,
            ema_12=ema_12,
            ema_26=ema_26,
            atr=atr,
            # Additional EMAs
            ema_20=ema_20,
            ema_50=ema_50
        )
    
    @staticmethod
    def generate_signals(indicators: IndicatorResults, current_price: float) -> TechnicalSignals:
        """
        Generate trading signals based on indicators.
        
        Args:
            indicators: Computed indicator results
            current_price: Current market price
            
        Returns:
            TechnicalSignals with RSI, MACD, and Bollinger Band signals
        """
        # RSI signals
        if indicators.rsi > 70.0:
            rsi_signal = TechnicalSignalType.OVERBOUGHT
        elif indicators.rsi < 30.0:
            rsi_signal = TechnicalSignalType.OVERSOLD
        else:
            rsi_signal = TechnicalSignalType.NEUTRAL
        
        # MACD signals (histogram crossover)
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
            bb_signal=bb_signal
        )


# Convenience functions for direct use
def compute_sma(prices: List[float], period: int) -> float:
    """Compute Simple Moving Average."""
    return PythonIndicatorEngine.compute_sma(prices, period)


def compute_ema(prices: List[float], period: int) -> float:
    """Compute Exponential Moving Average."""
    return PythonIndicatorEngine.compute_ema(prices, period)


def compute_rsi(prices: List[float], period: int = 14) -> float:
    """Compute Relative Strength Index."""
    return PythonIndicatorEngine.compute_rsi(prices, period)


def compute_macd(
    prices: List[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> MACDResult:
    """Compute MACD."""
    return PythonIndicatorEngine.compute_macd(prices, fast_period, slow_period, signal_period)


def compute_bollinger_bands(
    prices: List[float],
    period: int = 20,
    std_dev: float = 2.0
) -> BollingerBands:
    """Compute Bollinger Bands."""
    return PythonIndicatorEngine.compute_bollinger_bands(prices, period, std_dev)


def compute_atr(bars: List[OHLC], period: int = 14) -> float:
    """Compute Average True Range."""
    return PythonIndicatorEngine.compute_atr(bars, period)
