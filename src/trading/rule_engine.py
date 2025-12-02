"""
Rule-Based Trading Engine
No ML - Pure rule-based logic with risk management.

BUY LOGIC:
- EMA20 > EMA50
- SentimentIndex > 0.2
- CMS > 0.3
- No negative event keywords detected

SELL LOGIC:
- EMA20 < EMA50
- SentimentIndex < -0.3
- CMS < -0.3
- EventShockFactor < -1

RISK MANAGEMENT:
- ATR-based dynamic stop-loss
- Trailing stop-loss
- Fixed 1% capital risk per trade
- Position sizing formula
"""

import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
import json

from src.shared.redis_client import get_redis_client
from src.database.connection import get_db_session

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Trading signal types."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    CLOSE_LONG = "CLOSE_LONG"
    CLOSE_SHORT = "CLOSE_SHORT"


@dataclass
class MarketData:
    """Market data inputs for trading decisions."""
    symbol: str
    current_price: float
    ema_20: float
    ema_50: float
    atr: float
    sentiment_index: float
    cms_score: float
    event_shock_factor: float
    negative_events: List[str]
    timestamp: datetime


@dataclass
class RiskParameters:
    """Risk management parameters."""
    account_balance: float
    risk_per_trade_pct: float = 0.01  # 1% risk per trade
    atr_stop_multiplier: float = 2.0   # Stop loss = 2 × ATR
    trailing_stop_pct: float = 0.02    # 2% trailing stop
    max_position_size_pct: float = 0.1  # Max 10% of account per position
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class PositionSize:
    """Position sizing calculation result."""
    shares: int
    position_value: float
    risk_amount: float
    stop_loss_price: float
    take_profit_price: Optional[float]
    risk_reward_ratio: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class TradingSignal:
    """Trading signal with full context."""
    signal_type: SignalType
    symbol: str
    price: float
    confidence: float
    position_size: Optional[PositionSize]
    reasons: List[str]
    risk_params: RiskParameters
    market_data: MarketData
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'signal_type': self.signal_type.value,
            'symbol': self.symbol,
            'price': round(self.price, 2),
            'confidence': round(self.confidence, 4),
            'position_size': self.position_size.to_dict() if self.position_size else None,
            'reasons': self.reasons,
            'risk_params': self.risk_params.to_dict(),
            'market_data': {
                'ema_20': round(self.market_data.ema_20, 2),
                'ema_50': round(self.market_data.ema_50, 2),
                'atr': round(self.market_data.atr, 2),
                'sentiment_index': round(self.market_data.sentiment_index, 4),
                'cms_score': round(self.market_data.cms_score, 2),
                'event_shock_factor': round(self.market_data.event_shock_factor, 4),
                'negative_events': self.market_data.negative_events
            },
            'timestamp': self.timestamp.isoformat()
        }


class RuleBasedTradingEngine:
    """
    Rule-based trading engine with no ML.
    
    Uses pure technical and sentiment rules for signal generation
    with comprehensive risk management.
    """
    
    # BUY thresholds
    BUY_SENTIMENT_THRESHOLD = 0.2
    BUY_CMS_THRESHOLD = 0.3
    
    # SELL thresholds
    SELL_SENTIMENT_THRESHOLD = -0.3
    SELL_CMS_THRESHOLD = -0.3
    SELL_EVENT_SHOCK_THRESHOLD = -1.0
    
    # Negative event keywords
    NEGATIVE_KEYWORDS = [
        'bankruptcy', 'fraud', 'lawsuit', 'investigation',
        'scandal', 'layoff', 'downgrade', 'warning',
        'loss', 'decline', 'plunge', 'crash'
    ]
    
    def __init__(
        self,
        risk_params: RiskParameters,
        redis_channel: str = "trading.signals"
    ):
        """
        Initialize trading engine.
        
        Args:
            risk_params: Risk management parameters
            redis_channel: Redis channel for signal publishing
        """
        self.risk_params = risk_params
        self.redis_channel = redis_channel
        
        logger.info(
            f"Trading Engine initialized with {risk_params.risk_per_trade_pct:.1%} "
            f"risk per trade"
        )
    
    def generate_signal(self, market_data: MarketData) -> TradingSignal:
        """
        Generate trading signal based on rules.
        
        Args:
            market_data: Current market data
            
        Returns:
            TradingSignal with decision and context
        """
        reasons = []
        
        # Check BUY conditions
        buy_conditions = self._check_buy_conditions(market_data, reasons)
        
        # Check SELL conditions
        sell_conditions = self._check_sell_conditions(market_data, reasons)
        
        # Determine signal
        if buy_conditions['all_met']:
            signal_type = SignalType.BUY
            confidence = buy_conditions['confidence']
            position_size = self._calculate_position_size(
                market_data.current_price,
                market_data.atr,
                is_long=True
            )
        elif sell_conditions['all_met']:
            signal_type = SignalType.SELL
            confidence = sell_conditions['confidence']
            position_size = self._calculate_position_size(
                market_data.current_price,
                market_data.atr,
                is_long=False
            )
        else:
            signal_type = SignalType.HOLD
            confidence = 0.0
            position_size = None
            reasons.append("Conditions not met for BUY or SELL")
        
        signal = TradingSignal(
            signal_type=signal_type,
            symbol=market_data.symbol,
            price=market_data.current_price,
            confidence=confidence,
            position_size=position_size,
            reasons=reasons,
            risk_params=self.risk_params,
            market_data=market_data,
            timestamp=datetime.utcnow()
        )
        
        logger.info(
            f"Signal generated for {market_data.symbol}: {signal_type.value} "
            f"(confidence={confidence:.2%})"
        )
        
        return signal
    
    def _check_buy_conditions(
        self,
        data: MarketData,
        reasons: List[str]
    ) -> Dict[str, Any]:
        """
        Check all BUY conditions.
        
        BUY LOGIC:
        1. EMA20 > EMA50 (uptrend)
        2. SentimentIndex > 0.2 (positive sentiment)
        3. CMS > 0.3 (positive composite score)
        4. No negative event keywords detected
        
        Args:
            data: Market data
            reasons: List to append reasons to
            
        Returns:
            Dict with 'all_met' bool and 'confidence' float
        """
        conditions_met = []
        
        # 1. Check trend (EMA20 > EMA50)
        trend_bullish = data.ema_20 > data.ema_50
        conditions_met.append(trend_bullish)
        if trend_bullish:
            trend_strength = (data.ema_20 - data.ema_50) / data.ema_50
            reasons.append(
                f"[+] Bullish trend: EMA20 ({data.ema_20:.2f}) > "
                f"EMA50 ({data.ema_50:.2f}) by {trend_strength:.2%}"
            )
        else:
            reasons.append(
                f"[-] No bullish trend: EMA20 ({data.ema_20:.2f}) <= "
                f"EMA50 ({data.ema_50:.2f})"
            )
        
        # 2. Check sentiment
        sentiment_positive = data.sentiment_index > self.BUY_SENTIMENT_THRESHOLD
        conditions_met.append(sentiment_positive)
        if sentiment_positive:
            reasons.append(
                f"[+] Positive sentiment: {data.sentiment_index:.3f} > "
                f"{self.BUY_SENTIMENT_THRESHOLD}"
            )
        else:
            reasons.append(
                f"[-] Insufficient sentiment: {data.sentiment_index:.3f} <= "
                f"{self.BUY_SENTIMENT_THRESHOLD}"
            )
        
        # 3. Check CMS
        cms_positive = data.cms_score > self.BUY_CMS_THRESHOLD
        conditions_met.append(cms_positive)
        if cms_positive:
            reasons.append(
                f"[+] Positive CMS: {data.cms_score:.2f} > "
                f"{self.BUY_CMS_THRESHOLD}"
            )
        else:
            reasons.append(
                f"[-] Insufficient CMS: {data.cms_score:.2f} <= "
                f"{self.BUY_CMS_THRESHOLD}"
            )
        
        # 4. Check for negative events
        has_negative_events = any(
            keyword in event.lower()
            for event in data.negative_events
            for keyword in self.NEGATIVE_KEYWORDS
        )
        no_negative_events = not has_negative_events
        conditions_met.append(no_negative_events)
        if no_negative_events:
            reasons.append("[+] No negative events detected")
        else:
            reasons.append(
                f"[-] Negative events detected: {data.negative_events}"
            )
        
        # Calculate confidence based on how strongly conditions are met
        all_met = all(conditions_met)
        if all_met:
            # Confidence based on strength of signals
            sentiment_strength = min(data.sentiment_index / 1.0, 1.0)
            cms_strength = min(data.cms_score / 100.0, 1.0)
            trend_strength = min((data.ema_20 - data.ema_50) / data.ema_50 / 0.1, 1.0)
            
            confidence = (
                sentiment_strength * 0.4 +
                cms_strength * 0.3 +
                trend_strength * 0.2 +
                (1.0 if no_negative_events else 0.0) * 0.1
            )
        else:
            confidence = 0.0
        
        return {
            'all_met': all_met,
            'confidence': confidence,
            'conditions_met': sum(conditions_met),
            'total_conditions': len(conditions_met)
        }
    
    def _check_sell_conditions(
        self,
        data: MarketData,
        reasons: List[str]
    ) -> Dict[str, Any]:
        """
        Check all SELL conditions.
        
        SELL LOGIC:
        1. EMA20 < EMA50 (downtrend)
        2. SentimentIndex < -0.3 (negative sentiment)
        3. CMS < -0.3 (negative composite score)
        4. EventShockFactor < -1 (significant negative event)
        
        Args:
            data: Market data
            reasons: List to append reasons to
            
        Returns:
            Dict with 'all_met' bool and 'confidence' float
        """
        conditions_met = []
        
        # 1. Check trend (EMA20 < EMA50)
        trend_bearish = data.ema_20 < data.ema_50
        conditions_met.append(trend_bearish)
        if trend_bearish:
            trend_strength = (data.ema_50 - data.ema_20) / data.ema_50
            reasons.append(
                f"[+] Bearish trend: EMA20 ({data.ema_20:.2f}) < "
                f"EMA50 ({data.ema_50:.2f}) by {trend_strength:.2%}"
            )
        else:
            reasons.append(
                f"[-] No bearish trend: EMA20 ({data.ema_20:.2f}) >= "
                f"EMA50 ({data.ema_50:.2f})"
            )
        
        # 2. Check sentiment
        sentiment_negative = data.sentiment_index < self.SELL_SENTIMENT_THRESHOLD
        conditions_met.append(sentiment_negative)
        if sentiment_negative:
            reasons.append(
                f"[+] Negative sentiment: {data.sentiment_index:.3f} < "
                f"{self.SELL_SENTIMENT_THRESHOLD}"
            )
        else:
            reasons.append(
                f"[-] Insufficient negative sentiment: {data.sentiment_index:.3f} >= "
                f"{self.SELL_SENTIMENT_THRESHOLD}"
            )
        
        # 3. Check CMS
        cms_negative = data.cms_score < self.SELL_CMS_THRESHOLD
        conditions_met.append(cms_negative)
        if cms_negative:
            reasons.append(
                f"[+] Negative CMS: {data.cms_score:.2f} < "
                f"{self.SELL_CMS_THRESHOLD}"
            )
        else:
            reasons.append(
                f"[-] Insufficient negative CMS: {data.cms_score:.2f} >= "
                f"{self.SELL_CMS_THRESHOLD}"
            )
        
        # 4. Check event shock
        event_shock_negative = data.event_shock_factor < self.SELL_EVENT_SHOCK_THRESHOLD
        conditions_met.append(event_shock_negative)
        if event_shock_negative:
            reasons.append(
                f"[+] Significant negative event: {data.event_shock_factor:.2f} < "
                f"{self.SELL_EVENT_SHOCK_THRESHOLD}"
            )
        else:
            reasons.append(
                f"[-] No significant negative event: {data.event_shock_factor:.2f} >= "
                f"{self.SELL_EVENT_SHOCK_THRESHOLD}"
            )
        
        # Calculate confidence
        all_met = all(conditions_met)
        if all_met:
            sentiment_strength = min(abs(data.sentiment_index) / 1.0, 1.0)
            cms_strength = min(abs(data.cms_score) / 100.0, 1.0)
            trend_strength = min((data.ema_50 - data.ema_20) / data.ema_50 / 0.1, 1.0)
            event_strength = min(abs(data.event_shock_factor) / 2.0, 1.0)
            
            confidence = (
                sentiment_strength * 0.3 +
                cms_strength * 0.3 +
                trend_strength * 0.2 +
                event_strength * 0.2
            )
        else:
            confidence = 0.0
        
        return {
            'all_met': all_met,
            'confidence': confidence,
            'conditions_met': sum(conditions_met),
            'total_conditions': len(conditions_met)
        }
    
    def _calculate_position_size(
        self,
        entry_price: float,
        atr: float,
        is_long: bool = True
    ) -> PositionSize:
        """
        Calculate position size based on risk parameters.
        
        Position Sizing Formula:
        1. Risk amount = Account Balance × Risk %
        2. Stop loss distance = ATR × Multiplier
        3. Shares = Risk Amount / Stop Loss Distance
        4. Position value capped at Max Position Size %
        
        Args:
            entry_price: Entry price for the trade
            atr: Average True Range
            is_long: True for long position, False for short
            
        Returns:
            PositionSize with all calculations
        """
        # 1. Calculate risk amount
        risk_amount = self.risk_params.account_balance * self.risk_params.risk_per_trade_pct
        
        # 2. Calculate stop loss distance
        stop_distance = atr * self.risk_params.atr_stop_multiplier
        
        # 3. Calculate stop loss price
        if is_long:
            stop_loss_price = entry_price - stop_distance
            take_profit_price = entry_price + (stop_distance * 2)  # 2:1 R:R
        else:
            stop_loss_price = entry_price + stop_distance
            take_profit_price = entry_price - (stop_distance * 2)
        
        # 4. Calculate shares based on risk
        shares = int(risk_amount / stop_distance)
        
        # 5. Calculate position value
        position_value = shares * entry_price
        
        # 6. Check max position size constraint
        max_position_value = self.risk_params.account_balance * self.risk_params.max_position_size_pct
        if position_value > max_position_value:
            shares = int(max_position_value / entry_price)
            position_value = shares * entry_price
        
        # 7. Calculate actual risk amount
        actual_risk = shares * stop_distance
        
        # 8. Calculate risk/reward ratio
        profit_potential = abs(take_profit_price - entry_price) * shares
        risk_reward_ratio = profit_potential / actual_risk if actual_risk > 0 else 0
        
        return PositionSize(
            shares=shares,
            position_value=position_value,
            risk_amount=actual_risk,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            risk_reward_ratio=risk_reward_ratio
        )
    
    def calculate_trailing_stop(
        self,
        entry_price: float,
        current_price: float,
        is_long: bool = True
    ) -> float:
        """
        Calculate trailing stop loss price.
        
        Args:
            entry_price: Original entry price
            current_price: Current market price
            is_long: True for long position
            
        Returns:
            Trailing stop price
        """
        if is_long:
            # For long: stop trails below price
            profit = current_price - entry_price
            if profit > 0:
                trailing_stop = current_price * (1 - self.risk_params.trailing_stop_pct)
            else:
                # Use initial stop if not in profit
                trailing_stop = entry_price * (1 - self.risk_params.trailing_stop_pct)
        else:
            # For short: stop trails above price
            profit = entry_price - current_price
            if profit > 0:
                trailing_stop = current_price * (1 + self.risk_params.trailing_stop_pct)
            else:
                trailing_stop = entry_price * (1 + self.risk_params.trailing_stop_pct)
        
        return trailing_stop
    
    def publish_to_redis(self, signal: TradingSignal) -> None:
        """
        Publish trading signal to Redis.
        
        Args:
            signal: Trading signal to publish
        """
        try:
            redis_client = get_redis_client()
            
            message = signal.to_dict()
            redis_client.publish(self.redis_channel, json.dumps(message))
            
            logger.debug(
                f"Published {signal.signal_type.value} signal for "
                f"{signal.symbol} to Redis"
            )
            
        except Exception as e:
            logger.error(f"Failed to publish signal to Redis: {e}")
    
    def store_to_database(self, signal: TradingSignal) -> None:
        """
        Store trading signal to PostgreSQL.
        
        Args:
            signal: Trading signal to store
        """
        try:
            with get_db_session() as session:
                session.execute("""
                    INSERT INTO trading_signals (
                        symbol, signal_type, price, confidence,
                        shares, position_value, risk_amount,
                        stop_loss_price, take_profit_price, risk_reward_ratio,
                        reasons, market_data, timestamp
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    signal.symbol,
                    signal.signal_type.value,
                    signal.price,
                    signal.confidence,
                    signal.position_size.shares if signal.position_size else None,
                    signal.position_size.position_value if signal.position_size else None,
                    signal.position_size.risk_amount if signal.position_size else None,
                    signal.position_size.stop_loss_price if signal.position_size else None,
                    signal.position_size.take_profit_price if signal.position_size else None,
                    signal.position_size.risk_reward_ratio if signal.position_size else None,
                    json.dumps(signal.reasons),
                    json.dumps(signal.to_dict()['market_data']),
                    signal.timestamp
                ))
                session.commit()
                
            logger.debug(f"Stored signal for {signal.symbol} to database")
            
        except Exception as e:
            logger.error(f"Failed to store signal to database: {e}")
