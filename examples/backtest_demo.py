"""Demo script for backtesting module."""

import logging
from datetime import datetime, timedelta

from src.backtest import BacktestingModule
from src.database.connection import DatabaseConnection
from src.shared.models import BacktestConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Run backtesting demo."""
    logger.info("Starting backtesting demo")
    
    # Initialize database connection
    db_connection = DatabaseConnection()
    db_connection.initialize()
    
    try:
        # Create backtesting module
        backtest_module = BacktestingModule(db_connection)
        
        # Configure backtest
        config = BacktestConfig(
            symbol="AAPL",
            start_date=datetime.now() - timedelta(days=90),
            end_date=datetime.now(),
            initial_capital=100000.0,
            position_size=0.1,  # Use 10% of capital per trade
            cms_buy_threshold=60.0,
            cms_sell_threshold=-60.0
        )
        
        logger.info(f"Running backtest with config: {config}")
        
        # Run backtest
        result = backtest_module.run_backtest(config)
        
        # Display results
        logger.info("=" * 80)
        logger.info("BACKTEST RESULTS")
        logger.info("=" * 80)
        logger.info(f"Backtest ID: {result.backtest_id}")
        logger.info(f"Symbol: {result.config.symbol}")
        logger.info(f"Period: {result.config.start_date} to {result.config.end_date}")
        logger.info(f"Initial Capital: ${result.config.initial_capital:,.2f}")
        logger.info("")
        logger.info("PERFORMANCE METRICS:")
        logger.info(f"  Total Return: {result.metrics.total_return:.2%}")
        logger.info(f"  Sharpe Ratio: {result.metrics.sharpe_ratio:.2f}")
        logger.info(f"  Max Drawdown: {result.metrics.max_drawdown:.2%}")
        logger.info(f"  Win Rate: {result.metrics.win_rate:.2%}")
        logger.info(f"  Total Trades: {result.metrics.total_trades}")
        logger.info(f"  Avg Trade Duration: {result.metrics.avg_trade_duration}")
        logger.info("")
        
        if result.trades:
            logger.info("SAMPLE TRADES (first 5):")
            for i, trade in enumerate(result.trades[:5], 1):
                logger.info(f"  Trade {i}:")
                logger.info(f"    Entry: {trade.entry_time} @ ${trade.entry_price:.2f}")
                logger.info(f"    Exit: {trade.exit_time} @ ${trade.exit_price:.2f}")
                logger.info(f"    Quantity: {trade.quantity:.2f}")
                logger.info(f"    P&L: ${trade.pnl:.2f}")
                logger.info("")
        
        logger.info("=" * 80)
        logger.info(f"Results stored in database with ID: {result.backtest_id}")
        
    finally:
        # Clean up
        db_connection.close()
        logger.info("Database connection closed")


if __name__ == "__main__":
    main()
