from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.data_quality import AnalyticsReadyPost
from app.schemas.post import RawPostPayload
from app.schemas.topic import ExtractedTopic
from app.schemas.trend import TimeWindow, TopicTrendResult


class InsightType(str, Enum):
    """Categorical taxonomy for intelligence insights derived from social telemetry."""
    EMERGING_TREND = "emerging_trend"
    ANOMALOUS_SPIKE = "anomalous_spike"
    SENTIMENT_SHIFT = "sentiment_shift"
    CROSS_PLATFORM_PROPAGATION = "cross_platform_propagation"
    INFLUENCER_AMPLIFICATION = "influencer_amplification"
    NARRATIVE_EMERGENCE = "narrative_emergence"
    ENGAGEMENT_SURGE = "engagement_surge"
    DATA_QUALITY_ALERT = "data_quality_alert"


class InsightSeverity(str, Enum):
    """Operational urgency and triage priority for derived insights."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class InsightStatus(str, Enum):
    """Workflow tracking lifecycle states for intelligence alerts."""
    ACTIVE = "active"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class InsightEvidence(BaseModel):
    """
    Strictly structured, evidence-grounded trace linking an insight to verifiable metrics.
    Guarantees no ungrounded or fabricated statistical claims.
    """
    topic_id: Optional[str] = Field(default=None, description="Topic cluster identifier if applicable")
    topic_label: Optional[str] = Field(default=None, description="Human-readable topic title")
    growth_rate: Optional[float] = Field(default=None, description="Percentage growth rate (+/-) observed")
    current_volume: Optional[int] = Field(default=None, ge=0, description="Post count in the current evaluation window")
    baseline_volume: Optional[int] = Field(default=None, ge=0, description="Post count in the historical reference window")
    z_score: Optional[float] = Field(default=None, description="Statistical standard deviations above mean volume")
    sentiment_score: Optional[float] = Field(default=None, description="Aggregate polarity score (-1.0 to +1.0)")
    dominant_sentiment: Optional[str] = Field(default=None, description="Dominant sentiment label (positive, neutral, negative)")
    post_ids: List[int] = Field(default_factory=list, description="Primary database record IDs providing supporting evidence")
    external_post_ids: List[str] = Field(default_factory=list, description="Original platform external post IDs")
    key_authors: List[str] = Field(default_factory=list, description="Leading author handles driving the narrative")
    platforms: List[str] = Field(default_factory=list, description="Platforms where the signal was detected")
    time_window: Optional[TimeWindow] = Field(default=None, description="Time boundary covering the evidence window")
    raw_signals: Dict[str, Any] = Field(default_factory=dict, description="Underlying metric indicators and engine metadata")

    model_config = ConfigDict(from_attributes=True)


class InsightItem(BaseModel):
    """
    Discrete intelligence insight object with evidence provenance and actionable recommendations.
    """
    id: str = Field(..., description="Unique deterministic identifier (e.g. 'ins_20260909_001')")
    type: InsightType = Field(..., description="Categorical classification of the intelligence insight")
    title: str = Field(..., min_length=3, max_length=200, description="Concise executive headline summarizing the insight")
    summary: str = Field(..., min_length=10, description="Detailed explanatory intelligence assessment")
    severity: InsightSeverity = Field(default=InsightSeverity.MEDIUM, description="Operational triage priority")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Statistical confidence score (0.0 to 1.0)")
    affected_topic: Optional[str] = Field(default=None, description="Primary narrative or topic label affected")
    affected_platforms: List[str] = Field(default_factory=list, description="List of social platforms involved")
    evidence: InsightEvidence = Field(default_factory=InsightEvidence, description="Structured analytical evidence and provenance tracing")
    recommended_action: Optional[str] = Field(default=None, description="Suggested investigative or mitigation directive")
    action_items: List[str] = Field(default_factory=list, description="Specific checklist items for operational analysts")
    status: InsightStatus = Field(default=InsightStatus.ACTIVE, description="Lifecycle status of this insight alert")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the insight was synthesized in UTC",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extensible contextual metadata")

    model_config = ConfigDict(from_attributes=True)


class BatchInsightResult(BaseModel):
    """
    Container response aggregating synthesized intelligence insights with operational triage counts.
    """
    total_insights: int = Field(..., ge=0, description="Total number of insights generated")
    critical_count: int = Field(default=0, ge=0, description="Number of critical severity insights")
    high_count: int = Field(default=0, ge=0, description="Number of high severity insights")
    medium_count: int = Field(default=0, ge=0, description="Number of medium severity insights")
    low_count: int = Field(default=0, ge=0, description="Number of low severity insights")
    info_count: int = Field(default=0, ge=0, description="Number of informational insights")
    insights: List[InsightItem] = Field(default_factory=list, description="Ranked list of intelligence insights")
    model: str = Field(..., description="Identifier of the intelligence engine and version")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of intelligence report generation in UTC",
    )

    model_config = ConfigDict(from_attributes=True)


class IntelligenceAnalyzeRequest(BaseModel):
    """
    Payload for triggering intelligence synthesis across pre-extracted analytics or raw post streams.
    """
    posts: Optional[List[AnalyticsReadyPost]] = Field(default=None, description="Pre-validated analytics-ready posts")
    raw_posts: Optional[List[RawPostPayload]] = Field(default=None, description="Raw social-media post payloads")
    topics: Optional[List[ExtractedTopic]] = Field(default=None, description="Pre-extracted topic clusters")
    trends: Optional[List[TopicTrendResult]] = Field(default=None, description="Pre-computed trend trajectories")
    platform: Optional[str] = Field(default=None, description="Optional platform filter scoping")
    min_confidence: Optional[float] = Field(default=0.5, ge=0.0, le=1.0, description="Minimum confidence threshold for inclusion")
    max_insights: Optional[int] = Field(default=20, ge=1, le=100, description="Maximum insights to return")
    include_explanations: Optional[bool] = Field(default=False, description="Whether to synthesize and attach explanations to insights")
    include_ai: Optional[bool] = Field(default=False, description="Whether to generate AI qualitative interpretations")

    model_config = ConfigDict(from_attributes=True)



class InsightEvidenceReferences(BaseModel):
    """
    Structured references connecting an explanation back to underlying verifiable data records.
    """
    topic_id: Optional[str] = Field(default=None, description="Topic cluster identifier")
    topic_label: Optional[str] = Field(default=None, description="Human-readable topic title")
    post_ids: List[int] = Field(default_factory=list, description="Primary database post record IDs")
    external_post_ids: List[str] = Field(default_factory=list, description="Associated platform external post IDs")
    platforms: List[str] = Field(default_factory=list, description="Platforms where evidence was observed")
    time_window: Optional[TimeWindow] = Field(default=None, description="Time window covering the evidence")
    key_metrics: Dict[str, Any] = Field(default_factory=dict, description="Numeric metric values underpinning the insight")

    model_config = ConfigDict(from_attributes=True)


class InsightExplanation(BaseModel):
    """
    Analyst-facing structured explanation strictly distinguishing facts, interpretation, and recommendations.
    """
    insight_id: str = Field(..., description="Unique ID of the parent insight")
    type: InsightType = Field(..., description="Categorical type of the insight")
    title: str = Field(..., description="Executive title")
    summary: str = Field(..., description="High-level narrative summary")
    severity: InsightSeverity = Field(..., description="Operational triage severity")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Statistical confidence score")
    confidence_rationale: str = Field(..., description="Clear explanation of the confidence score")
    severity_rationale: str = Field(..., description="Clear explanation of the triage priority")
    facts: List[str] = Field(default_factory=list, description="Verifiable statements directly backed by source analytics")
    interpretation: str = Field(..., description="Cautious, evidence-grounded assessment of why the signal matters")
    recommended_action: Optional[str] = Field(default=None, description="Primary investigation directive")
    action_items: List[str] = Field(default_factory=list, description="Detailed actionable checklist for analysts")
    evidence_references: InsightEvidenceReferences = Field(
        default_factory=InsightEvidenceReferences,
        description="Traceable pointers to data records and metrics",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when explanation was synthesized in UTC",
    )

    model_config = ConfigDict(from_attributes=True)


class BatchExplanationResult(BaseModel):
    """
    Container response aggregating explanations for a batch of insights.
    """
    total_explanations: int = Field(..., ge=0, description="Total number of explanations generated")
    explanations: List[InsightExplanation] = Field(default_factory=list, description="List of generated insight explanations")
    model: str = Field(..., description="Explanation engine identifier and version")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of explanation report generation in UTC",
    )

    model_config = ConfigDict(from_attributes=True)


class UnifiedWorkflowResult(BaseModel):
    """
    Unified end-to-end intelligence result combining multi-facet analytics,
    detected insights, auditable explanations, and evidence provenance.
    """
    total_insights: int = Field(..., ge=0, description="Total number of insights generated")
    total_explanations: int = Field(default=0, ge=0, description="Total number of explanations generated")
    batch_insights: BatchInsightResult = Field(..., description="Container of generated intelligence insights")
    explanations: List[InsightExplanation] = Field(default_factory=list, description="List of generated explanations")
    ai_analyses: List[Any] = Field(default_factory=list, description="Optional AI qualitative interpretations")
    analytics_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary telemetry from underlying analytical models")

    model: str = Field(..., description="Identifier of the unified pipeline engine and version")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of unified intelligence report generation in UTC",
    )

    model_config = ConfigDict(from_attributes=True)
