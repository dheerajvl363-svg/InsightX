from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.post import PostMetricsSchema


class PostSummary(BaseModel):
    """Clean, structured representation of a post for analytics and downstream ML/NLP."""
    id: int = Field(..., description="Internal post primary key")
    platform: str = Field(..., description="Canonical platform name")
    external_post_id: str = Field(..., description="Platform-level post ID")
    text: Optional[str] = Field(default=None, description="Cleaned text content")
    author_username: Optional[str] = Field(default=None, description="Author username/handle")
    author_display_name: Optional[str] = Field(default=None, description="Author display name")
    posted_at: datetime = Field(..., description="Creation timestamp in UTC")
    collected_at: datetime = Field(..., description="Ingestion timestamp in UTC")
    url: Optional[str] = Field(default=None, description="Direct URL")
    language: Optional[str] = Field(default=None, description="Language code")
    metrics: Optional[PostMetricsSchema] = Field(default=None, description="Latest engagement metrics")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata dictionary")

    model_config = ConfigDict(from_attributes=True)


class PostListResponse(BaseModel):
    """Paginated list of posts matching query filters."""
    total: int = Field(..., description="Total posts matching filter criteria")
    limit: int = Field(..., description="Maximum records returned in this page")
    offset: int = Field(..., description="Offset position")
    items: List[PostSummary] = Field(default_factory=list, description="List of post records")


class CountResponse(BaseModel):
    """Count of posts matching applied filters."""
    count: int = Field(..., description="Count of matching posts")
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="Summary of applied filters")


class PlatformSummary(BaseModel):
    """Aggregate analytics summary for a specific platform."""
    platform: str = Field(..., description="Platform name")
    post_count: int = Field(..., description="Total posts stored for this platform")
    earliest_post: Optional[datetime] = Field(default=None, description="Earliest post timestamp")
    latest_post: Optional[datetime] = Field(default=None, description="Latest post timestamp")


class LanguageSummary(BaseModel):
    """Aggregate post count by language."""
    language: str = Field(..., description="Language code or 'unspecified'")
    post_count: int = Field(..., description="Number of posts in this language")


class EngagementSummary(BaseModel):
    """Aggregated engagement metrics across posts matching filters."""
    total_posts_analyzed: int = Field(..., description="Total posts evaluated")
    posts_with_metrics: int = Field(..., description="Posts having engagement data")
    total_likes: int = Field(default=0, description="Sum of likes")
    total_comments: int = Field(default=0, description="Sum of comments/replies")
    total_shares: int = Field(default=0, description="Sum of shares/retweets")
    total_views: int = Field(default=0, description="Sum of views/impressions")
    avg_likes: float = Field(default=0.0, description="Average likes per post")
    avg_comments: float = Field(default=0.0, description="Average comments per post")
    avg_shares: float = Field(default=0.0, description="Average shares per post")
    avg_views: float = Field(default=0.0, description="Average views per post")


class TimeSeriesPoint(BaseModel):
    """Single point in a time-series aggregation."""
    date: str = Field(..., description="Date string in YYYY-MM-DD format")
    count: int = Field(..., description="Number of posts created on this date")


class TimeSeriesResponse(BaseModel):
    """Time-series aggregation response."""
    interval: str = Field(default="day", description="Grouping interval")
    total_points: int = Field(..., description="Number of data points")
    points: List[TimeSeriesPoint] = Field(default_factory=list, description="Chronological series points")
