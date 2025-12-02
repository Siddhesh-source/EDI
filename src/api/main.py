"""FastAPI backend for the explainable algorithmic trading system."""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from src.shared.config import settings
from src.shared.redis_client import get_redis_client, close_redis_client
from src.shared.models import (
    BacktestConfig, BacktestResult, TradingSignal, Order, OrderStatus
)
from src.database.connection import initialize_database, close_database, get_db_session
from src.database.repositories import (
    TradingSignalRepository, OrderRepository, BacktestResultRepository
)
from src.backtest.engine import BacktestingModule
from src.signal.aggregator import SignalAggregator
from src.api.middleware import LoggingMiddleware, ErrorHandlingMiddleware, RateLimitMiddleware

logger = logging.getLogger(__name__)

# API Key authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """Verify API key authentication.
    
    Args:
        api_key: API key from request header
        
    Returns:
        API key if valid
        
    Raises:
        HTTPException: If API key is invalid or missing
    """
    if api_key is None:
        raise HTTPException(status_code=401, detail="API key is missing")
    
    if api_key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    return api_key


# Global instances
signal_aggregator: Optional[SignalAggregator] = None
backtest_module: Optional[BacktestingModule] = None
websocket_connections: List[WebSocket] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
    global signal_aggregator, backtest_module
    
    # Startup
    logger.info("Starting FastAPI backend...")
    
    # Initialize database
    initialize_database()
    logger.info("Database connection initialized")
    
    # Initialize Redis
    redis_client = get_redis_client()
    if not redis_client.ping():
        logger.warning("Redis connection failed, attempting reconnection...")
        redis_client.reconnect()
    logger.info("Redis connection initialized")
    
    # Initialize signal aggregator
    signal_aggregator = SignalAggregator(redis_client)
    signal_aggregator.start()
    logger.info("Signal aggregator initialized")
    
    # Initialize backtesting module
    from src.database.connection import db_connection
    backtest_module = BacktestingModule(db_connection)
    logger.info("Backtesting module initialized")
    
    # Start signal aggregator listening in background
    asyncio.create_task(signal_aggregator.listen())
    
    logger.info("FastAPI backend started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down FastAPI backend...")
    
    # Stop signal aggregator
    if signal_aggregator:
        signal_aggregator.stop()
    
    # Close connections
    close_redis_client()
    close_database()
    
    logger.info("FastAPI backend shut down successfully")


# Create FastAPI application
app = FastAPI(
    title="Explainable Algorithmic Trading System API",
    description="REST API for the explainable algorithmic trading platform",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware (order matters - first added is outermost)
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(LoggingMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    services: Dict[str, bool]


class SignalResponse(BaseModel):
    """Trading signal response."""
    signal_type: str
    cms_score: float
    sentiment_component: float
    technical_component: float
    regime_component: float
    confidence: float
    explanation: Dict[str, Any]
    timestamp: datetime


class BacktestRequest(BaseModel):
    """Backtest request."""
    symbol: str = Field(..., description="Stock symbol")
    start_date: datetime = Field(..., description="Start date for backtest")
    end_date: datetime = Field(..., description="End date for backtest")
    initial_capital: float = Field(100000.0, description="Initial capital")
    position_size: float = Field(0.1, description="Position size as fraction of capital")
    cms_buy_threshold: float = Field(60.0, description="CMS threshold for BUY signal")
    cms_sell_threshold: float = Field(-60.0, description="CMS threshold for SELL signal")


class BacktestResponse(BaseModel):
    """Backtest response."""
    backtest_id: str
    status: str
    message: str


class OrderResponse(BaseModel):
    """Order response."""
    order_id: str
    symbol: str
    order_type: str
    side: str
    quantity: float
    price: Optional[float]
    status: str
    timestamp: datetime


# Endpoints

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint.
    
    Returns:
        Health status of the system and its services
    """
    # Check database
    from src.database.connection import db_connection
    db_healthy = db_connection.health_check()
    
    # Check Redis
    redis_client = get_redis_client()
    redis_healthy = redis_client.ping()
    
    # Check signal aggregator
    aggregator_healthy = signal_aggregator is not None
    
    # Overall status
    all_healthy = db_healthy and redis_healthy and aggregator_healthy
    status = "healthy" if all_healthy else "degraded"
    
    return HealthResponse(
        status=status,
        timestamp=datetime.now(),
        services={
            "database": db_healthy,
            "redis": redis_healthy,
            "signal_aggregator": aggregator_healthy
        }
    )


@app.get("/api/v1/signal/current", response_model=Optional[SignalResponse])
async def get_current_signal(api_key: str = Depends(verify_api_key)):
    """Get the current trading signal.
    
    Returns:
        Current trading signal with CMS and explanation
    """
    if signal_aggregator is None:
        raise HTTPException(status_code=503, detail="Signal aggregator not initialized")
    
    # Get aggregated data
    aggregated_data = signal_aggregator.aggregate_data()
    
    if aggregated_data is None:
        return None
    
    # Generate signal
    signal = signal_aggregator.generate_signal(aggregated_data)
    
    return SignalResponse(
        signal_type=signal.signal_type.value,
        cms_score=signal.cms.score,
        sentiment_component=signal.cms.sentiment_component,
        technical_component=signal.cms.technical_component,
        regime_component=signal.cms.regime_component,
        confidence=signal.confidence,
        explanation={
            "summary": signal.explanation.summary,
            "sentiment_details": signal.explanation.sentiment_details,
            "technical_details": signal.explanation.technical_details,
            "regime_details": signal.explanation.regime_details,
            "event_details": signal.explanation.event_details,
            "component_scores": signal.explanation.component_scores
        },
        timestamp=signal.timestamp
    )


@app.get("/api/v1/signal/history", response_model=List[SignalResponse])
async def get_signal_history(
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = 100,
    api_key: str = Depends(verify_api_key)
):
    """Get historical trading signals.
    
    Args:
        start: Start datetime for filtering (optional)
        end: End datetime for filtering (optional)
        limit: Maximum number of signals to return
        
    Returns:
        List of historical trading signals
    """
    with next(get_db_session()) as session:
        repo = TradingSignalRepository(session)
        
        if start and end:
            signals = repo.get_by_timerange(start, end)
        else:
            signals = repo.get_latest(limit)
        
        return [
            SignalResponse(
                signal_type=signal.signal_type,
                cms_score=float(signal.cms_score),
                sentiment_component=float(signal.sentiment_component),
                technical_component=float(signal.technical_component),
                regime_component=float(signal.regime_component),
                confidence=signal.explanation.get('confidence', 0.0),
                explanation=signal.explanation,
                timestamp=signal.timestamp
            )
            for signal in signals
        ]


@app.post("/api/v1/backtest", response_model=BacktestResponse)
async def run_backtest(
    request: BacktestRequest,
    api_key: str = Depends(verify_api_key)
):
    """Run a backtest with the given configuration.
    
    Args:
        request: Backtest configuration
        
    Returns:
        Backtest ID and status
    """
    if backtest_module is None:
        raise HTTPException(status_code=503, detail="Backtesting module not initialized")
    
    try:
        # Create backtest config
        config = BacktestConfig(
            symbol=request.symbol,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            position_size=request.position_size,
            cms_buy_threshold=request.cms_buy_threshold,
            cms_sell_threshold=request.cms_sell_threshold
        )
        
        # Run backtest in background
        # Note: In production, this should be run in a task queue (Celery, etc.)
        result = backtest_module.run_backtest(config)
        
        return BacktestResponse(
            backtest_id=result.backtest_id,
            status="completed",
            message=f"Backtest completed with {result.metrics.total_trades} trades"
        )
        
    except Exception as e:
        logger.error(f"Backtest failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Backtest failed: {str(e)}"
        )


@app.get("/api/v1/backtest/{backtest_id}")
async def get_backtest_result(
    backtest_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get backtest results by ID.
    
    Args:
        backtest_id: Backtest ID
        
    Returns:
        Backtest results including trades, metrics, and equity curve
    """
    with next(get_db_session()) as session:
        repo = BacktestResultRepository(session)
        result = repo.get_by_id(backtest_id)
        
        if result is None:
            raise HTTPException(status_code=404, detail="Backtest not found")
        
        return {
            "backtest_id": result.id,
            "config": result.config,
            "metrics": result.metrics,
            "trades": result.trades,
            "equity_curve": result.equity_curve,
            "created_at": result.created_at
        }


@app.get("/api/v1/orders", response_model=List[OrderResponse])
async def get_orders(
    status: Optional[str] = None,
    limit: int = 100,
    api_key: str = Depends(verify_api_key)
):
    """Get orders, optionally filtered by status.
    
    Args:
        status: Order status to filter by (optional)
        limit: Maximum number of orders to return
        
    Returns:
        List of orders
    """
    with next(get_db_session()) as session:
        repo = OrderRepository(session)
        
        if status:
            orders = repo.get_by_status(status, limit)
        else:
            # Get all recent orders
            orders = session.query(repo.model).order_by(
                repo.model.timestamp.desc()
            ).limit(limit).all()
        
        return [
            OrderResponse(
                order_id=order.order_id,
                symbol=order.symbol,
                order_type=order.order_type,
                side=order.side,
                quantity=float(order.quantity),
                price=float(order.price) if order.price else None,
                status=order.status,
                timestamp=order.timestamp
            )
            for order in orders
        ]


@app.websocket("/ws/signals")
async def websocket_signals(websocket: WebSocket):
    """WebSocket endpoint for real-time signal updates.
    
    Clients connect to this endpoint to receive real-time trading signals.
    """
    await websocket.accept()
    websocket_connections.append(websocket)
    logger.info(f"WebSocket client connected. Total connections: {len(websocket_connections)}")
    
    try:
        # Send initial signal if available
        if signal_aggregator:
            aggregated_data = signal_aggregator.aggregate_data()
            if aggregated_data:
                signal = signal_aggregator.generate_signal(aggregated_data)
                await websocket.send_json({
                    "type": "signal",
                    "data": {
                        "signal_type": signal.signal_type.value,
                        "cms_score": signal.cms.score,
                        "sentiment_component": signal.cms.sentiment_component,
                        "technical_component": signal.cms.technical_component,
                        "regime_component": signal.cms.regime_component,
                        "confidence": signal.confidence,
                        "explanation": {
                            "summary": signal.explanation.summary,
                            "sentiment_details": signal.explanation.sentiment_details,
                            "technical_details": signal.explanation.technical_details,
                            "regime_details": signal.explanation.regime_details,
                            "event_details": signal.explanation.event_details,
                            "component_scores": signal.explanation.component_scores
                        },
                        "timestamp": signal.timestamp.isoformat()
                    }
                })
        
        # Keep connection alive and listen for client messages
        while True:
            # Wait for messages from client (ping/pong, etc.)
            data = await websocket.receive_text()
            
            # Echo back for now (can be used for commands later)
            if data == "ping":
                await websocket.send_text("pong")
                
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)
        logger.info(f"WebSocket connection closed. Total connections: {len(websocket_connections)}")


async def broadcast_signal(signal: TradingSignal):
    """Broadcast a trading signal to all connected WebSocket clients.
    
    Args:
        signal: Trading signal to broadcast
    """
    if not websocket_connections:
        return
    
    message = {
        "type": "signal",
        "data": {
            "signal_type": signal.signal_type.value,
            "cms_score": signal.cms.score,
            "sentiment_component": signal.cms.sentiment_component,
            "technical_component": signal.cms.technical_component,
            "regime_component": signal.cms.regime_component,
            "confidence": signal.confidence,
            "explanation": {
                "summary": signal.explanation.summary,
                "sentiment_details": signal.explanation.sentiment_details,
                "technical_details": signal.explanation.technical_details,
                "regime_details": signal.explanation.regime_details,
                "event_details": signal.explanation.event_details,
                "component_scores": signal.explanation.component_scores
            },
            "timestamp": signal.timestamp.isoformat()
        }
    }
    
    # Send to all connected clients
    disconnected = []
    for websocket in websocket_connections:
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send to WebSocket client: {e}")
            disconnected.append(websocket)
    
    # Remove disconnected clients
    for websocket in disconnected:
        websocket_connections.remove(websocket)


if __name__ == "__main__":
    import uvicorn
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run server
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        log_level=settings.log_level.lower()
    )
