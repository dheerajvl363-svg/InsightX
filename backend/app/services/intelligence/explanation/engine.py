from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.schemas.intelligence import (
    BatchExplanationResult,
    BatchInsightResult,
    InsightExplanation,
    InsightItem,
    InsightType,
)
from app.services.intelligence.explanation.base import BaseExplanationTemplate
from app.services.intelligence.explanation.cross_platform import CrossPlatformExplanationTemplate
from app.services.intelligence.explanation.emerging import EmergingTrendExplanationTemplate
from app.services.intelligence.explanation.generic import GenericExplanationTemplate
from app.services.intelligence.explanation.sentiment import SentimentShiftExplanationTemplate
from app.services.intelligence.explanation.spike import AnomalousSpikeExplanationTemplate


class DeterministicExplanationEngine:
    """
    Transforms structured InsightItem objects into evidence-grounded, human-readable explanations.
    Maintains strict separation between facts, interpretation, and recommendations.
    """

    def __init__(self):
        self._templates: Dict[InsightType, BaseExplanationTemplate] = {
            InsightType.EMERGING_TREND: EmergingTrendExplanationTemplate(),
            InsightType.ANOMALOUS_SPIKE: AnomalousSpikeExplanationTemplate(),
            InsightType.SENTIMENT_SHIFT: SentimentShiftExplanationTemplate(),
            InsightType.CROSS_PLATFORM_PROPAGATION: CrossPlatformExplanationTemplate(),
        }
        self._default_template = GenericExplanationTemplate()

    @property
    def model_name(self) -> str:
        return "insightx-explanation-deterministic-v1"

    def explain_insight(self, insight: InsightItem) -> InsightExplanation:
        """
        Generates a deterministic explanation for an individual insight item.
        """
        template = self._templates.get(insight.type, self._default_template)
        return template.explain(insight)

    def explain_batch(
        self,
        insights: Optional[List[InsightItem]] = None,
        batch_insight: Optional[BatchInsightResult] = None,
    ) -> BatchExplanationResult:
        """
        Generates explanations for a batch of insights.
        """
        resolved: List[InsightItem] = []
        if insights:
            resolved.extend(insights)
        elif batch_insight and batch_insight.insights:
            resolved.extend(batch_insight.insights)

        explanations = [self.explain_insight(item) for item in resolved]

        return BatchExplanationResult(
            total_explanations=len(explanations),
            explanations=explanations,
            model=self.model_name,
            generated_at=datetime.now(timezone.utc),
        )


_global_explanation_engine: Optional[DeterministicExplanationEngine] = None


def get_explanation_engine() -> DeterministicExplanationEngine:
    """Singleton dependency provider for DeterministicExplanationEngine."""
    global _global_explanation_engine
    if _global_explanation_engine is None:
        _global_explanation_engine = DeterministicExplanationEngine()
    return _global_explanation_engine
