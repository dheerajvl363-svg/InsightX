from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.schemas.analytics_engine import (
    EngagementScoreBreakdown,
    IntervalUnit,
    NarrativeIntelligence,
    Phase4AnalyticsReport,
    TemporalDynamicsReport,
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
