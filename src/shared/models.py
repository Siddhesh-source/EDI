"""Data models for the explainable algorithmic trading system."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Optional, Tuple


# News and Sentiment Models
@dataclass
class Article:
    """News article data model."""
    id: str
    title: str
    content: str
    source: str
    published_at: datetime
    symbols: List[str]


@dataclass
class SentimentScore:
    """Sentiment analysis result."""
    article_id: str
    score: float  # -1.0 to +1.0
    confidence: float  # 0.0 to 1.0
    keywords_positive: List[str]
    keywords_negative: List[str]
    timestamp: datetime


# Event Detection Models
class EventType(Enum):
    """Types of market events."""
    EARNINGS = "earnings"
    MERGER = "merger"
    ACQUISITION = "acquisition"
    BANKRUPTCY = "bankruptcy"
    REGULATORY = "regulatory"
    PRODUCT_LAUNCH = "product_launch"
    LEADERSHIP_CHANGE = "leadership_change"


@dataclass
class Event:
    """Market event detected from news."""
    id: str
    article_id: str
    event_type: EventType
    severity: float  # 0.0 to 1.0
    keywords: List[str]
    timestamp: datetime


# Technical Analysis Models
@dataclass
class OHLC:
    """Open-High-Low-Close price bar."""
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: datetime


@dataclass
class PriceData:
    """Price data for technical analysis."""
    symbol: str
    bars: List[OHLC]
    timestamp: datetime


@dataclass
class MACDResult:
    """MACD indicator result."""
    macd_line: float
    signal_line: float
    histogram: float


@dataclass
class BollingerBands:
    """Bollinger Bands indicator result."""
    upper: float
    middle: float
    lower: float


@dataclass
class IndicatorResults:
    """Technical indicator computation results."""
    rsi: float
    macd: MACDResult
    bollinger: BollingerBands
    sma_20: float
    sma_50: float
    ema_12: float
    ema_26: float
    atr: float


class TechnicalSignalType(Enum):
    """Technical signal types."""
    OVERBOUGHT = "overbought"
    OVERSOLD = "oversold"
    BULLISH_CROSS = "bullish_cross"
    BEARISH_CROSS = "bearish_cross"
    UPPER_BREACH = "upper_breach"
    LOWER_BREACH = "lower_breach"
    NEUTRAL = "neutral"


@dataclass
class TechnicalSignals:
    """Technical signals from indicators."""
    rsi_signal: TechnicalSignalType
    macd_signal: TechnicalSignalType
    bb_signal: TechnicalSignalType


# Market Regime Models
class RegimeType(Enum):
    """Market regime classifications."""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    CALM = "calm"


@dataclass
class MarketRegime:
    """Market regime detection result."""
    regime_type: RegimeType
    confidence: float  # 0.0 to 1.0
    volatility: float
    trend_strength: float
    timestamp: datetime


# Signal Aggregation Models
@dataclass
class AggregatedData:
    """Aggregated data from all sources."""
    sentiment_score: float
    technical_signals: TechnicalSignals
    regime: MarketRegime
    events: List[Event]
    timestamp: datetime


@dataclass
class CompositeMarketScore:
    """Composite Market Score (CMS) computation result."""
    score: float  # -100 to +100
    sentiment_component: float
    technical_component: float
    regime_component: float
    weights: Dict[str, float]
    timestamp: datetime


class TradingSignalType(Enum):
    """Trading signal types."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class Explanation:
    """Detailed explanation for trading signal."""
    summary: str
    sentiment_details: str
    technical_details: str
    regime_details: str
    event_details: str
    component_scores: Dict[str, float]


@dataclass
class TradingSignal:
    """Trading signal with explanation."""
    signal_type: TradingSignalType
    cms: CompositeMarketScore
    confidence: float
    explanation: Explanation
    timestamp: datetime


# Backtesting Models
@dataclass
class BacktestConfig:
    """Configuration for backtesting."""
    symbol: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    position_size: float
    cms_buy_threshold: float
    cms_sell_threshold: float


@dataclass
class Trade:
    """Trade record from backtesting or live trading."""
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    signal_type: TradingSignalType


@dataclass
class PerformanceMetrics:
    """Performance metrics for backtesting."""
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    avg_trade_duration: timedelta


@dataclass
class BacktestResult:
    """Backtesting result."""
    backtest_id: str
    config: BacktestConfig
    trades: List[Trade]
    metrics: PerformanceMetrics
    equity_curve: List[Tuple[datetime, float]]


# Order Execution Models
class OrderType(Enum):
    """Order types."""
    MARKET = "market"
    LIMIT = "limit"


class Side(Enum):
    """Order side."""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Order status."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    """Order for execution."""
    order_id: str
    symbol: str
    order_type: OrderType
    side: Side
    quantity: float
    price: Optional[float]
    status: OrderStatus
    signal_id: str
    timestamp: datetime
