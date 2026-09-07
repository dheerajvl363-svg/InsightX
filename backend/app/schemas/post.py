from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PostMetricsSchema(BaseModel):
    """Schema for social media post engagement metrics."""
    likes: Optional[int] = Field(default=0, ge=0, description="Count of likes/reactions")
    comments: Optional[int] = Field(default=0, ge=0, description="Count of comments/replies")
    shares: Optional[int] = Field(default=0, ge=0, description="Count of shares/retweets/reposts")
    views: Optional[int] = Field(default=0, ge=0, description="Count of views/impressions")
    collected_at: Optional[datetime] = Field(default=None, description="Timestamp of metric capture")

    model_config = ConfigDict(from_attributes=True)


class RawPostPayload(BaseModel):
    """
    Schema for incoming raw social media posts.
    Permissive to accept variations across platforms while validating core identifiers.
    """
    platform: str = Field(..., min_length=1, description="Source platform (e.g., X, Telegram, Reddit, YouTube)")
    external_id: Union[str, int] = Field(..., description="Unique platform-level identifier for the post")
    text: Optional[str] = Field(default=None, description="Main text/caption/message content")
    author_username: Optional[str] = Field(default=None, description="Author handle or username")
    author_display_name: Optional[str] = Field(default=None, description="Author full or display name")
    posted_at: Optional[Union[datetime, str, int, float]] = Field(
        default=None,
        description="Timestamp when post was created (ISO string, epoch int/float, or datetime)"
    )
    url: Optional[str] = Field(default=None, description="Link/URL to the original post")
    language: Optional[str] = Field(default=None, description="Language code (e.g., 'en', 'hi')")
    metrics: Optional[Union[PostMetricsSchema, Dict[str, Any]]] = Field(
        default=None,
        description="Engagement metrics if available"
    )
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Platform-specific metadata")
    raw_payload: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Full raw payload")

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @field_validator("platform")
    @classmethod
    def validate_platform_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("platform must not be empty or whitespace only")
        return v.strip()

    @field_validator("external_id")
    @classmethod
    def validate_external_id(cls, v: Union[str, int]) -> str:
        s = str(v).strip()
        if not s:
            raise ValueError("external_id must not be empty")
        return s

    @model_validator(mode="before")
    @classmethod
    def handle_common_aliases(cls, data: Any) -> Any:
        """Map common alias keys from various raw social media APIs."""
        if not isinstance(data, dict):
            return data

        # Map content -> text
        if "text" not in data or data["text"] is None:
            if "content" in data:
                data["text"] = data.get("content")
            elif "message" in data:
                data["text"] = data.get("message")
            elif "caption" in data:
                data["text"] = data.get("caption")

        # Map id -> external_id
        if "external_id" not in data or data["external_id"] is None:
            if "id" in data:
                data["external_id"] = data.get("id")
            elif "post_id" in data:
                data["external_id"] = data.get("post_id")

        # Map username -> author_username
        if "author_username" not in data or data["author_username"] is None:
            if "username" in data:
                data["author_username"] = data.get("username")
            elif "author" in data and isinstance(data["author"], str):
                data["author_username"] = data.get("author")

        # Map display_name -> author_display_name
        if "author_display_name" not in data or data["author_display_name"] is None:
            if "display_name" in data:
                data["author_display_name"] = data.get("display_name")

        return data


class NormalizedPost(BaseModel):
    """
    Standardized internal representation of a post, ready for database persistence.
    All fields are validated, normalized, and timestamped.
    """
    platform_name: str = Field(..., description="Canonical platform name (e.g., 'X', 'Telegram')")
    external_post_id: str = Field(..., description="Sanitized unique platform ID")
    text: Optional[str] = Field(default=None, description="Cleaned, normalized text content")
    author_username: Optional[str] = Field(default=None, description="Normalized author username")
    author_display_name: Optional[str] = Field(default=None, description="Normalized author display name")
    posted_at: datetime = Field(..., description="Creation timestamp in timezone-aware UTC")
    collected_at: datetime = Field(..., description="Ingestion timestamp in timezone-aware UTC")
    url: Optional[str] = Field(default=None, description="Sanitized post URL")
    language: Optional[str] = Field(default=None, description="Normalized lowercase language code")
    metrics: Optional[PostMetricsSchema] = Field(default=None, description="Validated metrics snapshot")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Preserved and enriched metadata")
    raw_payload: Dict[str, Any] = Field(default_factory=dict, description="Complete original raw payload")

    model_config = ConfigDict(from_attributes=True)


class IngestionResponse(BaseModel):
    """Structured response returned following an ingestion attempt."""
    status: str = Field(..., description="Outcome status (e.g. 'success', 'duplicate_ignored')")
    post_id: Optional[int] = Field(default=None, description="Internal database ID if stored")
    external_post_id: str = Field(..., description="External platform post ID")
    platform: str = Field(..., description="Canonical platform name")
    is_duplicate: bool = Field(default=False, description="True if post was already recorded")
    message: str = Field(..., description="Human-readable summary of ingestion result")
    collected_at: Optional[datetime] = Field(default=None, description="Ingestion timestamp")

    model_config = ConfigDict(from_attributes=True)


class BatchIngestionResponse(BaseModel):
    """Structured response returned for multi-post batch ingestion."""
    total_received: int = Field(..., description="Total posts submitted in batch")
    successful: int = Field(..., description="Count of successfully ingested posts")
    duplicates: int = Field(..., description="Count of duplicate posts handled safely")
    failed: int = Field(..., description="Count of invalid/rejected posts")
    results: List[IngestionResponse] = Field(default_factory=list, description="Itemized results")
