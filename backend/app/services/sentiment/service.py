from datetime import datetime, timezone
from typing import List, Optional, Union

from app.schemas.data_quality import AnalyticsReadyPost
from app.schemas.sentiment import (
    BatchSentimentResult,
    SentimentLabel,
    SentimentResult,
)
from app.services.sentiment.base import BaseSentimentEngine
from app.services.sentiment.engine import RuleBasedSentimentEngine


class SentimentAnalysisService:
    """
    Core Sentiment Analysis service for Phase 3.
    Consumes AnalyticsReadyPost records produced by Component 3.1 DataQualityService,
    runs sentiment inference through a swappable engine, and outputs structured SentimentResult.
    """

    def __init__(self, engine: Optional[BaseSentimentEngine] = None):
        self.engine = engine or RuleBasedSentimentEngine()

    def analyze(self, post: AnalyticsReadyPost) -> SentimentResult:
        """
        Analyzes sentiment for a validated AnalyticsReadyPost instance.
        """
        if not isinstance(post, AnalyticsReadyPost):
            raise TypeError(f"Expected AnalyticsReadyPost, got {type(post).__name__}")

        inference = self.engine.analyze_text(post.text)

        return SentimentResult(
            post_id=post.id,
            external_post_id=post.external_post_id,
            label=inference.label,
            score=inference.score,
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
    ) -> SentimentResult:
        """
        Direct text inference convenience method.
        """
        inference = self.engine.analyze_text(text or "")

        return SentimentResult(
            post_id=post_id,
            external_post_id=external_post_id,
            label=inference.label,
            score=inference.score,
            confidence=inference.confidence,
            probabilities=inference.probabilities,
            model=inference.model_name,
            analyzed_at=datetime.now(timezone.utc),
            details=inference.details,
        )

    def analyze_batch(self, posts: List[AnalyticsReadyPost]) -> BatchSentimentResult:
        """
        Analyzes sentiment across a batch of AnalyticsReadyPost instances.
        Returns aggregated class counts, average polarity, and itemized results.
        """
        if not posts:
            return BatchSentimentResult(
                total_analyzed=0,
                positive_count=0,
                neutral_count=0,
                negative_count=0,
                average_score=0.0,
                results=[],
            )

        results: List[SentimentResult] = []
        pos_count = 0
        neu_count = 0
        neg_count = 0
        total_score = 0.0

        for post in posts:
            res = self.analyze(post)
            results.append(res)
            total_score += res.score

            if res.label == SentimentLabel.POSITIVE:
                pos_count += 1
            elif res.label == SentimentLabel.NEGATIVE:
                neg_count += 1
            else:
                neu_count += 1

        avg_score = round(total_score / len(posts), 4) if posts else 0.0

        return BatchSentimentResult(
            total_analyzed=len(posts),
            positive_count=pos_count,
            neutral_count=neu_count,
            negative_count=neg_count,
            average_score=avg_score,
            results=results,
        )


# Global helper instance
_default_analyzer = SentimentAnalysisService()


def get_sentiment_analyzer() -> SentimentAnalysisService:
    """Returns the default SentimentAnalysisService instance."""
    return _default_analyzer
