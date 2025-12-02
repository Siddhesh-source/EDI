"""FastAPI endpoints for Enhanced NLP Engine."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from src.nlp.engine import EnhancedNLPEngine, NLPOutput
from src.shared.models import Article
from src.database.connection import get_db_session
from src.database.repositories import ArticleRepository
from src.api.main import verify_api_key

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/nlp", tags=["NLP"])

# Global NLP engine instance
nlp_engine: Optional[EnhancedNLPEngine] = None


def get_nlp_engine() -> EnhancedNLPEngine:
    """Get or create NLP engine instance."""
    global nlp_engine
    if nlp_engine is None:
        nlp_engine = EnhancedNLPEngine(
            window_size=20,
            decay_hours=24.0,
            high_severity_threshold=0.7
        )
    return nlp_engine


# Request/Response Models

class NLPAnalysisRequest(BaseModel):
    """Request for NLP analysis."""
    symbols: List[str] = Field(..., description="Stock symbols to analyze")
    lookback_hours: int = Field(24, description="Hours to look back for articles", ge=1, le=168)
    use_smoothing: bool = Field(True, description="Apply sliding window smoothing")
    apply_recency_decay: bool = Field(True, description="Apply temporal decay")


class SentimentIndexResponse(BaseModel):
    """Sentiment Index response."""
    raw_score: float
    weighted_score: float
    smoothed_score: float
    confidence: float
    article_count: int
    positive_ratio: float
    negative_ratio: float
    neutral_ratio: float
    timestamp: str


class EventShockFactorResponse(BaseModel):
    """Event Shock Factor response."""
    total_shock: float
    event_count: int
    high_severity_count: int
    event_type_distribution: dict
    max_severity: float
    avg_severity: float
    recency_factor: float
    dominant_event_type: Optional[str]
    timestamp: str


class NLPOutputResponse(BaseModel):
    """Complete NLP output response."""
    sentiment_index: SentimentIndexResponse
    event_shock_factor: EventShockFactorResponse
    raw_sentiments: List[dict]
    detected_events: List[dict]
    market_mood: str
    risk_level: str
    explanation: str
    timestamp: str


# Endpoints

@router.post("/analyze", response_model=NLPOutputResponse)
async def analyze_sentiment_and_events(
    request: NLPAnalysisRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Perform complete NLP analysis on recent articles.
    
    Returns Sentiment Index (SI), Event Shock Factor (ESF),
    market mood, risk level, and detailed explanation.
    
    Args:
        request: Analysis request with symbols and parameters
        
    Returns:
        Complete NLP output with all metrics
    """
    try:
        engine = get_nlp_engine()
        
        # Fetch recent articles from database
        with next(get_db_session()) as session:
            article_repo = ArticleRepository(session)
            
            # Get articles from last N hours
            start_time = datetime.now() - timedelta(hours=request.lookback_hours)
            db_articles = article_repo.get_by_timerange(start_time, datetime.now())
            
            # Filter by symbols if specified
            if request.symbols:
                db_articles = [
                    a for a in db_articles
                    if any(symbol in (a.symbols or []) for symbol in request.symbols)
                ]
            
            if not db_articles:
                raise HTTPException(
                    status_code=404,
                    detail=f"No articles found for symbols {request.symbols} in last {request.lookback_hours} hours"
                )
            
            # Convert to Article objects
            articles = [
                Article(
                    id=a.id,
                    title=a.title,
                    content=a.content or "",
                    source=a.source,
                    published_at=a.published_at,
                    symbols=a.symbols or []
                )
                for a in db_articles
            ]
        
        # Process articles through NLP engine
        output = engine.process_articles(
            articles,
            use_smoothing=request.use_smoothing,
            apply_recency_decay=request.apply_recency_decay
        )
        
        # Publish to Redis
        engine.publish_to_redis(output)
        
        # Convert to response model
        return NLPOutputResponse(
            sentiment_index=SentimentIndexResponse(**output.sentiment_index.to_dict()),
            event_shock_factor=EventShockFactorResponse(**output.event_shock_factor.to_dict()),
            raw_sentiments=output.raw_sentiments,
            detected_events=output.detected_events,
            market_mood=output.market_mood,
            risk_level=output.risk_level,
            explanation=output.explanation,
            timestamp=output.timestamp.isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"NLP analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"NLP analysis failed: {str(e)}"
        )


@router.get("/sentiment-index", response_model=SentimentIndexResponse)
async def get_current_sentiment_index(
    symbols: Optional[List[str]] = Query(None, description="Stock symbols to filter"),
    hours: int = Query(24, description="Hours to look back", ge=1, le=168),
    api_key: str = Depends(verify_api_key)
):
    """
    Get current Sentiment Index (SI).
    
    Args:
        symbols: Optional list of symbols to filter
        hours: Hours to look back for calculation
        
    Returns:
        Current Sentiment Index
    """
    try:
        engine = get_nlp_engine()
        
        # Fetch recent sentiments from database
        with next(get_db_session()) as session:
            from src.database.repositories import SentimentScoreRepository
            from src.shared.models import SentimentScore
            
            repo = SentimentScoreRepository(session)
            start_time = datetime.now() - timedelta(hours=hours)
            db_sentiments = repo.get_by_timerange(start_time, datetime.now())
            
            if not db_sentiments:
                raise HTTPException(
                    status_code=404,
                    detail=f"No sentiment data found in last {hours} hours"
                )
            
            # Convert to SentimentScore objects
            sentiments = [
                SentimentScore(
                    article_id=s.article_id,
                    score=float(s.score),
                    confidence=float(s.confidence),
                    keywords_positive=s.keywords_positive or [],
                    keywords_negative=s.keywords_negative or [],
                    timestamp=s.timestamp
                )
                for s in db_sentiments
            ]
        
        # Compute Sentiment Index
        si = engine.compute_sentiment_index(sentiments, use_smoothing=True)
        
        return SentimentIndexResponse(**si.to_dict())
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get sentiment index: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get sentiment index: {str(e)}"
        )


@router.get("/event-shock-factor", response_model=EventShockFactorResponse)
async def get_current_event_shock_factor(
    symbols: Optional[List[str]] = Query(None, description="Stock symbols to filter"),
    hours: int = Query(24, description="Hours to look back", ge=1, le=168),
    api_key: str = Depends(verify_api_key)
):
    """
    Get current Event Shock Factor (ESF).
    
    Args:
        symbols: Optional list of symbols to filter
        hours: Hours to look back for calculation
        
    Returns:
        Current Event Shock Factor
    """
    try:
        engine = get_nlp_engine()
        
        # Fetch recent events from database
        with next(get_db_session()) as session:
            from src.database.repositories import EventRepository
            from src.shared.models import Event, EventType
            
            repo = EventRepository(session)
            start_time = datetime.now() - timedelta(hours=hours)
            db_events = repo.get_by_timerange(start_time, datetime.now())
            
            if not db_events:
                # Return zero ESF if no events
                return EventShockFactorResponse(
                    total_shock=0.0,
                    event_count=0,
                    high_severity_count=0,
                    event_type_distribution={},
                    max_severity=0.0,
                    avg_severity=0.0,
                    recency_factor=1.0,
                    dominant_event_type=None,
                    timestamp=datetime.now().isoformat()
                )
            
            # Convert to Event objects
            events = [
                Event(
                    id=e.id,
                    article_id=e.article_id,
                    event_type=EventType(e.event_type),
                    severity=float(e.severity),
                    keywords=e.keywords or [],
                    timestamp=e.timestamp
                )
                for e in db_events
            ]
        
        # Compute Event Shock Factor
        esf = engine.compute_event_shock_factor(events, apply_recency_decay=True)
        
        return EventShockFactorResponse(**esf.to_dict())
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get event shock factor: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get event shock factor: {str(e)}"
        )


@router.get("/market-mood")
async def get_market_mood(
    symbols: Optional[List[str]] = Query(None, description="Stock symbols to filter"),
    hours: int = Query(24, description="Hours to look back", ge=1, le=168),
    api_key: str = Depends(verify_api_key)
):
    """
    Get current market mood classification.
    
    Returns: bullish, bearish, or neutral
    
    Args:
        symbols: Optional list of symbols to filter
        hours: Hours to look back for calculation
        
    Returns:
        Market mood and supporting metrics
    """
    try:
        # Get SI and ESF
        si_response = await get_current_sentiment_index(symbols, hours, api_key)
        esf_response = await get_current_event_shock_factor(symbols, hours, api_key)
        
        engine = get_nlp_engine()
        
        # Reconstruct SI and ESF objects
        from src.nlp.engine import SentimentIndex, EventShockFactor
        
        si = SentimentIndex(
            raw_score=si_response.raw_score,
            weighted_score=si_response.weighted_score,
            smoothed_score=si_response.smoothed_score,
            confidence=si_response.confidence,
            article_count=si_response.article_count,
            positive_ratio=si_response.positive_ratio,
            negative_ratio=si_response.negative_ratio,
            neutral_ratio=si_response.neutral_ratio,
            timestamp=datetime.fromisoformat(si_response.timestamp)
        )
        
        esf = EventShockFactor(
            total_shock=esf_response.total_shock,
            event_count=esf_response.event_count,
            high_severity_count=esf_response.high_severity_count,
            event_type_distribution=esf_response.event_type_distribution,
            max_severity=esf_response.max_severity,
            avg_severity=esf_response.avg_severity,
            recency_factor=esf_response.recency_factor,
            dominant_event_type=esf_response.dominant_event_type,
            timestamp=datetime.fromisoformat(esf_response.timestamp)
        )
        
        # Classify mood
        market_mood = engine.classify_market_mood(si, esf)
        risk_level = engine.assess_risk_level(si, esf)
        
        return {
            'market_mood': market_mood,
            'risk_level': risk_level,
            'sentiment_score': si.smoothed_score,
            'event_shock': esf.total_shock,
            'confidence': si.confidence,
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Failed to get market mood: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get market mood: {str(e)}"
        )


@router.get("/historical/sentiment-index")
async def get_historical_sentiment_index(
    hours: int = Query(24, description="Hours of history", ge=1, le=168),
    symbol: Optional[str] = Query(None, description="Optional symbol filter"),
    api_key: str = Depends(verify_api_key)
):
    """
    Get historical Sentiment Index values.
    
    Returns hourly SI values for the specified time period.
    
    Args:
        hours: Hours of history to retrieve
        symbol: Optional symbol filter
        
    Returns:
        List of historical Sentiment Index values
    """
    try:
        engine = get_nlp_engine()
        
        # Get historical SI
        historical_si = engine.get_historical_sentiment_index(hours, symbol)
        
        return {
            'data': [si.to_dict() for si in historical_si],
            'count': len(historical_si),
            'period_hours': hours,
            'symbol': symbol
        }
    
    except Exception as e:
        logger.error(f"Failed to get historical sentiment index: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get historical sentiment index: {str(e)}"
        )
