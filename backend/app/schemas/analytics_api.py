from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.data_quality import AnalyticsReadyPost, BatchDataQualityResult
from app.schemas.demographic import (
    BatchDemographicResult,
    DemographicDistribution,
    DemographicProfile,
)
from app.schemas.emotion import BatchEmotionResult, EmotionResult
from app.schemas.post import RawPostPayload
from app.schemas.sentiment import BatchSentimentResult, SentimentResult
from app.schemas.topic import BatchTopicResult, ExtractedTopic
from app.schemas.trend import BatchTrendResult, TopicTrendResult


class SentimentAnalyzeRequest(BaseModel):
    """Payload for sentiment analysis requests."""
    posts: Optional[List[AnalyticsReadyPost]] = Field(default=None, description="Pre-validated analytics-ready posts")
    raw_posts: Optional[List[RawPostPayload]] = Field(default=None, description="Raw social-media post payloads")
    text: Optional[str] = Field(default=None, description="Single text string for quick inference")

    model_config = ConfigDict(from_attributes=True)


class EmotionAnalyzeRequest(BaseModel):
    """Payload for emotion analysis requests."""
    posts: Optional[List[AnalyticsReadyPost]] = Field(default=None, description="Pre-validated analytics-ready posts")
    raw_posts: Optional[List[RawPostPayload]] = Field(default=None, description="Raw social-media post payloads")
    text: Optional[str] = Field(default=None, description="Single text string for quick inference")

    model_config = ConfigDict(from_attributes=True)


class TopicAnalyzeRequest(BaseModel):
    """Payload for topic clustering and narrative extraction requests."""
    posts: Optional[List[AnalyticsReadyPost]] = Field(default=None, description="Pre-validated analytics-ready posts")
    raw_posts: Optional[List[RawPostPayload]] = Field(default=None, description="Raw social-media post payloads")

    model_config = ConfigDict(from_attributes=True)


class TrendAnalyzeRequest(BaseModel):
    """Payload for temporal trend and emerging narrative requests."""
    posts: Optional[List[AnalyticsReadyPost]] = Field(default=None, description="Pre-validated analytics-ready posts")
    raw_posts: Optional[List[RawPostPayload]] = Field(default=None, description="Raw social-media post payloads")
    topics: Optional[List[ExtractedTopic]] = Field(default=None, description="Optional pre-extracted topics")
    reference_time: Optional[datetime] = Field(default=None, description="Upper bound reference timestamp in UTC")
    window_duration_seconds: Optional[int] = Field(default=3600, ge=60, description="Window duration in seconds")

    model_config = ConfigDict(from_attributes=True)


class DemographicAnalyzeRequest(BaseModel):
    """Payload for demographic aggregation requests."""
    posts: Optional[List[AnalyticsReadyPost]] = Field(default=None, description="Pre-validated analytics-ready posts")
    raw_posts: Optional[List[RawPostPayload]] = Field(default=None, description="Raw social-media post payloads")
    profiles: Optional[List[DemographicProfile]] = Field(default=None, description="Explicit demographic profiles")
    topics: Optional[List[ExtractedTopic]] = Field(default=None, description="Optional topics for correlation")
    sentiment_results: Optional[List[SentimentResult]] = Field(default=None, description="Optional sentiment results for correlation")
    trend_results: Optional[List[TopicTrendResult]] = Field(default=None, description="Optional trend results for correlation")

    model_config = ConfigDict(from_attributes=True)


class CombinedAnalyzeRequest(BaseModel):
    """Payload for unified multi-layer analytics orchestration pipeline."""
    posts: Optional[List[AnalyticsReadyPost]] = Field(default=None, description="Pre-validated analytics-ready posts")
    raw_posts: Optional[List[RawPostPayload]] = Field(default=None, description="Raw social-media post payloads")
    reference_time: Optional[datetime] = Field(default=None, description="Upper bound reference timestamp in UTC")
    window_duration_seconds: Optional[int] = Field(default=3600, ge=60, description="Window duration in seconds")
    include_sentiment: bool = Field(default=True, description="Run sentiment analysis engine")
    include_emotion: bool = Field(default=True, description="Run emotion analysis engine")
    include_topics: bool = Field(default=True, description="Run topic extraction engine")
    include_trends: bool = Field(default=True, description="Run trend detection engine")
    include_demographics: bool = Field(default=True, description="Run demographic intelligence engine")

    model_config = ConfigDict(from_attributes=True)


class CombinedAnalyticsResponse(BaseModel):
    """Structured response from unified multi-layer analytics orchestration pipeline."""
    total_posts_evaluated: int = Field(..., ge=0, description="Total input posts processed")
    valid_posts_count: int = Field(..., ge=0, description="Total posts meeting quality standards")
    data_quality: Optional[BatchDataQualityResult] = Field(default=None, description="Data quality evaluation summary")
    sentiment: Optional[BatchSentimentResult] = Field(default=None, description="Batch sentiment analysis outcome")
    emotion: Optional[BatchEmotionResult] = Field(default=None, description="Batch emotion analysis outcome")
    topics: Optional[BatchTopicResult] = Field(default=None, description="Extracted topic clusters")
    trends: Optional[BatchTrendResult] = Field(default=None, description="Temporal trend and velocity analysis")
    demographics: Optional[BatchDemographicResult] = Field(default=None, description="Demographic distribution and correlations")
    analyzed_at: datetime = Field(..., description="Pipeline execution timestamp in UTC")

    model_config = ConfigDict(from_attributes=True)
