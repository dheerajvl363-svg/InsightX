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
from app.schemas.trend import TimeWindow


class AIGroundingMetadata(BaseModel):
    """
    Explicit provenance metadata linking an AI analysis response back to deterministic telemetry.
    Ensures verifiable traceability of AI interpretations back to underlying evidence.
    """
    insight_id: str = Field(..., description="Unique ID of the parent insight")
    evidence_topic_id: Optional[str] = Field(default=None, description="Topic cluster identifier if applicable")
    evidence_topic_label: Optional[str] = Field(default=None, description="Topic cluster label if applicable")
    supporting_post_ids: List[int] = Field(default_factory=list, description="Primary database post IDs supporting the insight")
    external_post_ids: List[str] = Field(default_factory=list, description="Platform external post IDs supporting the insight")
    platforms: List[str] = Field(default_factory=list, description="Social media platforms where evidence was detected")
    time_window: Optional[TimeWindow] = Field(default=None, description="Time boundary for evidence observation")
    deterministic_metrics_used: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key numerical metrics provided to the AI context (z_score, growth_rate, sentiment_score, etc.)",
    )
    facts_count: int = Field(default=0, ge=0, description="Number of deterministic factual assertions in AI context")
    is_fully_grounded: bool = Field(default=True, description="True if evidence is available and verified; false if missing or flagged")

    model_config = ConfigDict(from_attributes=True)


class AIContext(BaseModel):
    """
    Structured context extracted exclusively from deterministic intelligence outputs.
    Serves as the sole factual payload provided to AI providers for interpretation.
    """
    insight_id: str = Field(..., description="Target insight identifier")
    type: InsightType = Field(..., description="Categorical taxonomy type")
    title: str = Field(..., description="Executive insight title")
    summary: str = Field(..., description="Deterministic summary statement")
    severity: InsightSeverity = Field(..., description="Triage priority level")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Statistical confidence score")
    affected_topic: Optional[str] = Field(default=None, description="Primary topic label")
    affected_platforms: List[str] = Field(default_factory=list, description="Platforms affected")
    facts: List[str] = Field(default_factory=list, description="Verifiable facts extracted from deterministic engine")
    deterministic_metrics: Dict[str, Any] = Field(default_factory=dict, description="Numeric telemetry metrics")
    supporting_post_ids: List[int] = Field(default_factory=list, description="Post database IDs")
    external_post_ids: List[str] = Field(default_factory=list, description="External platform post IDs")
    key_authors: List[str] = Field(default_factory=list, description="Leading author handles")
    time_window: Optional[TimeWindow] = Field(default=None, description="Temporal window of evidence")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Context creation timestamp")

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_insight_and_explanation(
        cls,
        insight: InsightItem,
        explanation: Optional[InsightExplanation] = None,
    ) -> "AIContext":
        """
        Factory constructing an AIContext strictly from an InsightItem and optional InsightExplanation.
        Guarantees no arbitrary application state or hallucinated context is injected.
        """
        ev: InsightEvidence = insight.evidence
        facts: List[str] = []
        if explanation and explanation.facts:
            facts = list(explanation.facts)

        metrics: Dict[str, Any] = {}
        if ev.growth_rate is not None:
            metrics["growth_rate"] = ev.growth_rate
        if ev.current_volume is not None:
            metrics["current_volume"] = ev.current_volume
        if ev.baseline_volume is not None:
            metrics["baseline_volume"] = ev.baseline_volume
        if ev.z_score is not None:
            metrics["z_score"] = ev.z_score
        if ev.sentiment_score is not None:
            metrics["sentiment_score"] = ev.sentiment_score
        if ev.dominant_sentiment is not None:
            metrics["dominant_sentiment"] = ev.dominant_sentiment

        return cls(
            insight_id=insight.id,
            type=insight.type,
            title=insight.title,
            summary=insight.summary,
            severity=insight.severity,
            confidence=insight.confidence,
            affected_topic=insight.affected_topic,
            affected_platforms=insight.affected_platforms or ev.platforms,
            facts=facts,
            deterministic_metrics=metrics,
            supporting_post_ids=ev.post_ids,
            external_post_ids=ev.external_post_ids,
            key_authors=ev.key_authors,
            time_window=ev.time_window,
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
