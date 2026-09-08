from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class EmotionLabel(str, Enum):
    """Canonical classification labels for emotion analysis."""
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    NEUTRAL = "neutral"


class EmotionProbabilities(BaseModel):
    """Probability distribution across all 7 emotion categories (sums to 1.0)."""
    joy: float = Field(default=0.0, ge=0.0, le=1.0, description="Probability of joy")
    sadness: float = Field(default=0.0, ge=0.0, le=1.0, description="Probability of sadness")
    anger: float = Field(default=0.0, ge=0.0, le=1.0, description="Probability of anger")
    fear: float = Field(default=0.0, ge=0.0, le=1.0, description="Probability of fear")
    surprise: float = Field(default=0.0, ge=0.0, le=1.0, description="Probability of surprise")
    disgust: float = Field(default=0.0, ge=0.0, le=1.0, description="Probability of disgust")
    neutral: float = Field(default=0.0, ge=0.0, le=1.0, description="Probability of neutral")


class EmotionResult(BaseModel):
    """
    Standardized emotion analysis output for a single social media post.
    Consumes AnalyticsReadyPost records and provides fine-grained emotional intelligence.
    """
    post_id: Optional[int] = Field(default=None, description="Database primary key if post is persisted")
    external_post_id: Optional[str] = Field(default=None, description="External platform post ID")
    primary_emotion: EmotionLabel = Field(..., description="Dominant emotion detected in the post")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score for the primary emotion")
    probabilities: EmotionProbabilities = Field(..., description="Full probability distribution across all 7 emotions")
    model: str = Field(..., description="Name and version of the emotion engine used for inference")
    analyzed_at: datetime = Field(..., description="Inference timestamp in UTC")
    details: Dict[str, Any] = Field(default_factory=dict, description="Lexical signals, emoji triggers, and contextual diagnostics")

    model_config = ConfigDict(from_attributes=True)


class BatchEmotionResult(BaseModel):
    """Aggregated emotion analysis results across a batch of posts."""
    total_analyzed: int = Field(..., ge=0, description="Total posts analyzed in this batch")
    emotion_distribution: Dict[str, int] = Field(default_factory=dict, description="Count of posts per primary emotion")
    results: List[EmotionResult] = Field(default_factory=list, description="Itemized emotion results")
