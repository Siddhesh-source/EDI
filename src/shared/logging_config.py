"""Logging configuration for the trading system."""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured information."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "component": record.name,
            "message": record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        # Format as key=value pairs
        formatted_parts = [f"{k}={v}" for k, v in log_data.items()]
        return " | ".join(formatted_parts)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    component_name: str = "trading_system"
) -> logging.Logger:
    """
    Set up logging configuration for the trading system.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for logging output
        component_name: Name of the component for logger identification
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(component_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(StructuredFormatter())
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(StructuredFormatter())
        logger.addHandler(file_handler)
    
    return logger


def get_logger(component_name: str) -> logging.Logger:
    """
    Get a logger for a specific component.
    
    Args:
        component_name: Name of the component
    
    Returns:
        Logger instance
    """
    return logging.getLogger(component_name)
