"""
Phase 5.5 — Dashboard & Combined Analytics Schemas.

Provides Pydantic response models for consolidated dashboard overview snapshots
and multi-platform comparison analytics.
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.analytics import EngagementSummary, PlatformSummary
from app.schemas.network import BatchNetworkResult
from app.schemas.sentiment import BatchSentimentResult
from app.schemas.topic import BatchTopicResult
from app.schemas.trend import BatchTrendResult


class DashboardOverviewResponse(BaseModel):
    """
    Unified high-level dashboard overview snapshot composed from multi-layer analytics.
    """

    total_posts: int = Field(..., ge=0, description="Total posts matching filter criteria")
    engagement_summary: Optional[EngagementSummary] = Field(
        default=None, description="Aggregate engagement summary metrics"
    )
    platforms: List[PlatformSummary] = Field(
        default_factory=list, description="Per-platform aggregate post count and time bounds"
    )
    sentiment: Optional[BatchSentimentResult] = Field(
        default=None, description="Batch sentiment analysis outcome"
    )
    topics: Optional[BatchTopicResult] = Field(
        default=None, description="Topic clusters extracted from filtered dataset"
    )
    trends: Optional[BatchTrendResult] = Field(
        default=None, description="Trend trajectory and velocity analysis"
    )
    network: Optional[BatchNetworkResult] = Field(
        default=None, description="Interaction graph and author influence summary"
    )
    generated_at: datetime = Field(..., description="Snapshot generation timestamp in UTC")

    model_config = ConfigDict(from_attributes=True)


class PlatformComparisonItem(BaseModel):
    """Platform-level comparative metrics summary."""

    platform: str = Field(..., description="Canonical platform name")
    post_count: int = Field(..., ge=0, description="Total posts for this platform")
    total_likes: int = Field(default=0, ge=0, description="Total likes")
    total_comments: int = Field(default=0, ge=0, description="Total comments")
    total_shares: int = Field(default=0, ge=0, description="Total shares")
    total_views: int = Field(default=0, ge=0, description="Total views")
    avg_engagement: float = Field(default=0.0, ge=0.0, description="Average engagement per post")
    sentiment_breakdown: Dict[str, int] = Field(
        default_factory=dict, description="Sentiment class counts for this platform"
    )

    model_config = ConfigDict(from_attributes=True)


class PlatformComparisonResponse(BaseModel):
    """Response payload for multi-platform comparative analytics."""

    total_platforms: int = Field(..., ge=0, description="Count of platforms evaluated")
    platforms: List[PlatformComparisonItem] = Field(
        default_factory=list, description="Itemized platform metrics"
    )
    generated_at: datetime = Field(..., description="Report generation timestamp in UTC")

    model_config = ConfigDict(from_attributes=True)
