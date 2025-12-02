"""SQLAlchemy ORM models for database tables."""

from datetime import datetime
from typing import List

from sqlalchemy import (
    ARRAY, DECIMAL, TIMESTAMP, BigInteger, Column, ForeignKey, Index, Integer,
    String, Text, text
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Price(Base):
    """Price data table."""
    __tablename__ = "prices"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    open = Column(DECIMAL(10, 2))
    high = Column(DECIMAL(10, 2))
    low = Column(DECIMAL(10, 2))
    close = Column(DECIMAL(10, 2))
    volume = Column(BigInteger)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    
    __table_args__ = (
        Index("idx_prices_symbol_timestamp", "symbol", "timestamp"),
    )


class Article(Base):
    """News articles table."""
    __tablename__ = "articles"
    
    id = Column(String(100), primary_key=True)
    title = Column(Text, nullable=False)
    content = Column(Text)
    source = Column(String(100))
    published_at = Column(TIMESTAMP(timezone=True), nullable=False)
    symbols = Column(ARRAY(Text))
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    
    # Relationships
    sentiment_scores = relationship("SentimentScore", back_populates="article")
    events = relationship("Event", back_populates="article")
    
    __table_args__ = (
        Index("idx_articles_published_at", "published_at"),
    )


class SentimentScore(Base):
    """Sentiment analysis scores table."""
    __tablename__ = "sentiment_scores"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(String(100), ForeignKey("articles.id"))
    score = Column(DECIMAL(3, 2), nullable=False)
    confidence = Column(DECIMAL(3, 2))
    keywords_positive = Column(ARRAY(Text))
    keywords_negative = Column(ARRAY(Text))
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    
    # Relationships
    article = relationship("Article", back_populates="sentiment_scores")
    
    __table_args__ = (
        Index("idx_sentiment_timestamp", "timestamp"),
    )


class Event(Base):
    """Market events table."""
    __tablename__ = "events"
    
    id = Column(String(100), primary_key=True)
    article_id = Column(String(100), ForeignKey("articles.id"))
    event_type = Column(String(50), nullable=False)
    severity = Column(DECIMAL(3, 2))
    keywords = Column(ARRAY(Text))
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    
    # Relationships
    article = relationship("Article", back_populates="events")
    
    __table_args__ = (
        Index("idx_events_timestamp", "timestamp"),
        Index("idx_events_severity", "severity"),
    )


class TradingSignal(Base):
    """Trading signals table."""
    __tablename__ = "trading_signals"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_type = Column(String(10), nullable=False)
    cms_score = Column(DECIMAL(5, 2), nullable=False)
    sentiment_component = Column(DECIMAL(5, 2))
    technical_component = Column(DECIMAL(5, 2))
    regime_component = Column(DECIMAL(5, 2))
    explanation = Column(JSONB)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    
    # Relationships
    orders = relationship("Order", back_populates="signal")
    
    __table_args__ = (
        Index("idx_signals_timestamp", "timestamp"),
        Index("idx_signals_type", "signal_type"),
    )


class Order(Base):
    """Orders table."""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(100), unique=True, nullable=False)
    symbol = Column(String(20), nullable=False)
    order_type = Column(String(20))
    side = Column(String(10))
    quantity = Column(DECIMAL(10, 2))
    price = Column(DECIMAL(10, 2))
    status = Column(String(20))
    signal_id = Column(Integer, ForeignKey("trading_signals.id"))
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    
    # Relationships
    signal = relationship("TradingSignal", back_populates="orders")
    
    __table_args__ = (
        Index("idx_orders_status", "status"),
        Index("idx_orders_timestamp", "timestamp"),
    )


class BacktestResult(Base):
    """Backtest results table."""
    __tablename__ = "backtest_results"
    
    id = Column(String(100), primary_key=True)
    config = Column(JSONB, nullable=False)
    metrics = Column(JSONB, nullable=False)
    trades = Column(JSONB, nullable=False)
    equity_curve = Column(JSONB, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    
    __table_args__ = (
        Index("idx_backtest_created_at", "created_at"),
    )
