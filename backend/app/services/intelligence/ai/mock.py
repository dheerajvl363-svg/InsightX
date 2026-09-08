from datetime import datetime, timezone
from typing import List, Optional

from app.services.intelligence.ai.base import BaseAIProvider
from app.services.intelligence.ai.grounding import validate_grounding
from app.services.intelligence.ai.schemas import (
    AIAnalysisRequest,
    AIAnalysisResponse,
    AIContext,
    AIGroundingMetadata,
)


class MockAIProvider(BaseAIProvider):
    """
    Deterministic, safe mock AI provider for testing and offline execution.
    
    Features:
    - Requires zero API keys or environment secrets.
    - Makes zero network connections.
    - Synthesizes structured, evidence-grounded interpretations using strictly
      the telemetry present in AIContext.
    """

    def __init__(self, model_name: str = "insightx-mock-ai-v1"):
        self._model_name = model_name

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return self._model_name

    def is_available(self) -> bool:
        return True

    def analyze_insight(self, request: AIAnalysisRequest) -> AIAnalysisResponse:
        """
        Synthesizes a mock AI interpretation strictly from request context.
        """
        ctx: AIContext = request.context
        now = datetime.now(timezone.utc)

        # Build grounded interpretation
        facts_summary = f" Supported by {len(ctx.facts)} deterministic facts." if ctx.facts else ""
        metrics_str = (
            ", ".join(f"{k}={v}" for k, v in ctx.deterministic_metrics.items())
            if ctx.deterministic_metrics
            else "no numeric metrics provided"
        )
        
        interpretation = (
            f"AI Assessment ({ctx.severity.value.upper()} priority): Signal '{ctx.title}' "
            f"exhibits {ctx.confidence * 100:.0f}% confidence across platform(s) "
            f"{', '.join(ctx.affected_platforms) if ctx.affected_platforms else 'unspecified'}. "
            f"Observed telemetry parameters ({metrics_str}).{facts_summary} "
            f"{ctx.summary}"
        )

        if request.prompt_instructions:
            interpretation += f" (Focused on: {request.prompt_instructions})"

        # Build AI recommendations
        recommendations: List[str] = [
            f"Monitor platform signals for '{ctx.affected_topic or ctx.title}' over the next evaluation window.",
            f"Review supporting telemetry posts (count={len(ctx.supporting_post_ids)}).",
        ]
        if ctx.severity in ("critical", "high"):
            recommendations.append("Alert domain leads for urgent operational triage.")

        recommendations = recommendations[: request.max_recommendations]

        confidence_assessment = (
            f"Statistical confidence is rated at {ctx.confidence:.2f}. "
            f"Evidence grounding is based on {len(ctx.supporting_post_ids)} primary post references."
        )

        initial_response = AIAnalysisResponse(
            insight_id=ctx.insight_id,
            interpretation=interpretation,
            ai_recommendations=recommendations,
            confidence_assessment=confidence_assessment,
            grounding_metadata=AIGroundingMetadata(
                insight_id=ctx.insight_id,
                supporting_post_ids=ctx.supporting_post_ids,
                external_post_ids=ctx.external_post_ids,
                platforms=ctx.affected_platforms,
                time_window=ctx.time_window,
                deterministic_metrics_used=ctx.deterministic_metrics,
                facts_count=len(ctx.facts),
                is_fully_grounded=True,
            ),
            provider_name=self.provider_name,
            model_name=self.model_name,
            generated_at=now,
            is_flagged_unsupported=False,
            validation_notes=[],
        )

        return validate_grounding(ctx, initial_response)
