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


class NarrativePlatformDistribution(BaseModel):
    """Platform-specific representation and engagement within a narrative."""
    platform: str = Field(..., description="Platform identifier")
    post_count: int = Field(default=0, ge=0, description="Posts on platform for this narrative")
    engagement_score: float = Field(default=0.0, ge=0.0, description="Total weighted engagement on platform")
    avg_sentiment_polarity: Optional[float] = Field(default=None, description="Mean sentiment polarity on platform")
    share_percentage: float = Field(default=0.0, ge=0.0, description="Percentage share of total narrative posts")

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
    total_engagement: float = Field(default=0.0, ge=0.0, description="Cumulative weighted engagement across narrative")
    avg_post_engagement: float = Field(default=0.0, ge=0.0, description="Average weighted engagement per narrative post")
    virality_index: float = Field(default=0.0, ge=0.0, description="Virality ratio across narrative")
    avg_sentiment_polarity: float = Field(default=0.0, description="Mean sentiment polarity across narrative posts")
    net_sentiment_score: float = Field(default=0.0, description="Net sentiment score (Pos - Neg) / Total")
    positive_percentage: float = Field(default=0.0, ge=0.0, description="Percentage of positive posts in narrative")
    negative_percentage: float = Field(default=0.0, ge=0.0, description="Percentage of negative posts in narrative")
    neutral_percentage: float = Field(default=0.0, ge=0.0, description="Percentage of neutral posts in narrative")
    narrative_impact_score: float = Field(
        default=0.0,
        ge=0.0,
        description="Multi-factor impact score combining volume, velocity, engagement, and sentiment intensity"
    )
    platforms: List[str] = Field(default_factory=list, description="Platforms carrying this narrative")
    platform_breakdown: Dict[str, NarrativePlatformDistribution] = Field(
        default_factory=dict,
        description="Per-platform narrative distributions"
    )
    sample_post_ids: List[str] = Field(default_factory=list, description="IDs of representative posts")

    model_config = ConfigDict(from_attributes=True)


class EngagementDistribution(BaseModel):
    """Statistical distribution summary of weighted engagement scores across posts."""
    min_engagement: float = Field(default=0.0, ge=0.0, description="Minimum post engagement score")
    max_engagement: float = Field(default=0.0, ge=0.0, description="Maximum post engagement score")
    mean_engagement: float = Field(default=0.0, ge=0.0, description="Arithmetic mean engagement score")
    median_engagement: float = Field(default=0.0, ge=0.0, description="Median engagement score")
    std_dev_engagement: float = Field(default=0.0, ge=0.0, description="Standard deviation of engagement scores")
    p25: float = Field(default=0.0, ge=0.0, description="25th percentile (Q1) engagement score")
    p75: float = Field(default=0.0, ge=0.0, description="75th percentile (Q3) engagement score")

    model_config = ConfigDict(from_attributes=True)


class PostEngagementProfile(BaseModel):
    """Individual post engagement scorecard and outlier flag."""
    post_id: str = Field(..., description="Unique post identifier")
    platform: str = Field(..., description="Publishing platform")
    likes: int = Field(default=0, ge=0, description="Likes count")
    comments: int = Field(default=0, ge=0, description="Comments count")
    shares: int = Field(default=0, ge=0, description="Shares count")
    views: int = Field(default=0, ge=0, description="Views count")
    weighted_score: float = Field(default=0.0, ge=0.0, description="Calculated weighted engagement score")
    virality_score: float = Field(default=0.0, ge=0.0, description="Post virality ratio (shares / max(likes, 1))")
    discussion_depth: float = Field(default=0.0, ge=0.0, description="Post discussion depth (comments / max(likes, 1))")
    engagement_rate: float = Field(default=0.0, ge=0.0, description="Interactions per view (if views > 0)")
    is_outlier: bool = Field(default=False, description="Flag indicating statistically high outlier engagement")

    model_config = ConfigDict(from_attributes=True)


class ViralityAnalytics(BaseModel):
    """Detailed virality and content amplification analytics."""
    virality_index: float = Field(default=0.0, ge=0.0, description="Aggregate virality ratio (shares / max(likes, 1))")
    amplification_rate: float = Field(
        default=0.0,
        ge=0.0,
        description="Share of total interactions that are shares: shares / max(likes+comments+shares, 1)"
    )
    shares_per_post: float = Field(default=0.0, ge=0.0, description="Average shares generated per post")
    high_virality_posts_count: int = Field(default=0, ge=0, description="Count of posts with virality ratio > 0.5")

    model_config = ConfigDict(from_attributes=True)


class DiscussionDepthAnalytics(BaseModel):
    """Detailed conversational depth and community engagement analytics."""
    discussion_depth: float = Field(default=0.0, ge=0.0, description="Aggregate discussion depth (comments / max(likes, 1))")
    conversation_rate: float = Field(
        default=0.0,
        ge=0.0,
        description="Share of total interactions that are comments: comments / max(likes+comments+shares, 1)"
    )
    comments_per_post: float = Field(default=0.0, ge=0.0, description="Average comments generated per post")
    high_discussion_posts_count: int = Field(default=0, ge=0, description="Count of posts with discussion depth > 0.5")

    model_config = ConfigDict(from_attributes=True)


class PlatformEngagementComparison(BaseModel):
    """Comparative engagement profile for a single social platform."""
    platform: str = Field(..., description="Platform name")
    total_posts: int = Field(default=0, ge=0, description="Total posts published on platform")
    post_share_pct: float = Field(default=0.0, ge=0.0, le=100.0, description="Platform share of total post volume (%)")
    engagement_share_pct: float = Field(default=0.0, ge=0.0, le=100.0, description="Platform share of total engagement (%)")
    weighted_engagement_score: float = Field(default=0.0, ge=0.0, description="Total weighted engagement on platform")
    avg_engagement_per_post: float = Field(default=0.0, ge=0.0, description="Average engagement per post on platform")
    virality_index: float = Field(default=0.0, ge=0.0, description="Platform virality ratio")
    discussion_depth: float = Field(default=0.0, ge=0.0, description="Platform discussion depth")
    engagement_rate_per_impression: float = Field(default=0.0, ge=0.0, description="Interactions per view on platform")
    efficiency_rank: int = Field(default=1, ge=1, description="Rank by average engagement per post (1 = highest)")

    model_config = ConfigDict(from_attributes=True)


class PlatformComparativeReport(BaseModel):
    """Cross-platform comparative benchmarking and ranking report."""
    platforms: Dict[str, PlatformEngagementComparison] = Field(
        default_factory=dict,
        description="Per-platform comparative profiles"
    )
    top_volume_platform: Optional[str] = Field(default=None, description="Platform with highest post volume")
    top_engaging_platform: Optional[str] = Field(default=None, description="Platform with highest total engagement")
    top_viral_platform: Optional[str] = Field(default=None, description="Platform with highest virality index")
    top_discussion_platform: Optional[str] = Field(default=None, description="Platform with highest discussion depth")

    model_config = ConfigDict(from_attributes=True)


class DetailedEngagementReport(BaseModel):
    """Comprehensive Phase 4.2 engagement analytics report."""
    overall: EngagementScoreBreakdown = Field(..., description="High-level aggregate engagement metrics")
    distribution: EngagementDistribution = Field(..., description="Engagement score statistical distribution")
    virality: ViralityAnalytics = Field(..., description="Amplification and virality metrics")
    discussion: DiscussionDepthAnalytics = Field(..., description="Conversational depth metrics")
    platform_comparison: PlatformComparativeReport = Field(
        ...,
        description="Cross-platform comparisons and efficiency rankings"
    )
    top_posts: List[PostEngagementProfile] = Field(
        default_factory=list,
        description="Top engaging posts sorted by weighted engagement score"
    )
    outliers: List[PostEngagementProfile] = Field(
        default_factory=list,
        description="Statistically high outlier posts"
    )

    model_config = ConfigDict(from_attributes=True)


class PostSentimentProfile(BaseModel):
    """Individual post sentiment polarity and confidence scorecard."""
    post_id: str = Field(..., description="Unique post identifier")
    platform: str = Field(..., description="Publishing platform")
    text_snippet: Optional[str] = Field(default=None, description="Truncated text excerpt for traceability")
    label: str = Field(..., description="Sentiment classification: positive, neutral, or negative")
    score: float = Field(..., ge=-1.0, le=1.0, description="Polarity score [-1.0, 1.0]")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model inference confidence score [0.0, 1.0]")
    details: Dict[str, Any] = Field(default_factory=dict, description="Lexical cues and diagnostic details")

    model_config = ConfigDict(from_attributes=True)


class SentimentDistributionSummary(BaseModel):
    """Aggregated statistical distribution summary of sentiment across posts."""
    total_evaluated: int = Field(default=0, ge=0, description="Total posts evaluated")
    positive_count: int = Field(default=0, ge=0, description="Count of positive posts")
    neutral_count: int = Field(default=0, ge=0, description="Count of neutral posts")
    negative_count: int = Field(default=0, ge=0, description="Count of negative posts")
    positive_percentage: float = Field(default=0.0, ge=0.0, le=100.0, description="Percentage of positive posts (%)")
    neutral_percentage: float = Field(default=0.0, ge=0.0, le=100.0, description="Percentage of neutral posts (%)")
    negative_percentage: float = Field(default=0.0, ge=0.0, le=100.0, description="Percentage of negative posts (%)")
    average_polarity: float = Field(default=0.0, ge=-1.0, le=1.0, description="Mean polarity score [-1.0, 1.0]")
    net_sentiment_score: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Net sentiment score: (positive_count - negative_count) / max(total_evaluated, 1)"
    )
    dominant_sentiment: str = Field(default="neutral", description="Most frequent sentiment label")

    model_config = ConfigDict(from_attributes=True)


class PlatformSentimentSummary(BaseModel):
    """Platform-partitioned sentiment analytics profile."""
    platform: str = Field(..., description="Platform identifier")
    distribution: SentimentDistributionSummary = Field(..., description="Sentiment breakdown on platform")
    dominant_sentiment: str = Field(default="neutral", description="Dominant sentiment on platform")
    net_sentiment_score: float = Field(default=0.0, description="Net sentiment score on platform")

    model_config = ConfigDict(from_attributes=True)


class TemporalSentimentPoint(BaseModel):
    """Temporal interval net sentiment tracker."""
    interval_start: datetime = Field(..., description="Start timestamp of observation bucket (UTC)")
    interval_end: datetime = Field(..., description="End timestamp of observation bucket (UTC)")
    post_count: int = Field(default=0, ge=0, description="Posts in interval")
    positive_count: int = Field(default=0, ge=0, description="Positive posts in interval")
    neutral_count: int = Field(default=0, ge=0, description="Neutral posts in interval")
    negative_count: int = Field(default=0, ge=0, description="Negative posts in interval")
    average_polarity: float = Field(default=0.0, description="Average polarity in interval")
    net_sentiment: float = Field(default=0.0, description="Net sentiment in interval")
    dominant_sentiment: str = Field(default="neutral", description="Dominant sentiment in interval")

    model_config = ConfigDict(from_attributes=True)


class DetailedSentimentReport(BaseModel):
    """Comprehensive Phase 4.3 sentiment analytics report."""
    overall_distribution: SentimentDistributionSummary = Field(
        ...,
        description="Aggregate sentiment distribution"
    )
    platform_sentiment: Dict[str, PlatformSentimentSummary] = Field(
        default_factory=dict,
        description="Per-platform sentiment breakdowns"
    )
    temporal_sentiment: List[TemporalSentimentPoint] = Field(
        default_factory=list,
        description="Time-series sentiment evolution"
    )
    top_positive_posts: List[PostSentimentProfile] = Field(
        default_factory=list,
        description="Top representative positive posts"
    )
    top_negative_posts: List[PostSentimentProfile] = Field(
        default_factory=list,
        description="Top representative negative posts"
    )
    model_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Sentiment model information and diagnostic metadata"
    )

    model_config = ConfigDict(from_attributes=True)


class TrendMomentumMetrics(BaseModel):
    """Statistical metrics distinguishing momentum from raw volume."""
    current_volume: int = Field(default=0, ge=0, description="Volume in observation window")
    baseline_volume: int = Field(default=0, ge=0, description="Volume in reference baseline window")
    growth_rate_pct: float = Field(default=0.0, description="Growth rate percentage relative to baseline")
    velocity: float = Field(default=0.0, description="Net post volume change per observation window")
    acceleration: float = Field(default=0.0, description="Rate of velocity change")
    momentum_score: float = Field(
        default=0.0,
        description="Composite trend momentum score (velocity * growth_multiplier * engagement_factor)"
    )
    z_score: float = Field(default=0.0, description="Statistical volume spike z-score")
    direction: str = Field(
        default="stable",
        description="Trend classification: emerging, accelerating, spiking, stable, or declining"
    )

    model_config = ConfigDict(from_attributes=True)


class TrendItemProfile(BaseModel):
    """Profile of an individual trending entity (hashtag, keyword, or topic)."""
    trend_id: str = Field(..., description="Unique trend identifier")
    name: str = Field(..., description="Display label, hashtag, or keyword")
    item_type: str = Field(default="topic", description="Entity type: hashtag, keyword, or topic")
    post_count: int = Field(default=0, ge=0, description="Total matching post occurrences")
    momentum: TrendMomentumMetrics = Field(
        default_factory=TrendMomentumMetrics,
        description="Momentum, velocity, and spike metrics"
    )
    sample_post_ids: List[str] = Field(default_factory=list, description="Sample post identifiers")
    is_emerging: bool = Field(default=False, description="Flag indicating newly surging topic with zero prior baseline")
    is_spiking: bool = Field(default=False, description="Flag indicating anomalous volume spike (z >= 2.0)")
    platforms: List[str] = Field(default_factory=list, description="Platforms where this trend is actively observed")

    model_config = ConfigDict(from_attributes=True)


class PlatformTrendSummary(BaseModel):
    """Platform-specific trend summary report."""
    platform: str = Field(..., description="Platform identifier")
    top_trends: List[TrendItemProfile] = Field(default_factory=list, description="Top trending items on platform")
    spiking_trends_count: int = Field(default=0, ge=0, description="Count of spiking trends on platform")
    emerging_trends_count: int = Field(default=0, ge=0, description="Count of emerging trends on platform")

    model_config = ConfigDict(from_attributes=True)


class DetailedTrendReport(BaseModel):
    """Comprehensive Phase 4.4 Trend Analytics report."""
    total_trends_evaluated: int = Field(default=0, ge=0, description="Total unique trends analyzed")
    emerging_count: int = Field(default=0, ge=0, description="Count of emerging trends")
    accelerating_count: int = Field(default=0, ge=0, description="Count of accelerating trends")
    spiking_count: int = Field(default=0, ge=0, description="Count of spiking trends")
    stable_count: int = Field(default=0, ge=0, description="Count of stable topics")
    declining_count: int = Field(default=0, ge=0, description="Count of declining topics")
    ranked_trends: List[TrendItemProfile] = Field(
        default_factory=list,
        description="Ranked list of all detected trends sorted by momentum score descending"
    )
    platform_trends: Dict[str, PlatformTrendSummary] = Field(
        default_factory=dict,
        description="Platform-partitioned trend distributions"
    )
    top_spiking_trends: List[TrendItemProfile] = Field(
        default_factory=list,
        description="Top anomalous volume spikes"
    )
    top_emerging_trends: List[TrendItemProfile] = Field(
        default_factory=list,
        description="Top newly emerging trends"
    )

    model_config = ConfigDict(from_attributes=True)


class DetailedNarrativeReport(BaseModel):
    """Comprehensive Phase 4.5 Narrative Analysis and Intelligence report."""
    total_narratives_evaluated: int = Field(default=0, ge=0, description="Total unique narrative clusters analyzed")
    emerging_count: int = Field(default=0, ge=0, description="Count of emerging narratives")
    accelerating_count: int = Field(default=0, ge=0, description="Count of accelerating narratives")
    peak_count: int = Field(default=0, ge=0, description="Count of peak narratives")
    sustained_count: int = Field(default=0, ge=0, description="Count of sustained narratives")
    decaying_count: int = Field(default=0, ge=0, description="Count of decaying narratives")
    dormant_count: int = Field(default=0, ge=0, description="Count of dormant narratives")
    ranked_narratives: List[NarrativeIntelligence] = Field(
        default_factory=list,
        description="Ranked list of narratives ordered by impact score descending"
    )
    dominant_narrative: Optional[NarrativeIntelligence] = Field(
        default=None,
        description="Highest impact narrative in discourse"
    )
    fastest_growing_narrative: Optional[NarrativeIntelligence] = Field(
        default=None,
        description="Narrative with highest positive volume velocity"
    )
    highest_engagement_narrative: Optional[NarrativeIntelligence] = Field(
        default=None,
        description="Narrative generating highest cumulative engagement"
    )
    cross_platform_narratives: List[NarrativeIntelligence] = Field(
        default_factory=list,
        description="Narratives present across 2 or more platforms"
    )

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
    detailed_engagement: Optional[DetailedEngagementReport] = Field(
        default=None,
        description="Extended Phase 4.2 multi-dimensional engagement analysis"
    )
    detailed_sentiment: Optional[DetailedSentimentReport] = Field(
        default=None,
        description="Extended Phase 4.3 multi-dimensional sentiment analysis"
    )
    detailed_trends: Optional[DetailedTrendReport] = Field(
        default=None,
        description="Extended Phase 4.4 multi-dimensional trend momentum analysis"
    )
    detailed_narratives: Optional[DetailedNarrativeReport] = Field(
        default=None,
        description="Extended Phase 4.5 multi-dimensional narrative intelligence analysis"
    )
    summary_insights: List[str] = Field(
        default_factory=list,
        description="Actionable intelligence bullet points generated by the engine"
    )

    model_config = ConfigDict(from_attributes=True)
