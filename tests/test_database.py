"""Tests for database connection and repository functionality."""

import pytest
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from src.database import (
    DatabaseConnection,
    initialize_database,
    close_database,
    get_db_session,
    run_migrations,
    PriceRepository,
    ArticleRepository,
    SentimentScoreRepository,
    EventRepository,
    TradingSignalRepository,
    OrderRepository,
    BacktestResultRepository,
)


class TestDatabaseConnection:
    """Test database connection management."""
    
    def test_database_initialization(self):
        """Test that database can be initialized."""
        try:
            initialize_database()
            assert True
        except Exception as e:
            pytest.fail(f"Database initialization failed: {e}")
        finally:
            close_database()
    
    def test_database_health_check(self):
        """Test database health check."""
        try:
            initialize_database()
            from src.database import db_connection
            assert db_connection.health_check() is True
        except Exception as e:
            pytest.fail(f"Database health check failed: {e}")
        finally:
            close_database()
    
    def test_get_session(self):
        """Test getting a database session."""
        try:
            initialize_database()
            with next(get_db_session()) as session:
                result = session.execute(text("SELECT 1"))
                assert result.scalar() == 1
        except Exception as e:
            pytest.fail(f"Getting database session failed: {e}")
        finally:
            close_database()


class TestDatabaseMigrations:
    """Test database migrations."""
    
    def test_run_migrations(self):
        """Test running database migrations."""
        try:
            initialize_database()
            from src.database import db_connection
            run_migrations(db_connection)
            assert True
        except Exception as e:
            pytest.fail(f"Running migrations failed: {e}")
        finally:
            close_database()
    
    def test_verify_schema(self):
        """Test schema verification."""
        try:
            initialize_database()
            from src.database import db_connection, DatabaseMigration
            
            migration = DatabaseMigration(db_connection)
            run_migrations(db_connection)
            
            assert migration.verify_schema() is True
        except Exception as e:
            pytest.fail(f"Schema verification failed: {e}")
        finally:
            close_database()


class TestRepositories:
    """Test repository functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        initialize_database()
        from src.database import db_connection
        run_migrations(db_connection)
        yield
        close_database()
    
    def test_price_repository_create(self):
        """Test creating a price record."""
        with next(get_db_session()) as session:
            repo = PriceRepository(session)
            price = repo.create(
                symbol="AAPL",
                timestamp=datetime.now(),
                open=150.0,
                high=152.0,
                low=149.0,
                close=151.0,
                volume=1000000
            )
            assert price.id is not None
            assert price.symbol == "AAPL"
    
    def test_article_repository_create(self):
        """Test creating an article record."""
        with next(get_db_session()) as session:
            repo = ArticleRepository(session)
            article = repo.create(
                id="test_article_1",
                title="Test Article",
                content="Test content",
                source="Test Source",
                published_at=datetime.now(),
                symbols=["AAPL", "GOOGL"]
            )
            assert article.id == "test_article_1"
            assert article.title == "Test Article"
    
    def test_sentiment_score_repository_create(self):
        """Test creating a sentiment score record."""
        with next(get_db_session()) as session:
            # First create an article
            article_repo = ArticleRepository(session)
            article = article_repo.create(
                id="test_article_2",
                title="Test Article",
                content="Test content",
                source="Test Source",
                published_at=datetime.now(),
                symbols=["AAPL"]
            )
            
            # Then create sentiment score
            sentiment_repo = SentimentScoreRepository(session)
            sentiment = sentiment_repo.create(
                article_id=article.id,
                score=0.75,
                confidence=0.85,
                keywords_positive=["bullish", "growth"],
                keywords_negative=[],
                timestamp=datetime.now()
            )
            assert sentiment.id is not None
            assert sentiment.score == 0.75
    
    def test_event_repository_create(self):
        """Test creating an event record."""
        with next(get_db_session()) as session:
            # First create an article
            article_repo = ArticleRepository(session)
            article = article_repo.create(
                id="test_article_3",
                title="Test Article",
                content="Test content",
                source="Test Source",
                published_at=datetime.now(),
                symbols=["AAPL"]
            )
            
            # Then create event
            event_repo = EventRepository(session)
            event = event_repo.create(
                id="test_event_1",
                article_id=article.id,
                event_type="earnings",
                severity=0.8,
                keywords=["earnings", "report"],
                timestamp=datetime.now()
            )
            assert event.id == "test_event_1"
            assert event.event_type == "earnings"
    
    def test_trading_signal_repository_create(self):
        """Test creating a trading signal record."""
        with next(get_db_session()) as session:
            repo = TradingSignalRepository(session)
            signal = repo.create(
                signal_type="buy",
                cms_score=75.5,
                sentiment_component=20.0,
                technical_component=35.5,
                regime_component=20.0,
                explanation={"summary": "Strong buy signal"},
                timestamp=datetime.now()
            )
            assert signal.id is not None
            assert signal.signal_type == "buy"
    
    def test_order_repository_create(self):
        """Test creating an order record."""
        with next(get_db_session()) as session:
            # First create a signal
            signal_repo = TradingSignalRepository(session)
            signal = signal_repo.create(
                signal_type="buy",
                cms_score=75.5,
                sentiment_component=20.0,
                technical_component=35.5,
                regime_component=20.0,
                explanation={"summary": "Strong buy signal"},
                timestamp=datetime.now()
            )
            
            # Then create order
            order_repo = OrderRepository(session)
            order = order_repo.create(
                order_id="test_order_1",
                symbol="AAPL",
                order_type="market",
                side="buy",
                quantity=10.0,
                price=150.0,
                status="pending",
                signal_id=signal.id,
                timestamp=datetime.now()
            )
            assert order.id is not None
            assert order.order_id == "test_order_1"
    
    def test_backtest_result_repository_create(self):
        """Test creating a backtest result record."""
        with next(get_db_session()) as session:
            repo = BacktestResultRepository(session)
            result = repo.create(
                id="test_backtest_1",
                config={"symbol": "AAPL", "start_date": "2023-01-01"},
                metrics={"total_return": 0.15, "sharpe_ratio": 1.5},
                trades=[],
                equity_curve=[]
            )
            assert result.id == "test_backtest_1"
    
    def test_repository_get_by_id(self):
        """Test getting a record by ID."""
        with next(get_db_session()) as session:
            repo = PriceRepository(session)
            
            # Create a record
            price = repo.create(
                symbol="AAPL",
                timestamp=datetime.now(),
                open=150.0,
                high=152.0,
                low=149.0,
                close=151.0,
                volume=1000000
            )
            
            # Retrieve it
            retrieved = repo.get_by_id(price.id)
            assert retrieved is not None
            assert retrieved.id == price.id
            assert retrieved.symbol == "AAPL"
    
    def test_repository_update(self):
        """Test updating a record."""
        with next(get_db_session()) as session:
            repo = PriceRepository(session)
            
            # Create a record
            price = repo.create(
                symbol="AAPL",
                timestamp=datetime.now(),
                open=150.0,
                high=152.0,
                low=149.0,
                close=151.0,
                volume=1000000
            )
            
            # Update it
            updated = repo.update(price.id, close=155.0)
            assert updated is not None
            assert updated.close == 155.0
    
    def test_repository_delete(self):
        """Test deleting a record."""
        with next(get_db_session()) as session:
            repo = PriceRepository(session)
            
            # Create a record
            price = repo.create(
                symbol="AAPL",
                timestamp=datetime.now(),
                open=150.0,
                high=152.0,
                low=149.0,
                close=151.0,
                volume=1000000
            )
            
            # Delete it
            deleted = repo.delete(price.id)
            assert deleted is True
            
            # Verify it's gone
            retrieved = repo.get_by_id(price.id)
            assert retrieved is None
    
    def test_repository_count(self):
        """Test counting records."""
        with next(get_db_session()) as session:
            repo = PriceRepository(session)
            
            initial_count = repo.count()
            
            # Create some records
            for i in range(3):
                repo.create(
                    symbol="AAPL",
                    timestamp=datetime.now(),
                    open=150.0,
                    high=152.0,
                    low=149.0,
                    close=151.0,
                    volume=1000000
                )
            
            final_count = repo.count()
            assert final_count == initial_count + 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
