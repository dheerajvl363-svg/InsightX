from datetime import datetime, timedelta, timezone
from typing import List, Optional, Union

from app.schemas.data_quality import AnalyticsReadyPost
from app.schemas.topic import BatchTopicResult, ExtractedTopic
from app.schemas.trend import (
    BatchTrendResult,
    TopicTrendResult,
    TrendDirection,
)
from app.services.trend.base import BaseTrendEngine
from app.services.trend.engine import StatisticalTrendEngine


class TrendAnalysisService:
    """
    Trend Analysis and Emerging Narrative Detection Service for Phase 3.
    Consumes extracted topics and timestamped AnalyticsReadyPost instances,
    evaluating velocity, temporal growth, statistical surges, and emerging narratives.
    """

    def __init__(self, engine: Optional[BaseTrendEngine] = None):
        self.engine = engine or StatisticalTrendEngine()

    def analyze_topic(
        self,
        topic: ExtractedTopic,
        posts: List[AnalyticsReadyPost],
        reference_time: Optional[datetime] = None,
        window_duration: Optional[timedelta] = None,
    ) -> TopicTrendResult:
        """
        Analyzes the volume trajectory and trend classification for a single topic.
        """
        if not isinstance(topic, ExtractedTopic):
            raise TypeError(f"Expected ExtractedTopic, got {type(topic).__name__}")
        if not isinstance(posts, list):
            raise TypeError(f"Expected list of AnalyticsReadyPost, got {type(posts).__name__}")
        for p in posts:
            if not isinstance(p, AnalyticsReadyPost):
                raise TypeError(f"Expected AnalyticsReadyPost elements, found {type(p).__name__}")

        return self.engine.analyze_topic_trend(
            topic=topic,
            posts=posts,
            reference_time=reference_time,
            window_duration=window_duration,
        )

    def analyze_trends(
        self,
        topics: Union[List[ExtractedTopic], BatchTopicResult],
        posts: List[AnalyticsReadyPost],
        reference_time: Optional[datetime] = None,
        window_duration: Optional[timedelta] = None,
    ) -> BatchTrendResult:
        """
        Analyzes temporal trends across multiple topics or a BatchTopicResult.
        """
        if isinstance(topics, BatchTopicResult):
            topic_list = topics.topics
        elif isinstance(topics, list):
            topic_list = topics
        else:
            raise TypeError(f"Expected List[ExtractedTopic] or BatchTopicResult, got {type(topics).__name__}")

        for t in topic_list:
            if not isinstance(t, ExtractedTopic):
                raise TypeError(f"Expected ExtractedTopic elements in topic list, found {type(t).__name__}")

        if not isinstance(posts, list):
            raise TypeError(f"Expected list of AnalyticsReadyPost, got {type(posts).__name__}")
        for p in posts:
            if not isinstance(p, AnalyticsReadyPost):
                raise TypeError(f"Expected AnalyticsReadyPost elements, found {type(p).__name__}")

        if not topic_list:
            return BatchTrendResult(
                total_topics_evaluated=0,
                emerging_topics_count=0,
                spiking_topics_count=0,
                growing_topics_count=0,
                trends=[],
                model=self.engine.model_name,
                analyzed_at=datetime.now(timezone.utc),
            )

        trend_results = self.engine.analyze_batch_trends(
            topics=topic_list,
            posts=posts,
            reference_time=reference_time,
            window_duration=window_duration,
        )

        emerging_count = sum(1 for t in trend_results if t.direction == TrendDirection.EMERGING or t.is_emerging)
        spiking_count = sum(1 for t in trend_results if t.direction == TrendDirection.SPIKING or t.is_spiking)
        growing_count = sum(1 for t in trend_results if t.direction == TrendDirection.GROWING)

        return BatchTrendResult(
            total_topics_evaluated=len(topic_list),
            emerging_topics_count=emerging_count,
            spiking_topics_count=spiking_count,
            growing_topics_count=growing_count,
            trends=trend_results,
            model=self.engine.model_name,
            analyzed_at=datetime.now(timezone.utc),
        )


# Global default service instance
_default_trend_analyzer = TrendAnalysisService()


def get_trend_analyzer() -> TrendAnalysisService:
    """Provides the singleton instance of TrendAnalysisService."""
    return _default_trend_analyzer
