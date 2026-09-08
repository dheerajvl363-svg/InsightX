from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.schemas.dashboard import DashboardOverviewResponse, PlatformComparisonResponse
from app.schemas.data_quality import AnalyticsReadyPost
from app.schemas.intelligence import (
    BatchInsightResult,
    InsightItem,
    IntelligenceAnalyzeRequest,
)
from app.schemas.network import BatchNetworkResult
from app.schemas.sentiment import BatchSentimentResult
from app.schemas.topic import BatchTopicResult, ExtractedTopic
from app.schemas.trend import BatchTrendResult, TopicTrendResult


class BaseIntelligenceEngine(ABC):
    """
    Abstract interface for evidence-grounded intelligence synthesis engines.
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Returns the unique identifier and version string of the engine."""
        pass

    @abstractmethod
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
        Synthesizes structured, evidence-grounded insights from multi-facet analytics.
        """
        pass
