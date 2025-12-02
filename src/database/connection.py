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
    """Manages PostgreSQL database connections with pooling and retry logic."""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize database connection manager.
        
        Args:
            database_url: PostgreSQL connection URL. If None, uses settings.database_url
        """
        self.database_url = database_url or settings.database_url
        self._engine: Optional[create_engine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._write_queue: OperationQueue = OperationQueue(max_size=10000)
        self._circuit_breaker = get_circuit_breaker(
            name="postgresql",
            failure_threshold=5,
            recovery_timeout=30.0,
            expected_exception=(OperationalError, DatabaseError)
        )
        self._queue_processing_enabled = False
        
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
        """Get a database session with automatic cleanup and retry logic.
        
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
            # Commit with retry logic
            self._commit_with_retry(session)
        except CircuitBreakerOpenError as e:
            session.rollback()
            error_logger.log_error(e, {'action': 'session_commit'})
            raise
        except (OperationalError, DatabaseError) as e:
            session.rollback()
            error_logger.log_error(e, {'action': 'session_commit'})
            # Mark circuit breaker failure
            self._circuit_breaker._on_failure()
            raise
        except Exception as e:
            session.rollback()
            error_logger.log_error(e, {'action': 'session_commit'})
            raise
        finally:
            session.close()
    
    def _commit_with_retry(self, session: Session, max_attempts: int = 3):
        """
        Commit session with retry logic.
        
        Args:
            session: SQLAlchemy session
            max_attempts: Maximum retry attempts
        """
        for attempt in range(max_attempts):
            try:
                # Use circuit breaker for commit
                self._circuit_breaker.call(session.commit)
                return
            except CircuitBreakerOpenError:
                # Circuit is open, queue the operation
                logger.warning("Database circuit breaker open, cannot commit")
                raise
            except (OperationalError, DatabaseError) as e:
                if attempt < max_attempts - 1:
                    delay = 1.0 * (2 ** attempt)
                    logger.warning(
                        f"Database commit failed (attempt {attempt + 1}/{max_attempts}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"Database commit failed after {max_attempts} attempts")
                    raise
    
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
            error_logger.log_error(e, {'action': 'health_check'})
            return False
    
    def queue_write_operation(
        self,
        operation: Callable,
        *args,
        **kwargs
    ) -> bool:
        """
        Queue a write operation for later execution.
        
        Args:
            operation: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            True if queued successfully, False otherwise
        """
        operation_data = {
            'operation': operation,
            'args': args,
            'kwargs': kwargs,
            'timestamp': datetime.now()
        }
        
        success = self._write_queue.enqueue(operation_data)
        
        if success:
            logger.info(
                f"Write operation queued: {operation.__name__}. "
                f"Queue size: {self._write_queue.size()}"
            )
        else:
            logger.error(
                f"Failed to queue write operation: {operation.__name__}. "
                f"Queue full ({self._write_queue.max_size})"
            )
        
        return success
    
    def process_queued_operations(self, max_operations: int = 100) -> int:
        """
        Process queued write operations.
        
        Args:
            max_operations: Maximum operations to process
            
        Returns:
            Number of operations successfully processed
        """
        if not self.health_check():
            logger.warning("Database unhealthy, skipping queue processing")
            return 0
        
        processed = 0
        failed = 0
        
        for _ in range(min(max_operations, self._write_queue.size())):
            operation_data = self._write_queue.dequeue()
            if not operation_data:
                break
            
            try:
                operation = operation_data['operation']
                args = operation_data['args']
                kwargs = operation_data['kwargs']
                
                # Execute operation
                operation(*args, **kwargs)
                processed += 1
                
            except Exception as e:
                failed += 1
                error_logger.log_error(
                    e,
                    {
                        'action': 'process_queued_operation',
                        'operation': operation_data['operation'].__name__
                    }
                )
                
                # Re-queue if not too old (older than 5 minutes)
                age = (datetime.now() - operation_data['timestamp']).total_seconds()
                if age < 300:
                    self._write_queue.enqueue(operation_data)
        
        if processed > 0 or failed > 0:
            logger.info(
                f"Processed {processed} queued operations, {failed} failed. "
                f"Remaining: {self._write_queue.size()}"
            )
        
        return processed
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get statistics about the write queue."""
        return self._write_queue.get_stats()
    
    def enable_queue_processing(self):
        """Enable automatic queue processing."""
        self._queue_processing_enabled = True
        logger.info("Database queue processing enabled")
    
    def disable_queue_processing(self):
        """Disable automatic queue processing."""
        self._queue_processing_enabled = False
        logger.info("Database queue processing disabled")


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
