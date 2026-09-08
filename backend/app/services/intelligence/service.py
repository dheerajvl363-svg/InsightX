from typing import List, Optional

from app.schemas.dashboard import DashboardOverviewResponse, PlatformComparisonResponse
from app.schemas.data_quality import AnalyticsReadyPost
from app.schemas.intelligence import BatchInsightResult
from app.schemas.network import BatchNetworkResult
from app.schemas.sentiment import BatchSentimentResult
from app.schemas.topic import BatchTopicResult, ExtractedTopic
from app.schemas.trend import BatchTrendResult, TopicTrendResult
from app.services.intelligence.base import BaseIntelligenceEngine
from app.services.intelligence.engine import DeterministicIntelligenceEngine


class IntelligenceAnalysisService:
    """
    Service wrapper for evidence-grounded intelligence generation.
    """

    def __init__(self, engine: Optional[BaseIntelligenceEngine] = None):
        self.engine = engine or DeterministicIntelligenceEngine()

    @property
    def model_name(self) -> str:
        return self.engine.model_name

    def generate_insights(
        self,
        trends: Optional[List[TopicTrendResult]] = None,
        batch_trend: Optional[BatchTrendResult] = None,
        topics: Optional[List[ExtractedTopic]] = None,
        batch_topic: Optional[BatchTopicResult] = None,
        sentiment: Optional[BatchSentimentResult] = None,
        overview: Optional[DashboardOverviewResponse] = None,
        platform_comparison: Optional[PlatformComparisonResponse] = None,
        network: Optional[BatchNetworkResult] = None,
        posts: Optional[List[AnalyticsReadyPost]] = None,
        min_confidence: float = 0.5,
        max_insights: int = 20,
    ) -> BatchInsightResult:
        """
        Synthesizes structured intelligence insights across provided analytics.
        """
        return self.engine.generate_insights(
            trends=trends,
            batch_trend=batch_trend,
            topics=topics,
            batch_topic=batch_topic,
            sentiment=sentiment,
            overview=overview,
            platform_comparison=platform_comparison,
            network=network,
            posts=posts,
            min_confidence=min_confidence,
            max_insights=max_insights,
        )


_global_intelligence_service: Optional[IntelligenceAnalysisService] = None


def get_intelligence_analyzer() -> IntelligenceAnalysisService:
    """Singleton dependency provider for IntelligenceAnalysisService."""
    global _global_intelligence_service
    if _global_intelligence_service is None:
        _global_intelligence_service = IntelligenceAnalysisService()
    return _global_intelligence_service
