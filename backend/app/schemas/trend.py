from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TrendDirection(str, Enum):
    """Classification states for temporal topic trends."""
    EMERGING = "emerging"
    SPIKING = "spiking"
    GROWING = "growing"
    STABLE = "stable"
    DECLINING = "declining"


class TimeWindow(BaseModel):
    """Explicit time boundaries for an evaluation interval in UTC."""
    start: datetime = Field(..., description="Start boundary timestamp in UTC")
    end: datetime = Field(..., description="End boundary timestamp in UTC")

    model_config = ConfigDict(from_attributes=True)


class TopicTrendResult(BaseModel):
    """
    Temporal trend analysis outcome for an individual topic/narrative cluster.
    """
    topic_id: str = Field(..., description="Deterministic machine identifier of the topic")
    topic_label: str = Field(..., description="Human-readable display title for the topic")
    current_volume: int = Field(..., ge=0, description="Post volume in the current evaluation window")
    baseline_volume: int = Field(..., ge=0, description="Post volume in the reference/baseline window")
    growth_rate: float = Field(..., description="Percentage growth rate (+/-) relative to baseline")
    direction: TrendDirection = Field(..., description="Classified trajectory state (emerging, spiking, growing, stable, declining)")
    trend_score: float = Field(..., description="Composite velocity/momentum score for ranking topics")
    is_emerging: bool = Field(default=False, description="Flag indicating newly surging topic with little/no prior baseline")
    is_spiking: bool = Field(default=False, description="Flag indicating sudden anomalous volume surge")
    post_ids: List[int] = Field(default_factory=list, description="Internal database IDs of posts in current window")
    external_post_ids: List[str] = Field(default_factory=list, description="External platform IDs of posts in current window")
    current_window: TimeWindow = Field(..., description="Time window for current period evaluation")
    baseline_window: Optional[TimeWindow] = Field(default=None, description="Time window for baseline period")
    details: Dict[str, Any] = Field(default_factory=dict, description="Statistical signals (z-score, historical volumes, velocity)")

    model_config = ConfigDict(from_attributes=True)


class BatchTrendResult(BaseModel):
    """
    Aggregated multi-topic temporal trend analysis output across a batch of topics/posts.
    """
    total_topics_evaluated: int = Field(..., ge=0, description="Total topic clusters evaluated")
    emerging_topics_count: int = Field(default=0, ge=0, description="Count of topics classified as emerging")
    spiking_topics_count: int = Field(default=0, ge=0, description="Count of topics experiencing statistical spikes")
    growing_topics_count: int = Field(default=0, ge=0, description="Count of topics with positive growth")
    trends: List[TopicTrendResult] = Field(default_factory=list, description="Ranked topic trends sorted by trend score descending")
    model: str = Field(..., description="Name and version of the trend analysis engine used")
    analyzed_at: datetime = Field(..., description="Analysis execution timestamp in UTC")

    model_config = ConfigDict(from_attributes=True)
