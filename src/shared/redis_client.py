"""Redis pub/sub pipeline for real-time data streaming."""

import asyncio
import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime
from collections import deque
import redis
from redis.connection import ConnectionPool
from redis.exceptions import ConnectionError, TimeoutError, RedisError

from src.shared.config import settings
from src.shared.error_handling import (
    get_circuit_breaker,
    CircuitBreakerOpenError,
    ErrorLogger,
    get_degradation_manager
)

logger = logging.getLogger(__name__)
error_logger = ErrorLogger("redis")


class RedisChannels:
    """Redis channel names."""
    PRICES = "prices"
    SENTIMENT = "sentiment"
    EVENTS = "events"
    INDICATORS = "indicators"
    REGIME = "regime"
    SIGNALS = "signals"
    
    @classmethod
    def all_channels(cls) -> List[str]:
        """Get all channel names."""
        return [cls.PRICES, cls.SENTIMENT, cls.EVENTS, cls.INDICATORS, cls.REGIME, cls.SIGNALS]


class RedisPublisher:
    """Publisher interface for Redis pub/sub."""
    
    def __init__(self, redis_client: redis.Redis):
        """Initialize publisher with Redis client."""
        self.redis_client = redis_client
        self._buffer: deque = deque(maxlen=1000)
        self._buffer_enabled = False
        
    def publish(self, channel: str, data: Dict[str, Any]) -> bool:
        """
        Publish data to a Redis channel.
        
        Args:
            channel: Channel name to publish to
            data: Data dictionary to publish
            
        Returns:
            True if published successfully, False otherwise
        """
        try:
            message = json.dumps(data, default=str)
            self.redis_client.publish(channel, message)
            logger.debug(f"Published to {channel}: {message[:100]}...")
            return True
        except (ConnectionError, TimeoutError, RedisError) as e:
            logger.warning(f"Failed to publish to {channel}, buffering message: {e}")
            if self._buffer_enabled:
                self._buffer.append((channel, data, time.time()))
            return False
        except Exception as e:
            logger.error(f"Error publishing to {channel}: {e}")
            if self._buffer_enabled:
                self._buffer.append((channel, data, time.time()))
            return False
    
    def enable_buffering(self):
        """Enable local buffering when Redis is unavailable."""
        self._buffer_enabled = True
        logger.info("Redis publisher buffering enabled")
    
    def disable_buffering(self):
        """Disable local buffering."""
        self._buffer_enabled = False
        logger.info("Redis publisher buffering disabled")
    
    def replay_buffer(self) -> int:
        """
        Replay buffered messages after reconnection.
        
        Returns:
            Number of messages successfully replayed
        """
        if not self._buffer:
            return 0
            
        replayed = 0
        failed_messages = []
        
        while self._buffer:
            channel, data, timestamp = self._buffer.popleft()
            age = time.time() - timestamp
            
            # Skip messages older than 5 minutes
            if age > 300:
                logger.warning(f"Skipping stale buffered message (age: {age:.1f}s)")
                continue
                
            if self.publish(channel, data):
                replayed += 1
            else:
                failed_messages.append((channel, data, timestamp))
        
        # Re-add failed messages to buffer
        for msg in failed_messages:
            self._buffer.append(msg)
        
        logger.info(f"Replayed {replayed} buffered messages, {len(failed_messages)} failed")
        return replayed


class RedisSubscriber:
    """Subscriber interface for Redis pub/sub."""
    
    def __init__(self, redis_client: redis.Redis):
        """Initialize subscriber with Redis client."""
        self.redis_client = redis_client
        self.pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
        self._handlers: Dict[str, List[Callable]] = {}
        self._subscribed_channels: Set[str] = set()
        self._running = False
        
    def subscribe(self, channels: List[str], handler: Callable[[str, Dict[str, Any]], None]):
        """
        Subscribe to Redis channels with a message handler.
        
        Args:
            channels: List of channel names to subscribe to
            handler: Callback function to handle messages (channel, data)
        """
        for channel in channels:
            if channel not in self._handlers:
                self._handlers[channel] = []
                self.pubsub.subscribe(channel)
                self._subscribed_channels.add(channel)
                logger.info(f"Subscribed to channel: {channel}")
            
            self._handlers[channel].append(handler)
    
    def unsubscribe(self, channels: List[str]):
        """Unsubscribe from Redis channels."""
        for channel in channels:
            if channel in self._subscribed_channels:
                self.pubsub.unsubscribe(channel)
                self._subscribed_channels.remove(channel)
                if channel in self._handlers:
                    del self._handlers[channel]
                logger.info(f"Unsubscribed from channel: {channel}")
    
    async def listen(self):
        """Listen for messages on subscribed channels."""
        self._running = True
        logger.info(f"Started listening on channels: {list(self._subscribed_channels)}")
        
        while self._running:
            try:
                message = self.pubsub.get_message(timeout=1.0)
                if message and message['type'] == 'message':
                    channel = message['channel'].decode('utf-8')
                    data_str = message['data'].decode('utf-8')
                    
                    try:
                        data = json.loads(data_str)
                        
                        # Call all handlers for this channel
                        if channel in self._handlers:
                            for handler in self._handlers[channel]:
                                try:
                                    handler(channel, data)
                                except Exception as e:
                                    logger.error(f"Error in handler for {channel}: {e}")
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to decode message from {channel}: {e}")
                        
            except (ConnectionError, TimeoutError) as e:
                logger.error(f"Redis connection error while listening: {e}")
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Unexpected error while listening: {e}")
                await asyncio.sleep(1)
    
    def stop(self):
        """Stop listening for messages."""
        self._running = False
        logger.info("Stopped listening for messages")
    
    def close(self):
        """Close the subscriber and cleanup resources."""
        self.stop()
        self.pubsub.close()
        logger.info("Subscriber closed")


class RedisClient:
    """Main Redis client with connection management and reconnection logic."""
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        db: int = None,
        max_connections: int = 50
    ):
        """
        Initialize Redis client with connection pooling.
        
        Args:
            host: Redis host (defaults to settings)
            port: Redis port (defaults to settings)
            db: Redis database number (defaults to settings)
            max_connections: Maximum connections in pool
        """
        self.host = host or settings.redis_host
        self.port = port or settings.redis_port
        self.db = db or settings.redis_db
        
        self.pool = ConnectionPool(
            host=self.host,
            port=self.port,
            db=self.db,
            max_connections=max_connections,
            decode_responses=False
        )
        
        self.client = redis.Redis(connection_pool=self.pool)
        self.publisher = RedisPublisher(self.client)
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        self._base_backoff = 1.0
        self._circuit_breaker = get_circuit_breaker(
            name="redis",
            failure_threshold=5,
            recovery_timeout=30.0,
            expected_exception=(ConnectionError, TimeoutError, RedisError)
        )
        self._degradation_manager = get_degradation_manager()
        
        logger.info(f"Redis client initialized: {self.host}:{self.port}/{self.db}")
    
    def ping(self) -> bool:
        """Check if Redis connection is alive."""
        try:
            self._circuit_breaker.call(self.client.ping)
            self._degradation_manager.mark_service_available("redis")
            return True
        except CircuitBreakerOpenError:
            logger.warning("Redis circuit breaker is open")
            self._degradation_manager.mark_service_unavailable("redis")
            return False
        except Exception as e:
            error_logger.log_error(e, {'action': 'ping'})
            self._degradation_manager.mark_service_unavailable("redis")
            return False
    
    def reconnect(self) -> bool:
        """
        Attempt to reconnect to Redis with exponential backoff.
        
        Returns:
            True if reconnection successful, False otherwise
        """
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            error_logger.log_error(
                Exception(f"Max reconnection attempts ({self._max_reconnect_attempts}) reached"),
                {'action': 'reconnect'}
            )
            self._degradation_manager.mark_service_unavailable("redis")
            return False
        
        backoff = self._base_backoff * (2 ** self._reconnect_attempts)
        logger.info(f"Attempting reconnection {self._reconnect_attempts + 1}/{self._max_reconnect_attempts} "
                   f"after {backoff}s backoff")
        
        time.sleep(backoff)
        
        try:
            # Create new connection pool
            self.pool = ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                max_connections=50,
                decode_responses=False
            )
            self.client = redis.Redis(connection_pool=self.pool)
            
            # Test connection
            if self.ping():
                logger.info("Redis reconnection successful")
                self._reconnect_attempts = 0
                
                # Reset circuit breaker
                self._circuit_breaker.reset()
                
                # Replay buffered messages
                self.publisher.redis_client = self.client
                replayed = self.publisher.replay_buffer()
                self.publisher.disable_buffering()
                
                logger.info(f"Replayed {replayed} buffered messages after reconnection")
                
                self._degradation_manager.mark_service_available("redis")
                return True
            else:
                self._reconnect_attempts += 1
                return False
                
        except Exception as e:
            error_logger.log_error(e, {'action': 'reconnect', 'attempt': self._reconnect_attempts + 1})
            self._reconnect_attempts += 1
            return False
    
    def create_subscriber(self) -> RedisSubscriber:
        """Create a new subscriber instance."""
        return RedisSubscriber(self.client)
    
    def publish(self, channel: str, data: Dict[str, Any]) -> bool:
        """
        Publish data to a channel.
        
        Args:
            channel: Channel name
            data: Data to publish
            
        Returns:
            True if successful, False otherwise
        """
        success = self.publisher.publish(channel, data)
        
        # If publish failed, enable buffering and attempt reconnection
        if not success:
            self.publisher.enable_buffering()
            if self.reconnect():
                # Try publishing again after reconnection
                return self.publisher.publish(channel, data)
        
        return success
    
    def close(self):
        """Close Redis connection and cleanup resources."""
        try:
            self.client.close()
            self.pool.disconnect()
            logger.info("Redis client closed")
        except Exception as e:
            logger.error(f"Error closing Redis client: {e}")


# Global Redis client instance
_redis_client: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    """Get or create global Redis client instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client


def close_redis_client():
    """Close global Redis client instance."""
    global _redis_client
    if _redis_client is not None:
        _redis_client.close()
        _redis_client = None
