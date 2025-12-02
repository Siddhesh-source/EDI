"""Database connection and repository module."""

from src.database.connection import (
    DatabaseConnection,
    close_database,
    db_connection,
    get_db_session,
    initialize_database,
)
from src.database.migrations import DatabaseMigration, run_migrations
from src.database.models import (
    Article,
    BacktestResult,
    Base,
    Event,
    Order,
    Price,
    SentimentScore,
    TradingSignal,
)
from src.database.repositories import (
    ArticleRepository,
    BacktestResultRepository,
    EventRepository,
    OrderRepository,
    PriceRepository,
    SentimentScoreRepository,
    TradingSignalRepository,
)
from src.database.repository import BaseRepository

__all__ = [
    # Connection
    "DatabaseConnection",
    "db_connection",
    "initialize_database",
    "close_database",
    "get_db_session",
    # Models
    "Base",
    "Price",
    "Article",
    "SentimentScore",
    "Event",
    "TradingSignal",
    "Order",
    "BacktestResult",
    # Repositories
    "BaseRepository",
    "PriceRepository",
    "ArticleRepository",
    "SentimentScoreRepository",
    "EventRepository",
    "TradingSignalRepository",
    "OrderRepository",
    "BacktestResultRepository",
    # Migrations
    "DatabaseMigration",
    "run_migrations",
]
