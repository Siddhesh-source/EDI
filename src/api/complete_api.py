"""
Complete FastAPI Backend for Algorithmic Trading System
Includes all endpoints for news, sentiment, CMS, signals, backtesting, and trading.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import json

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import asyncio

from src.nlp.engine import EnhancedNLPEngine
from src.regime.enhanced_detector import EnhancedMarketRegimeDetector
from src.signal.cms_engine import CMSEngine, CMSComponents
from src.trading.rule_engine import RuleBasedTradingEngine, MarketData, RiskParameters
from src.backtest.engine import BacktestingModule
from src.broker.zerodha_client import ZerodhaClient
from src.shared.redis_client import get_redis_client
from src.database.connection import get_db_session
from src.api.middleware import setup_middleware

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Algorithmic Trading API",
    description="Complete backend for rule-based algorithmic trading system",
    version="1.0.0"
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup custom middleware
setup_middleware(app)

# Initialize components
nlp_engine = EnhancedNLPEngine()
regime_detector = EnhancedMarketRegimeDetector()
cms_engine = CMSEngine()
redis_client = get_redis_client()

# Zerodha client (initialized on demand)
zerodha_client: Optional[ZerodhaClient] = None


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class NewsArticle(BaseModel):
    source: str
    title: str
    content: str
    url: Optional[str] = None
    author: Optional[str] = None
    published_at: datetime
    symbols: List[str] = []


class SentimentRequest(BaseModel):
    articles: List[NewsArticle]


class CMSRequest(BaseModel):
    symbol: str
    sentiment_index: float = Field(..., ge=-1, le=1)
    volatility_index: float = Field(..., ge=0, le=1)
    trend_strength: float = Field(..., ge=-1, le=1)
    event_shock_factor: float = Field(..., ge=0, le=1)


class BacktestRequest(BaseModel):
    symbol: str
    start_date: datetime
    end_date: datetime
    initial_capital: float = 100000
    position_size_pct: float = 0.1
    strategy_params: Optional[Dict[str, Any]] = None


class OrderRequest(BaseModel):
    symbol: str
    exchange: str = "NSE"
    transaction_type: str  # 'BUY' or 'SELL'
    quantity: int
    order_type: str = "MARKET"  # 'MARKET', 'LIMIT', 'SL', 'SL-M'
    product: str = "CNC"  # 'CNC', 'MIS', 'NRML'
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    tag: Optional[str] = None


class ZerodhaAuthRequest(BaseModel):
    api_key: str
    api_secret: str
    request_token: Optional[str] = None


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

def get_zerodha_client() -> ZerodhaClient:
    """Get Zerodha client instance."""
    global zerodha_client
    if zerodha_client is None:
        raise HTTPException(
            status_code=401,
            detail="Zerodha client not initialized. Please authenticate first."
        )
    return zerodha_client


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "nlp_engine": "active",
            "cms_engine": "active",
            "regime_detector": "active",
            "redis": "connected" if redis_client.ping() else "disconnected",
            "zerodha": "authenticated" if zerodha_client else "not_authenticated"
        }
    }


# ============================================================================
# NEWS & SENTIMENT ENDPOINTS
# ============================================================================

@app.post("/news/sentiment")
async def analyze_sentiment(request: SentimentRequest):
    """
    Analyze sentiment for news articles.
    
    Returns sentiment scores, detected events, and aggregated metrics.
    """
    try:
        # Convert to internal format
        articles = [
            {
                "source": article.source,
                "title": article.title,
                "content": article.content,
                "url": article.url,
                "published_at": article.published_at,
                "symbols": article.symbols
            }
            for article in request.articles
        ]
        
        # Process with NLP engine
        result = nlp_engine.process_articles(articles)
        
        # Store in database
        with get_db_session() as session:
            for article, sentiment in zip(articles, result.article_sentiments):
                # Store article
                session.execute("""
                    INSERT INTO news_raw (
                        source, title, content, url, published_at, symbols
                    ) VALUES (
                        %(source)s, %(title)s, %(content)s, %(url)s, %(published_at)s, %(symbols)s
                    )
                    RETURNING id
                """, article)
                article_id = session.fetchone()[0]
                
                # Store sentiment
                session.execute("""
                    INSERT INTO sentiment_scores (
                        article_id, score, confidence, method
                    ) VALUES (
                        %s, %s, %s, 'enhanced_nlp'
                    )
                """, (article_id, sentiment.score, sentiment.confidence))
            
            session.commit()
        
        # Stream to Redis
        redis_client.publish(
            "news.sentiment.live",
            json.dumps({
                "sentiment_index": result.sentiment_index.smoothed_score,
                "confidence": result.sentiment_index.confidence,
                "article_count": len(articles),
                "timestamp": datetime.utcnow().isoformat()
            })
        )
        
        return {
            "sentiment_index": result.sentiment_index.smoothed_score,
            "confidence": result.sentiment_index.confidence,
            "article_sentiments": [
                {
                    "score": s.score,
                    "confidence": s.confidence,
                    "positive": s.positive_score,
                    "negative": s.negative_score,
                    "neutral": s.neutral_score
                }
                for s in result.article_sentiments
            ],
            "detected_events": [
                {
                    "type": e.event_type,
                    "severity": e.severity,
                    "keywords": e.keywords
                }
                for e in result.detected_events
            ],
            "event_shock_factor": result.event_shock_factor.total_shock
        }
        
    except Exception as e:
        logger.error(f"Sentiment analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sentiment/live")
async def stream_sentiment():
    """
    Stream live sentiment updates via Server-Sent Events.
    """
    async def event_generator():
        pubsub = redis_client.pubsub()
        pubsub.subscribe(['news.sentiment.live'])
        
        try:
            for message in pubsub.listen():
                if message['type'] == 'message':
                    yield f"data: {message['data']}\n\n"
                await asyncio.sleep(0.1)
        finally:
            pubsub.unsubscribe()
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


# ============================================================================
# CMS ENDPOINTS
# ============================================================================

@app.post("/cms/calculate")
async def calculate_cms(request: CMSRequest):
    """
    Calculate Composite Market Score.
    """
    try:
        components = CMSComponents(
            sentiment_index=request.sentiment_index,
            volatility_index=request.volatility_index,
            trend_strength=request.trend_strength,
            event_shock_factor=request.event_shock_factor
        )
        
        result = cms_engine.compute_cms(components)
        
        # Store in database
        with get_db_session() as session:
            session.execute("""
                INSERT INTO cms_values (
                    symbol, cms_score, sentiment_index, volatility_index,
                    trend_strength, event_shock_factor, signal_type,
                    confidence, explanation
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                request.symbol, result.cms_score,
                components.sentiment_index, components.volatility_index,
                components.trend_strength, components.event_shock_factor,
                result.signal_type, result.confidence, result.explanation
            ))
            session.commit()
        
        # Stream to Redis
        redis_client.publish(
            "cms.live",
            json.dumps({
                "symbol": request.symbol,
                "cms_score": result.cms_score,
                "signal_type": result.signal_type,
                "confidence": result.confidence,
                "timestamp": datetime.utcnow().isoformat()
            })
        )
        
        return result.to_dict()
        
    except Exception as e:
        logger.error(f"CMS calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cms/live")
async def stream_cms():
    """
    Stream live CMS updates via Server-Sent Events.
    """
    async def event_generator():
        pubsub = redis_client.pubsub()
        pubsub.subscribe(['cms.live'])
        
        try:
            for message in pubsub.listen():
                if message['type'] == 'message':
                    yield f"data: {message['data']}\n\n"
                await asyncio.sleep(0.1)
        finally:
            pubsub.unsubscribe()
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


@app.get("/cms/history/{symbol}")
async def get_cms_history(
    symbol: str,
    days: int = Query(7, ge=1, le=90)
):
    """
    Get historical CMS values for a symbol.
    """
    try:
        with get_db_session() as session:
            result = session.execute("""
                SELECT
                    cms_score, signal_type, confidence,
                    sentiment_index, volatility_index,
                    trend_strength, event_shock_factor,
                    timestamp
                FROM cms_values
                WHERE symbol = %s
                  AND timestamp > NOW() - INTERVAL '%s days'
                ORDER BY timestamp DESC
            """, (symbol, days))
            
            history = [
                {
                    "cms_score": row[0],
                    "signal_type": row[1],
                    "confidence": row[2],
                    "sentiment_index": row[3],
                    "volatility_index": row[4],
                    "trend_strength": row[5],
                    "event_shock_factor": row[6],
                    "timestamp": row[7].isoformat()
                }
                for row in result.fetchall()
            ]
        
        return {"symbol": symbol, "history": history}
        
    except Exception as e:
        logger.error(f"Failed to fetch CMS history: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# ============================================================================
# REGIME & SI
GNALS ENDPOINTS
# ============================================================================

@app.get("/regime/live")
async def stream_regime():
    """
    Stream live market regime updates via Server-Sent Events.
    """
    async def event_generator():
        pubsub = redis_client.pubsub()
        pubsub.subscribe(['regime.live'])
        
        try:
            for message in pubsub.listen():
                if message['type'] == 'message':
                    yield f"data: {message['data']}\n\n"
                await asyncio.sleep(0.1)
        finally:
            pubsub.unsubscribe()
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


@app.get("/signals/live")
async def stream_signals():
    """
    Stream live trading signals via Server-Sent Events.
    """
    async def event_generator():
        pubsub = redis_client.pubsub()
        pubsub.subscribe(['signals.live'])
        
        try:
            for message in pubsub.listen():
                if message['type'] == 'message':
                    yield f"data: {message['data']}\n\n"
                await asyncio.sleep(0.1)
        finally:
            pubsub.unsubscribe()
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


@app.get("/signals/history/{symbol}")
async def get_signal_history(
    symbol: str,
    days: int = Query(7, ge=1, le=90)
):
    """
    Get historical trading signals for a symbol.
    """
    try:
        with get_db_session() as session:
            result = session.execute("""
                SELECT
                    signal_type, price, confidence,
                    shares, position_value, risk_amount,
                    stop_loss_price, take_profit_price,
                    executed, timestamp
                FROM signals
                WHERE symbol = %s
                  AND timestamp > NOW() - INTERVAL '%s days'
                ORDER BY timestamp DESC
            """, (symbol, days))
            
            signals = [
                {
                    "signal_type": row[0],
                    "price": float(row[1]),
                    "confidence": float(row[2]),
                    "shares": row[3],
                    "position_value": float(row[4]) if row[4] else None,
                    "risk_amount": float(row[5]) if row[5] else None,
                    "stop_loss_price": float(row[6]) if row[6] else None,
                    "take_profit_price": float(row[7]) if row[7] else None,
                    "executed": row[8],
                    "timestamp": row[9].isoformat()
                }
                for row in result.fetchall()
            ]
        
        return {"symbol": symbol, "signals": signals}
        
    except Exception as e:
        logger.error(f"Failed to fetch signal history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# BACKTESTING ENDPOINTS
# ============================================================================

@app.post("/backtest/run")
async def run_backtest(request: BacktestRequest, background_tasks: BackgroundTasks):
    """
    Run a backtest for the given configuration.
    
    Returns backtest ID immediately and runs backtest in background.
    """
    try:
        from src.shared.models import BacktestConfig
        from src.database.connection import DatabaseConnection
        
        # Create backtest configuration
        config = BacktestConfig(
            symbol=request.symbol,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            position_size=request.position_size_pct,
            cms_buy_threshold=request.strategy_params.get('cms_buy_threshold', 50) if request.strategy_params else 50,
            cms_sell_threshold=request.strategy_params.get('cms_sell_threshold', -50) if request.strategy_params else -50
        )
        
        # Initialize backtest engine
        db_connection = DatabaseConnection()
        backtest_engine = BacktestingModule(db_connection)
        
        # Run backtest in background
        def run_backtest_task():
            result = backtest_engine.run_backtest(config)
            
            # Stream result to Redis
            redis_client.publish(
                "backtest.results",
                json.dumps({
                    "backtest_id": result.backtest_id,
                    "symbol": request.symbol,
                    "total_return": result.metrics.total_return,
                    "sharpe_ratio": result.metrics.sharpe_ratio,
                    "max_drawdown": result.metrics.max_drawdown,
                    "win_rate": result.metrics.win_rate,
                    "total_trades": result.metrics.total_trades,
                    "timestamp": datetime.utcnow().isoformat()
                })
            )
        
        background_tasks.add_task(run_backtest_task)
        
        return {
            "message": "Backtest started",
            "symbol": request.symbol,
            "start_date": request.start_date.isoformat(),
            "end_date": request.end_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/backtest/results")
async def get_backtest_results(
    symbol: Optional[str] = None,
    limit: int = Query(10, ge=1, le=100)
):
    """
    Get backtest results, optionally filtered by symbol.
    """
    try:
        with get_db_session() as session:
            if symbol:
                query = """
                    SELECT
                        id, name, symbol, total_return, cagr,
                        sharpe_ratio, sortino_ratio, max_drawdown,
                        win_rate, profit_factor, total_trades,
                        executed_at
                    FROM backtest_results
                    WHERE symbol = %s
                    ORDER BY executed_at DESC
                    LIMIT %s
                """
                result = session.execute(query, (symbol, limit))
            else:
                query = """
                    SELECT
                        id, name, symbol, total_return, cagr,
                        sharpe_ratio, sortino_ratio, max_drawdown,
                        win_rate, profit_factor, total_trades,
                        executed_at
                    FROM backtest_results
                    ORDER BY executed_at DESC
                    LIMIT %s
                """
                result = session.execute(query, (limit,))
            
            results = [
                {
                    "id": str(row[0]),
                    "name": row[1],
                    "symbol": row[2],
                    "total_return": float(row[3]) if row[3] else None,
                    "cagr": float(row[4]) if row[4] else None,
                    "sharpe_ratio": float(row[5]) if row[5] else None,
                    "sortino_ratio": float(row[6]) if row[6] else None,
                    "max_drawdown": float(row[7]) if row[7] else None,
                    "win_rate": float(row[8]) if row[8] else None,
                    "profit_factor": float(row[9]) if row[9] else None,
                    "total_trades": row[10],
                    "executed_at": row[11].isoformat()
                }
                for row in result.fetchall()
            ]
        
        return {"results": results}
        
    except Exception as e:
        logger.error(f"Failed to fetch backtest results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/backtest/result/{backtest_id}")
async def get_backtest_detail(backtest_id: str):
    """
    Get detailed backtest result including equity curve and trades.
    """
    try:
        with get_db_session() as session:
            result = session.execute("""
                SELECT
                    id, name, symbol, start_date, end_date,
                    initial_capital, total_return, cagr,
                    sharpe_ratio, sortino_ratio, max_drawdown,
                    win_rate, profit_factor, total_trades,
                    winning_trades, losing_trades,
                    avg_win, avg_loss, largest_win, largest_loss,
                    equity_curve, drawdown_curve, trades
                FROM backtest_results
                WHERE id = %s
            """, (backtest_id,))
            
            row = result.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Backtest not found")
            
            return {
                "id": str(row[0]),
                "name": row[1],
                "symbol": row[2],
                "start_date": row[3].isoformat(),
                "end_date": row[4].isoformat(),
                "initial_capital": float(row[5]),
                "metrics": {
                    "total_return": float(row[6]) if row[6] else None,
                    "cagr": float(row[7]) if row[7] else None,
                    "sharpe_ratio": float(row[8]) if row[8] else None,
                    "sortino_ratio": float(row[9]) if row[9] else None,
                    "max_drawdown": float(row[10]) if row[10] else None,
                    "win_rate": float(row[11]) if row[11] else None,
                    "profit_factor": float(row[12]) if row[12] else None,
                    "total_trades": row[13],
                    "winning_trades": row[14],
                    "losing_trades": row[15],
                    "avg_win": float(row[16]) if row[16] else None,
                    "avg_loss": float(row[17]) if row[17] else None,
                    "largest_win": float(row[18]) if row[18] else None,
                    "largest_loss": float(row[19]) if row[19] else None
                },
                "equity_curve": row[20],
                "drawdown_curve": row[21],
                "trades": row[22]
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch backtest detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ZERODHA AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/zerodha/auth/init")
async def zerodha_auth_init(request: ZerodhaAuthRequest):
    """
    Initialize Zerodha authentication.
    
    Returns login URL for user to authenticate.
    """
    try:
        global zerodha_client
        zerodha_client = ZerodhaClient(
            api_key=request.api_key,
            api_secret=request.api_secret
        )
        
        login_url = zerodha_client.get_login_url()
        
        return {
            "login_url": login_url,
            "message": "Please visit the login URL and authorize the application"
        }
        
    except Exception as e:
        logger.error(f"Zerodha auth init failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/zerodha/auth/complete")
async def zerodha_auth_complete(request: ZerodhaAuthRequest):
    """
    Complete Zerodha authentication with request token.
    
    Exchanges request token for access token.
    """
    try:
        if zerodha_client is None:
            raise HTTPException(
                status_code=400,
                detail="Please initialize authentication first"
            )
        
        if not request.request_token:
            raise HTTPException(
                status_code=400,
                detail="request_token is required"
            )
        
        # Generate access token
        session_data = zerodha_client.generate_session(request.request_token)
        
        return {
            "message": "Authentication successful",
            "user_id": session_data.get("user_id"),
            "user_name": session_data.get("user_name"),
            "email": session_data.get("email")
        }
        
    except Exception as e:
        logger.error(f"Zerodha auth complete failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# TRADING ENDPOINTS
# ============================================================================

@app.post("/trade/execute")
async def execute_trade(
    request: OrderRequest,
    client: ZerodhaClient = Depends(get_zerodha_client)
):
    """
    Execute a trade through Zerodha.
    """
    try:
        # Place order
        order_id = client.place_order(
            symbol=request.symbol,
            exchange=request.exchange,
            transaction_type=request.transaction_type,
            quantity=request.quantity,
            order_type=request.order_type,
            product=request.product,
            price=request.price,
            trigger_price=request.trigger_price,
            tag=request.tag
        )
        
        # Get order details
        order_details = client.get_order_history(order_id)
        
        # Store in database
        with get_db_session() as session:
            session.execute("""
                INSERT INTO zerodha_orders (
                    order_id, symbol, exchange, transaction_type,
                    order_type, product, quantity, price,
                    trigger_price, status, order_timestamp
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                order_id, request.symbol, request.exchange,
                request.transaction_type, request.order_type,
                request.product, request.quantity, request.price,
                request.trigger_price, order_details[0]['status'],
                datetime.utcnow()
            ))
            session.commit()
        
        # Stream to Redis
        redis_client.publish(
            "trades.live",
            json.dumps({
                "order_id": order_id,
                "symbol": request.symbol,
                "transaction_type": request.transaction_type,
                "quantity": request.quantity,
                "status": order_details[0]['status'],
                "timestamp": datetime.utcnow().isoformat()
            })
        )
        
        return {
            "order_id": order_id,
            "status": order_details[0]['status'],
            "message": "Order placed successfully"
        }
        
    except Exception as e:
        logger.error(f"Trade execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trade/status/{order_id}")
async def get_trade_status(
    order_id: str,
    client: ZerodhaClient = Depends(get_zerodha_client)
):
    """
    Get status of a specific order.
    """
    try:
        order_history = client.get_order_history(order_id)
        
        if not order_history:
            raise HTTPException(status_code=404, detail="Order not found")
        
        latest_order = order_history[-1]
        
        # Update database
        with get_db_session() as session:
            session.execute("""
                UPDATE zerodha_orders
                SET status = %s,
                    filled_quantity = %s,
                    average_price = %s,
                    updated_at = NOW()
                WHERE order_id = %s
            """, (
                latest_order['status'],
                latest_order.get('filled_quantity', 0),
                latest_order.get('average_price'),
                order_id
            ))
            session.commit()
        
        return {
            "order_id": order_id,
            "status": latest_order['status'],
            "filled_quantity": latest_order.get('filled_quantity', 0),
            "pending_quantity": latest_order.get('pending_quantity', 0),
            "average_price": latest_order.get('average_price'),
            "order_timestamp": latest_order.get('order_timestamp'),
            "exchange_timestamp": latest_order.get('exchange_timestamp')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trade status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trade/logs")
async def get_trade_logs(
    symbol: Optional[str] = None,
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(50, ge=1, le=500)
):
    """
    Get trade execution logs.
    """
    try:
        with get_db_session() as session:
            if symbol:
                query = """
                    SELECT
                        order_id, symbol, exchange, transaction_type,
                        order_type, quantity, price, filled_quantity,
                        average_price, status, order_timestamp
                    FROM zerodha_orders
                    WHERE symbol = %s
                      AND order_timestamp > NOW() - INTERVAL '%s days'
                    ORDER BY order_timestamp DESC
                    LIMIT %s
                """
                result = session.execute(query, (symbol, days, limit))
            else:
                query = """
                    SELECT
                        order_id, symbol, exchange, transaction_type,
                        order_type, quantity, price, filled_quantity,
                        average_price, status, order_timestamp
                    FROM zerodha_orders
                    WHERE order_timestamp > NOW() - INTERVAL '%s days'
                    ORDER BY order_timestamp DESC
                    LIMIT %s
                """
                result = session.execute(query, (days, limit))
            
            logs = [
                {
                    "order_id": row[0],
                    "symbol": row[1],
                    "exchange": row[2],
                    "transaction_type": row[3],
                    "order_type": row[4],
                    "quantity": row[5],
                    "price": float(row[6]) if row[6] else None,
                    "filled_quantity": row[7],
                    "average_price": float(row[8]) if row[8] else None,
                    "status": row[9],
                    "order_timestamp": row[10].isoformat()
                }
                for row in result.fetchall()
            ]
        
        return {"logs": logs}
        
    except Exception as e:
        logger.error(f"Failed to fetch trade logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/trade/modify/{order_id}")
async def modify_order(
    order_id: str,
    quantity: Optional[int] = None,
    price: Optional[float] = None,
    order_type: Optional[str] = None,
    trigger_price: Optional[float] = None,
    client: ZerodhaClient = Depends(get_zerodha_client)
):
    """
    Modify an existing order.
    """
    try:
        client.modify_order(
            order_id=order_id,
            quantity=quantity,
            price=price,
            order_type=order_type,
            trigger_price=trigger_price
        )
        
        # Update database
        with get_db_session() as session:
            updates = []
            params = []
            
            if quantity is not None:
                updates.append("quantity = %s")
                params.append(quantity)
            if price is not None:
                updates.append("price = %s")
                params.append(price)
            if order_type is not None:
                updates.append("order_type = %s")
                params.append(order_type)
            if trigger_price is not None:
                updates.append("trigger_price = %s")
                params.append(trigger_price)
            
            updates.append("updated_at = NOW()")
            params.append(order_id)
            
            query = f"""
                UPDATE zerodha_orders
                SET {', '.join(updates)}
                WHERE order_id = %s
            """
            session.execute(query, tuple(params))
            session.commit()
        
        return {"message": "Order modified successfully", "order_id": order_id}
        
    except Exception as e:
        logger.error(f"Order modification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/trade/cancel/{order_id}")
async def cancel_order(
    order_id: str,
    client: ZerodhaClient = Depends(get_zerodha_client)
):
    """
    Cancel an existing order.
    """
    try:
        client.cancel_order(order_id)
        
        # Update database
        with get_db_session() as session:
            session.execute("""
                UPDATE zerodha_orders
                SET status = 'CANCELLED',
                    updated_at = NOW()
                WHERE order_id = %s
            """, (order_id,))
            session.commit()
        
        # Stream to Redis
        redis_client.publish(
            "trades.live",
            json.dumps({
                "order_id": order_id,
                "status": "CANCELLED",
                "timestamp": datetime.utcnow().isoformat()
            })
        )
        
        return {"message": "Order cancelled successfully", "order_id": order_id}
        
    except Exception as e:
        logger.error(f"Order cancellation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trade/holdings")
async def get_holdings(client: ZerodhaClient = Depends(get_zerodha_client)):
    """
    Get current holdings from Zerodha.
    """
    try:
        holdings = client.get_holdings()
        return {"holdings": holdings}
        
    except Exception as e:
        logger.error(f"Failed to fetch holdings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trade/positions")
async def get_positions(client: ZerodhaClient = Depends(get_zerodha_client)):
    """
    Get current positions from Zerodha.
    """
    try:
        positions = client.get_positions()
        
        # Store snapshot in database
        with get_db_session() as session:
            for position in positions.get('net', []):
                session.execute("""
                    INSERT INTO zerodha_positions_snapshot (
                        symbol, exchange, product, quantity,
                        average_price, last_price, pnl
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    position['tradingsymbol'],
                    position['exchange'],
                    position['product'],
                    position['quantity'],
                    position['average_price'],
                    position['last_price'],
                    position['pnl']
                ))
            session.commit()
        
        return {"positions": positions}
        
    except Exception as e:
        logger.error(f"Failed to fetch positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trade/margins")
async def get_margins(client: ZerodhaClient = Depends(get_zerodha_client)):
    """
    Get margin details from Zerodha.
    """
    try:
        margins = client.get_margins()
        return {"margins": margins}
        
    except Exception as e:
        logger.error(f"Failed to fetch margins: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# STARTUP & SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting Algorithmic Trading API...")
    logger.info("All services initialized successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Algorithmic Trading API...")
    if redis_client:
        redis_client.close()
    logger.info("Shutdown complete")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
