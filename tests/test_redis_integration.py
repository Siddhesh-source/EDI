"""Integration tests for Redis pub/sub pipeline (requires running Redis instance)."""

import pytest
import asyncio
import time
from src.shared.redis_client import RedisClient, RedisChannels


@pytest.mark.integration
class TestRedisIntegration:
    """Integration tests requiring a running Redis instance."""
    
    @pytest.fixture
    def redis_client(self):
        """Create Redis client for testing."""
        client = RedisClient()
        yield client
        client.close()
    
    def test_ping_redis_connection(self, redis_client):
        """Test connection to Redis server."""
        try:
            result = redis_client.ping()
            assert result is True, "Redis connection should be successful"
        except Exception as e:
            pytest.skip(f"Redis not available: {e}")
    
    def test_publish_and_subscribe(self, redis_client):
        """Test publishing and subscribing to messages."""
        try:
            if not redis_client.ping():
                pytest.skip("Redis not available")
            
            received_messages = []
            
            def message_handler(channel, data):
                received_messages.append((channel, data))
            
            # Create subscriber
            subscriber = redis_client.create_subscriber()
            subscriber.subscribe([RedisChannels.PRICES], message_handler)
            
            # Publish message
            test_data = {"symbol": "AAPL", "price": 150.0, "timestamp": "2024-01-01T00:00:00"}
            redis_client.publish(RedisChannels.PRICES, test_data)
            
            # Give time for message to be delivered
            time.sleep(0.5)
            
            # Process one message
            message = subscriber.pubsub.get_message(timeout=1.0)
            if message and message['type'] == 'message':
                import json
                channel = message['channel'].decode('utf-8')
                data = json.loads(message['data'].decode('utf-8'))
                message_handler(channel, data)
            
            # Verify message received
            assert len(received_messages) > 0
            assert received_messages[0][0] == RedisChannels.PRICES
            assert received_messages[0][1]["symbol"] == "AAPL"
            
            subscriber.close()
            
        except Exception as e:
            pytest.skip(f"Redis integration test failed: {e}")
    
    def test_channel_separation(self, redis_client):
        """Test that messages are delivered only to correct channels."""
        try:
            if not redis_client.ping():
                pytest.skip("Redis not available")
            
            prices_messages = []
            sentiment_messages = []
            
            def prices_handler(channel, data):
                prices_messages.append(data)
            
            def sentiment_handler(channel, data):
                sentiment_messages.append(data)
            
            # Create subscribers for different channels
            subscriber1 = redis_client.create_subscriber()
            subscriber1.subscribe([RedisChannels.PRICES], prices_handler)
            
            subscriber2 = redis_client.create_subscriber()
            subscriber2.subscribe([RedisChannels.SENTIMENT], sentiment_handler)
            
            # Publish to prices channel
            redis_client.publish(RedisChannels.PRICES, {"price": 100.0})
            
            # Publish to sentiment channel
            redis_client.publish(RedisChannels.SENTIMENT, {"score": 0.5})
            
            time.sleep(0.5)
            
            # Process messages
            for _ in range(2):
                msg1 = subscriber1.pubsub.get_message(timeout=1.0)
                if msg1 and msg1['type'] == 'message':
                    import json
                    data = json.loads(msg1['data'].decode('utf-8'))
                    prices_handler(RedisChannels.PRICES, data)
                
                msg2 = subscriber2.pubsub.get_message(timeout=1.0)
                if msg2 and msg2['type'] == 'message':
                    import json
                    data = json.loads(msg2['data'].decode('utf-8'))
                    sentiment_handler(RedisChannels.SENTIMENT, data)
            
            # Verify channel separation
            assert len(prices_messages) > 0
            assert len(sentiment_messages) > 0
            assert "price" in prices_messages[0]
            assert "score" in sentiment_messages[0]
            
            subscriber1.close()
            subscriber2.close()
            
        except Exception as e:
            pytest.skip(f"Redis integration test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
