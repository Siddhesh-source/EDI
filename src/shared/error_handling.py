"""Comprehensive error handling with circuit breaker patterns."""

import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar, Generic
from functools import wraps
from threading import Lock
from collections import deque

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class ServiceError(Exception):
    """Base exception for service errors."""
    pass


class ServiceUnavailableError(ServiceError):
    """Exception raised when a service is unavailable."""
    pass


class CircuitBreakerOpenError(ServiceError):
    """Exception raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for external services.
    
    Prevents cascading failures by stopping requests to failing services
    and allowing them time to recover.
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception,
        half_open_max_calls: int = 3
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Name of the service/circuit
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to catch
            half_open_max_calls: Max calls to allow in half-open state
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.half_open_max_calls = half_open_max_calls
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._half_open_calls = 0
        self._lock = Lock()
        
        logger.info(
            f"Circuit breaker '{name}' initialized "
            f"(threshold={failure_threshold}, timeout={recovery_timeout}s)"
        )
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state
    
    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Original exception from function
        """
        with self._lock:
            # Check if we should attempt recovery
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    logger.info(f"Circuit breaker '{self.name}' entering HALF_OPEN state")
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.name}' is OPEN. "
                        f"Service unavailable."
                    )
            
            # Limit calls in half-open state
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.name}' is HALF_OPEN. "
                        f"Max test calls reached."
                    )
                self._half_open_calls += 1
        
        # Execute function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self._last_failure_time is None:
            return True
        
        elapsed = (datetime.now() - self._last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful call."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                logger.info(f"Circuit breaker '{self.name}' closing (service recovered)")
                self._state = CircuitState.CLOSED
            
            self._failure_count = 0
            self._last_failure_time = None
    
    def _on_failure(self):
        """Handle failed call."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now()
            
            if self._state == CircuitState.HALF_OPEN:
                logger.warning(
                    f"Circuit breaker '{self.name}' reopening "
                    f"(recovery attempt failed)"
                )
                self._state = CircuitState.OPEN
            elif self._failure_count >= self.failure_threshold:
                logger.error(
                    f"Circuit breaker '{self.name}' opening "
                    f"(threshold reached: {self._failure_count} failures)"
                )
                self._state = CircuitState.OPEN
    
    def reset(self):
        """Manually reset circuit breaker to closed state."""
        with self._lock:
            logger.info(f"Circuit breaker '{self.name}' manually reset")
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_failure_time = None
            self._half_open_calls = 0
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status information."""
        return {
            'name': self.name,
            'state': self._state.value,
            'failure_count': self._failure_count,
            'last_failure_time': self._last_failure_time.isoformat() if self._last_failure_time else None,
            'failure_threshold': self.failure_threshold,
            'recovery_timeout': self.recovery_timeout
        }


class RetryPolicy:
    """Retry policy with exponential backoff."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        """
        Initialize retry policy.
        
        Args:
            max_attempts: Maximum retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
            jitter: Add random jitter to delays
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for given attempt number.
        
        Args:
            attempt: Attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        
        if self.jitter:
            import random
            delay *= (0.5 + random.random())
        
        return delay


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_attempts: Maximum retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exceptions: Tuple of exceptions to catch
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            policy = RetryPolicy(max_attempts, base_delay, max_delay)
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts - 1:
                        delay = policy.get_delay(attempt)
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {e}"
                        )
            
            raise last_exception
        
        return wrapper
    return decorator


class ErrorLogger:
    """
    Structured error logger with component tracking.
    
    Logs errors with timestamp, component name, error type, and stack trace.
    """
    
    def __init__(self, component_name: str):
        """
        Initialize error logger.
        
        Args:
            component_name: Name of the component
        """
        self.component_name = component_name
        self.logger = logging.getLogger(component_name)
    
    def log_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        level: int = logging.ERROR
    ):
        """
        Log error with structured format.
        
        Args:
            error: Exception to log
            context: Additional context information
            level: Logging level
        """
        error_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'component': self.component_name,
            'error_type': type(error).__name__,
            'error_message': str(error),
        }
        
        if context:
            error_data['context'] = context
        
        self.logger.log(
            level,
            f"Error in {self.component_name}: {error}",
            exc_info=True,
            extra={'extra_fields': error_data}
        )
    
    def log_warning(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Log warning with structured format.
        
        Args:
            message: Warning message
            context: Additional context information
        """
        warning_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'component': self.component_name,
            'message': message,
        }
        
        if context:
            warning_data['context'] = context
        
        self.logger.warning(
            message,
            extra={'extra_fields': warning_data}
        )
    
    def log_info(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Log info with structured format.
        
        Args:
            message: Info message
            context: Additional context information
        """
        info_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'component': self.component_name,
            'message': message,
        }
        
        if context:
            info_data['context'] = context
        
        self.logger.info(
            message,
            extra={'extra_fields': info_data}
        )


class OperationQueue(Generic[T]):
    """
    Queue for buffering operations when service is unavailable.
    
    Used for database writes and other operations that can be retried.
    """
    
    def __init__(self, max_size: int = 10000):
        """
        Initialize operation queue.
        
        Args:
            max_size: Maximum queue size
        """
        self.max_size = max_size
        self._queue: deque = deque(maxlen=max_size)
        self._lock = Lock()
        self._dropped_count = 0
    
    def enqueue(self, operation: T) -> bool:
        """
        Add operation to queue.
        
        Args:
            operation: Operation to queue
            
        Returns:
            True if enqueued, False if queue is full
        """
        with self._lock:
            if len(self._queue) >= self.max_size:
                self._dropped_count += 1
                logger.warning(
                    f"Operation queue full ({self.max_size}), "
                    f"dropping operation. Total dropped: {self._dropped_count}"
                )
                return False
            
            self._queue.append(operation)
            return True
    
    def dequeue(self) -> Optional[T]:
        """
        Remove and return operation from queue.
        
        Returns:
            Operation or None if queue is empty
        """
        with self._lock:
            if self._queue:
                return self._queue.popleft()
            return None
    
    def peek(self) -> Optional[T]:
        """
        View next operation without removing it.
        
        Returns:
            Operation or None if queue is empty
        """
        with self._lock:
            if self._queue:
                return self._queue[0]
            return None
    
    def size(self) -> int:
        """Get current queue size."""
        with self._lock:
            return len(self._queue)
    
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        with self._lock:
            return len(self._queue) == 0
    
    def clear(self):
        """Clear all operations from queue."""
        with self._lock:
            self._queue.clear()
            logger.info("Operation queue cleared")
    
    def get_stats(self) -> Dict[str, int]:
        """Get queue statistics."""
        with self._lock:
            return {
                'size': len(self._queue),
                'max_size': self.max_size,
                'dropped_count': self._dropped_count
            }


class GracefulDegradation:
    """
    Manager for graceful degradation when services are unavailable.
    
    Tracks service availability and provides fallback mechanisms.
    """
    
    def __init__(self):
        """Initialize graceful degradation manager."""
        self._service_status: Dict[str, bool] = {}
        self._fallback_data: Dict[str, Any] = {}
        self._last_update: Dict[str, datetime] = {}
        self._lock = Lock()
    
    def mark_service_unavailable(self, service_name: str):
        """
        Mark a service as unavailable.
        
        Args:
            service_name: Name of the service
        """
        with self._lock:
            self._service_status[service_name] = False
            self._last_update[service_name] = datetime.now()
            logger.warning(f"Service '{service_name}' marked as unavailable")
    
    def mark_service_available(self, service_name: str):
        """
        Mark a service as available.
        
        Args:
            service_name: Name of the service
        """
        with self._lock:
            self._service_status[service_name] = True
            self._last_update[service_name] = datetime.now()
            logger.info(f"Service '{service_name}' marked as available")
    
    def is_service_available(self, service_name: str) -> bool:
        """
        Check if a service is available.
        
        Args:
            service_name: Name of the service
            
        Returns:
            True if available, False otherwise
        """
        with self._lock:
            return self._service_status.get(service_name, True)
    
    def set_fallback_data(self, service_name: str, data: Any):
        """
        Set fallback data for a service.
        
        Args:
            service_name: Name of the service
            data: Fallback data
        """
        with self._lock:
            self._fallback_data[service_name] = data
            self._last_update[service_name] = datetime.now()
            logger.info(f"Fallback data set for service '{service_name}'")
    
    def get_fallback_data(self, service_name: str) -> Optional[Any]:
        """
        Get fallback data for a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Fallback data or None
        """
        with self._lock:
            return self._fallback_data.get(service_name)
    
    def get_data_age(self, service_name: str) -> Optional[timedelta]:
        """
        Get age of fallback data.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Age of data or None
        """
        with self._lock:
            last_update = self._last_update.get(service_name)
            if last_update:
                return datetime.now() - last_update
            return None
    
    def is_data_stale(
        self,
        service_name: str,
        max_age_seconds: float = 300.0
    ) -> bool:
        """
        Check if fallback data is stale.
        
        Args:
            service_name: Name of the service
            max_age_seconds: Maximum age in seconds
            
        Returns:
            True if data is stale, False otherwise
        """
        age = self.get_data_age(service_name)
        if age is None:
            return True
        return age.total_seconds() > max_age_seconds
    
    def get_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all services."""
        with self._lock:
            status = {}
            for service_name in self._service_status:
                age = self.get_data_age(service_name)
                status[service_name] = {
                    'available': self._service_status[service_name],
                    'has_fallback': service_name in self._fallback_data,
                    'data_age_seconds': age.total_seconds() if age else None,
                    'last_update': self._last_update[service_name].isoformat() if service_name in self._last_update else None
                }
            return status


# Global instances
_circuit_breakers: Dict[str, CircuitBreaker] = {}
_degradation_manager = GracefulDegradation()


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exception: type = Exception
) -> CircuitBreaker:
    """
    Get or create a circuit breaker.
    
    Args:
        name: Name of the circuit breaker
        failure_threshold: Number of failures before opening
        recovery_timeout: Seconds to wait before recovery attempt
        expected_exception: Exception type to catch
        
    Returns:
        CircuitBreaker instance
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception
        )
    return _circuit_breakers[name]


def get_degradation_manager() -> GracefulDegradation:
    """Get global graceful degradation manager."""
    return _degradation_manager


def get_all_circuit_breakers() -> Dict[str, CircuitBreaker]:
    """Get all circuit breakers."""
    return _circuit_breakers.copy()
