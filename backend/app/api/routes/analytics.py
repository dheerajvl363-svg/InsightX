from datetime import datetime, timedelta, timezone
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import ErrorResponse
from app.schemas.analytics import (
    AuthorListResponse,
    CountResponse,
    EngagementSummary,
    EngagementTimeSeriesResponse,
    LanguageSummary,
    PlatformSummary,
    PostListResponse,
    TimeSeriesResponse,
    TopicListResponse,
)
from app.schemas.analytics_api import (
    CombinedAnalyticsResponse,
    CombinedAnalyzeRequest,
    DemographicAnalyzeRequest,
    EmotionAnalyzeRequest,
    SentimentAnalyzeRequest,
    TopicAnalyzeRequest,
    TrendAnalyzeRequest,
)
from app.schemas.dashboard import (
    DashboardOverviewResponse,
    PlatformComparisonResponse,
)
from app.schemas.data_quality import AnalyticsReadyPost, BatchDataQualityResult
from app.schemas.demographic import (
    BatchDemographicResult,
    DemographicDistribution,
    DemographicProfile,
)
from app.schemas.emotion import BatchEmotionResult, EmotionResult
from app.schemas.post import RawPostPayload
from app.schemas.network import BatchNetworkResult, NetworkAnalyzeRequest
from app.schemas.sentiment import BatchSentimentResult, SentimentResult
from app.schemas.topic import BatchTopicResult, ExtractedTopic
from app.schemas.trend import BatchTrendResult, TopicTrendResult
from app.services.analytics import AnalyticsService
from app.services.dashboard import DashboardService
from app.services.data_quality import DataQualityService, get_data_quality_service
from app.services.demographic import (
    DemographicAnalysisService,
    get_demographic_analyzer,
)
from app.services.emotion import (
    EmotionAnalysisService,
    get_emotion_analyzer,
)
from app.services.network import (
    NetworkAnalysisService,
    get_network_analyzer,
)
from app.services.normalizer import DataNormalizer
from app.services.sentiment import (
    SentimentAnalysisService,
    get_sentiment_analyzer,
)
from app.services.topic import (
    TopicAnalysisService,
    get_topic_analyzer,
)
from app.services.trend import (
    TrendAnalysisService,
    get_trend_analyzer,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Analytics"])



ALLOWED_SORT_BY = {"posted_at", "likes", "comments", "shares", "views"}
ALLOWED_AUTHOR_SORT_BY = {
    "post_count",
    "total_likes",
    "total_comments",
    "total_shares",
    "total_views",
}
ALLOWED_TOPIC_SORT_BY = {
    "post_count",
    "total_likes",
    "total_comments",
    "total_shares",
    "total_views",
}
ALLOWED_ORDER = {"asc", "desc"}


def validate_date_range(start: Optional[datetime], end: Optional[datetime]):
    """Helper to ensure start_date <= end_date."""
    if start and end and start > end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date cannot be after end_date.",
        )


def validate_sort_parameters(
    sort_by: Optional[str],
    order: Optional[str],
    allowed_fields: set[str],
    default_sort_by: str = "posted_at",
) -> tuple[str, str]:
    """Helper to validate sort_by and order query parameters against an allowed field set."""
    clean_sort_by = (sort_by or default_sort_by).strip().lower()
    if clean_sort_by not in allowed_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort_by field '{sort_by}'. Supported fields: {', '.join(sorted(allowed_fields))}.",
        )

    clean_order = (order or "desc").strip().lower()
    if clean_order not in ALLOWED_ORDER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid order '{order}'. Supported orders: {', '.join(sorted(ALLOWED_ORDER))}.",
        )

    return clean_sort_by, clean_order


@router.get(
    "/posts",
    response_model=PostListResponse,
    summary="Query posts for analytics & NLP",
    description="Returns paginated posts with deterministic ordering and optional search, platform, language, author, date, engagement, and sorting filters.",
)
def get_posts(
    platform: Optional[str] = Query(None, description="Filter by platform name (e.g. 'X', 'Telegram')"),
    language: Optional[str] = Query(None, description="Filter by lowercase language code (e.g. 'en', 'hi', 'te')"),
    start_date: Optional[datetime] = Query(None, description="Filter posts on or after this timestamp"),
    end_date: Optional[datetime] = Query(None, description="Filter posts on or before this timestamp"),
    author: Optional[str] = Query(None, description="Filter by author username/handle"),
    search: Optional[str] = Query(None, description="Case-insensitive substring search in post text"),
    min_likes: Optional[int] = Query(None, ge=0, description="Minimum likes (latest metric snapshot)"),
    min_comments: Optional[int] = Query(None, ge=0, description="Minimum comments (latest metric snapshot)"),
    min_shares: Optional[int] = Query(None, ge=0, description="Minimum shares (latest metric snapshot)"),
    min_views: Optional[int] = Query(None, ge=0, description="Minimum views (latest metric snapshot)"),
    sort_by: Optional[str] = Query("posted_at", description="Field to sort by ('posted_at', 'likes', 'comments', 'shares', 'views')"),
    order: Optional[str] = Query("desc", description="Sort order ('asc' or 'desc')"),
    limit: int = Query(50, ge=1, le=200, description="Max posts to return (1-200)"),
    offset: int = Query(0, ge=0, description="Offset position for pagination"),
    db: Session = Depends(get_db),
) -> PostListResponse:
    validate_date_range(start_date, end_date)
    clean_sort_by, clean_order = validate_sort_parameters(sort_by, order, ALLOWED_SORT_BY, default_sort_by="posted_at")
    try:
        service = AnalyticsService(db)
        return service.get_posts(
            platform=platform,
            language=language,
            start_time=start_date,
            end_time=end_date,
            author_username=author,
            search=search,
            min_likes=min_likes,
            min_comments=min_comments,
            min_shares=min_shares,
            min_views=min_views,
            sort_by=clean_sort_by,
            order=clean_order,
            limit=limit,
            offset=offset,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error querying posts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while querying posts.",
        )


@router.get(
    "/count",
    response_model=CountResponse,
    summary="Get post counts with filters",
    description="Returns the total count of posts matching optional search, platform, language, and date range filters.",
)
def get_count(
    platform: Optional[str] = Query(None, description="Filter by platform name"),
    language: Optional[str] = Query(None, description="Filter by language code"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    author: Optional[str] = Query(None, description="Filter by author username"),
    search: Optional[str] = Query(None, description="Case-insensitive substring search in post text"),
    min_likes: Optional[int] = Query(None, ge=0, description="Minimum likes (latest metric snapshot)"),
    min_comments: Optional[int] = Query(None, ge=0, description="Minimum comments (latest metric snapshot)"),
    min_shares: Optional[int] = Query(None, ge=0, description="Minimum shares (latest metric snapshot)"),
    min_views: Optional[int] = Query(None, ge=0, description="Minimum views (latest metric snapshot)"),
    db: Session = Depends(get_db),
) -> CountResponse:
    validate_date_range(start_date, end_date)
    try:
        service = AnalyticsService(db)
        return service.get_post_count(
            platform=platform,
            language=language,
            start_time=start_date,
            end_time=end_date,
            author_username=author,
            search=search,
            min_likes=min_likes,
            min_comments=min_comments,
            min_shares=min_shares,
            min_views=min_views,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error counting posts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while counting posts.",
        )


@router.get(
    "/platforms",
    response_model=List[PlatformSummary],
    summary="Platform analytics summary",
    description="Returns aggregate post counts and chronological bounds across all registered platforms.",
)
def get_platform_summary(db: Session = Depends(get_db)) -> List[PlatformSummary]:
    try:
        service = AnalyticsService(db)
        return service.get_platform_summary()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error retrieving platform summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving platform summary.",
        )


@router.get(
    "/languages",
    response_model=List[LanguageSummary],
    summary="Language distribution summary",
    description="Returns aggregate post counts grouped by language code.",
)
def get_language_summary(db: Session = Depends(get_db)) -> List[LanguageSummary]:
    try:
        service = AnalyticsService(db)
        return service.get_language_summary()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error retrieving language summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving language summary.",
        )


@router.get(
    "/engagement",
    response_model=EngagementSummary,
    summary="Engagement metrics summary",
    description="Computes aggregate likes, comments, shares, and views across posts matching filters.",
)
def get_engagement_summary(
    platform: Optional[str] = Query(None, description="Filter by platform name"),
    language: Optional[str] = Query(None, description="Filter by language code"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    db: Session = Depends(get_db),
) -> EngagementSummary:
    validate_date_range(start_date, end_date)
    try:
        service = AnalyticsService(db)
        return service.get_engagement_summary(
            platform=platform,
            language=language,
            start_time=start_date,
            end_time=end_date,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error calculating engagement summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while calculating engagement summary.",
        )


@router.get(
    "/timeseries",
    response_model=TimeSeriesResponse,
    summary="Daily post volume time-series",
    description="Returns daily post counts grouped chronologically for trend and volume analysis.",
)
def get_timeseries(
    platform: Optional[str] = Query(None, description="Filter by platform name"),
    language: Optional[str] = Query(None, description="Filter by language code"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    db: Session = Depends(get_db),
) -> TimeSeriesResponse:
    validate_date_range(start_date, end_date)
    try:
        service = AnalyticsService(db)
        return service.get_time_series(
            platform=platform,
            language=language,
            start_time=start_date,
            end_time=end_date,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error generating time-series: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating time-series analytics.",
        )


@router.get(
    "/timeseries/engagement",
    response_model=EngagementTimeSeriesResponse,
    summary="Daily engagement time-series",
    description="Returns daily post counts and aggregate engagement metrics (likes, comments, shares, views) grouped chronologically.",
)
def get_engagement_timeseries(
    platform: Optional[str] = Query(None, description="Filter by platform name"),
    language: Optional[str] = Query(None, description="Filter by language code"),
    author: Optional[str] = Query(None, description="Filter by author username"),
    search: Optional[str] = Query(None, description="Case-insensitive substring search in post text"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    db: Session = Depends(get_db),
) -> EngagementTimeSeriesResponse:
    validate_date_range(start_date, end_date)
    try:
        service = AnalyticsService(db)
        return service.get_engagement_time_series(
            platform=platform,
            language=language,
            author=author,
            search=search,
            start_date=start_date,
            end_date=end_date,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error generating engagement time-series: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating engagement time-series analytics.",
        )


@router.get(
    "/authors",
    response_model=AuthorListResponse,
    summary="Author analytics summary",
    description="Returns aggregated post counts and engagement metrics grouped by author.",
)
def get_authors(
    platform: Optional[str] = Query(None, description="Filter by platform name"),
    language: Optional[str] = Query(None, description="Filter by language code"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    search: Optional[str] = Query(None, description="Case-insensitive substring search in post text"),
    sort_by: Optional[str] = Query("post_count", description="Field to sort by ('post_count', 'total_likes', 'total_comments', 'total_shares', 'total_views')"),
    order: Optional[str] = Query("desc", description="Sort order ('asc' or 'desc')"),
    limit: int = Query(50, ge=1, le=200, description="Max authors to return (1-200)"),
    offset: int = Query(0, ge=0, description="Offset position for pagination"),
    db: Session = Depends(get_db),
) -> AuthorListResponse:
    validate_date_range(start_date, end_date)
    clean_sort_by, clean_order = validate_sort_parameters(sort_by, order, ALLOWED_AUTHOR_SORT_BY, default_sort_by="post_count")
    try:
        service = AnalyticsService(db)
        return service.get_author_summary(
            platform=platform,
            language=language,
            start_date=start_date,
            end_date=end_date,
            search=search,
            sort_by=clean_sort_by,
            order=clean_order,
            limit=limit,
            offset=offset,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error retrieving author summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving author summary.",
        )


@router.get(
    "/topics",
    response_model=TopicListResponse,
    summary="Topic analytics summary",
    description="Returns aggregated post counts and engagement metrics grouped by topic.",
)
def get_topics(
    platform: Optional[str] = Query(None, description="Filter by platform name"),
    language: Optional[str] = Query(None, description="Filter by language code"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    search: Optional[str] = Query(None, description="Case-insensitive substring search in post text"),
    sort_by: Optional[str] = Query("post_count", description="Field to sort by ('post_count', 'total_likes', 'total_comments', 'total_shares', 'total_views')"),
    order: Optional[str] = Query("desc", description="Sort order ('asc' or 'desc')"),
    limit: int = Query(50, ge=1, le=200, description="Max topics to return (1-200)"),
    offset: int = Query(0, ge=0, description="Offset position for pagination"),
    db: Session = Depends(get_db),
) -> TopicListResponse:
    validate_date_range(start_date, end_date)
    clean_sort_by, clean_order = validate_sort_parameters(sort_by, order, ALLOWED_TOPIC_SORT_BY, default_sort_by="post_count")
    try:
        service = AnalyticsService(db)
        return service.get_topic_summary(
            platform=platform,
            language=language,
            start_date=start_date,
            end_date=end_date,
            search=search,
            sort_by=clean_sort_by,
            order=clean_order,
            limit=limit,
            offset=offset,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error retrieving topic summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving topic summary.",
        )


# =====================================================================
# Phase 3 Analytics Dependency Inversion Providers
# =====================================================================

def get_sentiment_service() -> SentimentAnalysisService:
    return get_sentiment_analyzer()


def get_emotion_service() -> EmotionAnalysisService:
    return get_emotion_analyzer()


def get_topic_service() -> TopicAnalysisService:
    return get_topic_analyzer()


def get_trend_service() -> TrendAnalysisService:
    return get_trend_analyzer()


def get_demographic_service() -> DemographicAnalysisService:
    return get_demographic_analyzer()


def get_quality_service() -> DataQualityService:
    return get_data_quality_service()


def get_network_service() -> NetworkAnalysisService:
    return get_network_analyzer()


def get_dashboard_service(db: Session = Depends(get_db)) -> DashboardService:
    return DashboardService(db)


def _fetch_db_posts_as_analytics_ready(
    db: Session,
    platform: Optional[str] = None,
    language: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[AnalyticsReadyPost]:
    validate_date_range(start_date, end_date)
    analytics_svc = AnalyticsService(db)
    post_list = analytics_svc.get_posts(
        platform=platform,
        language=language,
        start_time=start_date,
        end_time=end_date,
        search=search,
        limit=limit,
        offset=offset,
    )
    ready_posts: List[AnalyticsReadyPost] = []
    for item in post_list.items:
        text_str = item.text or ""
        if text_str.strip():
            ready_posts.append(
                AnalyticsReadyPost(
                    id=item.id,
                    platform=item.platform,
                    external_post_id=item.external_post_id,
                    text=text_str,
                    raw_text=text_str,
                    author_username=item.author_username,
                    author_display_name=item.author_display_name,
                    posted_at=item.posted_at,
                    collected_at=item.collected_at,
                    url=item.url,
                    language=item.language,
                    metrics=item.metrics,
                    metadata=item.metadata or {},
                    char_count=len(text_str),
                    word_count=len(text_str.split()),
                )
            )
    return ready_posts


def _resolve_analytics_posts(
    posts: Optional[List[AnalyticsReadyPost]] = None,
    raw_posts: Optional[List[RawPostPayload]] = None,
    text: Optional[str] = None,
    quality_service: Optional[DataQualityService] = None,
) -> List[AnalyticsReadyPost]:
    """
    Standardizes request input into a list of quality-validated AnalyticsReadyPost instances.
    """
    quality_svc = quality_service or get_data_quality_service()

    if posts is not None:
        if len(posts) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty post list provided for analysis.",
            )
        for p in posts:
            if not isinstance(p, AnalyticsReadyPost):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid post format: expected AnalyticsReadyPost",
                )
        return posts

    if raw_posts is not None:
        if len(raw_posts) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty post list provided for analysis.",
            )
        normalized = [DataNormalizer.normalize(p) for p in raw_posts]
        batch_result = quality_svc.validate_batch(normalized)
        if batch_result.valid_count == 0 and len(raw_posts) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All submitted raw posts failed data quality validation.",
            )
        return batch_result.valid_posts


    if text is not None and text.strip():
        raw = RawPostPayload(
            platform="api",
            external_id="api_post_1",
            text=text.strip(),
            posted_at=datetime.now(timezone.utc),
        )
        norm = DataNormalizer.normalize(raw)
        res = quality_svc.validate_and_prepare(norm)
        if res.is_valid and res.post:
            return [res.post]
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Text failed data quality validation: {', '.join(res.errors)}",
            )


    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="No post content provided for analysis. Please provide 'posts', 'raw_posts', or 'text'.",
    )


# =====================================================================
# Phase 3 Analytics API Endpoints
# =====================================================================

@router.post(
    "/sentiment",
    response_model=BatchSentimentResult,
    summary="Sentiment Analysis",
    description="Analyzes the polarity and sentiment class of social media posts.",
)
def analyze_sentiment(
    payload: SentimentAnalyzeRequest,
    service: SentimentAnalysisService = Depends(get_sentiment_service),
    quality_service: DataQualityService = Depends(get_quality_service),
) -> BatchSentimentResult:
    try:
        posts = _resolve_analytics_posts(
            posts=payload.posts,
            raw_posts=payload.raw_posts,
            text=payload.text,
            quality_service=quality_service,
        )
        return service.analyze_batch(posts)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error during sentiment analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during sentiment analysis.",
        )


@router.post(
    "/emotion",
    response_model=BatchEmotionResult,
    summary="Emotion Analysis",
    description="Detects primary emotional expressions across 7 discrete emotional states.",
)
def analyze_emotion(
    payload: EmotionAnalyzeRequest,
    service: EmotionAnalysisService = Depends(get_emotion_service),
    quality_service: DataQualityService = Depends(get_quality_service),
) -> BatchEmotionResult:
    try:
        posts = _resolve_analytics_posts(
            posts=payload.posts,
            raw_posts=payload.raw_posts,
            text=payload.text,
            quality_service=quality_service,
        )
        return service.analyze_batch(posts)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error during emotion analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during emotion analysis.",
        )


@router.post(
    "/topics",
    response_model=BatchTopicResult,
    summary="Topic Extraction & Narrative Detection",
    description="Extracts representative keywords, multi-word phrases, and clusters posts into coherent topic groups.",
)
def extract_topics(
    payload: TopicAnalyzeRequest,
    service: TopicAnalysisService = Depends(get_topic_service),
    quality_service: DataQualityService = Depends(get_quality_service),
) -> BatchTopicResult:
    try:
        posts = _resolve_analytics_posts(
            posts=payload.posts,
            raw_posts=payload.raw_posts,
            quality_service=quality_service,
        )
        return service.extract_topics(posts)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error during topic extraction: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during topic extraction.",
        )


@router.post(
    "/trends",
    response_model=BatchTrendResult,
    summary="Trend Detection & Emerging Narrative Analysis",
    description="Evaluates temporal velocity, volume growth rates, statistical spikes, and emerging narratives.",
)
def analyze_trends(
    payload: TrendAnalyzeRequest,
    trend_service: TrendAnalysisService = Depends(get_trend_service),
    topic_service: TopicAnalysisService = Depends(get_topic_service),
    quality_service: DataQualityService = Depends(get_quality_service),
) -> BatchTrendResult:
    try:
        posts = _resolve_analytics_posts(
            posts=payload.posts,
            raw_posts=payload.raw_posts,
            quality_service=quality_service,
        )

        topics = payload.topics
        if not topics:
            topic_result = topic_service.extract_topics(posts)
            topics = topic_result.topics

        duration = timedelta(seconds=payload.window_duration_seconds or 3600)

        return trend_service.analyze_trends(
            topics=topics,
            posts=posts,
            reference_time=payload.reference_time,
            window_duration=duration,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error during trend analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during trend analysis.",
        )


@router.post(
    "/demographics",
    response_model=BatchDemographicResult,
    summary="Demographic Intelligence",
    description="Aggregates demographic distributions across age groups, gender categories, and geographic locations.",
)
def analyze_demographics(
    payload: DemographicAnalyzeRequest,
    service: DemographicAnalysisService = Depends(get_demographic_service),
    quality_service: DataQualityService = Depends(get_quality_service),
) -> BatchDemographicResult:
    try:
        if payload.profiles is not None:
            return service.analyze_batch(
                data=payload.profiles,
                topics=payload.topics,
                sentiment_results=payload.sentiment_results,
                trend_results=payload.trend_results,
            )

        posts = _resolve_analytics_posts(
            posts=payload.posts,
            raw_posts=payload.raw_posts,
            quality_service=quality_service,
        )
        return service.analyze_batch(
            data=posts,
            topics=payload.topics,
            sentiment_results=payload.sentiment_results,
            trend_results=payload.trend_results,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error during demographic analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during demographic analysis.",
        )


@router.post(
    "/analyze",
    response_model=CombinedAnalyticsResponse,
    summary="Unified Multi-Layer Analytics Pipeline",
    description="Orchestrates data quality, sentiment, emotion, topics, trends, and demographics in a single request.",
)
def analyze_all(
    payload: CombinedAnalyzeRequest,
    quality_service: DataQualityService = Depends(get_quality_service),
    sentiment_service: SentimentAnalysisService = Depends(get_sentiment_service),
    emotion_service: EmotionAnalysisService = Depends(get_emotion_service),
    topic_service: TopicAnalysisService = Depends(get_topic_service),
    trend_service: TrendAnalysisService = Depends(get_trend_service),
    demographic_service: DemographicAnalysisService = Depends(get_demographic_service),
) -> CombinedAnalyticsResponse:
    try:
        quality_batch: Optional[BatchDataQualityResult] = None
        ready_posts: List[AnalyticsReadyPost] = []

        if payload.posts is not None:
            if len(payload.posts) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Empty post list provided for analysis.",
                )
            ready_posts = payload.posts
            total_eval = len(ready_posts)
        elif payload.raw_posts is not None:
            if len(payload.raw_posts) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Empty post list provided for analysis.",
                )
            total_eval = len(payload.raw_posts)
            normalized = [DataNormalizer.normalize(p) for p in payload.raw_posts]
            quality_batch = quality_service.validate_batch(normalized)
            ready_posts = quality_batch.valid_posts
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No post content provided for analysis. Please provide 'posts' or 'raw_posts'.",
            )


        # 1. Sentiment
        sentiment_res: Optional[BatchSentimentResult] = None
        if payload.include_sentiment and ready_posts:
            sentiment_res = sentiment_service.analyze_batch(ready_posts)

        # 2. Emotion
        emotion_res: Optional[BatchEmotionResult] = None
        if payload.include_emotion and ready_posts:
            emotion_res = emotion_service.analyze_batch(ready_posts)

        # 3. Topics
        topic_res: Optional[BatchTopicResult] = None
        if payload.include_topics and ready_posts:
            topic_res = topic_service.extract_topics(ready_posts)

        # 4. Trends
        trend_res: Optional[BatchTrendResult] = None
        if payload.include_trends and ready_posts and topic_res and topic_res.topics:
            duration = timedelta(seconds=payload.window_duration_seconds or 3600)
            trend_res = trend_service.analyze_trends(
                topics=topic_res,
                posts=ready_posts,
                reference_time=payload.reference_time,
                window_duration=duration,
            )

        # 5. Demographics
        demo_res: Optional[BatchDemographicResult] = None
        if payload.include_demographics and ready_posts:
            demo_res = demographic_service.analyze_batch(
                data=ready_posts,
                topics=topic_res.topics if topic_res else None,
                sentiment_results=sentiment_res.results if sentiment_res else None,
                trend_results=trend_res.trends if trend_res else None,
            )

        return CombinedAnalyticsResponse(
            total_posts_evaluated=total_eval,
            valid_posts_count=len(ready_posts),
            data_quality=quality_batch,
            sentiment=sentiment_res,
            emotion=emotion_res,
            topics=topic_res,
            trends=trend_res,
            demographics=demo_res,
            analyzed_at=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error during unified analytics execution: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during unified analytics pipeline execution.",
        )


# =====================================================================
# Database-backed GET variants & Network Analysis
# =====================================================================

@router.get(
    "/sentiment",
    response_model=BatchSentimentResult,
    summary="Get Sentiment Analysis for Database Posts",
    description="Retrieves sentiment analysis and distribution for posts stored in the database matching optional filter criteria.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid query filter parameters or date range."},
        422: {"description": "Validation error on parameter type or boundary bounds."},
        500: {"model": ErrorResponse, "description": "Unexpected internal database or service error."},
    },
)
def get_sentiment_analytics(
    platform: Optional[str] = Query(None, description="Filter by platform name"),
    language: Optional[str] = Query(None, description="Filter by language code"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    search: Optional[str] = Query(None, description="Case-insensitive substring search in post text"),
    limit: int = Query(100, ge=1, le=500, description="Max posts to evaluate (1-500)"),
    offset: int = Query(0, ge=0, description="Offset position"),
    db: Session = Depends(get_db),
    service: SentimentAnalysisService = Depends(get_sentiment_service),
) -> BatchSentimentResult:
    try:
        posts = _fetch_db_posts_as_analytics_ready(
            db=db,
            platform=platform,
            language=language,
            start_date=start_date,
            end_date=end_date,
            search=search,
            limit=limit,
            offset=offset,
        )
        return service.analyze_batch(posts)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying sentiment analytics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while computing sentiment analytics.",
        )


@router.get(
    "/trends",
    response_model=BatchTrendResult,
    summary="Get Trend Detection for Database Posts",
    description="Retrieves trend momentum and trajectory analysis for posts stored in the database matching optional filter criteria.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid query filter parameters or date range."},
        422: {"description": "Validation error on parameter type or boundary bounds."},
        500: {"model": ErrorResponse, "description": "Unexpected internal database or service error."},
    },
)
def get_trend_analytics(
    platform: Optional[str] = Query(None, description="Filter by platform name"),
    language: Optional[str] = Query(None, description="Filter by language code"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    search: Optional[str] = Query(None, description="Case-insensitive substring search in post text"),
    window_duration_seconds: int = Query(3600, ge=60, description="Time window duration in seconds"),
    limit: int = Query(100, ge=1, le=500, description="Max posts to evaluate (1-500)"),
    offset: int = Query(0, ge=0, description="Offset position"),
    db: Session = Depends(get_db),
    trend_service: TrendAnalysisService = Depends(get_trend_service),
    topic_service: TopicAnalysisService = Depends(get_topic_service),
) -> BatchTrendResult:
    try:
        posts = _fetch_db_posts_as_analytics_ready(
            db=db,
            platform=platform,
            language=language,
            start_date=start_date,
            end_date=end_date,
            search=search,
            limit=limit,
            offset=offset,
        )
        topic_res = topic_service.extract_topics(posts)
        duration = timedelta(seconds=window_duration_seconds)
        return trend_service.analyze_trends(
            topics=topic_res.topics,
            posts=posts,
            window_duration=duration,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying trend analytics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while computing trend analytics.",
        )


@router.get(
    "/network",
    response_model=BatchNetworkResult,
    summary="Get Network & Influence Analysis for Database Posts",
    description="Retrieves interaction graph, influencer rankings, and domain sharing summary for database posts matching filters.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid query filter parameters or date range."},
        422: {"description": "Validation error on parameter type or boundary bounds."},
        500: {"model": ErrorResponse, "description": "Unexpected internal database or service error."},
    },
)
def get_network_analytics(
    platform: Optional[str] = Query(None, description="Filter by platform name"),
    language: Optional[str] = Query(None, description="Filter by language code"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    search: Optional[str] = Query(None, description="Case-insensitive substring search in post text"),
    limit: int = Query(100, ge=1, le=500, description="Max posts to evaluate (1-500)"),
    offset: int = Query(0, ge=0, description="Offset position"),
    db: Session = Depends(get_db),
    network_service: NetworkAnalysisService = Depends(get_network_service),
) -> BatchNetworkResult:
    try:
        posts = _fetch_db_posts_as_analytics_ready(
            db=db,
            platform=platform,
            language=language,
            start_date=start_date,
            end_date=end_date,
            search=search,
            limit=limit,
            offset=offset,
        )
        return network_service.analyze_batch(posts)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying network analytics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while computing network analytics.",
        )


@router.post(
    "/network",
    response_model=BatchNetworkResult,
    summary="Network & Influence Analysis",
    description="Computes interaction graph structure, node degrees, author influence rankings, and domain sharing.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid payload format or missing content."},
        422: {"description": "Validation error on request body."},
        500: {"model": ErrorResponse, "description": "Unexpected internal error during network analysis."},
    },
)
def analyze_network(
    payload: NetworkAnalyzeRequest,
    network_service: NetworkAnalysisService = Depends(get_network_service),
    quality_service: DataQualityService = Depends(get_quality_service),
) -> BatchNetworkResult:
    try:
        posts = _resolve_analytics_posts(
            posts=payload.posts,
            raw_posts=payload.raw_posts,
            text=payload.text,
            quality_service=quality_service,
        )
        return network_service.analyze_batch(posts)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error during network analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during network analysis.",
        )


# =====================================================================
# Phase 5.5 — Dashboard & Combined Analytics Endpoints
# =====================================================================

@router.get(
    "/overview",
    response_model=DashboardOverviewResponse,
    summary="High-Level Dashboard Overview",
    description="Provides a consolidated dashboard snapshot synthesizing engagement metrics, platform summaries, sentiment analysis, topic clusters, trend momentum, and network influence.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid query filter parameters or date bounds."},
        422: {"description": "Validation error on parameter input types."},
        500: {"model": ErrorResponse, "description": "Unexpected internal database or service error."},
    },
)
def get_dashboard_overview(
    platform: Optional[str] = Query(None, description="Filter by platform name"),
    language: Optional[str] = Query(None, description="Filter by language code"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    search: Optional[str] = Query(None, description="Case-insensitive substring search in post text"),
    limit: int = Query(100, ge=1, le=500, description="Max posts to evaluate for NLP/ML (1-500)"),
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardOverviewResponse:
    validate_date_range(start_date, end_date)
    try:
        return service.get_overview(
            platform=platform,
            language=language,
            start_date=start_date,
            end_date=end_date,
            search=search,
            limit=limit,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating dashboard overview: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating dashboard overview.",
        )


@router.get(
    "/platforms/compare",
    response_model=PlatformComparisonResponse,
    summary="Multi-Platform Comparative Analytics",
    description="Provides cross-platform metrics comparison synthesizing post counts, aggregate engagement, and sentiment distribution.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid date range parameters."},
        422: {"description": "Validation error on parameter types."},
        500: {"model": ErrorResponse, "description": "Unexpected internal database or service error."},
    },
)
def get_platform_comparison(
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    service: DashboardService = Depends(get_dashboard_service),
) -> PlatformComparisonResponse:
    validate_date_range(start_date, end_date)
    try:
        return service.get_platform_comparison(
            start_date=start_date,
            end_date=end_date,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error comparing platforms: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while computing platform comparison.",
        )

