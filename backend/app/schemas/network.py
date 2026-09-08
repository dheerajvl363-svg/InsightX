"""
Phase 5.3 — Network & Link Analysis Schemas.

Provides Pydantic schemas for network graph nodes, edges, influencer rankings,
and domain sharing summaries across social media posts.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.data_quality import AnalyticsReadyPost
from app.schemas.post import RawPostPayload


class NetworkNode(BaseModel):
    """Node in the interaction / influence graph."""

    id: str = Field(..., description="Unique node identifier")
    label: str = Field(..., description="Display label (author username, domain, hashtag, or platform)")
    node_type: str = Field(..., description="Type of entity: 'author', 'domain', 'hashtag', or 'platform'")
    degree: int = Field(default=0, ge=0, description="Total connection count (degree)")
    influence_score: float = Field(default=0.0, ge=0.0, description="Computed influence score")

    model_config = ConfigDict(from_attributes=True)


class NetworkEdge(BaseModel):
    """Edge in the interaction / influence graph."""

    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    weight: int = Field(default=1, ge=1, description="Edge weight / co-occurrence count")
    relation_type: str = Field(..., description="Type of relation (e.g. 'author_mention', 'posts_domain', 'uses_hashtag')")

    model_config = ConfigDict(from_attributes=True)


class BatchNetworkResult(BaseModel):
    """Batch network and influence analysis outcome."""

    total_nodes: int = Field(..., ge=0, description="Total node count in graph")
    total_edges: int = Field(..., ge=0, description="Total edge count in graph")
    nodes: List[NetworkNode] = Field(default_factory=list, description="Graph nodes")
    edges: List[NetworkEdge] = Field(default_factory=list, description="Graph edges")
    top_influencers: List[NetworkNode] = Field(default_factory=list, description="Ranked top influential nodes")
    top_domains: List[Dict[str, Any]] = Field(default_factory=list, description="Most frequent external domains shared")
    analyzed_at: datetime = Field(..., description="Analysis execution timestamp in UTC")

    model_config = ConfigDict(from_attributes=True)


class NetworkAnalyzeRequest(BaseModel):
    """Payload for network and influence analysis requests."""

    posts: Optional[List[AnalyticsReadyPost]] = Field(default=None, description="Pre-validated analytics-ready posts")
    raw_posts: Optional[List[RawPostPayload]] = Field(default=None, description="Raw social-media post payloads")
    text: Optional[str] = Field(default=None, description="Single text string for quick inference")

    model_config = ConfigDict(from_attributes=True)
