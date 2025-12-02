"""Order executor for automated trading through Kite Connect API."""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from threading import Lock

from src.shared.models import (
    Order, OrderStatus, OrderType, Side, TradingSignal, TradingSignalType
)
from src.shared.redis_client import RedisChannels, RedisClient, RedisSubscriber
from src.shared.config import settings
from src.database.connection import get_db_session
from src.database.repositories import OrderRepository

logger = logging.getLogger(__name__)


class RiskManagementError(Exception):
    """Exception raised when risk management validation fails."""
    pass


class KiteConnectClient:
    """
    Client for interacting with Zerodha Kite Connect API.
    
    This is a wrapper around the Kite Connect API that handles
    authentication, order placement, and status tracking.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        access_token: Optional[str] = None
    ):
        """
        Initialize Kite Connect client.
        
        Args:
            api_key: Kite Connect API key
            api_secret: Kite Connect API secret
            access_token: Kite Connect access token
        """
        self.api_key = api_key or settings.kite_api_key
        self.api_secret = api_secret or settings.kite_api_secret
        self.access_token = access_token or settings.kite_access_token
        
        if not self.api_key or not self.access_token:
            logger.warning(
                "Kite Connect credentials not configured. "
                "Order execution will be simulated."
            )
            self._simulation_mode = True
        else:
            self._simulation_mode = False
            self._initialize_kite()
        
        self._order_counter = 0
        logger.info(
            f"Kite Connect client initialized "
            f"(simulation_mode={self._simulation_mode})"
        )
    
    def _initialize_kite(self):
        """Initialize Kite Connect SDK."""
        try:
            from kiteconnect import KiteConnect
            self.kite = KiteConnect(api_key=self.api_key)
            self.kite.set_access_token(self.access_token)
            logger.info("Kite Connect SDK initialized successfully")
        except ImportError:
            logger.warning(
                "kiteconnect package not installed. "
                "Running in simulation mode."
            )
            self._simulation_mode = True
        except Exception as e:
            logger.error(f"Failed to initialize Kite Connect: {e}")
            self._simulation_mode = True
    
    def place_order(
        self,
        symbol: str,
        side: Side,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None
    ) -> str:
        """
        Place an order through Kite Connect API.
        
        Args:
            symbol: Trading symbol
            side: Order side (BUY/SELL)
            quantity: Order quantity
            order_type: Order type (MARKET/LIMIT)
            price: Limit price (required for LIMIT orders)
            
        Returns:
            Order ID from broker
            
        Raises:
            Exception: If order placement fails
        """
        if self._simulation_mode:
            return self._simulate_order_placement(symbol, side, quantity, order_type, price)
        
        try:
            # Map our enums to Kite Connect constants
            kite_side = self.kite.TRANSACTION_TYPE_BUY if side == Side.BUY else self.kite.TRANSACTION_TYPE_SELL
            kite_order_type = self.kite.ORDER_TYPE_MARKET if order_type == OrderType.MARKET else self.kite.ORDER_TYPE_LIMIT
            
            # Place order
            order_params = {
                'tradingsymbol': symbol,
                'exchange': self.kite.EXCHANGE_NSE,  # Default to NSE
                'transaction_type': kite_side,
                'quantity': int(quantity),
                'order_type': kite_order_type,
                'product': self.kite.PRODUCT_CNC,  # Cash and Carry
                'validity': self.kite.VALIDITY_DAY
            }
            
            if order_type == OrderType.LIMIT and price is not None:
                order_params['price'] = price
            
            order_id = self.kite.place_order(**order_params)
            logger.info(
                f"Order placed successfully: {order_id} "
                f"({side.value} {quantity} {symbol})"
            )
            return str(order_id)
            
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            raise
    
    def _simulate_order_placement(
        self,
        symbol: str,
        side: Side,
        quantity: float,
        order_type: OrderType,
        price: Optional[float]
    ) -> str:
        """Simulate order placement for testing."""
        self._order_counter += 1
        order_id = f"SIM{datetime.now().strftime('%Y%m%d')}{self._order_counter:06d}"
        logger.info(
            f"[SIMULATION] Order placed: {order_id} "
            f"({side.value} {quantity} {symbol} @ {price or 'MARKET'})"
        )
        return order_id
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get order status from Kite Connect API.
        
        Args:
            order_id: Order ID from broker
            
        Returns:
            Order status information
        """
        if self._simulation_mode:
            return self._simulate_order_status(order_id)
        
        try:
            orders = self.kite.orders()
            for order in orders:
                if str(order['order_id']) == order_id:
                    return order
            
            logger.warning(f"Order {order_id} not found")
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get order status: {e}")
            return {}
    
    def _simulate_order_status(self, order_id: str) -> Dict[str, Any]:
        """Simulate order status for testing."""
        return {
            'order_id': order_id,
            'status': 'COMPLETE',
            'filled_quantity': 1,
            'average_price': 100.0
        }
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.
        
        Args:
            order_id: Order ID from broker
            
        Returns:
            True if cancellation successful, False otherwise
        """
        if self._simulation_mode:
            logger.info(f"[SIMULATION] Order cancelled: {order_id}")
            return True
        
        try:
            self.kite.cancel_order(
                variety=self.kite.VARIETY_REGULAR,
                order_id=order_id
            )
            logger.info(f"Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False


class OrderExecutor:
    """
    Order executor that subscribes to trading signals and executes orders.
    
    Validates signals against risk management rules before execution,
    tracks order status, and stores orders in the database.
    """
    
    def __init__(
        self,
        redis_client: RedisClient,
        kite_client: Optional[KiteConnectClient] = None,
        enable_auto_trading: bool = None,
        position_size: float = None,
        max_position_size: float = 10000.0,
        max_daily_trades: int = 10
    ):
        """
        Initialize order executor.
        
        Args:
            redis_client: Redis client for pub/sub
            kite_client: Kite Connect client (creates new if None)
            enable_auto_trading: Enable automatic order execution
            position_size: Default position size per trade
            max_position_size: Maximum position size allowed
            max_daily_trades: Maximum trades per day
        """
        self.redis_client = redis_client
        self.kite_client = kite_client or KiteConnectClient()
        self.subscriber: Optional[RedisSubscriber] = None
        
        # Trading configuration
        self.enable_auto_trading = (
            enable_auto_trading 
            if enable_auto_trading is not None 
            else settings.enable_auto_trading
        )
        self.position_size = position_size or settings.position_size
        self.max_position_size = max_position_size
        self.max_daily_trades = max_daily_trades
        
        # State tracking
        self._lock = Lock()
        self._daily_trade_count = 0
        self._current_position_size = 0.0
        self._last_reset_date = datetime.now().date()
        
        logger.info(
            f"Order executor initialized "
            f"(auto_trading={self.enable_auto_trading}, "
            f"position_size={self.position_size})"
        )
    
    def start(self):
        """Start subscribing to trading signals."""
        self.subscriber = self.redis_client.create_subscriber()
        self.subscriber.subscribe([RedisChannels.SIGNALS], self._handle_signal)
        logger.info("Order executor started, listening for signals")
    
    async def listen(self):
        """Listen for trading signals."""
        if self.subscriber is None:
            raise RuntimeError("Executor not started. Call start() first.")
        
        await self.subscriber.listen()
    
    def stop(self):
        """Stop listening and cleanup."""
        if self.subscriber:
            self.subscriber.stop()
            self.subscriber.close()
            logger.info("Order executor stopped")
    
    def _handle_signal(self, channel: str, data: Dict[str, Any]):
        """
        Handle incoming trading signal.
        
        Args:
            channel: Channel name (should be 'signals')
            data: Signal data
        """
        try:
            # Parse signal
            signal_type = TradingSignalType(data['signal_type'])
            
            # Only process BUY and SELL signals
            if signal_type == TradingSignalType.HOLD:
                logger.debug("Received HOLD signal, no action taken")
                return
            
            # Check if auto trading is enabled
            if not self.enable_auto_trading:
                logger.info(
                    f"Received {signal_type.value} signal but auto trading is disabled"
                )
                return
            
            # Create signal object for validation
            # Note: We don't have the full signal object, just the data
            # For validation, we mainly need the signal type and CMS score
            cms_score = float(data.get('cms_score', 0.0))
            
            # Validate signal
            try:
                self.validate_signal(signal_type, cms_score)
            except RiskManagementError as e:
                logger.warning(f"Signal validation failed: {e}")
                return
            
            # Execute order
            # For now, we'll use a default symbol (should come from signal in production)
            symbol = "RELIANCE"  # TODO: Extract from signal data
            self.execute_order(signal_type, symbol, data)
            
        except Exception as e:
            logger.error(f"Error handling signal: {e}", exc_info=True)
    
    def validate_signal(
        self,
        signal_type: TradingSignalType,
        cms_score: float
    ) -> bool:
        """
        Validate trading signal against risk management rules.
        
        Args:
            signal_type: Type of trading signal
            cms_score: Composite Market Score
            
        Returns:
            True if validation passes
            
        Raises:
            RiskManagementError: If validation fails
        """
        with self._lock:
            # Reset daily counters if new day
            current_date = datetime.now().date()
            if current_date != self._last_reset_date:
                self._daily_trade_count = 0
                self._last_reset_date = current_date
                logger.info("Daily trade counters reset")
            
            # Check daily trade limit
            if self._daily_trade_count >= self.max_daily_trades:
                raise RiskManagementError(
                    f"Daily trade limit reached ({self.max_daily_trades})"
                )
            
            # Check position size limit
            if signal_type == TradingSignalType.BUY:
                new_position = self._current_position_size + self.position_size
                if new_position > self.max_position_size:
                    raise RiskManagementError(
                        f"Position size limit exceeded "
                        f"(current={self._current_position_size}, "
                        f"max={self.max_position_size})"
                    )
            
            # Validate CMS score strength
            if signal_type == TradingSignalType.BUY:
                if cms_score <= settings.cms_buy_threshold:
                    raise RiskManagementError(
                        f"BUY signal CMS score too low "
                        f"({cms_score} <= {settings.cms_buy_threshold})"
                    )
            elif signal_type == TradingSignalType.SELL:
                if cms_score >= settings.cms_sell_threshold:
                    raise RiskManagementError(
                        f"SELL signal CMS score too high "
                        f"({cms_score} >= {settings.cms_sell_threshold})"
                    )
            
            logger.debug(f"Signal validation passed for {signal_type.value}")
            return True
    
    def execute_order(
        self,
        signal_type: TradingSignalType,
        symbol: str,
        signal_data: Dict[str, Any]
    ) -> Optional[Order]:
        """
        Execute an order based on trading signal.
        
        Args:
            signal_type: Type of trading signal
            symbol: Trading symbol
            signal_data: Full signal data from Redis
            
        Returns:
            Order object if successful, None otherwise
        """
        try:
            # Determine order side
            side = Side.BUY if signal_type == TradingSignalType.BUY else Side.SELL
            
            # Place order through Kite Connect
            order_id = self.kite_client.place_order(
                symbol=symbol,
                side=side,
                quantity=self.position_size,
                order_type=OrderType.MARKET
            )
            
            # Create order object
            order = Order(
                order_id=order_id,
                symbol=symbol,
                order_type=OrderType.MARKET,
                side=side,
                quantity=self.position_size,
                price=None,  # Market order, no price
                status=OrderStatus.SUBMITTED,
                signal_id=str(signal_data.get('timestamp', '')),  # Use timestamp as signal ID
                timestamp=datetime.now()
            )
            
            # Store order in database
            self._store_order(order)
            
            # Update state
            with self._lock:
                self._daily_trade_count += 1
                if side == Side.BUY:
                    self._current_position_size += self.position_size
                else:
                    self._current_position_size -= self.position_size
            
            logger.info(
                f"Order executed: {order_id} "
                f"({side.value} {self.position_size} {symbol})"
            )
            
            return order
            
        except Exception as e:
            logger.error(f"Failed to execute order: {e}", exc_info=True)
            self._handle_execution_error(e)
            return None
    
    def _store_order(self, order: Order):
        """
        Store order in PostgreSQL database.
        
        Args:
            order: Order to store
        """
        try:
            with get_db_session() as session:
                repo = OrderRepository(session)
                
                # Convert to database model
                from src.database.models import Order as DBOrder
                
                db_order = DBOrder(
                    order_id=order.order_id,
                    symbol=order.symbol,
                    order_type=order.order_type.value,
                    side=order.side.value,
                    quantity=order.quantity,
                    price=order.price,
                    status=order.status.value,
                    signal_id=None,  # Will be linked later if needed
                    timestamp=order.timestamp
                )
                
                repo.create(db_order)
                session.commit()
                logger.debug(f"Order stored in database: {order.order_id}")
                
        except Exception as e:
            logger.error(f"Failed to store order in database: {e}")
    
    def check_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """
        Check order status from Kite Connect API.
        
        Args:
            order_id: Order ID from broker
            
        Returns:
            OrderStatus if found, None otherwise
        """
        try:
            status_data = self.kite_client.get_order_status(order_id)
            
            if not status_data:
                return None
            
            # Map Kite status to our OrderStatus
            kite_status = status_data.get('status', '').upper()
            status_map = {
                'COMPLETE': OrderStatus.FILLED,
                'OPEN': OrderStatus.SUBMITTED,
                'PENDING': OrderStatus.PENDING,
                'CANCELLED': OrderStatus.CANCELLED,
                'REJECTED': OrderStatus.REJECTED
            }
            
            return status_map.get(kite_status, OrderStatus.PENDING)
            
        except Exception as e:
            logger.error(f"Failed to check order status: {e}")
            return None
    
    def handle_fill(self, order_id: str):
        """
        Handle order fill notification.
        
        Args:
            order_id: Order ID that was filled
        """
        try:
            # Update order status in database
            with get_db_session() as session:
                repo = OrderRepository(session)
                updated_order = repo.update_status(order_id, OrderStatus.FILLED.value)
                
                if updated_order:
                    session.commit()
                    logger.info(f"Order {order_id} marked as FILLED")
                else:
                    logger.warning(f"Order {order_id} not found in database")
                    
        except Exception as e:
            logger.error(f"Failed to handle order fill: {e}")
    
    def _handle_execution_error(self, error: Exception):
        """
        Handle order execution errors.
        
        Args:
            error: Exception that occurred
        """
        logger.error(f"Order execution error: {error}")
        
        # Check if it's a Kite Connect API error
        if "kiteconnect" in str(type(error)).lower():
            logger.error(
                "Kite Connect API error detected. "
                "Disabling automatic trading."
            )
            self.enable_auto_trading = False
            
            # TODO: Send alert to dashboard via WebSocket
            # For now, just log the error
            logger.critical(
                "AUTOMATIC TRADING DISABLED due to Kite Connect API failure. "
                "Manual intervention required."
            )
