"""Database migration utilities."""

import logging
from pathlib import Path

from sqlalchemy import text

from src.database.connection import DatabaseConnection
from src.database.models import Base

logger = logging.getLogger(__name__)


class DatabaseMigration:
    """Handles database schema migrations."""
    
    def __init__(self, db_connection: DatabaseConnection):
        """Initialize migration manager.
        
        Args:
            db_connection: Database connection instance
        """
        self.db_connection = db_connection
    
    def create_all_tables(self) -> None:
        """Create all tables defined in SQLAlchemy models.
        
        This is idempotent - tables that already exist will not be recreated.
        """
        try:
            logger.info("Creating database tables from SQLAlchemy models")
            Base.metadata.create_all(bind=self.db_connection.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise
    
    def drop_all_tables(self) -> None:
        """Drop all tables defined in SQLAlchemy models.
        
        WARNING: This will delete all data!
        """
        try:
            logger.warning("Dropping all database tables")
            Base.metadata.drop_all(bind=self.db_connection.engine)
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Error dropping tables: {e}")
            raise
    
    def execute_sql_file(self, sql_file_path: str) -> None:
        """Execute SQL commands from a file.
        
        Args:
            sql_file_path: Path to SQL file
        """
        try:
            sql_path = Path(sql_file_path)
            if not sql_path.exists():
                raise FileNotFoundError(f"SQL file not found: {sql_file_path}")
            
            logger.info(f"Executing SQL file: {sql_file_path}")
            
            with open(sql_path, 'r') as f:
                sql_content = f.read()
            
            # Split by semicolon and execute each statement
            statements = [s.strip() for s in sql_content.split(';') if s.strip()]
            
            with self.db_connection.get_session() as session:
                for statement in statements:
                    if statement:
                        logger.debug(f"Executing: {statement[:100]}...")
                        session.execute(text(statement))
            
            logger.info(f"SQL file executed successfully: {sql_file_path}")
        except Exception as e:
            logger.error(f"Error executing SQL file: {e}")
            raise
    
    def verify_schema(self) -> bool:
        """Verify that all required tables exist.
        
        Returns:
            True if all tables exist, False otherwise
        """
        required_tables = [
            'prices',
            'articles',
            'sentiment_scores',
            'events',
            'trading_signals',
            'orders',
            'backtest_results'
        ]
        
        try:
            with self.db_connection.get_session() as session:
                result = session.execute(text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                ))
                existing_tables = {row[0] for row in result}
            
            missing_tables = set(required_tables) - existing_tables
            
            if missing_tables:
                logger.warning(f"Missing tables: {missing_tables}")
                return False
            
            logger.info("All required tables exist")
            return True
        except Exception as e:
            logger.error(f"Error verifying schema: {e}")
            raise
    
    def initialize_schema(self, sql_file_path: str = "init_db.sql") -> None:
        """Initialize database schema using SQL file.
        
        Args:
            sql_file_path: Path to initialization SQL file
        """
        try:
            logger.info("Initializing database schema")
            
            # First try to execute the SQL file if it exists
            if Path(sql_file_path).exists():
                self.execute_sql_file(sql_file_path)
            else:
                # Fallback to creating tables from SQLAlchemy models
                logger.info(f"SQL file {sql_file_path} not found, using SQLAlchemy models")
                self.create_all_tables()
            
            # Verify schema
            if self.verify_schema():
                logger.info("Database schema initialized successfully")
            else:
                raise RuntimeError("Schema verification failed after initialization")
        except Exception as e:
            logger.error(f"Error initializing schema: {e}")
            raise


def run_migrations(db_connection: DatabaseConnection) -> None:
    """Run database migrations.
    
    Args:
        db_connection: Database connection instance
    """
    migration = DatabaseMigration(db_connection)
    migration.initialize_schema()
