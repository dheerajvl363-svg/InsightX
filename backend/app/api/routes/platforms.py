import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.platform import PlatformResponse
from app.services.analytics import AnalyticsService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Platforms"])


@router.get(
    "",
    response_model=List[PlatformResponse],
    summary="List Registered Platforms",
    description="Returns list of canonical platform definitions registered in InsightX.",
)
def get_platforms(
    db: Session = Depends(get_db),
) -> List[PlatformResponse]:
    try:
        service = AnalyticsService(db)
        return service.get_platforms_list()
    except Exception as e:
        logger.error(f"Error listing platforms: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving platform list.",
        )
