"""Middleware for FastAPI application."""

import logging
import time
import traceback
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging all HTTP requests and responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            HTTP response
        """
        # Generate request ID
        request_id = f"{int(time.time() * 1000)}"
        
        # Log request
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )
        
        # Time the request
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log response
            logger.info(
                f"[{request_id}] {request.method} {request.url.path} "
                f"completed with status {response.status_code} in {duration:.3f}s"
            )
            
            # Add custom headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{duration:.3f}"
            
            return response
            
        except Exception as e:
            # Log error
            duration = time.time() - start_time
            logger.error(
                f"[{request_id}] {request.method} {request.url.path} "
                f"failed after {duration:.3f}s: {str(e)}\n{traceback.format_exc()}"
            )
            
            # Return error response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error",
                    "message": str(e),
                    "request_id": request_id
                },
                headers={
                    "X-Request-ID": request_id,
                    "X-Process-Time": f"{duration:.3f}"
                }
            )


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for handling errors and returning appropriate responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with error handling.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            HTTP response
        """
        try:
            response = await call_next(request)
            return response
            
        except ValueError as e:
            logger.warning(f"Validation error: {e}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "Validation error",
                    "message": str(e)
                }
            )
            
        except PermissionError as e:
            logger.warning(f"Permission denied: {e}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": "Permission denied",
                    "message": str(e)
                }
            )
            
        except FileNotFoundError as e:
            logger.warning(f"Resource not found: {e}")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "error": "Resource not found",
                    "message": str(e)
                }
            )
            
        except TimeoutError as e:
            logger.error(f"Request timeout: {e}")
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content={
                    "error": "Request timeout",
                    "message": str(e)
                }
            )
            
        except Exception as e:
            logger.error(f"Unhandled error: {e}\n{traceback.format_exc()}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error",
                    "message": "An unexpected error occurred"
                }
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware (in-memory, per-IP)."""
    
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        """Initialize rate limiter.
        
        Args:
            app: FastAPI application
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # {ip: [(timestamp, count)]}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            HTTP response
        """
        # Skip rate limiting for health check
        if request.url.path == "/health":
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Get current time
        current_time = time.time()
        
        # Clean up old entries
        if client_ip in self.requests:
            self.requests[client_ip] = [
                (ts, count) for ts, count in self.requests[client_ip]
                if current_time - ts < self.window_seconds
            ]
        
        # Count requests in current window
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        
        request_count = sum(count for _, count in self.requests[client_ip])
        
        # Check rate limit
        if request_count >= self.max_requests:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.max_requests} requests per {self.window_seconds} seconds"
                }
            )
        
        # Add current request
        self.requests[client_ip].append((current_time, 1))
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(self.max_requests - request_count - 1)
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.window_seconds))
        
        return response
