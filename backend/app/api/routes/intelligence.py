import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.routes.analytics import (
    _fetch_db_posts_as_analytics_ready,
    get_dashboard_service,
    get_network_service,
    get_sentiment_service,
    get_topic_service,
    get_trend_service,
)
from app.database import get_db
from app.schemas.intelligence import (
    BatchExplanationResult,
    BatchInsightResult,
    InsightExplanation,
    IntelligenceAnalyzeRequest,
)
from app.services.dashboard import DashboardService
from app.services.intelligence import (
    DeterministicExplanationEngine,
    IntelligenceAnalysisService,
    get_explanation_engine,
    get_intelligence_analyzer,
)
from app.services.network import NetworkAnalysisService
from app.services.sentiment import SentimentAnalysisService
from app.services.topic import TopicAnalysisService
from app.services.trend import TrendAnalysisService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Intelligence"])


@router.get(
    "/insights",
    response_model=BatchInsightResult,
    summary="Fetch Recent Insights",
    description="Generates and returns synthesized insights based on recent platform data.",
)
def get_insights(
    platform: Optional[str] = Query(None, description="Filter by platform name"),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    max_insights: int = Query(20, ge=1, le=100, description="Maximum insights to return"),
    db: Session = Depends(get_db),
    intelligence_service: IntelligenceAnalysisService = Depends(get_intelligence_analyzer),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
    sentiment_service: SentimentAnalysisService = Depends(get_sentiment_service),
    topic_service: TopicAnalysisService = Depends(get_topic_service),
    trend_service: TrendAnalysisService = Depends(get_trend_service),
    network_service: NetworkAnalysisService = Depends(get_network_service),
) -> BatchInsightResult:
    try:
        # Fetch posts for the last 24 hours as a default observation window
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=1)
        
        posts = _fetch_db_posts_as_analytics_ready(
            db=db,
            platform=platform,
            start_date=start_time,
            end_date=end_time,
            limit=200,
        )

        if not posts:
            return BatchInsightResult(
                total_insights=0,
                insights=[],
                model=intelligence_service.model_name,
            )

        # Generate intermediate analytics required by intelligence engine
        sentiment_res = sentiment_service.analyze_batch(posts)
        topic_res = topic_service.extract_topics(posts)
        trend_res = trend_service.analyze_trends(topics=topic_res.topics, posts=posts)
        network_res = network_service.analyze_batch(posts)
        overview_res = dashboard_service.get_overview(platform=platform)

        # Synthesize insights
        result = intelligence_service.generate_insights(
            trends=trend_res.trends,
            batch_trend=trend_res,
            topics=topic_res.topics,
            batch_topic=topic_res,
            sentiment=sentiment_res,
            overview=overview_res,
            network=network_res,
            posts=posts,
            min_confidence=min_confidence,
            max_insights=max_insights,
        )
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating insights: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while synthesizing intelligence.",
        )


@router.get(
    "/insights/{insight_id}/explanation",
    response_model=InsightExplanation,
    summary="Get Insight Explanation",
    description="Returns the detailed, human-readable evidence and explanation for a specific insight.",
)
def get_insight_explanation(
    insight_id: str,
    platform: Optional[str] = Query(None, description="Filter by platform name (must match original GET /insights query)"),
    db: Session = Depends(get_db),
    intelligence_service: IntelligenceAnalysisService = Depends(get_intelligence_analyzer),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
    sentiment_service: SentimentAnalysisService = Depends(get_sentiment_service),
    topic_service: TopicAnalysisService = Depends(get_topic_service),
    trend_service: TrendAnalysisService = Depends(get_trend_service),
    network_service: NetworkAnalysisService = Depends(get_network_service),
    explanation_engine: DeterministicExplanationEngine = Depends(get_explanation_engine),
) -> InsightExplanation:
    try:
        # Regenerate insights to find the matching insight deterministically
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=1)
        
        posts = _fetch_db_posts_as_analytics_ready(
            db=db,
            platform=platform,
            start_date=start_time,
            end_date=end_time,
            limit=200,
        )

        if not posts:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Insight {insight_id} not found.")

        sentiment_res = sentiment_service.analyze_batch(posts)
        topic_res = topic_service.extract_topics(posts)
        trend_res = trend_service.analyze_trends(topics=topic_res.topics, posts=posts)
        network_res = network_service.analyze_batch(posts)
        overview_res = dashboard_service.get_overview(platform=platform)

        result = intelligence_service.generate_insights(
            trends=trend_res.trends,
            batch_trend=trend_res,
            topics=topic_res.topics,
            batch_topic=topic_res,
            sentiment=sentiment_res,
            overview=overview_res,
            network=network_res,
            posts=posts,
        )

        for insight in result.insights:
            if insight.id == insight_id:
                return explanation_engine.explain_insight(insight)
                
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Insight {insight_id} not found in recent generated insights.",
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating explanation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating the explanation.",
        )


@router.post(
    "/analyze",
    response_model=BatchInsightResult,
    summary="Analyze Payload for Insights",
    description="Generates insights based on a provided payload of posts or pre-computed trends.",
)
def analyze_payload(
    payload: IntelligenceAnalyzeRequest,
    intelligence_service: IntelligenceAnalysisService = Depends(get_intelligence_analyzer),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
    sentiment_service: SentimentAnalysisService = Depends(get_sentiment_service),
    topic_service: TopicAnalysisService = Depends(get_topic_service),
    trend_service: TrendAnalysisService = Depends(get_trend_service),
    network_service: NetworkAnalysisService = Depends(get_network_service),
) -> BatchInsightResult:
    try:
        if not payload.posts and not payload.raw_posts and not payload.trends and not payload.topics:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payload must contain at least posts, raw_posts, trends, or topics.",
            )

        posts = None
        if payload.posts or payload.raw_posts:
            from app.api.routes.analytics import _resolve_analytics_posts
            posts = _resolve_analytics_posts(
                posts=payload.posts,
                raw_posts=payload.raw_posts
            )

        # Recompute missing intermediate inputs if posts are available
        sentiment_res = None
        topic_res = None
        trend_res = None
        network_res = None
        overview_res = dashboard_service.get_overview(platform=payload.platform) if payload.platform else None

        if posts:
            sentiment_res = sentiment_service.analyze_batch(posts)
            
            topics = payload.topics
            if not topics:
                topic_res = topic_service.extract_topics(posts)
                topics = topic_res.topics

            trends = payload.trends
            if not trends and topics:
                trend_res = trend_service.analyze_trends(topics=topics, posts=posts)
                trends = trend_res.trends

            network_res = network_service.analyze_batch(posts)
        else:
            topics = payload.topics
            trends = payload.trends

        result = intelligence_service.generate_insights(
            trends=trends,
            batch_trend=trend_res,
            topics=topics,
            batch_topic=topic_res,
            sentiment=sentiment_res,
            overview=overview_res,
            network=network_res,
            posts=posts,
            min_confidence=payload.min_confidence or 0.5,
            max_insights=payload.max_insights or 20,
        )
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error analyzing intelligence payload: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during payload analysis.",
        )
