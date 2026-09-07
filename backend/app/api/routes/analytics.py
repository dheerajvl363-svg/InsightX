from datetime import datetime
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.analytics import (
    CountResponse,
    EngagementSummary,
    LanguageSummary,
    PlatformSummary,
    PostListResponse,
    TimeSeriesResponse,
)
from app.services.analytics import AnalyticsService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Analytics"])


def validate_date_range(start: Optional[datetime], end: Optional[datetime]):
    """Helper to ensure start_date <= end_date."""
    if start and end and start > end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date cannot be after end_date.",
        )


@router.get(
    "/posts",
    response_model=PostListResponse,
    summary="Query posts for analytics & NLP",
    description="Returns paginated posts with deterministic ordering and optional search, platform, language, author, and date filters.",
)
def get_posts(
    platform: Optional[str] = Query(None, description="Filter by platform name (e.g. 'X', 'Telegram')"),
    language: Optional[str] = Query(None, description="Filter by lowercase language code (e.g. 'en', 'hi', 'te')"),
    start_date: Optional[datetime] = Query(None, description="Filter posts on or after this timestamp"),
    end_date: Optional[datetime] = Query(None, description="Filter posts on or before this timestamp"),
    author: Optional[str] = Query(None, description="Filter by author username/handle"),
    search: Optional[str] = Query(None, description="Case-insensitive substring search in post text"),
    limit: int = Query(50, ge=1, le=200, description="Max posts to return (1-200)"),
    offset: int = Query(0, ge=0, description="Offset position for pagination"),
    db: Session = Depends(get_db),
) -> PostListResponse:
    validate_date_range(start_date, end_date)
    try:
        service = AnalyticsService(db)
        return service.get_posts(
            platform=platform,
            language=language,
            start_time=start_date,
            end_time=end_date,
            author_username=author,
            search=search,
            limit=limit,
            offset=offset,
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
