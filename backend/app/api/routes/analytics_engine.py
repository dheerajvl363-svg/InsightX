from datetime import datetime, timezone
import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.analytics_engine import (
    AnalyticsEngineAnalyzeRequest,
    AnalyticsEngineCapabilitiesResponse,
    DetailedEngagementReport,
    DetailedNarrativeReport,
    DetailedSentimentReport,
    DetailedTrendReport,
    IntervalUnit,
    Phase4AnalyticsReport,
    TemporalDynamicsReport,
)
from app.schemas.post import RawPostPayload
from app.services.analytics_engine import (
    AnalyticsEngineService,
    extract_post_timestamp,
    get_analytics_engine_service,
)
from app.services.data_quality import (
    DataQualityService,
    get_data_quality_service,
)
from app.services.normalizer import DataNormalizer

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Analytics Engine"])


def _resolve_and_filter_posts(
    payload: AnalyticsEngineAnalyzeRequest,
    quality_service: DataQualityService,
) -> List[Any]:
    """
    Standardizes input payloads (posts, raw_posts, or ad-hoc text),
    applies temporal bounds, and filters by specified platforms.
    """
    if payload.start_time and payload.end_time and payload.start_time > payload.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_time cannot be after end_time.",
        )

    resolved: List[Any] = []

    if payload.posts is not None:
        if len(payload.posts) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty post list provided for analysis.",
            )
        resolved = list(payload.posts)
    elif payload.raw_posts is not None:
        if len(payload.raw_posts) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty post list provided for analysis.",
            )
        raw_models: List[RawPostPayload] = []
        for p in payload.raw_posts:
            if isinstance(p, RawPostPayload):
                raw_models.append(p)
            elif isinstance(p, dict):
                try:
                    raw_models.append(RawPostPayload.model_validate(p))
                except Exception as e:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Invalid raw post format: {e}",
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid raw post payload type: {type(p).__name__}",
                )
        normalized = [DataNormalizer.normalize(p) for p in raw_models]
        quality_batch = quality_service.validate_batch(normalized)
        if quality_batch.valid_count == 0 and len(payload.raw_posts) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All submitted raw posts failed data quality validation.",
            )
        resolved = list(quality_batch.valid_posts)

    elif payload.text is not None and payload.text.strip():
        raw = RawPostPayload(
            platform="api",
            external_id="api_post_1",
            text=payload.text.strip(),
            posted_at=datetime.now(timezone.utc),
        )
        norm = DataNormalizer.normalize(raw)
        res = quality_service.validate_and_prepare(norm)
        if res.is_valid and res.post:
            resolved = [res.post]
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Text failed data quality validation: {', '.join(res.errors)}",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No post content provided for analysis. Please provide 'posts', 'raw_posts', or 'text'.",
        )

    # Optional temporal window filtering
    if payload.start_time or payload.end_time:
        filtered_temporal: List[Any] = []
        for p in resolved:
            ts = extract_post_timestamp(p)
            if ts is not None:
                if payload.start_time and ts < payload.start_time:
                    continue
                if payload.end_time and ts > payload.end_time:
                    continue
            filtered_temporal.append(p)
        resolved = filtered_temporal

    # Optional platform filtering
    if payload.platform_filter is not None:
        plat_targets = {p.strip().lower() for p in payload.platform_filter if p and p.strip()}
        if plat_targets:
            filtered_platform: List[Any] = []
            for p in resolved:
                plat_val = getattr(p, "platform", None)
                if plat_val is None and isinstance(p, dict):
                    plat_val = p.get("platform")
                if plat_val and str(plat_val).strip().lower() in plat_targets:
                    filtered_platform.append(p)
            resolved = filtered_platform

    return resolved


@router.get(
    "/health",
    summary="Analytics Engine Health Check",
    description="Lightweight health probe verifying analytics engine availability.",
)
def get_engine_health() -> dict:
    """Return operational health status for the Analytics Engine subsystem."""
    return {"status": "ok", "service": "analytics_engine", "version": "4.7.0"}


@router.get(
    "/capabilities",
    response_model=AnalyticsEngineCapabilitiesResponse,
    summary="Analytics Engine Capabilities & Metadata",
    description="Returns metadata on active analytical engines, supported intervals, and capabilities.",
)
def get_engine_capabilities() -> AnalyticsEngineCapabilitiesResponse:
    """Return runtime metadata and supported analytical feature capabilities."""
    return AnalyticsEngineCapabilitiesResponse()


@router.post(
    "/analyze",
    response_model=Phase4AnalyticsReport,
    summary="Unified Multi-Dimensional Analytics Report",
    description=(
        "Executes the full Phase 4 Analytics Engine pipeline synthesizing engagement analytics, "
        "sentiment breakdown, trend momentum, narrative intelligence, and temporal dynamics."
    ),
)
def analyze_comprehensive(
    payload: AnalyticsEngineAnalyzeRequest,
    engine_service: AnalyticsEngineService = Depends(get_analytics_engine_service),
    quality_service: DataQualityService = Depends(get_data_quality_service),
) -> Phase4AnalyticsReport:
    """Run full Phase 4 Analytics Engine pipeline and return comprehensive intelligence report."""
    try:
        posts = _resolve_and_filter_posts(payload=payload, quality_service=quality_service)
        report = engine_service.analyze(
            posts=posts,
            topics=payload.topics,
            interval_unit=payload.interval_unit or IntervalUnit.HOUR,
            reference_time=payload.reference_time,
            rolling_window_size=payload.rolling_window_size or 3,
            anomaly_threshold_z=payload.anomaly_threshold_z or 2.0,
        )

        # Apply optional top_k truncation to ranked lists
        if payload.top_k is not None and payload.top_k > 0:
            if report.detailed_trends and report.detailed_trends.ranked_trends:
                report.detailed_trends.ranked_trends = report.detailed_trends.ranked_trends[:payload.top_k]
            if report.detailed_narratives and report.detailed_narratives.ranked_narratives:
                report.detailed_narratives.ranked_narratives = report.detailed_narratives.ranked_narratives[:payload.top_k]
            if report.narratives:
                report.narratives = report.narratives[:payload.top_k]

        return report
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in analyze_comprehensive: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during analytics engine processing.",
        )


@router.post(
    "/engagement",
    response_model=DetailedEngagementReport,
    summary="Specialized Engagement Analytics",
    description="Computes multi-dimensional engagement profiles, virality indices, discussion depth, and platform breakdowns.",
)
def analyze_engagement(
    payload: AnalyticsEngineAnalyzeRequest,
    engine_service: AnalyticsEngineService = Depends(get_analytics_engine_service),
    quality_service: DataQualityService = Depends(get_data_quality_service),
) -> DetailedEngagementReport:
    """Run specialized engagement analytics engine on target posts."""
    try:
        posts = _resolve_and_filter_posts(payload=payload, quality_service=quality_service)
        return engine_service.engagement_engine.generate_detailed_report(posts)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in analyze_engagement: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during engagement analytics processing.",
        )


@router.post(
    "/sentiment",
    response_model=DetailedSentimentReport,
    summary="Specialized Sentiment Analytics",
    description="Computes polarity distributions, Net Sentiment Score (NSS), temporal sentiment drift, and per-platform sentiment.",
)
def analyze_sentiment(
    payload: AnalyticsEngineAnalyzeRequest,
    engine_service: AnalyticsEngineService = Depends(get_analytics_engine_service),
    quality_service: DataQualityService = Depends(get_data_quality_service),
) -> DetailedSentimentReport:
    """Run specialized sentiment analytics engine on target posts."""
    try:
        posts = _resolve_and_filter_posts(payload=payload, quality_service=quality_service)
        return engine_service.sentiment_engine.generate_detailed_report(
            posts=posts,
            interval_unit=payload.interval_unit or IntervalUnit.HOUR,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in analyze_sentiment: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during sentiment analytics processing.",
        )


@router.post(
    "/trends",
    response_model=DetailedTrendReport,
    summary="Specialized Trend Detection & Momentum",
    description="Detects surging keywords and hashtags with volume velocity, acceleration, momentum scores, and spike anomalies.",
)
def analyze_trends(
    payload: AnalyticsEngineAnalyzeRequest,
    engine_service: AnalyticsEngineService = Depends(get_analytics_engine_service),
    quality_service: DataQualityService = Depends(get_data_quality_service),
) -> DetailedTrendReport:
    """Run specialized trend analytics engine on target posts."""
    try:
        posts = _resolve_and_filter_posts(payload=payload, quality_service=quality_service)
        report = engine_service.trend_engine.generate_detailed_report(
            posts=posts,
            topics=payload.topics,
            reference_time=payload.reference_time,
        )
        if payload.top_k is not None and payload.top_k > 0:
            report.ranked_trends = report.ranked_trends[:payload.top_k]
        return report
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in analyze_trends: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during trend analytics processing.",
        )


@router.post(
    "/narratives",
    response_model=DetailedNarrativeReport,
    summary="Specialized Narrative Intelligence",
    description="Groups cohesive conversation themes, models 6-stage lifecycles, computes narrative impact scores, and tracks sentiment drift.",
)
def analyze_narratives(
    payload: AnalyticsEngineAnalyzeRequest,
    engine_service: AnalyticsEngineService = Depends(get_analytics_engine_service),
    quality_service: DataQualityService = Depends(get_data_quality_service),
) -> DetailedNarrativeReport:
    """Run specialized narrative dynamics engine on target posts."""
    try:
        posts = _resolve_and_filter_posts(payload=payload, quality_service=quality_service)
        report = engine_service.narrative_engine.generate_detailed_report(
            posts=posts,
            topics=payload.topics,
            reference_time=payload.reference_time,
        )
        if payload.top_k is not None and payload.top_k > 0:
            report.ranked_narratives = report.ranked_narratives[:payload.top_k]
        return report
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in analyze_narratives: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during narrative analytics processing.",
        )


@router.post(
    "/time-series",
    response_model=TemporalDynamicsReport,
    summary="Specialized Time-Series Analytics",
    description="Generates discrete temporal buckets with moving averages, velocity, acceleration, baseline comparisons, and anomaly detection.",
)
def analyze_time_series(
    payload: AnalyticsEngineAnalyzeRequest,
    engine_service: AnalyticsEngineService = Depends(get_analytics_engine_service),
    quality_service: DataQualityService = Depends(get_data_quality_service),
) -> TemporalDynamicsReport:
    """Run specialized time-series dynamics engine on target posts."""
    try:
        posts = _resolve_and_filter_posts(payload=payload, quality_service=quality_service)
        return engine_service.time_series_engine.generate_time_series(
            posts=posts,
            interval_unit=payload.interval_unit or IntervalUnit.HOUR,
            rolling_window_size=payload.rolling_window_size or 3,
            anomaly_threshold_z=payload.anomaly_threshold_z or 2.0,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in analyze_time_series: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during time-series analytics processing.",
        )
