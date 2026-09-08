from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class IntervalUnit(str, Enum):
    """Supported temporal interval granularity for time-series aggregation."""
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"


class NarrativeLifecycleStage(str, Enum):
    """Lifecycle trajectory states for evolving discussion themes and narratives."""
    EMERGING = "emerging"
    ACCELERATING = "accelerating"
    PEAK = "peak"
    SUSTAINED = "sustained"
    DECAYING = "decaying"
    DORMANT = "dormant"


class EngagementScoreBreakdown(BaseModel):
    """Detailed multi-metric engagement profile with virality and depth metrics."""
    total_posts: int = Field(default=0, ge=0, description="Total number of posts in sample")
    total_likes: int = Field(default=0, ge=0, description="Cumulative like count")
    total_comments: int = Field(default=0, ge=0, description="Cumulative comment count")
    total_shares: int = Field(default=0, ge=0, description="Cumulative share/repost count")
    total_views: int = Field(default=0, ge=0, description="Cumulative impression/view count")
    weighted_engagement_score: float = Field(
        default=0.0,
        ge=0.0,
        description="Weighted engagement score: likes*1.0 + comments*2.0 + shares*3.0"
    )
    virality_index: float = Field(
        default=0.0,
        ge=0.0,
        description="Virality ratio: shares / max(likes, 1)"
    )
    discussion_depth: float = Field(
        default=0.0,
        ge=0.0,
        description="Discussion depth ratio: comments / max(likes, 1)"
    )
    engagement_rate_per_impression: float = Field(
        default=0.0,
        ge=0.0,
        description="Total interactions per impression: (likes+comments+shares) / max(views, 1)"
    )
    average_post_engagement: float = Field(
        default=0.0,
        ge=0.0,
        description="Average weighted engagement per post"
    )

    model_config = ConfigDict(from_attributes=True)


class TimeSeriesBucket(BaseModel):
    """Single discrete interval bucket within a temporal time-series aggregation."""
    bucket_start: datetime = Field(..., description="Start timestamp of the bucket window (inclusive, UTC)")
    bucket_end: datetime = Field(..., description="End timestamp of the bucket window (exclusive, UTC)")
    post_count: int = Field(default=0, ge=0, description="Number of posts published in interval")
    engagement_score: float = Field(default=0.0, ge=0.0, description="Weighted engagement score in interval")
    total_likes: int = Field(default=0, ge=0, description="Likes within interval")
    total_comments: int = Field(default=0, ge=0, description="Comments within interval")
    total_shares: int = Field(default=0, ge=0, description="Shares within interval")
    total_views: int = Field(default=0, ge=0, description="Views within interval")
    avg_sentiment_polarity: Optional[float] = Field(
        default=None,
        description="Mean sentiment polarity score [-1.0, 1.0] for posts in interval"
    )
    dominant_sentiment: Optional[str] = Field(default=None, description="Most frequent sentiment in interval")
    dominant_emotion: Optional[str] = Field(default=None, description="Most frequent emotion in interval")
    rolling_post_count_avg: Optional[float] = Field(
        default=None,
        description="k-period rolling average of post count"
    )
    rolling_engagement_avg: Optional[float] = Field(
        default=None,
        description="k-period rolling average of weighted engagement"
    )
    is_anomaly: bool = Field(
        default=False,
        description="Flag indicating if volume or engagement is a statistical anomaly"
    )
    anomaly_score: Optional[float] = Field(
        default=0.0,
        description="Standard deviation z-score relative to baseline distribution"
    )

    model_config = ConfigDict(from_attributes=True)


class TemporalDynamicsReport(BaseModel):
    """Comprehensive time-series aggregation report across configured granularity."""
    interval_unit: IntervalUnit = Field(default=IntervalUnit.HOUR, description="Granularity interval")
    total_buckets: int = Field(..., ge=0, description="Total discrete interval buckets")
    start_time: Optional[datetime] = Field(default=None, description="Earliest timestamp in time series")
    end_time: Optional[datetime] = Field(default=None, description="Latest timestamp in time series")
    buckets: List[TimeSeriesBucket] = Field(default_factory=list, description="Ordered time buckets")
    peak_bucket_start: Optional[datetime] = Field(default=None, description="Timestamp of highest volume bucket")
    peak_bucket_volume: int = Field(default=0, ge=0, description="Maximum post volume in any single bucket")
    peak_bucket_engagement: float = Field(default=0.0, ge=0.0, description="Maximum engagement in any single bucket")
    anomalous_intervals_count: int = Field(default=0, ge=0, description="Number of anomalous interval spikes")

    model_config = ConfigDict(from_attributes=True)


class NarrativeTrajectoryMetrics(BaseModel):
    """Velocity, acceleration, and sentiment shift metrics for topic lifecycle determination."""
    current_volume: int = Field(default=0, ge=0, description="Post volume in current observation period")
    previous_volume: int = Field(default=0, ge=0, description="Post volume in preceding baseline period")
    volume_velocity: float = Field(
        default=0.0,
        description="Rate of post generation change (current_volume - previous_volume)"
    )
    volume_acceleration: float = Field(
        default=0.0,
        description="Rate of velocity change (velocity_diff / time_factor)"
    )
    engagement_velocity: float = Field(
        default=0.0,
        description="Rate of engagement accumulation"
    )
    sentiment_drift: float = Field(
        default=0.0,
        description="Shift in mean sentiment polarity between periods (current - previous)"
    )
    stage: NarrativeLifecycleStage = Field(
        default=NarrativeLifecycleStage.EMERGING,
        description="Categorized lifecycle stage"
    )

    model_config = ConfigDict(from_attributes=True)


class NarrativeIntelligence(BaseModel):
    """Structured narrative intelligence unit combining topics, lifecycle, and dynamics."""
    topic_id: str = Field(..., description="Unique topic or cluster identifier")
    label: str = Field(..., description="Descriptive label or dominant headline")
    keywords: List[str] = Field(default_factory=list, description="Associated characteristic keywords")
    first_seen: Optional[datetime] = Field(default=None, description="Earliest post timestamp for topic")
    last_seen: Optional[datetime] = Field(default=None, description="Most recent post timestamp for topic")
    post_count: int = Field(default=0, ge=0, description="Total posts associated with topic")
    lifecycle_stage: NarrativeLifecycleStage = Field(
        default=NarrativeLifecycleStage.EMERGING,
        description="Current narrative lifecycle status"
    )
    trajectory: NarrativeTrajectoryMetrics = Field(
        default_factory=NarrativeTrajectoryMetrics,
        description="Dynamic velocity and acceleration statistics"
    )
    dominant_sentiment: Optional[str] = Field(default=None, description="Dominant sentiment polarity")
    dominant_emotion: Optional[str] = Field(default=None, description="Dominant emotional profile")
    sample_post_ids: List[str] = Field(default_factory=list, description="IDs of representative posts")

    model_config = ConfigDict(from_attributes=True)


class Phase4AnalyticsReport(BaseModel):
    """Comprehensive high-level analytical intelligence report produced by Phase 4 Engine."""
    total_posts_evaluated: int = Field(..., ge=0, description="Number of posts evaluated")
    analyzed_at: datetime = Field(..., description="Analysis execution timestamp in UTC")
    time_window_start: Optional[datetime] = Field(default=None, description="Earliest post timestamp")
    time_window_end: Optional[datetime] = Field(default=None, description="Latest post timestamp")
    engagement_analytics: EngagementScoreBreakdown = Field(
        ...,
        description="Aggregated engagement metrics and virality indices"
    )
    temporal_dynamics: TemporalDynamicsReport = Field(
        ...,
        description="Temporal interval distributions and rolling metrics"
    )
    narratives: List[NarrativeIntelligence] = Field(
        default_factory=list,
        description="Narrative lifecycle tracking and trajectory modeling"
    )
    platform_breakdown: Dict[str, EngagementScoreBreakdown] = Field(
        default_factory=dict,
        description="Per-platform engagement and virality breakdowns"
    )
    summary_insights: List[str] = Field(
        default_factory=list,
        description="Actionable intelligence bullet points generated by the engine"
    )

    model_config = ConfigDict(from_attributes=True)
