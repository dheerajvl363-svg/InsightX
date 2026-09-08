from abc import ABC, abstractmethod
from typing import List, Optional

from app.schemas.demographic import (
    BatchDemographicResult,
    DemographicDistribution,
    DemographicProfile,
    SentimentDemographicResult,
    TopicDemographicResult,
    TrendDemographicResult,
)
from app.schemas.sentiment import SentimentResult
from app.schemas.topic import ExtractedTopic
from app.schemas.trend import TopicTrendResult


class BaseDemographicEngine(ABC):
    """
    Abstract Base Class for Demographic Intelligence Engines.
    Provides standardized methods for privacy-preserving demographic aggregation
    across Age, Gender, and Location dimensions.
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Returns the canonical model name and version identifier."""
        pass

    @abstractmethod
    def aggregate_distribution(
        self,
        profiles: List[DemographicProfile],
    ) -> DemographicDistribution:
        """
        Aggregates demographic distributions across Age, Gender, and Geography.
        """
        pass

    @abstractmethod
    def analyze_topic_demographics(
        self,
        topic: ExtractedTopic,
        profiles: List[DemographicProfile],
    ) -> TopicDemographicResult:
        """
        Calculates the demographic composition for a single topic cluster.
        """
        pass

    @abstractmethod
    def analyze_sentiment_demographics(
        self,
        sentiment_label: str,
        profiles: List[DemographicProfile],
    ) -> SentimentDemographicResult:
        """
        Calculates demographic distributions associated with a sentiment class.
        """
        pass

    @abstractmethod
    def analyze_trend_demographics(
        self,
        trend: TopicTrendResult,
        profiles: List[DemographicProfile],
    ) -> TrendDemographicResult:
        """
        Calculates demographic distributions driving a trending topic.
        """
        pass

    @abstractmethod
    def analyze_batch(
        self,
        profiles: List[DemographicProfile],
        topics: Optional[List[ExtractedTopic]] = None,
        sentiment_results: Optional[List[SentimentResult]] = None,
        trend_results: Optional[List[TopicTrendResult]] = None,
    ) -> BatchDemographicResult:
        """
        Generates a comprehensive multi-dimensional demographic intelligence report.
        """
        pass
