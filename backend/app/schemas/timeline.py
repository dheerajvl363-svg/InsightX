"""
Phase 5.4 — Timeline API Schemas.

Provides Pydantic schemas for time-bucketed activity aggregation in API responses.
"""

from datetime import datetime
from typing import Dict, List
from pydantic import BaseModel, ConfigDict, Field


class TimelineBucket(BaseModel):
    """Single time bucket representation in timeline aggregation."""

    timestamp: datetime = Field(..., description="Bucket start timestamp in UTC")
    count: int = Field(..., ge=0, description="Total post count in this time bucket")
    platform_breakdown: Dict[str, int] = Field(
        default_factory=dict, description="Post count breakdown by platform"
    )

    model_config = ConfigDict(from_attributes=True)


class TimelineResponse(BaseModel):
    """Time-bucketed post activity response."""

    granularity: str = Field(..., description="Time aggregation granularity ('hour', 'day', 'week')")
    total_buckets: int = Field(..., ge=0, description="Total buckets returned")
    total_posts: int = Field(..., ge=0, description="Total posts aggregated across buckets")
    buckets: List[TimelineBucket] = Field(
        default_factory=list, description="Chronological time buckets"
    )

    model_config = ConfigDict(from_attributes=True)
