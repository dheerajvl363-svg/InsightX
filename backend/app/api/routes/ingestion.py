from datetime import datetime, timezone
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.platform import Platform
from app.schemas.platform import PlatformResponse
from app.schemas.post import (
    BatchIngestionResponse,
    IngestionResponse,
    NormalizedPost,
    RawPostPayload,
)
from app.services.ingestion import IngestionService
from app.services.normalizer import DataNormalizer

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Ingestion"])


@router.post(
    "/posts",
    response_model=IngestionResponse,
    summary="Ingest a single social media post",
    description="Validates, normalizes, and stores a single social media post. Handles duplicates safely.",
)
def ingest_single_post(
    payload: RawPostPayload,
    response: Response,
    db: Session = Depends(get_db),
) -> IngestionResponse:
    """
    Ingests one raw social-media post payload:
    1. Validates payload via RawPostPayload.
    2. Normalizes structure, platform name, text, and timestamps.
    3. Persists record in PostgreSQL with deduplication check.
    4. Returns IngestionResponse (HTTP 201 for new post, HTTP 200 for duplicate).
    """
    try:
        normalized = DataNormalizer.normalize(payload)
        service = IngestionService(db)
        result = service.ingest_post(normalized)

        # Set HTTP status code: 201 Created for new posts, 200 OK for duplicates
        if result.is_duplicate:
            response.status_code = status.HTTP_200_OK
        else:
            response.status_code = status.HTTP_201_CREATED

        return result

    except ValueError as val_err:
        logger.warning(f"Validation error during ingestion: {val_err}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception as exc:
        logger.error(f"Unexpected error ingesting post: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while ingesting the post.",
        )


@router.post(
    "/posts/batch",
    response_model=BatchIngestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest a batch of social media posts",
    description="Validates, normalizes, and batch-stores multiple social media posts transactionally with savepoints.",
)
def ingest_batch_posts(
    payloads: List[Dict[str, Any]],
    db: Session = Depends(get_db),
) -> BatchIngestionResponse:
    """
    Ingests multiple social-media posts:
    1. Validates each incoming record against RawPostPayload individually.
    2. Normalizes valid payloads via DataNormalizer.
    3. Any validation or normalization failure is isolated and recorded as a failed item.
    4. Valid posts are batch-persisted via IngestionService.ingest_batch().
    5. Returns aggregate counts: total_received, successful, duplicates, and failed.
    """
    if not payloads:
        return BatchIngestionResponse(
            total_received=0,
            successful=0,
            duplicates=0,
            failed=0,
            results=[],
        )

    normalized_posts: List[NormalizedPost] = []
    pre_failed_results: List[IngestionResponse] = []

    for raw_item in payloads:
        try:
            # 1. Pydantic validation per record
            validated = RawPostPayload.model_validate(raw_item)
            # 2. Normalization
            normalized = DataNormalizer.normalize(validated)
            normalized_posts.append(normalized)
        except (ValidationError, ValueError) as val_err:
            ext_id = str(raw_item.get("external_id") or raw_item.get("id") or "unknown")
            platform_name = str(raw_item.get("platform") or "unknown")
            logger.warning(f"Validation failed for batch record {ext_id}: {val_err}")
            pre_failed_results.append(
                IngestionResponse(
                    status="failed",
                    post_id=None,
                    external_post_id=ext_id,
                    platform=platform_name,
                    is_duplicate=False,
                    message=f"Validation failed: {str(val_err)}",
                    collected_at=datetime.now(timezone.utc),
                )
            )
        except Exception as norm_err:
            ext_id = str(raw_item.get("external_id") or raw_item.get("id") or "unknown")
            platform_name = str(raw_item.get("platform") or "unknown")
            logger.warning(f"Normalization failed for batch record {ext_id}: {norm_err}")
            pre_failed_results.append(
                IngestionResponse(
                    status="failed",
                    post_id=None,
                    external_post_id=ext_id,
                    platform=platform_name,
                    is_duplicate=False,
                    message=f"Normalization failed: {str(norm_err)}",
                    collected_at=datetime.now(timezone.utc),
                )
            )

    service = IngestionService(db)
    batch_result = service.ingest_batch(normalized_posts)

    # Combine with any pre-validation/normalization failures
    total_received = len(payloads)
    total_failed = batch_result.failed + len(pre_failed_results)
    combined_results = batch_result.results + pre_failed_results

    return BatchIngestionResponse(
        total_received=total_received,
        successful=batch_result.successful,
        duplicates=batch_result.duplicates,
        failed=total_failed,
        results=combined_results,
    )


@router.get(
    "/platforms",
    response_model=List[PlatformResponse],
    status_code=status.HTTP_200_OK,
    summary="List all registered platforms",
    description="Returns all social media platforms currently registered in PostgreSQL.",
)
def list_platforms(db: Session = Depends(get_db)) -> List[PlatformResponse]:
    """
    Returns the list of currently registered platforms.
    """
    platforms = db.query(Platform).order_by(Platform.id).all()
    return platforms
