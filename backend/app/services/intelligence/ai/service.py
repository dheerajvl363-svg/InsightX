import logging
from typing import List, Optional

from app.schemas.intelligence import InsightExplanation, InsightItem
from app.services.intelligence.ai.base import BaseAIProvider
from app.services.intelligence.ai.context_builder import EvidenceGroundedContextBuilder
from app.services.intelligence.ai.factory import get_ai_provider
from app.services.intelligence.ai.schemas import (
    AIAnalysisRequest,
    AIAnalysisResponse,
)

logger = logging.getLogger(__name__)


class AIAssistedIntelligenceService:
    """
    High-level orchestrator service for AI-assisted interpretation of intelligence insights.
    
    Binds deterministic intelligence outputs (InsightItem, InsightExplanation) to a provider-agnostic
    AI interpretation provider (BaseAIProvider) using EvidenceGroundedContextBuilder.
    """

    def __init__(
        self,
        provider: Optional[BaseAIProvider] = None,
        context_builder: Optional[EvidenceGroundedContextBuilder] = None,
    ):
        self._provider = provider or get_ai_provider()
        self._builder = context_builder or EvidenceGroundedContextBuilder()

    @property
    def provider(self) -> BaseAIProvider:
        return self._provider

    def analyze_insight(
        self,
        insight: InsightItem,
        explanation: Optional[InsightExplanation] = None,
        prompt_instructions: Optional[str] = None,
        max_post_ids: int = 25,
    ) -> AIAnalysisResponse:
        """
        Generates an AI-assisted qualitative interpretation response for a single insight.
        """
        request = self._builder.build_request(
            insight=insight,
            explanation=explanation,
            prompt_instructions=prompt_instructions,
            max_post_ids=max_post_ids,
        )
        return self._provider.analyze_insight(request)

    def analyze_batch(
        self,
        insights: List[InsightItem],
        explanations: Optional[List[InsightExplanation]] = None,
        prompt_instructions: Optional[str] = None,
        max_post_ids: int = 25,
    ) -> List[AIAnalysisResponse]:
        """
        Batch analyzes a list of insights.
        """
        expl_map = {e.insight_id: e for e in (explanations or [])}
        requests: List[AIAnalysisRequest] = []
        for item in insights:
            expl = expl_map.get(item.id)
            req = self._builder.build_request(
                insight=item,
                explanation=expl,
                prompt_instructions=prompt_instructions,
                max_post_ids=max_post_ids,
            )
            requests.append(req)

        return self._provider.batch_analyze_insights(requests)


_global_ai_service: Optional[AIAssistedIntelligenceService] = None


def get_ai_intelligence_service() -> AIAssistedIntelligenceService:
    """Dependency provider returning singleton instance of AIAssistedIntelligenceService."""
    global _global_ai_service
    if _global_ai_service is None:
        _global_ai_service = AIAssistedIntelligenceService()
    return _global_ai_service
