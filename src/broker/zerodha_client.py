"""
Zerodha Kite Connect Integration
Handles authentication, order placement, and position management for Indian markets.
"""

import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from kiteconnect import KiteConnect
from kiteconnect.exceptions import (
    KiteException, NetworkException, TokenException,
    PermissionException, OrderException
)

from src.shared.redis_client import get_redis_client
from src.database.connection import get_db_session

logger = logging.getLogger(__name__)


class ZerodhaClient:
    """
    Zerodha Kite Connect API client with retry logic and error handling.
    """
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        access_token: Optional[str] = None
    ):
        """
        Initialize Zerodha client.
        
        Args:
            api_key: Zerodha API key
            api_secret: Zerodha API secret
            access_token: Optional access token (if already authenticated)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.kite = KiteConnect(api_key=api_key)
        
        if access_token:
            self.kite.set_access_token(access_token)
            self.access_token = access_token
        else:
            self.access_token = None
        
        self.redis_client = get_redis_client()
        
        logger.info("Zerodha client initialized")
    
    def get_login_url(self) -> str:
        """
        Get Zerodha login URL for authentication.
        
        Returns:
            Login URL string
        """
        login_url = self.kite.login_url()
        logger.info(f"Generated login URL: {login_url}")
        return login_url
    
    def generate_session(self, request_token: str) -> Dict[str, Any]:
        """
        Generate session and access token from request token.
        
        Args:
            request_token: Request token from Zerodha login callback
            
        Returns:
            Session data with access token
            
        Raises:
            TokenException: If token generation fails
        """
        try:
            data = self.kite.generate_session(
                request_token=request_token,
                api_secret=self.api_secret
            )
            
            self.access_token = data["access_token"]
            self.kite.set_access_token(self.access_token)
            
            # Store access token in Redis (expires in 24 hours)
            self.redis_client.setex(
                f"zerodha:access_token:{self.api_key}",
                86400,  # 24 hours
                self.access_token
            )
            
            logger.info("Session generated successfully")
            return data
            
        except TokenException as e:
            logger.error(f"Token generation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during session generation: {e}")
            raise
    
    def _retry_on_failure(
        self,
        func,
        *args,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        **kwargs
    ) -> Any:
        """
        Retry function on network/temporary failures.
        
        Args:
            func: Function to execute
            max_retries: Maximum number of retries
            retry_delay: Delay between retries in seconds
            *args, **kwargs: Arguments for the function
            
        Returns:
            Function result
            
        Raises:
            Exception: If all retries fail
        """
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except NetworkException as e:
                last_exception = e
                logger.warning(
                    f"Network error on attempt {attempt + 1}/{max_retries}: {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
            except TokenException as e:
                logger.error(f"Token expired or invalid: {e}")
                raise
            except Exception as e:
                last_exception = e
                logger.error(f"Error on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
        
        logger.error(f"All {max_retries} attempts failed")
        raise last_exception
    
    def place_order(
        self,
        symbol: str,
        exchange: str,
        transaction_type: str,
        quantity: int,
        order_type: str = "MARKET",
        product: str = "CNC",
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        validity: str = "DAY",
        disclosed_quantity: int = 0,
        tag: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Place an order on Zerodha.
        
        Args:
            symbol: Trading symbol (e.g., 'RELIANCE')
            exchange: Exchange ('NSE' or 'BSE')
            transaction_type: 'BUY' or 'SELL'
            quantity: Number of shares
            order_type: 'MARKET', 'LIMIT', 'SL', 'SL-M'
            product: 'CNC' (delivery), 'MIS' (intraday), 'NRML' (normal)
            price: Limit price (for LIMIT orders)
            trigger_price: Trigger price (for SL orders)
            validity: 'DAY' or 'IOC'
            disclosed_quantity: Disclosed quantity for iceberg orders
            tag: Custom tag for order tracking
            
        Returns:
            Order response with order_id
            
        Raises:
            OrderException: If order placement fails
        """
        try:
            order_params = {
                "tradingsymbol": symbol,
                "exchange": exchange,
                "transaction_type": transaction_type,
                "quantity": quantity,
                "order_type": order_type,
                "product": product,
                "validity": validity,
                "disclosed_quantity": disclosed_quantity
            }
            
            if price:
                order_params["price"] = price
            if trigger_price:
                order_params["trigger_price"] = trigger_price
            if tag:
                order_params["tag"] = tag
            
            # Place order with retry logic
            order_id = self._retry_on_failure(
                self.kite.place_order,
                variety=self.kite.VARIETY_REGULAR,
                **order_params
            )
            
            logger.info(
                f"Order placed: {transaction_type} {quantity} {symbol} @ "
                f"{order_type}, Order ID: {order_id}"
            )
            
            # Fetch order details
            order_details = self._retry_on_failure(
                self.kite.order_history,
                order_id=order_id
            )
            
            # Store in database
            self._store_order_in_db(order_details[-1] if order_details else {})
            
            # Stream to Redis
            self._stream_order_update(order_details[-1] if order_details else {})
            
            return {
                "order_id": order_id,
                "status": "success",
                "details": order_details[-1] if order_details else {}
            }
            
        except OrderException as e:
            logger.error(f"Order placement failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error placing order: {e}")
            raise
    
    def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        order_type: Optional[str] = None,
        validity: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Modify an existing order.
        
        Args:
            order_id: Order ID to modify
            quantity: New quantity
            price: New price
            trigger_price: New trigger price
            order_type: New order type
            validity: New validity
            
        Returns:
            Modified order details
        """
        try:
            modify_params = {}
            if quantity is not None:
                modify_params["quantity"] = quantity
            if price is not None:
                modify_params["price"] = price
            if trigger_price is not None:
                modify_params["trigger_price"] = trigger_price
            if order_type is not None:
                modify_params["order_type"] = order_type
            if validity is not None:
                modify_params["validity"] = validity
            
            result = self._retry_on_failure(
                self.kite.modify_order,
                variety=self.kite.VARIETY_REGULAR,
                order_id=order_id,
                **modify_params
            )
            
            logger.info(f"Order {order_id} modified successfully")
            
            # Fetch updated order details
            order_details = self._retry_on_failure(
                self.kite.order_history,
                order_id=order_id
            )
            
            # Update database
            self._store_order_in_db(order_details[-1] if order_details else {})
            
            # Stream update
            self._stream_order_update(order_details[-1] if order_details else {})
            
            return {
                "order_id": order_id,
                "status": "modified",
                "details": order_details[-1] if order_details else {}
            }
            
        except Exception as e:
            logger.error(f"Order modification failed: {e}")
            raise
    
    def cancel_order(
        self,
        order_id: str,
        variety: str = "regular"
    ) -> Dict[str, Any]:
        """
        Cancel an order.
        
        Args:
            order_id: Order ID to cancel
            variety: Order variety
            
        Returns:
            Cancellation confirmation
        """
        try:
            result = self._retry_on_failure(
                self.kite.cancel_order,
                variety=variety,
                order_id=order_id
            )
            
            logger.info(f"Order {order_id} cancelled successfully")
            
            # Fetch final order status
            order_details = self._retry_on_failure(
                self.kite.order_history,
                order_id=order_id
            )
            
            # Update database
            self._store_order_in_db(order_details[-1] if order_details else {})
            
            # Stream update
            self._stream_order_update(order_details[-1] if order_details else {})
            
            return {
                "order_id": order_id,
                "status": "cancelled",
                "details": order_details[-1] if order_details else {}
            }
            
        except Exception as e:
            logger.error(f"Order cancellation failed: {e}")
            raise
    
    def get_orders(self) -> List[Dict[str, Any]]:
        """
        Get all orders for the day.
        
        Returns:
            List of orders
        """
        try:
            orders = self._retry_on_failure(self.kite.orders)
            logger.info(f"Fetched {len(orders)} orders")
            return orders
        except Exception as e:
            logger.error(f"Failed to fetch orders: {e}")
            raise
    
    def get_positions(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get current positions.
        
        Returns:
            Dictionary with 'net' and 'day' positions
        """
        try:
            positions = self._retry_on_failure(self.kite.positions)
            logger.info(
                f"Fetched positions: {len(positions.get('net', []))} net, "
                f"{len(positions.get('day', []))} day"
            )
            
            # Store snapshot in database
            self._store_positions_snapshot(positions)
            
            return positions
        except Exception as e:
            logger.error(f"Failed to fetch positions: {e}")
            raise
    
    def get_holdings(self) -> List[Dict[str, Any]]:
        """
        Get holdings (long-term investments).
        
        Returns:
            List of holdings
        """
        try:
            holdings = self._retry_on_failure(self.kite.holdings)
            logger.info(f"Fetched {len(holdings)} holdings")
            return holdings
        except Exception as e:
            logger.error(f"Failed to fetch holdings: {e}")
            raise
    
    def get_margins(self) -> Dict[str, Any]:
        """
        Get account margins.
        
        Returns:
            Margin details for all segments
        """
        try:
            margins = self._retry_on_failure(self.kite.margins)
            logger.info("Fetched account margins")
            return margins
        except Exception as e:
            logger.error(f"Failed to fetch margins: {e}")
            raise
    
    def _store_order_in_db(self, order: Dict[str, Any]) -> None:
        """
        Store order in PostgreSQL.
        
        Args:
            order: Order details from Zerodha
        """
        try:
            with get_db_session() as session:
                session.execute("""
                    INSERT INTO zerodha_orders (
                        order_id, exchange_order_id, symbol, exchange,
                        transaction_type, order_type, product,
                        quantity, price, trigger_price, disclosed_quantity,
                        filled_quantity, pending_quantity, cancelled_quantity,
                        average_price, status, status_message,
                        order_timestamp, exchange_timestamp
                    ) VALUES (
                        %(order_id)s, %(exchange_order_id)s, %(tradingsymbol)s, %(exchange)s,
                        %(transaction_type)s, %(order_type)s, %(product)s,
                        %(quantity)s, %(price)s, %(trigger_price)s, %(disclosed_quantity)s,
                        %(filled_quantity)s, %(pending_quantity)s, %(cancelled_quantity)s,
                        %(average_price)s, %(status)s, %(status_message)s,
                        %(order_timestamp)s, %(exchange_timestamp)s
                    )
                    ON CONFLICT (order_id)
                    DO UPDATE SET
                        filled_quantity = EXCLUDED.filled_quantity,
                        pending_quantity = EXCLUDED.pending_quantity,
                        cancelled_quantity = EXCLUDED.cancelled_quantity,
                        average_price = EXCLUDED.average_price,
                        status = EXCLUDED.status,
                        status_message = EXCLUDED.status_message,
                        updated_at = NOW()
                """, order)
                session.commit()
                
            logger.debug(f"Order {order.get('order_id')} stored in database")
            
        except Exception as e:
            logger.error(f"Failed to store order in database: {e}")
    
    def _stream_order_update(self, order: Dict[str, Any]) -> None:
        """
        Stream order update to Redis.
        
        Args:
            order: Order details
        """
        try:
            message = {
                "order_id": order.get("order_id"),
                "symbol": order.get("tradingsymbol"),
                "status": order.get("status"),
                "filled_quantity": order.get("filled_quantity"),
                "average_price": order.get("average_price"),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self.redis_client.publish(
                "orders.updates",
                json.dumps(message)
            )
            
            logger.debug(f"Order update streamed to Redis: {order.get('order_id')}")
            
        except Exception as e:
            logger.error(f"Failed to stream order update: {e}")
    
    def _store_positions_snapshot(self, positions: Dict[str, List[Dict]]) -> None:
        """
        Store positions snapshot in database.
        
        Args:
            positions: Positions data from Zerodha
        """
        try:
            with get_db_session() as session:
                for position in positions.get("net", []):
                    session.execute("""
                        INSERT INTO zerodha_positions_snapshot (
                            symbol, exchange, product,
                            quantity, overnight_quantity,
                            average_price, last_price, close_price,
                            pnl, day_pnl
                        ) VALUES (
                            %(tradingsymbol)s, %(exchange)s, %(product)s,
                            %(quantity)s, %(overnight_quantity)s,
                            %(average_price)s, %(last_price)s, %(close_price)s,
                            %(pnl)s, %(day_pnl)s
                        )
                    """, position)
                session.commit()
                
            logger.debug("Positions snapshot stored in database")
            
        except Exception as e:
            logger.error(f"Failed to store positions snapshot: {e}")
