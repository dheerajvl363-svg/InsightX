from datetime import datetime
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
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
from app.services.analytics import AnalyticsService

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


def validate_sort_params(sort_by: Optional[str], order: Optional[str]) -> tuple[str, str]:
    """Helper to validate sort_by and order query parameters."""
    clean_sort_by = (sort_by or "posted_at").strip().lower()
    if clean_sort_by not in ALLOWED_SORT_BY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort_by field '{sort_by}'. Supported fields: {', '.join(sorted(ALLOWED_SORT_BY))}.",
        )

    clean_order = (order or "desc").strip().lower()
    if clean_order not in ALLOWED_ORDER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid order '{order}'. Supported orders: {', '.join(sorted(ALLOWED_ORDER))}.",
        )

    return clean_sort_by, clean_order


def validate_author_sort_params(sort_by: Optional[str], order: Optional[str]) -> tuple[str, str]:
    """Helper to validate author sort_by and order query parameters."""
    clean_sort_by = (sort_by or "post_count").strip().lower()
    if clean_sort_by not in ALLOWED_AUTHOR_SORT_BY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort_by field '{sort_by}'. Supported fields: {', '.join(sorted(ALLOWED_AUTHOR_SORT_BY))}.",
        )

    clean_order = (order or "desc").strip().lower()
    if clean_order not in ALLOWED_ORDER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid order '{order}'. Supported orders: {', '.join(sorted(ALLOWED_ORDER))}.",
        )

    return clean_sort_by, clean_order


def validate_topic_sort_params(sort_by: Optional[str], order: Optional[str]) -> tuple[str, str]:
    """Helper to validate topic sort_by and order query parameters."""
    clean_sort_by = (sort_by or "post_count").strip().lower()
    if clean_sort_by not in ALLOWED_TOPIC_SORT_BY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort_by field '{sort_by}'. Supported fields: {', '.join(sorted(ALLOWED_TOPIC_SORT_BY))}.",
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
    clean_sort_by, clean_order = validate_sort_params(sort_by, order)
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
    clean_sort_by, clean_order = validate_author_sort_params(sort_by, order)
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
    clean_sort_by, clean_order = validate_topic_sort_params(sort_by, order)
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
