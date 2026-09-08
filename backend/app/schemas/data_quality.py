from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.post import PostMetricsSchema


class AnalyticsReadyPost(BaseModel):
    """
    Standardized, quality-validated representation of a social media post,
    guaranteed to have usable text and clean metadata for downstream Phase 3 AI/NLP models
    (sentiment, emotion, topic extraction, NER, trend analysis).
    """
    id: Optional[int] = Field(default=None, description="Database primary key if persisted")
    platform: str = Field(..., min_length=1, description="Canonical platform name (e.g. X, Telegram)")
    external_post_id: str = Field(..., min_length=1, description="Unique platform-level identifier")
    text: str = Field(..., min_length=1, description="Cleaned, normalized text content guaranteed non-empty")
    raw_text: Optional[str] = Field(default=None, description="Original raw text prior to cleaning")
    author_username: Optional[str] = Field(default=None, description="Normalized author username")
    author_display_name: Optional[str] = Field(default=None, description="Normalized author display name")
    posted_at: datetime = Field(..., description="Creation timestamp in UTC")
    collected_at: Optional[datetime] = Field(default=None, description="Ingestion timestamp in UTC")
    url: Optional[str] = Field(default=None, description="Direct URL to post")
    language: Optional[str] = Field(default=None, description="Language code")
    metrics: Optional[PostMetricsSchema] = Field(default=None, description="Latest engagement metrics snapshot")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Enriched metadata")
    char_count: int = Field(default=0, ge=0, description="Character count of cleaned text")
    word_count: int = Field(default=0, ge=0, description="Word count of cleaned text")
    quality_flags: List[str] = Field(default_factory=list, description="Quality and semantic flags (e.g. has_emojis, has_hashtags)")

    model_config = ConfigDict(from_attributes=True)


class DataQualityResult(BaseModel):
    """
    Validation and quality assessment outcome for a single social media record.
    """
    is_valid: bool = Field(..., description="True if record meets all quality standards for analytics")
    errors: List[str] = Field(default_factory=list, description="Explicit failure reasons if invalid")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal notices or anomalies")
    post: Optional[AnalyticsReadyPost] = Field(default=None, description="Sanitized analytics-ready post if valid")


class RejectedRecord(BaseModel):
    """Details for a record rejected during quality validation."""
    external_post_id: Optional[str] = Field(default=None, description="Identifier of rejected record if present")
    platform: Optional[str] = Field(default=None, description="Platform of rejected record if present")
    errors: List[str] = Field(default_factory=list, description="List of validation failure reasons")
    raw_excerpt: Optional[str] = Field(default=None, description="Summary or snippet of raw input")


class BatchDataQualityResult(BaseModel):
    """
    Aggregated outcome of batch data quality validation.
    """
    total_evaluated: int = Field(..., ge=0, description="Total records evaluated")
    valid_count: int = Field(..., ge=0, description="Count of valid records ready for analytics")
    invalid_count: int = Field(..., ge=0, description="Count of rejected or malformed records")
    valid_posts: List[AnalyticsReadyPost] = Field(default_factory=list, description="Quality-approved posts")
    rejected_records: List[RejectedRecord] = Field(default_factory=list, description="Rejected records with failure reasons")
