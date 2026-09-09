from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.intelligence import (
    InsightEvidence,
    InsightEvidenceReferences,
    InsightExplanation,
    InsightItem,
    InsightSeverity,
    InsightType,
)
from app.schemas.post import RawPostPayload
from app.schemas.trend import TimeWindow


class AIGroundingMetadata(BaseModel):
    """
    Explicit provenance metadata linking an AI analysis response back to deterministic telemetry.
    Ensures verifiable traceability of AI interpretations back to underlying evidence.
    """
    insight_id: str = Field(..., description="Unique ID of the parent insight")
    evidence_topic_id: Optional[str] = Field(default=None, description="Topic cluster identifier if applicable")
    evidence_topic_label: Optional[str] = Field(default=None, description="Topic cluster label if applicable")
    total_supporting_post_count: int = Field(default=0, ge=0, description="Total count of supporting DB post records")
    supporting_post_ids: List[int] = Field(default_factory=list, description="Selected/bounded database post IDs passed to context")
    total_external_post_count: int = Field(default=0, ge=0, description="Total count of external post references")
    external_post_ids: List[str] = Field(default_factory=list, description="Selected/bounded external platform post IDs")
    total_key_author_count: int = Field(default=0, ge=0, description="Total count of key authors driving narrative")
    total_fact_count: int = Field(default=0, ge=0, description="Total count of deterministic factual assertions")
    evidence_is_truncated: bool = Field(default=False, description="True if selected evidence is a subset of total evidence universe")
    platforms: List[str] = Field(default_factory=list, description="Social media platforms where evidence was detected")
    time_window: Optional[TimeWindow] = Field(default=None, description="Time boundary for evidence observation")
    deterministic_metrics_used: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key numerical metrics provided to the AI context (z_score, growth_rate, sentiment_score, etc.)",
    )
    facts_count: int = Field(default=0, ge=0, description="Number of selected deterministic facts in AI context")
    is_fully_grounded: bool = Field(default=True, description="True if evidence is available and verified; false if missing or flagged")

    model_config = ConfigDict(from_attributes=True)


class AIContext(BaseModel):
    """
    Structured context extracted exclusively from deterministic intelligence outputs.
    Serves as the sole factual payload provided to AI providers for interpretation.

    Guarantees:

    - Authoritative totals are preserved separately from selected/compacted item lists.
    - AI providers know when evidence is a context subset (evidence_is_truncated=True).
    """
    insight_id: str = Field(..., description="Target insight identifier")
    type: InsightType = Field(..., description="Categorical taxonomy type")
    title: str = Field(..., description="Executive insight title")
    summary: str = Field(..., description="Deterministic summary statement")
    severity: InsightSeverity = Field(..., description="Triage priority level")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Statistical confidence score")
    confidence_rationale: Optional[str] = Field(default=None, description="Explanation of statistical confidence")
    severity_rationale: Optional[str] = Field(default=None, description="Explanation of triage priority level")
    affected_topic: Optional[str] = Field(default=None, description="Primary topic label")
    affected_platforms: List[str] = Field(default_factory=list, description="Platforms affected")

    # Facts with totals and bounds
    total_fact_count: int = Field(default=0, ge=0, description="Total count of deterministic facts")
    facts: List[str] = Field(default_factory=list, description="Verifiable selected facts extracted from deterministic engine")

    deterministic_metrics: Dict[str, Any] = Field(default_factory=dict, description="Numeric telemetry metrics")

    # Supporting Posts with totals and bounds
    total_supporting_post_count: int = Field(default=0, ge=0, description="Authoritative total count of supporting DB posts")
    supporting_post_ids: List[int] = Field(default_factory=list, description="Selected DB post IDs for context subset")

    # External Posts with totals and bounds
    total_external_post_count: int = Field(default=0, ge=0, description="Authoritative total count of external platform posts")
    external_post_ids: List[str] = Field(default_factory=list, description="Selected external post IDs for context subset")

    # Key Authors with totals and bounds
    total_key_author_count: int = Field(default=0, ge=0, description="Authoritative total count of key authors")
    key_authors: List[str] = Field(default_factory=list, description="Selected key author handles for context subset")

    evidence_is_truncated: bool = Field(default=False, description="True if selected evidence items are a subset of total evidence universe")

    is_fully_grounded: bool = Field(default=True, description="True if verifiable evidence is present; false if evidence is missing")
    time_window: Optional[TimeWindow] = Field(default=None, description="Temporal window of evidence")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Context creation timestamp")

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_insight_and_explanation(
        cls,
        insight: InsightItem,
        explanation: Optional[InsightExplanation] = None,
        max_post_ids: int = 25,
        max_external_post_ids: int = 25,
        max_key_authors: int = 10,
        max_facts: int = 10,
    ) -> "AIContext":
        """
        Factory constructing an AIContext strictly from an InsightItem and optional InsightExplanation.
        Delegates to EvidenceGroundedContextBuilder for robust truncation and totality preservation.
        """
        from app.services.intelligence.ai.context_builder import EvidenceGroundedContextBuilder
        return EvidenceGroundedContextBuilder.build_context(
            insight=insight,
            explanation=explanation,
            max_post_ids=max_post_ids,
            max_external_post_ids=max_external_post_ids,
            max_key_authors=max_key_authors,
            max_facts=max_facts,
        )


class AIAnalysisRequest(BaseModel):
    """
    Structured request payload sent to an AI provider.
    Carries the deterministic AIContext alongside optional operational prompt instructions.
    """
    context: AIContext = Field(..., description="Deterministic facts and evidence context")
    prompt_instructions: Optional[str] = Field(
        default=None,
        description="Optional custom focus instructions (e.g. 'Focus on brand impact' or 'Suggest PR mitigation')",
    )
    max_recommendations: int = Field(default=3, ge=1, le=10, description="Maximum number of AI recommendations requested")

    model_config = ConfigDict(from_attributes=True)


class AIAnalysisResponse(BaseModel):
    """
    Structured response generated by an AI provider for qualitative interpretation and suggestions.
    Keeps AI-generated interpretation clearly separated from deterministic facts.
    """
    insight_id: str = Field(..., description="Parent insight ID")
    interpretation: str = Field(..., description="AI-assisted qualitative narrative synthesis")
    ai_recommendations: List[str] = Field(default_factory=list, description="AI-generated actionable suggestions")
    confidence_assessment: Optional[str] = Field(default=None, description="AI commentary on nuance, uncertainty, or noise")
    grounding_metadata: AIGroundingMetadata = Field(..., description="Explicit provenance linking response to facts")
    disclaimer: str = Field(
        default="AI-generated interpretation assistant. Deterministic analytics and evidence remain the source of truth.",
        description="Mandatory disclaimer distinguishing AI interpretation from factual evidence",
    )
    provider_name: str = Field(..., description="Identifier of the AI provider (e.g. 'mock-ai-provider')")
    model_name: str = Field(..., description="Model version string (e.g. 'insightx-mock-ai-v1')")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when response was generated in UTC",
    )
    is_flagged_unsupported: bool = Field(
        default=False,
        description="Flagged true if evidence is missing, context lacks post support, or grounding validation failed",
    )
    validation_notes: List[str] = Field(
        default_factory=list,
        description="Validation feedback or audit logs from grounding checker",
    )

    model_config = ConfigDict(from_attributes=True)


class AIInterpretationRequest(BaseModel):
    """
    Payload for requesting AI qualitative interpretation of a specific insight.
    Includes strict server-side bounding on max_post_ids and prompt_instructions.
    """
    platform: Optional[str] = Field(default=None, description="Optional platform filter scoping")
    raw_posts: Optional[List[RawPostPayload]] = Field(
        default=None,
        description="Optional in-memory raw posts for ad-hoc insight interpretation",
    )
    prompt_instructions: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional analyst instructions (treated as untrusted input)",
    )
    max_post_ids: int = Field(
        default=25,
        ge=1,
        le=50,
        description="Server-side bounded maximum number of supporting post IDs to include in context",
    )

    model_config = ConfigDict(from_attributes=True)


class AIInterpretationResponse(BaseModel):
    """
    Auditable combined response integrating deterministic facts/evidence with AI interpretation.
    Strictly isolates AI qualitative outputs from deterministic telemetry and baseline explanations.
    """
    insight_id: str = Field(..., description="Unique deterministic identifier of the insight")
    insight: InsightItem = Field(..., description="Deterministic source of truth insight with evidence")
    explanation: InsightExplanation = Field(..., description="Deterministic auditable baseline explanation")
    ai_analysis: AIAnalysisResponse = Field(..., description="AI-assisted qualitative narrative synthesis and recommendations")
    is_fallback_used: bool = Field(default=False, description="True if AI provider fallback was used due to unavailability or failure")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when response was assembled in UTC",
    )

    model_config = ConfigDict(from_attributes=True)
