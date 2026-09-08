from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SinglePostTopicResult(BaseModel):
    """
    Topic and keyword extraction output for an individual post.
    """
    post_id: Optional[int] = Field(default=None, description="Database primary key if post is persisted")
    external_post_id: Optional[str] = Field(default=None, description="Platform external post ID")
    keywords: List[str] = Field(default_factory=list, description="Ranked keywords extracted from the post")
    keyphrases: List[str] = Field(default_factory=list, description="Multi-word phrases extracted from the post")
    hashtags: List[str] = Field(default_factory=list, description="Hashtags identified in the post")
    suggested_label: Optional[str] = Field(default=None, description="Primary representative topic label for this post")

    model_config = ConfigDict(from_attributes=True)


class ExtractedTopic(BaseModel):
    """
    Structured representation of a topic / narrative cluster across one or more posts.
    """
    topic_id: str = Field(..., description="Deterministic machine-readable topic identifier")
    label: str = Field(..., description="Descriptive human-readable topic title")
    keywords: List[str] = Field(default_factory=list, description="Top representative keywords for this topic")
    keyphrases: List[str] = Field(default_factory=list, description="Top multi-word keyphrases for this topic")
    post_count: int = Field(..., ge=1, description="Number of posts associated with this topic cluster")
    post_ids: List[int] = Field(default_factory=list, description="Internal database IDs of member posts")
    external_post_ids: List[str] = Field(default_factory=list, description="External platform IDs of member posts")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Topic cohesion / confidence score")

    model_config = ConfigDict(from_attributes=True)


class BatchTopicResult(BaseModel):
    """
    Aggregated multi-post topic clustering and narrative extraction result.
    """
    total_posts_analyzed: int = Field(..., ge=0, description="Total posts evaluated in batch")
    total_topics_found: int = Field(..., ge=0, description="Count of distinct topics identified")
    topics: List[ExtractedTopic] = Field(default_factory=list, description="Identified topic clusters ordered by post volume")
    unclustered_posts_count: int = Field(default=0, ge=0, description="Count of posts without distinct topic signals")
    model: str = Field(..., description="Name and version of the topic extraction engine used")
    analyzed_at: datetime = Field(..., description="Timestamp of analysis in UTC")
