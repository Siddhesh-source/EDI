"""Database connection management with connection pooling."""

import logging
import time
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator, Optional, Callable, Any, Dict
from datetime import datetime

from sqlalchemy import create_engine, event, pool, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import OperationalError, DatabaseError

from src.shared.config import settings
from src.shared.error_handling import (
    retry_with_backoff,
    OperationQueue,
    ErrorLogger,
    get_circuit_breaker,
    CircuitBreakerOpenError
)

logger = logging.getLogger(__name__)
error_logger = ErrorLogger("database")


class DatabaseConnection:
    """Manages PostgreSQL database connections with pooling."""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize database connection manager.
        
        Args:
            database_url: PostgreSQL connection URL. If None, uses settings.database_url
        """
        self.database_url = database_url or settings.database_url
        self._engine: Optional[create_engine] = None
        self._session_factory: Optional[sessionmaker] = None
        
    def initialize(self) -> None:
        """Initialize the database engine and session factory with connection pooling."""
        if self._engine is not None:
            logger.warning("Database engine already initialized")
            return
            
        logger.info(f"Initializing database connection to {self.database_url.split('@')[1]}")
        
        # Create engine with connection pooling
        self._engine = create_engine(
            self.database_url,
            poolclass=pool.QueuePool,
            pool_size=10,  # Number of connections to maintain
            max_overflow=20,  # Additional connections when pool is exhausted
            pool_timeout=30,  # Seconds to wait for connection
            pool_recycle=3600,  # Recycle connections after 1 hour
            pool_pre_ping=True,  # Verify connections before using
            echo=False,  # Set to True for SQL query logging
        )
        
        # Add connection event listeners
        @event.listens_for(self._engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            """Log new database connections."""
            logger.debug("New database connection established")
        
        @event.listens_for(self._engine, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            """Log connection checkout from pool."""
            logger.debug("Connection checked out from pool")
        
        # Create session factory
        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
        
        logger.info("Database connection initialized successfully")
    
    def close(self) -> None:
        """Close database engine and cleanup connections."""
        if self._engine is not None:
            logger.info("Closing database connections")
            self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Database connections closed")
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session with automatic cleanup.
        
        Yields:
            Session: SQLAlchemy session
            
        Example:
            with db.get_session() as session:
                result = session.execute(query)
                session.commit()
        """
        if self._session_factory is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    @property
    def engine(self):
        """Get the database engine."""
        if self._engine is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._engine
    
    def health_check(self) -> bool:
        """Check if database connection is healthy.
        
        Returns:
            bool: True if connection is healthy, False otherwise
        """
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global database connection instance
db_connection = DatabaseConnection()


def initialize_database() -> None:
    """Initialize the global database connection."""
    db_connection.initialize()


def close_database() -> None:
    """Close the global database connection."""
    db_connection.close()


def get_db_session() -> Generator[Session, None, None]:
    """Get a database session from the global connection.
    
    Yields:
        Session: SQLAlchemy session
    """
    with db_connection.get_session() as session:
        yield session
