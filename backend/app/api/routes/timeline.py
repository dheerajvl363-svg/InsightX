from datetime import datetime
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import ErrorResponse
from app.schemas.timeline import TimelineResponse
from app.services.analytics import AnalyticsService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Timeline"])


def validate_date_range(start: Optional[datetime], end: Optional[datetime]):
    if start and end and start > end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date cannot be after end_date.",
        )


@router.get(
    "",
    response_model=TimelineResponse,
    summary="Get Time-Bucketed Post Timeline",
    description="Computes post activity volume and per-platform distribution aggregated chronologically into time buckets ('hour', 'day', 'week').",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid date range bounds or granularity string."},
        422: {"description": "Validation error on query parameter types."},
        500: {"model": ErrorResponse, "description": "Unexpected internal database or service error."},
    },
)
def get_timeline(
    platform: Optional[str] = Query(None, description="Filter by platform name"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    granularity: Optional[str] = Query("day", description="Aggregation time window ('hour', 'day', 'week')"),
    db: Session = Depends(get_db),
) -> TimelineResponse:
    validate_date_range(start_date, end_date)
    clean_granularity = (granularity or "day").strip().lower()
    if clean_granularity not in {"hour", "day", "week"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid granularity '{granularity}'. Supported values: 'hour', 'day', 'week'.",
        )

    try:
        service = AnalyticsService(db)
        return service.get_timeline(
            platform=platform,
            start_time=start_date,
            end_time=end_date,
            granularity=clean_granularity,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error computing timeline: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while computing timeline analytics.",
        )
