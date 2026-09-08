from datetime import datetime
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.analytics import PostListResponse, PostSummary
from app.schemas.common import ErrorResponse
from app.services.analytics import AnalyticsService, ALLOWED_SORT_BY

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Posts"])


def validate_date_range(start: Optional[datetime], end: Optional[datetime]):
    if start and end and start > end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date cannot be after end_date.",
        )


@router.get(
    "",
    response_model=PostListResponse,
    summary="List Social Media Posts",
    description="Returns a paginated list of social media posts matching optional platform, date range, search, author, metric, and sorting criteria.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid query filter parameters or date bounds."},
        422: {"description": "Validation error on input parameter types or boundaries."},
        500: {"model": ErrorResponse, "description": "Unexpected internal database or service error."},
    },
)
def get_posts(
    platform: Optional[str] = Query(None, description="Filter by platform name"),
    language: Optional[str] = Query(None, description="Filter by language code"),
    start_date: Optional[datetime] = Query(None, description="Filter posts created on or after this timestamp"),
    end_date: Optional[datetime] = Query(None, description="Filter posts created on or before this timestamp"),
    author: Optional[str] = Query(None, description="Filter by author username"),
    search: Optional[str] = Query(None, description="Case-insensitive substring search in post text"),
    min_likes: Optional[int] = Query(None, ge=0, description="Minimum likes metric filter"),
    min_comments: Optional[int] = Query(None, ge=0, description="Minimum comments metric filter"),
    min_shares: Optional[int] = Query(None, ge=0, description="Minimum shares metric filter"),
    min_views: Optional[int] = Query(None, ge=0, description="Minimum views metric filter"),
    sort_by: Optional[str] = Query("posted_at", description="Field to sort by ('posted_at', 'likes', 'comments', 'shares', 'views')"),
    order: Optional[str] = Query("desc", description="Sort order ('asc' or 'desc')"),
    limit: int = Query(50, ge=1, le=200, description="Max posts to return per page (1-200)"),
    offset: int = Query(0, ge=0, description="Offset position for pagination"),
    db: Session = Depends(get_db),
) -> PostListResponse:
    validate_date_range(start_date, end_date)
    clean_sort_by = (sort_by or "posted_at").strip().lower()
    if clean_sort_by not in ALLOWED_SORT_BY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort_by field '{sort_by}'. Supported fields: {', '.join(sorted(ALLOWED_SORT_BY))}.",
        )
    clean_order = (order or "desc").strip().lower()
    if clean_order not in {"asc", "desc"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid order '{order}'. Supported orders: 'asc', 'desc'.",
        )

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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying posts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while querying posts.",
        )



@router.get(
    "/{post_id}",
    response_model=PostSummary,
    summary="Get Single Post by ID",
    description="Retrieves a single social media post record by its internal database primary key.",
    responses={
        404: {"model": ErrorResponse, "description": "Post not found for the given post_id."},
        500: {"model": ErrorResponse, "description": "Unexpected internal database or service error."},
    },
)
def get_post_by_id(
    post_id: int = Path(..., description="Internal post primary key ID", ge=1),
    db: Session = Depends(get_db),
) -> PostSummary:
    try:
        service = AnalyticsService(db)
        post = service.get_post_by_id(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post with ID {post_id} not found.",
            )
        return post
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving post {post_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving post details.",
        )
