"""Specialized repositories for each database table."""

import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from src.database.models import (
    Article, BacktestResult, Event, Order, Price, SentimentScore, TradingSignal
)
from src.database.repository import BaseRepository

logger = logging.getLogger(__name__)


class PriceRepository(BaseRepository[Price]):
    """Repository for price data."""
    
    def __init__(self, session: Session):
        super().__init__(Price, session)
    
    def get_by_symbol_and_timerange(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Price]:
        """Get price data for a symbol within a time range.
        
        Args:
            symbol: Stock symbol
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            List of price records ordered by timestamp
        """
        try:
            return self.session.query(Price).filter(
                and_(
                    Price.symbol == symbol,
                    Price.timestamp >= start_time,
                    Price.timestamp <= end_time
                )
            ).order_by(Price.timestamp).all()
        except Exception as e:
            logger.error(f"Error getting prices for {symbol}: {e}")
            raise
    
    def get_latest_by_symbol(self, symbol: str, limit: int = 100) -> List[Price]:
        """Get the most recent price data for a symbol.
        
        Args:
            symbol: Stock symbol
            limit: Number of records to return
            
        Returns:
            List of price records ordered by timestamp descending
        """
        try:
            return self.session.query(Price).filter(
                Price.symbol == symbol
            ).order_by(desc(Price.timestamp)).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting latest prices for {symbol}: {e}")
            raise


class ArticleRepository(BaseRepository[Article]):
    """Repository for news articles."""
    
    def __init__(self, session: Session):
        super().__init__(Article, session)
    
    def get_by_timerange(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Article]:
        """Get articles within a time range.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            List of articles ordered by published_at
        """
        try:
            return self.session.query(Article).filter(
                and_(
                    Article.published_at >= start_time,
                    Article.published_at <= end_time
                )
            ).order_by(Article.published_at).all()
        except Exception as e:
            logger.error(f"Error getting articles by timerange: {e}")
            raise
    
    def get_by_symbol(self, symbol: str, limit: Optional[int] = None) -> List[Article]:
        """Get articles mentioning a specific symbol.
        
        Args:
            symbol: Stock symbol
            limit: Maximum number of articles to return
            
        Returns:
            List of articles ordered by published_at descending
        """
        try:
            query = self.session.query(Article).filter(
                Article.symbols.contains([symbol])
            ).order_by(desc(Article.published_at))
            
            if limit is not None:
                query = query.limit(limit)
            
            return query.all()
        except Exception as e:
            logger.error(f"Error getting articles for symbol {symbol}: {e}")
            raise


class SentimentScoreRepository(BaseRepository[SentimentScore]):
    """Repository for sentiment scores."""
    
    def __init__(self, session: Session):
        super().__init__(SentimentScore, session)
    
    def get_by_article_id(self, article_id: str) -> Optional[SentimentScore]:
        """Get sentiment score for an article.
        
        Args:
            article_id: Article ID
            
        Returns:
            Sentiment score or None if not found
        """
        try:
            return self.session.query(SentimentScore).filter(
                SentimentScore.article_id == article_id
            ).first()
        except Exception as e:
            logger.error(f"Error getting sentiment for article {article_id}: {e}")
            raise
    
    def get_by_timerange(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[SentimentScore]:
        """Get sentiment scores within a time range.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            List of sentiment scores ordered by timestamp
        """
        try:
            return self.session.query(SentimentScore).filter(
                and_(
                    SentimentScore.timestamp >= start_time,
                    SentimentScore.timestamp <= end_time
                )
            ).order_by(SentimentScore.timestamp).all()
        except Exception as e:
            logger.error(f"Error getting sentiment scores by timerange: {e}")
            raise


class EventRepository(BaseRepository[Event]):
    """Repository for market events."""
    
    def __init__(self, session: Session):
        super().__init__(Event, session)
    
    def get_by_timerange(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Event]:
        """Get events within a time range.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            List of events ordered by timestamp
        """
        try:
            return self.session.query(Event).filter(
                and_(
                    Event.timestamp >= start_time,
                    Event.timestamp <= end_time
                )
            ).order_by(Event.timestamp).all()
        except Exception as e:
            logger.error(f"Error getting events by timerange: {e}")
            raise
    
    def get_high_severity_events(
        self,
        severity_threshold: float = 0.7,
        limit: Optional[int] = None
    ) -> List[Event]:
        """Get high-severity events.
        
        Args:
            severity_threshold: Minimum severity score
            limit: Maximum number of events to return
            
        Returns:
            List of events ordered by severity descending
        """
        try:
            query = self.session.query(Event).filter(
                Event.severity >= severity_threshold
            ).order_by(desc(Event.severity))
            
            if limit is not None:
                query = query.limit(limit)
            
            return query.all()
        except Exception as e:
            logger.error(f"Error getting high severity events: {e}")
            raise
    
    def get_by_event_type(
        self,
        event_type: str,
        limit: Optional[int] = None
    ) -> List[Event]:
        """Get events by type.
        
        Args:
            event_type: Event type to filter by
            limit: Maximum number of events to return
            
        Returns:
            List of events ordered by timestamp descending
        """
        try:
            query = self.session.query(Event).filter(
                Event.event_type == event_type
            ).order_by(desc(Event.timestamp))
            
            if limit is not None:
                query = query.limit(limit)
            
            return query.all()
        except Exception as e:
            logger.error(f"Error getting events by type {event_type}: {e}")
            raise


class TradingSignalRepository(BaseRepository[TradingSignal]):
    """Repository for trading signals."""
    
    def __init__(self, session: Session):
        super().__init__(TradingSignal, session)
    
    def get_by_timerange(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[TradingSignal]:
        """Get trading signals within a time range.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            List of signals ordered by timestamp
        """
        try:
            return self.session.query(TradingSignal).filter(
                and_(
                    TradingSignal.timestamp >= start_time,
                    TradingSignal.timestamp <= end_time
                )
            ).order_by(TradingSignal.timestamp).all()
        except Exception as e:
            logger.error(f"Error getting signals by timerange: {e}")
            raise
    
    def get_latest(self, limit: int = 10) -> List[TradingSignal]:
        """Get the most recent trading signals.
        
        Args:
            limit: Number of signals to return
            
        Returns:
            List of signals ordered by timestamp descending
        """
        try:
            return self.session.query(TradingSignal).order_by(
                desc(TradingSignal.timestamp)
            ).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting latest signals: {e}")
            raise
    
    def get_by_signal_type(
        self,
        signal_type: str,
        limit: Optional[int] = None
    ) -> List[TradingSignal]:
        """Get signals by type.
        
        Args:
            signal_type: Signal type (BUY, SELL, HOLD)
            limit: Maximum number of signals to return
            
        Returns:
            List of signals ordered by timestamp descending
        """
        try:
            query = self.session.query(TradingSignal).filter(
                TradingSignal.signal_type == signal_type
            ).order_by(desc(TradingSignal.timestamp))
            
            if limit is not None:
                query = query.limit(limit)
            
            return query.all()
        except Exception as e:
            logger.error(f"Error getting signals by type {signal_type}: {e}")
            raise


class OrderRepository(BaseRepository[Order]):
    """Repository for orders."""
    
    def __init__(self, session: Session):
        super().__init__(Order, session)
    
    def get_by_order_id(self, order_id: str) -> Optional[Order]:
        """Get an order by its order ID.
        
        Args:
            order_id: Order ID from broker
            
        Returns:
            Order or None if not found
        """
        try:
            return self.session.query(Order).filter(
                Order.order_id == order_id
            ).first()
        except Exception as e:
            logger.error(f"Error getting order {order_id}: {e}")
            raise
    
    def get_by_status(self, status: str, limit: Optional[int] = None) -> List[Order]:
        """Get orders by status.
        
        Args:
            status: Order status
            limit: Maximum number of orders to return
            
        Returns:
            List of orders ordered by timestamp descending
        """
        try:
            query = self.session.query(Order).filter(
                Order.status == status
            ).order_by(desc(Order.timestamp))
            
            if limit is not None:
                query = query.limit(limit)
            
            return query.all()
        except Exception as e:
            logger.error(f"Error getting orders by status {status}: {e}")
            raise
    
    def get_by_signal_id(self, signal_id: int) -> List[Order]:
        """Get orders associated with a signal.
        
        Args:
            signal_id: Trading signal ID
            
        Returns:
            List of orders
        """
        try:
            return self.session.query(Order).filter(
                Order.signal_id == signal_id
            ).all()
        except Exception as e:
            logger.error(f"Error getting orders for signal {signal_id}: {e}")
            raise
    
    def update_status(self, order_id: str, status: str) -> Optional[Order]:
        """Update order status.
        
        Args:
            order_id: Order ID from broker
            status: New status
            
        Returns:
            Updated order or None if not found
        """
        try:
            order = self.get_by_order_id(order_id)
            if order is None:
                logger.warning(f"Order {order_id} not found")
                return None
            
            order.status = status
            self.session.flush()
            logger.debug(f"Updated order {order_id} status to {status}")
            return order
        except Exception as e:
            logger.error(f"Error updating order status: {e}")
            raise


class BacktestResultRepository(BaseRepository[BacktestResult]):
    """Repository for backtest results."""
    
    def __init__(self, session: Session):
        super().__init__(BacktestResult, session)
    
    def get_latest(self, limit: int = 10) -> List[BacktestResult]:
        """Get the most recent backtest results.
        
        Args:
            limit: Number of results to return
            
        Returns:
            List of backtest results ordered by created_at descending
        """
        try:
            return self.session.query(BacktestResult).order_by(
                desc(BacktestResult.created_at)
            ).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting latest backtest results: {e}")
            raise
