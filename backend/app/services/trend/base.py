from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Optional

from app.schemas.data_quality import AnalyticsReadyPost
from app.schemas.topic import ExtractedTopic
from app.schemas.trend import TopicTrendResult


class BaseTrendEngine(ABC):
    """
    Abstract Base Class for Phase 3 Trend Detection and Emerging Narrative Engines.
    Provides a standardized interface for calculating temporal velocity,
    growth rates, spikes, and topic trajectory states.
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Returns the canonical model name and version identifier."""
        pass

    @abstractmethod
    def analyze_topic_trend(
        self,
        topic: ExtractedTopic,
        posts: List[AnalyticsReadyPost],
        reference_time: Optional[datetime] = None,
        window_duration: Optional[timedelta] = None,
    ) -> TopicTrendResult:
        """
        Analyzes the temporal volume trend for a single topic cluster.
        """
        pass

    @abstractmethod
    def analyze_batch_trends(
        self,
        topics: List[ExtractedTopic],
        posts: List[AnalyticsReadyPost],
        reference_time: Optional[datetime] = None,
        window_duration: Optional[timedelta] = None,
    ) -> List[TopicTrendResult]:
        """
        Analyzes temporal trends across multiple topic clusters in batch.
        """
        pass
