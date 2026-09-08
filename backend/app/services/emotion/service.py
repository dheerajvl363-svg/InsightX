from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.schemas.data_quality import AnalyticsReadyPost
from app.schemas.emotion import (
    BatchEmotionResult,
    EmotionLabel,
    EmotionResult,
)
from app.services.emotion.base import BaseEmotionEngine
from app.services.emotion.engine import RuleBasedEmotionEngine


class EmotionAnalysisService:
    """
    Emotion Analysis Service for Phase 3.
    Consumes AnalyticsReadyPost records, executes emotion inference via swappable engines,
    and returns standardized EmotionResult with 7-class probability distributions.
    """

    def __init__(self, engine: Optional[BaseEmotionEngine] = None):
        self.engine = engine or RuleBasedEmotionEngine()

    def analyze(self, post: AnalyticsReadyPost) -> EmotionResult:
        """
        Analyzes emotion for a single AnalyticsReadyPost instance.
        """
        if not isinstance(post, AnalyticsReadyPost):
            raise TypeError(f"Expected AnalyticsReadyPost, got {type(post).__name__}")

        inference = self.engine.analyze_text(post.text)

        return EmotionResult(
            post_id=post.id,
            external_post_id=post.external_post_id,
            primary_emotion=inference.primary_emotion,
            confidence=inference.confidence,
            probabilities=inference.probabilities,
            model=inference.model_name,
            analyzed_at=datetime.now(timezone.utc),
            details=inference.details,
        )

    def analyze_text(
        self,
        text: str,
        external_post_id: Optional[str] = None,
        post_id: Optional[int] = None,
    ) -> EmotionResult:
        """
        Direct text inference convenience method.
        """
        inference = self.engine.analyze_text(text or "")

        return EmotionResult(
            post_id=post_id,
            external_post_id=external_post_id,
            primary_emotion=inference.primary_emotion,
            confidence=inference.confidence,
            probabilities=inference.probabilities,
            model=inference.model_name,
            analyzed_at=datetime.now(timezone.utc),
            details=inference.details,
        )

    def analyze_batch(self, posts: List[AnalyticsReadyPost]) -> BatchEmotionResult:
        """
        Analyzes emotion across a batch of AnalyticsReadyPost instances.
        Aggregates class counts and provides itemized results.
        """
        if not posts:
            return BatchEmotionResult(
                total_analyzed=0,
                emotion_distribution={label.value: 0 for label in EmotionLabel},
                results=[],
            )

        results: List[EmotionResult] = []
        distribution: Dict[str, int] = {label.value: 0 for label in EmotionLabel}

        for post in posts:
            res = self.analyze(post)
            results.append(res)
            distribution[res.primary_emotion.value] = distribution.get(res.primary_emotion.value, 0) + 1

        return BatchEmotionResult(
            total_analyzed=len(posts),
            emotion_distribution=distribution,
            results=results,
        )


# Global default instance
_default_emotion_analyzer = EmotionAnalysisService()


def get_emotion_analyzer() -> EmotionAnalysisService:
    """Returns the default EmotionAnalysisService instance."""
    return _default_emotion_analyzer
