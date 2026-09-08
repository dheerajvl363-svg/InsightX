from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SentimentLabel(str, Enum):
    """Canonical classification labels for sentiment analysis."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class SentimentProbabilities(BaseModel):
    """Probability distribution across sentiment classes (sums to 1.0)."""
    positive: float = Field(..., ge=0.0, le=1.0, description="Probability of positive sentiment")
    neutral: float = Field(..., ge=0.0, le=1.0, description="Probability of neutral sentiment")
    negative: float = Field(..., ge=0.0, le=1.0, description="Probability of negative sentiment")


class SentimentResult(BaseModel):
    """
    Standardized sentiment analysis output for a single post.
    Compatible with database Sentiment model and downstream Phase 3 components.
    """
    post_id: Optional[int] = Field(default=None, description="Database primary key if post is persisted")
    external_post_id: Optional[str] = Field(default=None, description="External platform-level post ID")
    label: SentimentLabel = Field(..., description="Predicted sentiment class (positive, neutral, negative)")
    score: float = Field(..., ge=-1.0, le=1.0, description="Polarity score ranging from -1.0 (most negative) to +1.0 (most positive)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence score between 0.0 and 1.0")
    probabilities: SentimentProbabilities = Field(..., description="Class probability distribution")
    model: str = Field(..., description="Name and version of the sentiment model used for inference")
    analyzed_at: datetime = Field(..., description="Timestamp of inference in UTC")
    details: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic signals and lexical cues")

    model_config = ConfigDict(from_attributes=True)


class BatchSentimentResult(BaseModel):
    """Aggregated sentiment analysis results across a batch of posts."""
    total_analyzed: int = Field(..., ge=0, description="Total posts analyzed")
    positive_count: int = Field(..., ge=0, description="Count of positive posts")
    neutral_count: int = Field(..., ge=0, description="Count of neutral posts")
    negative_count: int = Field(..., ge=0, description="Count of negative posts")
    average_score: float = Field(..., ge=-1.0, le=1.0, description="Mean polarity score across batch")
    results: List[SentimentResult] = Field(default_factory=list, description="Itemized sentiment results")
