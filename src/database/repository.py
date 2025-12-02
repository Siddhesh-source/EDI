"""Base repository pattern for data access."""

import logging
from datetime import datetime
from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.database.models import Base

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Base repository providing common CRUD operations."""
    
    def __init__(self, model: Type[T], session: Session):
        """Initialize repository.
        
        Args:
            model: SQLAlchemy model class
            session: Database session
        """
        self.model = model
        self.session = session
    
    def create(self, **kwargs) -> T:
        """Create a new record.
        
        Args:
            **kwargs: Field values for the new record
            
        Returns:
            Created model instance
        """
        try:
            instance = self.model(**kwargs)
            self.session.add(instance)
            self.session.flush()
            logger.debug(f"Created {self.model.__name__} record")
            return instance
        except Exception as e:
            logger.error(f"Error creating {self.model.__name__}: {e}")
            raise
    
    def get_by_id(self, id_value) -> Optional[T]:
        """Get a record by ID.
        
        Args:
            id_value: Primary key value
            
        Returns:
            Model instance or None if not found
        """
        try:
            return self.session.query(self.model).filter(
                self.model.id == id_value
            ).first()
        except Exception as e:
            logger.error(f"Error getting {self.model.__name__} by ID: {e}")
            raise
    
    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[T]:
        """Get all records with optional pagination.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of model instances
        """
        try:
            query = self.session.query(self.model)
            if limit is not None:
                query = query.limit(limit).offset(offset)
            return query.all()
        except Exception as e:
            logger.error(f"Error getting all {self.model.__name__}: {e}")
            raise
    
    def update(self, id_value, **kwargs) -> Optional[T]:
        """Update a record by ID.
        
        Args:
            id_value: Primary key value
            **kwargs: Fields to update
            
        Returns:
            Updated model instance or None if not found
        """
        try:
            instance = self.get_by_id(id_value)
            if instance is None:
                logger.warning(f"{self.model.__name__} with ID {id_value} not found")
                return None
            
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            
            self.session.flush()
            logger.debug(f"Updated {self.model.__name__} record {id_value}")
            return instance
        except Exception as e:
            logger.error(f"Error updating {self.model.__name__}: {e}")
            raise
    
    def delete(self, id_value) -> bool:
        """Delete a record by ID.
        
        Args:
            id_value: Primary key value
            
        Returns:
            True if deleted, False if not found
        """
        try:
            instance = self.get_by_id(id_value)
            if instance is None:
                logger.warning(f"{self.model.__name__} with ID {id_value} not found")
                return False
            
            self.session.delete(instance)
            self.session.flush()
            logger.debug(f"Deleted {self.model.__name__} record {id_value}")
            return True
        except Exception as e:
            logger.error(f"Error deleting {self.model.__name__}: {e}")
            raise
    
    def count(self) -> int:
        """Count total records.
        
        Returns:
            Total number of records
        """
        try:
            return self.session.query(self.model).count()
        except Exception as e:
            logger.error(f"Error counting {self.model.__name__}: {e}")
            raise
    
    def exists(self, id_value) -> bool:
        """Check if a record exists.
        
        Args:
            id_value: Primary key value
            
        Returns:
            True if exists, False otherwise
        """
        try:
            return self.session.query(
                self.session.query(self.model).filter(
                    self.model.id == id_value
                ).exists()
            ).scalar()
        except Exception as e:
            logger.error(f"Error checking {self.model.__name__} existence: {e}")
            raise
