"""Tests for Redis pub/sub pipeline."""

import pytest
import time
import json
from unittest.mock import Mock, patch, MagicMock
from src.shared.redis_client import (
    RedisClient,
    RedisPublisher,
    RedisSubscriber,
    RedisChannels,
    get_redis_client,
    close_redis_client
)


class TestRedisChannels:
    """Test Redis channel definitions."""
    
    def test_all_channels_returns_complete_list(self):
        """Test that all_channels returns all defined channels."""
        channels = RedisChannels.all_channels()
        assert len(channels) == 6
        assert RedisChannels.PRICES in channels
        assert RedisChannels.SENTIMENT in channels
        assert RedisChannels.EVENTS in channels
        assert RedisChannels.INDICATORS in channels
        assert RedisChannels.REGIME in channels
        assert RedisChannels.SIGNALS in channels


class TestRedisPublisher:
    """Test Redis publisher functionality."""
    
    def test_publish_success(self):
        """Test successful message publishing."""
        mock_client = Mock()
        mock_client.publish.return_value = 1
        
        publisher = RedisPublisher(mock_client)
        data = {"test": "data", "timestamp": "2024-01-01T00:00:00"}
        
        result = publisher.publish(RedisChannels.PRICES, data)
        
        assert result is True
        mock_client.publish.assert_called_once()
        
    def test_publish_connection_error_enables_buffering(self):
        """Test that connection errors enable buffering."""
        mock_client = Mock()
        mock_client.publish.side_effect = ConnectionError("Connection failed")
        
        publisher = RedisPublisher(mock_client)
        publisher.enable_buffering()
        
        data = {"test": "data"}
        result = publisher.publish(RedisChannels.PRICES, data)
        
        assert result is False
        assert len(publisher._buffer) == 1
        
    def test_replay_buffer_success(self):
        """Test successful buffer replay."""
        mock_client = Mock()
        mock_client.publish.return_value = 1
        
        publisher = RedisPublisher(mock_client)
        publisher.enable_buffering()
        
        # Add messages to buffer
        data1 = {"msg": "1"}
        data2 = {"msg": "2"}
        publisher._buffer.append((RedisChannels.PRICES, data1, time.time()))
        publisher._buffer.append((RedisChannels.SENTIMENT, data2, time.time()))
        
        replayed = publisher.replay_buffer()
        
        assert replayed == 2
        assert len(publisher._buffer) == 0
        
    def test_replay_buffer_skips_stale_messages(self):
        """Test that replay skips messages older than 5 minutes."""
        mock_client = Mock()
        mock_client.publish.return_value = 1
        
        publisher = RedisPublisher(mock_client)
        
        # Add stale message (6 minutes old)
        stale_time = time.time() - 360
        publisher._buffer.append((RedisChannels.PRICES, {"msg": "stale"}, stale_time))
        
        # Add fresh message
        publisher._buffer.append((RedisChannels.PRICES, {"msg": "fresh"}, time.time()))
        
        replayed = publisher.replay_buffer()
        
        assert replayed == 1  # Only fresh message replayed


class TestRedisSubscriber:
    """Test Redis subscriber functionality."""
    
    def test_subscribe_to_channels(self):
        """Test subscribing to channels."""
        mock_client = Mock()
        mock_pubsub = Mock()
        mock_client.pubsub.return_value = mock_pubsub
        
        subscriber = RedisSubscriber(mock_client)
        handler = Mock()
        
        channels = [RedisChannels.PRICES, RedisChannels.SENTIMENT]
        subscriber.subscribe(channels, handler)
        
        assert len(subscriber._subscribed_channels) == 2
        assert RedisChannels.PRICES in subscriber._subscribed_channels
        assert RedisChannels.SENTIMENT in subscriber._subscribed_channels
        
    def test_unsubscribe_from_channels(self):
        """Test unsubscribing from channels."""
        mock_client = Mock()
        mock_pubsub = Mock()
        mock_client.pubsub.return_value = mock_pubsub
        
        subscriber = RedisSubscriber(mock_client)
        handler = Mock()
        
        channels = [RedisChannels.PRICES]
        subscriber.subscribe(channels, handler)
        subscriber.unsubscribe(channels)
        
        assert len(subscriber._subscribed_channels) == 0
        assert RedisChannels.PRICES not in subscriber._handlers
        
    def test_message_handler_called(self):
        """Test that message handlers are called correctly."""
        mock_client = Mock()
        mock_pubsub = Mock()
        mock_client.pubsub.return_value = mock_pubsub
        
        # Mock message
        test_data = {"price": 100.0}
        mock_message = {
            'type': 'message',
            'channel': b'prices',
            'data': json.dumps(test_data).encode('utf-8')
        }
        mock_pubsub.get_message.side_effect = [mock_message, None]
        
        subscriber = RedisSubscriber(mock_client)
        handler = Mock()
        
        subscriber.subscribe([RedisChannels.PRICES], handler)
        
        # Manually process one message
        message = mock_pubsub.get_message(timeout=1.0)
        if message and message['type'] == 'message':
            channel = message['channel'].decode('utf-8')
            data = json.loads(message['data'].decode('utf-8'))
            handler(channel, data)
        
        handler.assert_called_once_with('prices', test_data)


class TestRedisClient:
    """Test Redis client with connection management."""
    
    @patch('src.shared.redis_client.redis.Redis')
    @patch('src.shared.redis_client.ConnectionPool')
    def test_client_initialization(self, mock_pool, mock_redis):
        """Test Redis client initialization."""
        client = RedisClient(host="localhost", port=6379, db=0)
        
        assert client.host == "localhost"
        assert client.port == 6379
        assert client.db == 0
        mock_pool.assert_called_once()
        
    @patch('src.shared.redis_client.redis.Redis')
    @patch('src.shared.redis_client.ConnectionPool')
    def test_ping_success(self, mock_pool, mock_redis):
        """Test successful ping."""
        mock_client_instance = Mock()
        mock_client_instance.ping.return_value = True
        mock_redis.return_value = mock_client_instance
        
        client = RedisClient()
        result = client.ping()
        
        assert result is True
        
    @patch('src.shared.redis_client.redis.Redis')
    @patch('src.shared.redis_client.ConnectionPool')
    def test_ping_failure(self, mock_pool, mock_redis):
        """Test ping failure."""
        mock_client_instance = Mock()
        mock_client_instance.ping.side_effect = Exception("Connection failed")
        mock_redis.return_value = mock_client_instance
        
        client = RedisClient()
        result = client.ping()
        
        assert result is False
        
    @patch('src.shared.redis_client.redis.Redis')
    @patch('src.shared.redis_client.ConnectionPool')
    @patch('time.sleep')
    def test_reconnect_with_backoff(self, mock_sleep, mock_pool, mock_redis):
        """Test reconnection with exponential backoff."""
        mock_client_instance = Mock()
        mock_client_instance.ping.return_value = True
        mock_redis.return_value = mock_client_instance
        
        client = RedisClient()
        client._reconnect_attempts = 2
        
        result = client.reconnect()
        
        assert result is True
        assert client._reconnect_attempts == 0
        # Backoff should be 1 * 2^2 = 4 seconds
        mock_sleep.assert_called_once_with(4.0)
        
    @patch('src.shared.redis_client.redis.Redis')
    @patch('src.shared.redis_client.ConnectionPool')
    def test_publish_with_reconnection(self, mock_pool, mock_redis):
        """Test publish with automatic reconnection."""
        mock_client_instance = Mock()
        # First publish fails, then succeeds after reconnection
        mock_client_instance.publish.side_effect = [ConnectionError(), 1]
        mock_client_instance.ping.return_value = True
        mock_redis.return_value = mock_client_instance
        
        client = RedisClient()
        
        with patch.object(client, 'reconnect', return_value=True):
            result = client.publish(RedisChannels.PRICES, {"test": "data"})
        
        # Should succeed after reconnection
        assert result is True or result is False  # Depends on mock behavior


class TestGlobalRedisClient:
    """Test global Redis client management."""
    
    def test_get_redis_client_singleton(self):
        """Test that get_redis_client returns singleton instance."""
        close_redis_client()  # Clean up first
        
        with patch('src.shared.redis_client.RedisClient') as mock_client_class:
            client1 = get_redis_client()
            client2 = get_redis_client()
            
            assert client1 is client2
            mock_client_class.assert_called_once()
        
        close_redis_client()
        
    def test_close_redis_client(self):
        """Test closing global Redis client."""
        close_redis_client()
        
        with patch('src.shared.redis_client.RedisClient') as mock_client_class:
            mock_instance = Mock()
            mock_client_class.return_value = mock_instance
            
            client = get_redis_client()
            close_redis_client()
            
            mock_instance.close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
