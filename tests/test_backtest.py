"""Tests for backtesting module."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
import numpy as np

from src.backtest.engine import BacktestingModule
from src.database.connection import DatabaseConnection
from src.shared.models import (
    BacktestConfig, Trade, TradingSignalType, OHLC, Event, EventType
)


class TestBacktestingModule:
    """Test suite for BacktestingModule."""
    
    @pytest.fixture
    def mock_db_connection(self):
        """Create a mock database connection."""
        from contextlib import contextmanager
        
        mock_conn = Mock(spec=DatabaseConnection)
        mock_session = MagicMock()
        
        @contextmanager
        def mock_get_session():
            yield mock_session
        
        mock_conn.get_session = mock_get_session
        return mock_conn
    
    @pytest.fixture
    def backtest_module(self, mock_db_connection):
        """Create a backtesting module instance."""
        return BacktestingModule(mock_db_connection)
    
    @pytest.fixture
    def sample_config(self):
        """Create a sample backtest configuration."""
        return BacktestConfig(
            symbol="AAPL",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 3, 31),
            initial_capital=100000.0,
            position_size=0.1,
            cms_buy_threshold=60.0,
            cms_sell_threshold=-60.0
        )
    
    def test_compute_metrics_with_trades(self, backtest_module):
        """Test performance metrics computation with trades."""
        trades = [
            Trade(
                entry_time=datetime(2024, 1, 1),
                exit_time=datetime(2024, 1, 5),
                entry_price=100.0,
                exit_price=110.0,
                quantity=10.0,
                pnl=100.0,
                signal_type=TradingSignalType.BUY
            ),
            Trade(
                entry_time=datetime(2024, 1, 10),
                exit_time=datetime(2024, 1, 15),
                entry_price=110.0,
                exit_price=105.0,
                quantity=10.0,
                pnl=-50.0,
                signal_type=TradingSignalType.BUY
            ),
            Trade(
                entry_time=datetime(2024, 1, 20),
                exit_time=datetime(2024, 1, 25),
                entry_price=105.0,
                exit_price=120.0,
                quantity=10.0,
                pnl=150.0,
                signal_type=TradingSignalType.BUY
            )
        ]
        
        equity_curve = [
            (datetime(2024, 1, 1), 100000.0),
            (datetime(2024, 1, 5), 100100.0),
            (datetime(2024, 1, 10), 100100.0),
            (datetime(2024, 1, 15), 100050.0),
            (datetime(2024, 1, 20), 100050.0),
            (datetime(2024, 1, 25), 100200.0)
        ]
        
        metrics = backtest_module.compute_metrics(trades, 100000.0, equity_curve)
        
        assert metrics.total_trades == 3
        assert metrics.total_return == pytest.approx(0.002, rel=1e-3)  # 0.2% return
        assert 0.0 <= metrics.win_rate <= 1.0
        assert metrics.win_rate == pytest.approx(2/3, rel=1e-3)  # 2 wins out of 3
        assert metrics.max_drawdown >= 0.0
        assert isinstance(metrics.avg_trade_duration, timedelta)
    
    def test_compute_metrics_no_trades(self, backtest_module):
        """Test performance metrics computation with no trades."""
        trades = []
        equity_curve = [(datetime(2024, 1, 1), 100000.0)]
        
        metrics = backtest_module.compute_metrics(trades, 100000.0, equity_curve)
        
        assert metrics.total_trades == 0
        assert metrics.total_return == 0.0
        assert metrics.sharpe_ratio == 0.0
        assert metrics.max_drawdown == 0.0
        assert metrics.win_rate == 0.0
        assert metrics.avg_trade_duration == timedelta(0)
    
    def test_compute_sharpe_ratio(self, backtest_module):
        """Test Sharpe ratio computation."""
        # Create equity curve with positive returns
        equity_curve = [
            (datetime(2024, 1, 1), 100000.0),
            (datetime(2024, 1, 2), 101000.0),
            (datetime(2024, 1, 3), 102000.0),
            (datetime(2024, 1, 4), 103000.0),
            (datetime(2024, 1, 5), 104000.0)
        ]
        
        sharpe = backtest_module._compute_sharpe_ratio(equity_curve, 100000.0)
        
        # Sharpe should be positive for positive returns
        assert sharpe > 0.0
        assert isinstance(sharpe, float)
    
    def test_compute_max_drawdown(self, backtest_module):
        """Test maximum drawdown computation."""
        # Create equity curve with a drawdown
        equity_curve = [
            (datetime(2024, 1, 1), 100000.0),
            (datetime(2024, 1, 2), 110000.0),  # Peak
            (datetime(2024, 1, 3), 105000.0),  # Drawdown
            (datetime(2024, 1, 4), 100000.0),  # Larger drawdown
            (datetime(2024, 1, 5), 108000.0)   # Recovery
        ]
        
        max_dd = backtest_module._compute_max_drawdown(equity_curve)
        
        # Max drawdown should be (110000 - 100000) / 110000 ≈ 0.0909
        assert max_dd == pytest.approx(0.0909, rel=1e-2)
        assert 0.0 <= max_dd <= 1.0
    
    def test_compute_max_drawdown_no_drawdown(self, backtest_module):
        """Test maximum drawdown with no drawdown."""
        # Equity curve with only increases
        equity_curve = [
            (datetime(2024, 1, 1), 100000.0),
            (datetime(2024, 1, 2), 101000.0),
            (datetime(2024, 1, 3), 102000.0),
            (datetime(2024, 1, 4), 103000.0)
        ]
        
        max_dd = backtest_module._compute_max_drawdown(equity_curve)
        
        assert max_dd == 0.0
    
    def test_generate_signal_from_data_buy(self, backtest_module, sample_config):
        """Test signal generation for BUY condition."""
        data = {
            'price': OHLC(100.0, 105.0, 99.0, 103.0, 1000000, datetime.now()),
            'sentiment': 0.8,  # Positive sentiment
            'events': [
                Event(
                    id="e1",
                    article_id="a1",
                    event_type=EventType.EARNINGS,
                    severity=0.9,
                    keywords=["earnings", "beat"],
                    timestamp=datetime.now()
                )
            ],
            'signal': None
        }
        
        signal = backtest_module._generate_signal_from_data(
            data, sample_config, datetime.now()
        )
        
        assert signal == TradingSignalType.BUY
    
    def test_generate_signal_from_data_sell(self, backtest_module, sample_config):
        """Test signal generation for SELL condition."""
        data = {
            'price': OHLC(100.0, 105.0, 99.0, 103.0, 1000000, datetime.now()),
            'sentiment': -0.8,  # Negative sentiment
            'events': [
                Event(
                    id="e1",
                    article_id="a1",
                    event_type=EventType.BANKRUPTCY,
                    severity=0.9,
                    keywords=["bankruptcy", "crisis"],
                    timestamp=datetime.now()
                )
            ],
            'signal': None
        }
        
        signal = backtest_module._generate_signal_from_data(
            data, sample_config, datetime.now()
        )
        
        assert signal == TradingSignalType.SELL
    
    def test_generate_signal_from_data_hold(self, backtest_module, sample_config):
        """Test signal generation for HOLD condition."""
        data = {
            'price': OHLC(100.0, 105.0, 99.0, 103.0, 1000000, datetime.now()),
            'sentiment': 0.0,  # Neutral sentiment
            'events': [],
            'signal': None
        }
        
        signal = backtest_module._generate_signal_from_data(
            data, sample_config, datetime.now()
        )
        
        assert signal == TradingSignalType.HOLD
    
    def test_compute_simple_cms(self, backtest_module):
        """Test simple CMS computation."""
        data = {
            'sentiment': 0.5,
            'events': [
                Event(
                    id="e1",
                    article_id="a1",
                    event_type=EventType.EARNINGS,
                    severity=0.8,
                    keywords=["earnings"],
                    timestamp=datetime.now()
                )
            ]
        }
        
        cms = backtest_module._compute_simple_cms(data)
        
        # CMS should be positive with positive sentiment and events
        assert cms > 0.0
        assert -100.0 <= cms <= 100.0
    
    def test_compute_simple_cms_bounds(self, backtest_module):
        """Test that CMS is always within bounds."""
        # Test extreme positive
        data_positive = {
            'sentiment': 1.0,
            'events': [
                Event(
                    id="e1",
                    article_id="a1",
                    event_type=EventType.EARNINGS,
                    severity=1.0,
                    keywords=["earnings"],
                    timestamp=datetime.now()
                )
            ]
        }
        
        cms_positive = backtest_module._compute_simple_cms(data_positive)
        assert -100.0 <= cms_positive <= 100.0
        
        # Test extreme negative
        data_negative = {
            'sentiment': -1.0,
            'events': []
        }
        
        cms_negative = backtest_module._compute_simple_cms(data_negative)
        assert -100.0 <= cms_negative <= 100.0
    
    def test_simulate_trading_chronological_order(self, backtest_module, sample_config):
        """Test that trading simulation processes data chronologically."""
        # Create historical data with timestamps out of order
        historical_data = {
            datetime(2024, 1, 3): {
                'price': OHLC(103.0, 105.0, 102.0, 104.0, 1000000, datetime(2024, 1, 3)),
                'sentiment': 0.5,
                'events': [],
                'signal': None
            },
            datetime(2024, 1, 1): {
                'price': OHLC(100.0, 102.0, 99.0, 101.0, 1000000, datetime(2024, 1, 1)),
                'sentiment': 0.0,
                'events': [],
                'signal': None
            },
            datetime(2024, 1, 2): {
                'price': OHLC(101.0, 103.0, 100.0, 102.0, 1000000, datetime(2024, 1, 2)),
                'sentiment': 0.3,
                'events': [],
                'signal': None
            }
        }
        
        trades, equity_curve = backtest_module.simulate_trading(
            historical_data, sample_config
        )
        
        # Verify equity curve is in chronological order
        timestamps = [ts for ts, _ in equity_curve]
        assert timestamps == sorted(timestamps), "Equity curve should be chronological"
    
    def test_simulate_trading_buy_sell_cycle(self, backtest_module, sample_config):
        """Test a complete buy-sell trading cycle."""
        # Create data that triggers BUY then SELL
        # Note: CMS = sentiment * 100 * 0.5 + event * 100 * 0.5
        # For BUY: need CMS > 60, so sentiment needs to be > 1.2 (clamped to 1.0)
        # We need strong positive events to push CMS above 60
        historical_data = {
            datetime(2024, 1, 1): {
                'price': OHLC(100.0, 102.0, 99.0, 100.0, 1000000, datetime(2024, 1, 1)),
                'sentiment': 1.0,  # Max positive
                'events': [
                    Event(
                        id="e1",
                        article_id="a1",
                        event_type=EventType.EARNINGS,
                        severity=0.8,
                        keywords=["earnings", "beat"],
                        timestamp=datetime(2024, 1, 1)
                    )
                ],
                'signal': None
            },
            datetime(2024, 1, 2): {
                'price': OHLC(100.0, 103.0, 100.0, 102.0, 1000000, datetime(2024, 1, 2)),
                'sentiment': 0.0,  # HOLD
                'events': [],
                'signal': None
            },
            datetime(2024, 1, 3): {
                'price': OHLC(102.0, 105.0, 102.0, 105.0, 1000000, datetime(2024, 1, 3)),
                'sentiment': -1.0,  # Max negative
                'events': [
                    Event(
                        id="e2",
                        article_id="a2",
                        event_type=EventType.BANKRUPTCY,
                        severity=0.8,
                        keywords=["bankruptcy", "crisis"],
                        timestamp=datetime(2024, 1, 3)
                    )
                ],
                'signal': None
            }
        }
        
        trades, equity_curve = backtest_module.simulate_trading(
            historical_data, sample_config
        )
        
        # Should have at least one trade
        assert len(trades) >= 1
        
        # First trade should have entry and exit
        if trades:
            trade = trades[0]
            assert trade.entry_time < trade.exit_time
            assert trade.entry_price > 0
            assert trade.exit_price > 0
            assert trade.quantity > 0
    
    def test_create_empty_result(self, backtest_module, sample_config):
        """Test creation of empty result when no data available."""
        result = backtest_module._create_empty_result(sample_config)
        
        assert result.backtest_id is not None
        assert result.config == sample_config
        assert len(result.trades) == 0
        assert result.metrics.total_trades == 0
        assert result.metrics.total_return == 0.0
        assert len(result.equity_curve) == 1
        assert result.equity_curve[0][1] == sample_config.initial_capital


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
