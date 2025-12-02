"""Backtesting engine for strategy validation."""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.database.connection import DatabaseConnection
from src.database.repositories import (
    BacktestResultRepository, PriceRepository, SentimentScoreRepository,
    EventRepository, TradingSignalRepository
)
from src.shared.models import (
    BacktestConfig, BacktestResult, Trade, PerformanceMetrics,
    TradingSignalType, OHLC, CompositeMarketScore, TradingSignal,
    Explanation, AggregatedData, TechnicalSignals, MarketRegime,
    Event, EventType, RegimeType, TechnicalSignalType
)

logger = logging.getLogger(__name__)


class BacktestingModule:
    """Backtesting module for historical strategy validation."""
    
    def __init__(self, db_connection: DatabaseConnection):
        """Initialize backtesting module.
        
        Args:
            db_connection: Database connection instance
        """
        self.db_connection = db_connection
        logger.info("Backtesting module initialized")
    
    def run_backtest(self, config: BacktestConfig) -> BacktestResult:
        """Run a complete backtest with the given configuration.
        
        Args:
            config: Backtest configuration
            
        Returns:
            BacktestResult with trades, metrics, and equity curve
        """
        logger.info(
            f"Starting backtest for {config.symbol} from {config.start_date} "
            f"to {config.end_date}"
        )
        
        # Load historical data
        historical_data = self.load_historical_data(
            config.symbol,
            config.start_date,
            config.end_date
        )
        
        if not historical_data:
            logger.warning("No historical data found for backtest")
            return self._create_empty_result(config)
        
        # Simulate trading
        trades, equity_curve = self.simulate_trading(historical_data, config)
        
        # Compute performance metrics
        metrics = self.compute_metrics(trades, config.initial_capital, equity_curve)
        
        # Create backtest result
        backtest_id = str(uuid.uuid4())
        result = BacktestResult(
            backtest_id=backtest_id,
            config=config,
            trades=trades,
            metrics=metrics,
            equity_curve=equity_curve
        )
        
        # Store result in database
        self._store_result(result)
        
        logger.info(
            f"Backtest completed: {metrics.total_trades} trades, "
            f"{metrics.total_return:.2%} return, "
            f"Sharpe: {metrics.sharpe_ratio:.2f}"
        )
        
        return result
    
    def load_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[datetime, Dict]:
        """Load historical price and signal data from PostgreSQL.
        
        Args:
            symbol: Stock symbol
            start_date: Start date for historical data
            end_date: End date for historical data
            
        Returns:
            Dictionary mapping timestamps to data containing prices and signals
        """
        logger.info(f"Loading historical data for {symbol}")
        
        with self.db_connection.get_session() as session:
            # Load price data
            price_repo = PriceRepository(session)
            prices = price_repo.get_by_symbol_and_timerange(
                symbol, start_date, end_date
            )
            
            # Load sentiment scores
            sentiment_repo = SentimentScoreRepository(session)
            sentiments = sentiment_repo.get_by_timerange(start_date, end_date)
            
            # Load events
            event_repo = EventRepository(session)
            events = event_repo.get_by_timerange(start_date, end_date)
            
            # Load trading signals (if any exist from previous runs)
            signal_repo = TradingSignalRepository(session)
            signals = signal_repo.get_by_timerange(start_date, end_date)
        
        # Organize data by timestamp
        historical_data = {}
        
        # Add price data
        for price in prices:
            ts = price.timestamp
            if ts not in historical_data:
                historical_data[ts] = {
                    'price': None,
                    'sentiment': None,
                    'events': [],
                    'signal': None
                }
            
            historical_data[ts]['price'] = OHLC(
                open=float(price.open),
                high=float(price.high),
                low=float(price.low),
                close=float(price.close),
                volume=int(price.volume),
                timestamp=price.timestamp
            )
        
        # Add sentiment data (aggregate by timestamp)
        sentiment_by_time = {}
        for sentiment in sentiments:
            ts = sentiment.timestamp
            if ts not in sentiment_by_time:
                sentiment_by_time[ts] = []
            sentiment_by_time[ts].append(float(sentiment.score))
        
        # Average sentiment scores for each timestamp
        for ts, scores in sentiment_by_time.items():
            if ts in historical_data:
                historical_data[ts]['sentiment'] = np.mean(scores)
        
        # Add event data
        for event in events:
            ts = event.timestamp
            if ts in historical_data:
                historical_data[ts]['events'].append(Event(
                    id=event.id,
                    article_id=event.article_id,
                    event_type=EventType(event.event_type),
                    severity=float(event.severity),
                    keywords=event.keywords,
                    timestamp=event.timestamp
                ))
        
        # Add signal data (if available)
        for signal in signals:
            ts = signal.timestamp
            if ts in historical_data:
                historical_data[ts]['signal'] = signal
        
        logger.info(f"Loaded {len(historical_data)} data points")
        return historical_data
    
    def simulate_trading(
        self,
        historical_data: Dict[datetime, Dict],
        config: BacktestConfig
    ) -> Tuple[List[Trade], List[Tuple[datetime, float]]]:
        """Simulate trading based on historical data and configuration.
        
        This method replays data chronologically without look-ahead bias.
        
        Args:
            historical_data: Historical price and signal data
            config: Backtest configuration
            
        Returns:
            Tuple of (trades list, equity curve)
        """
        logger.info("Starting trade simulation")
        
        # Sort timestamps chronologically to prevent look-ahead bias
        sorted_timestamps = sorted(historical_data.keys())
        
        trades: List[Trade] = []
        equity_curve: List[Tuple[datetime, float]] = []
        
        current_capital = config.initial_capital
        current_position: Optional[Dict] = None  # {entry_time, entry_price, quantity}
        
        # Track equity at each timestamp
        equity_curve.append((sorted_timestamps[0], current_capital))
        
        for timestamp in sorted_timestamps:
            data = historical_data[timestamp]
            price_data = data.get('price')
            
            if price_data is None:
                continue
            
            current_price = price_data.close
            
            # Calculate current equity (capital + position value)
            current_equity = current_capital
            if current_position is not None:
                position_value = current_position['quantity'] * current_price
                current_equity = current_capital + position_value
            
            equity_curve.append((timestamp, current_equity))
            
            # Generate signal based on available data
            signal = self._generate_signal_from_data(data, config, timestamp)
            
            # Execute trading logic
            if signal == TradingSignalType.BUY and current_position is None:
                # Enter long position
                quantity = (current_capital * config.position_size) / current_price
                current_position = {
                    'entry_time': timestamp,
                    'entry_price': current_price,
                    'quantity': quantity
                }
                current_capital -= quantity * current_price
                logger.debug(
                    f"BUY at {timestamp}: {quantity:.2f} @ {current_price:.2f}"
                )
            
            elif signal == TradingSignalType.SELL and current_position is not None:
                # Exit long position
                exit_value = current_position['quantity'] * current_price
                current_capital += exit_value
                
                pnl = exit_value - (current_position['quantity'] * current_position['entry_price'])
                
                trade = Trade(
                    entry_time=current_position['entry_time'],
                    exit_time=timestamp,
                    entry_price=current_position['entry_price'],
                    exit_price=current_price,
                    quantity=current_position['quantity'],
                    pnl=pnl,
                    signal_type=TradingSignalType.BUY  # Entry signal type
                )
                trades.append(trade)
                
                logger.debug(
                    f"SELL at {timestamp}: {current_position['quantity']:.2f} @ "
                    f"{current_price:.2f}, PnL: {pnl:.2f}"
                )
                
                current_position = None
        
        # Close any open position at the end
        if current_position is not None:
            final_timestamp = sorted_timestamps[-1]
            final_price = historical_data[final_timestamp]['price'].close
            exit_value = current_position['quantity'] * final_price
            current_capital += exit_value
            
            pnl = exit_value - (current_position['quantity'] * current_position['entry_price'])
            
            trade = Trade(
                entry_time=current_position['entry_time'],
                exit_time=final_timestamp,
                entry_price=current_position['entry_price'],
                exit_price=final_price,
                quantity=current_position['quantity'],
                pnl=pnl,
                signal_type=TradingSignalType.BUY
            )
            trades.append(trade)
            
            logger.debug(f"Closed final position: PnL {pnl:.2f}")
        
        logger.info(f"Simulation completed: {len(trades)} trades executed")
        return trades, equity_curve
    
    def _generate_signal_from_data(
        self,
        data: Dict,
        config: BacktestConfig,
        timestamp: datetime
    ) -> TradingSignalType:
        """Generate trading signal from available data.
        
        This is a simplified signal generation for backtesting.
        In production, this would use the full signal aggregator.
        
        Args:
            data: Data point containing price, sentiment, events
            config: Backtest configuration
            timestamp: Current timestamp
            
        Returns:
            Trading signal type
        """
        # If we have a pre-computed signal, use it
        if data.get('signal') is not None:
            signal = data['signal']
            return TradingSignalType(signal.signal_type)
        
        # Otherwise, compute a simple CMS-based signal
        cms_score = self._compute_simple_cms(data)
        
        if cms_score > config.cms_buy_threshold:
            return TradingSignalType.BUY
        elif cms_score < config.cms_sell_threshold:
            return TradingSignalType.SELL
        else:
            return TradingSignalType.HOLD
    
    def _compute_simple_cms(self, data: Dict) -> float:
        """Compute a simple CMS score from available data.
        
        Args:
            data: Data point containing sentiment and events
            
        Returns:
            CMS score between -100 and 100
        """
        # Simple weighted combination
        sentiment_weight = 0.5
        event_weight = 0.5
        
        # Sentiment component
        sentiment_score = data.get('sentiment', 0.0)
        sentiment_component = sentiment_score * 100 * sentiment_weight
        
        # Event component (based on severity and type)
        event_component = 0.0
        events = data.get('events', [])
        if events:
            # Negative event types should decrease score
            negative_event_types = {
                EventType.BANKRUPTCY, EventType.REGULATORY
            }
            
            event_scores = []
            for e in events:
                severity = e.severity
                # Negative events get negative score
                if e.event_type in negative_event_types:
                    event_scores.append(-severity)
                else:
                    event_scores.append(severity)
            
            avg_event_score = np.mean(event_scores)
            event_component = avg_event_score * 100 * event_weight
        
        cms = sentiment_component + event_component
        
        # Clamp to [-100, 100]
        return max(-100.0, min(100.0, cms))
    
    def compute_metrics(
        self,
        trades: List[Trade],
        initial_capital: float,
        equity_curve: List[Tuple[datetime, float]]
    ) -> PerformanceMetrics:
        """Compute performance metrics from trades and equity curve.
        
        Args:
            trades: List of executed trades
            initial_capital: Starting capital
            equity_curve: List of (timestamp, equity) tuples
            
        Returns:
            Performance metrics
        """
        logger.info("Computing performance metrics")
        
        if not trades:
            return PerformanceMetrics(
                total_return=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                total_trades=0,
                avg_trade_duration=timedelta(0)
            )
        
        # Total return
        final_equity = equity_curve[-1][1] if equity_curve else initial_capital
        total_return = (final_equity - initial_capital) / initial_capital
        
        # Sharpe ratio
        sharpe_ratio = self._compute_sharpe_ratio(equity_curve, initial_capital)
        
        # Maximum drawdown
        max_drawdown = self._compute_max_drawdown(equity_curve)
        
        # Win rate
        winning_trades = sum(1 for trade in trades if trade.pnl > 0)
        win_rate = winning_trades / len(trades) if trades else 0.0
        
        # Average trade duration
        trade_durations = [
            (trade.exit_time - trade.entry_time).total_seconds()
            for trade in trades
        ]
        avg_duration_seconds = np.mean(trade_durations) if trade_durations else 0
        avg_trade_duration = timedelta(seconds=avg_duration_seconds)
        
        metrics = PerformanceMetrics(
            total_return=total_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            total_trades=len(trades),
            avg_trade_duration=avg_trade_duration
        )
        
        logger.info(
            f"Metrics computed: Return={total_return:.2%}, "
            f"Sharpe={sharpe_ratio:.2f}, DD={max_drawdown:.2%}, "
            f"WinRate={win_rate:.2%}"
        )
        
        return metrics
    
    def _compute_sharpe_ratio(
        self,
        equity_curve: List[Tuple[datetime, float]],
        initial_capital: float
    ) -> float:
        """Compute Sharpe ratio from equity curve.
        
        Args:
            equity_curve: List of (timestamp, equity) tuples
            initial_capital: Starting capital
            
        Returns:
            Sharpe ratio (annualized)
        """
        if len(equity_curve) < 2:
            return 0.0
        
        # Calculate returns
        equities = [equity for _, equity in equity_curve]
        returns = np.diff(equities) / equities[:-1]
        
        if len(returns) == 0 or np.std(returns) == 0:
            return 0.0
        
        # Annualized Sharpe ratio (assuming daily data)
        # Sharpe = (mean_return - risk_free_rate) / std_return * sqrt(252)
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        risk_free_rate = 0.0  # Simplified: assume 0 risk-free rate
        
        sharpe = (mean_return - risk_free_rate) / std_return * np.sqrt(252)
        
        return float(sharpe)
    
    def _compute_max_drawdown(
        self,
        equity_curve: List[Tuple[datetime, float]]
    ) -> float:
        """Compute maximum drawdown from equity curve.
        
        Args:
            equity_curve: List of (timestamp, equity) tuples
            
        Returns:
            Maximum drawdown as a fraction (0.0 to 1.0)
        """
        if len(equity_curve) < 2:
            return 0.0
        
        equities = [equity for _, equity in equity_curve]
        peak = equities[0]
        max_dd = 0.0
        
        for equity in equities:
            if equity > peak:
                peak = equity
            
            drawdown = (peak - equity) / peak if peak > 0 else 0.0
            max_dd = max(max_dd, drawdown)
        
        return float(max_dd)
    
    def _store_result(self, result: BacktestResult) -> None:
        """Store backtest result in PostgreSQL.
        
        Args:
            result: Backtest result to store
        """
        logger.info(f"Storing backtest result {result.backtest_id}")
        
        with self.db_connection.get_session() as session:
            repo = BacktestResultRepository(session)
            
            # Convert result to database model format
            from src.database.models import BacktestResult as DBBacktestResult
            
            db_result = DBBacktestResult(
                id=result.backtest_id,
                config={
                    'symbol': result.config.symbol,
                    'start_date': result.config.start_date.isoformat(),
                    'end_date': result.config.end_date.isoformat(),
                    'initial_capital': result.config.initial_capital,
                    'position_size': result.config.position_size,
                    'cms_buy_threshold': result.config.cms_buy_threshold,
                    'cms_sell_threshold': result.config.cms_sell_threshold
                },
                metrics={
                    'total_return': result.metrics.total_return,
                    'sharpe_ratio': result.metrics.sharpe_ratio,
                    'max_drawdown': result.metrics.max_drawdown,
                    'win_rate': result.metrics.win_rate,
                    'total_trades': result.metrics.total_trades,
                    'avg_trade_duration': result.metrics.avg_trade_duration.total_seconds()
                },
                trades=[
                    {
                        'entry_time': trade.entry_time.isoformat(),
                        'exit_time': trade.exit_time.isoformat(),
                        'entry_price': trade.entry_price,
                        'exit_price': trade.exit_price,
                        'quantity': trade.quantity,
                        'pnl': trade.pnl,
                        'signal_type': trade.signal_type.value
                    }
                    for trade in result.trades
                ],
                equity_curve=[
                    {
                        'timestamp': ts.isoformat(),
                        'equity': equity
                    }
                    for ts, equity in result.equity_curve
                ]
            )
            
            repo.create(db_result)
        
        logger.info(f"Backtest result {result.backtest_id} stored successfully")
    
    def _create_empty_result(self, config: BacktestConfig) -> BacktestResult:
        """Create an empty backtest result when no data is available.
        
        Args:
            config: Backtest configuration
            
        Returns:
            Empty backtest result
        """
        backtest_id = str(uuid.uuid4())
        
        return BacktestResult(
            backtest_id=backtest_id,
            config=config,
            trades=[],
            metrics=PerformanceMetrics(
                total_return=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                total_trades=0,
                avg_trade_duration=timedelta(0)
            ),
            equity_curve=[(config.start_date, config.initial_capital)]
        )
