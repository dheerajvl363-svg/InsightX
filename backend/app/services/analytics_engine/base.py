from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.schemas.analytics_engine import (
    DetailedEngagementReport,
    DetailedSentimentReport,
    DetailedTrendReport,
    EngagementDistribution,
    EngagementScoreBreakdown,
    IntervalUnit,
    NarrativeIntelligence,
    Phase4AnalyticsReport,
    PlatformComparativeReport,
    PlatformSentimentSummary,
    PlatformTrendSummary,
    PostEngagementProfile,
    PostSentimentProfile,
    SentimentDistributionSummary,
    TemporalDynamicsReport,
    TemporalSentimentPoint,
    TrendItemProfile,
    TrendMomentumMetrics,
)


class BaseEngagementEngine(ABC):
    """Abstract interface for multi-metric engagement and virality scoring."""

    @abstractmethod
    def calculate_engagement(self, posts: List[Any]) -> EngagementScoreBreakdown:
        """Calculate weighted engagement scores, virality index, and interaction rates."""
        pass

    @abstractmethod
    def calculate_platform_breakdown(self, posts: List[Any]) -> Dict[str, EngagementScoreBreakdown]:
        """Calculate engagement breakdowns partitioned by social platform."""
        pass

    @abstractmethod
    def calculate_distribution(self, posts: List[Any]) -> EngagementDistribution:
        """Calculate statistical distribution of engagement scores across posts."""
        pass

    @abstractmethod
    def extract_top_posts(
        self, posts: List[Any], limit: int = 10, outlier_sigma: float = 2.0
    ) -> Any:
        """Extract top engaging posts and statistically high outliers."""
        pass

    @abstractmethod
    def calculate_platform_comparison(self, posts: List[Any]) -> PlatformComparativeReport:
        """Calculate cross-platform comparative benchmarks, shares, and efficiency rankings."""
        pass

    @abstractmethod
    def generate_detailed_report(self, posts: List[Any], top_limit: int = 10) -> DetailedEngagementReport:
        """Generate comprehensive Phase 4.2 multi-dimensional engagement analysis report."""
        pass


class BaseTimeSeriesEngine(ABC):
    """Abstract interface for temporal bucketing, moving averages, and anomaly detection."""

    @abstractmethod
    def generate_time_series(
        self,
        posts: List[Any],
        interval_unit: IntervalUnit = IntervalUnit.HOUR,
        rolling_window_size: int = 3,
        anomaly_threshold_z: float = 2.0,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> TemporalDynamicsReport:
        """Generate discrete temporal buckets with rolling statistics and peak/anomaly detection."""
        pass


class BaseNarrativeEngine(ABC):
    """Abstract interface for narrative lifecycle tracking and trajectory modeling."""

    @abstractmethod
    def analyze_narratives(
        self,
        posts: List[Any],
        topics: Optional[List[Any]] = None,
        reference_time: Optional[datetime] = None,
        split_ratio: float = 0.5,
    ) -> List[NarrativeIntelligence]:
        """Analyze topic lifecycle stages, velocity, acceleration, and sentiment drift."""
        pass


class BaseSentimentAnalyticsEngine(ABC):
    """Abstract interface for multi-dimensional sentiment analysis and aggregated dynamics."""

    @abstractmethod
    def analyze_post(self, post: Any) -> PostSentimentProfile:
        """Analyze polarity and confidence for an individual post."""
        pass

    @abstractmethod
    def analyze_batch(self, posts: List[Any]) -> List[PostSentimentProfile]:
        """Analyze a collection of posts and produce itemized sentiment profiles."""
        pass

    @abstractmethod
    def calculate_distribution(self, posts: List[Any]) -> SentimentDistributionSummary:
        """Calculate aggregated sentiment counts, percentages, and net score."""
        pass

    @abstractmethod
    def calculate_platform_sentiment(self, posts: List[Any]) -> Dict[str, PlatformSentimentSummary]:
        """Calculate sentiment distribution partitioned by social media platform."""
        pass

    @abstractmethod
    def calculate_temporal_sentiment(
        self, posts: List[Any], interval_unit: IntervalUnit = IntervalUnit.HOUR
    ) -> List[TemporalSentimentPoint]:
        """Calculate temporal net sentiment evolution across continuous time intervals."""
        pass

    @abstractmethod
    def generate_detailed_report(
        self, posts: List[Any], top_limit: int = 5, interval_unit: IntervalUnit = IntervalUnit.HOUR
    ) -> DetailedSentimentReport:
        """Generate comprehensive Phase 4.3 sentiment analytics report."""
        pass


class BaseTrendAnalyticsEngine(ABC):
    """Abstract interface for temporal trend detection, velocity, and momentum scoring."""

    @abstractmethod
    def calculate_trend_momentum(
        self,
        current_volume: int,
        baseline_volume: int,
        current_engagement: float = 0.0,
        baseline_engagement: float = 0.0,
        z_score: float = 0.0,
    ) -> TrendMomentumMetrics:
        """Calculate growth rate, velocity, acceleration, and momentum score."""
        pass

    @abstractmethod
    def analyze_trends(
        self,
        posts: List[Any],
        topics: Optional[List[Any]] = None,
        reference_time: Optional[datetime] = None,
    ) -> List[TrendItemProfile]:
        """Identify and score trending topics, keywords, and hashtags."""
        pass

    @abstractmethod
    def calculate_platform_trends(
        self, posts: List[Any], top_limit: int = 5
    ) -> Dict[str, PlatformTrendSummary]:
        """Calculate trend rankings partitioned by platform."""
        pass

    @abstractmethod
    def generate_detailed_report(
        self,
        posts: List[Any],
        topics: Optional[List[Any]] = None,
        top_limit: int = 10,
        reference_time: Optional[datetime] = None,
    ) -> DetailedTrendReport:
        """Generate comprehensive Phase 4.4 Trend Analytics report."""
        pass


class BaseAnalyticsEngine(ABC):
    """High-level facade interface orchestrating full Phase 4 analytics."""

    @abstractmethod
    def analyze(
        self,
        posts: List[Any],
        topics: Optional[List[Any]] = None,
        interval_unit: IntervalUnit = IntervalUnit.HOUR,
        reference_time: Optional[datetime] = None,
    ) -> Phase4AnalyticsReport:
        """Produce a comprehensive unified Phase 4 analytical intelligence report."""
        pass
