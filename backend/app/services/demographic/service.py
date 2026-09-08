from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from app.schemas.data_quality import AnalyticsReadyPost
from app.schemas.demographic import (
    BatchDemographicResult,
    DemographicDistribution,
    DemographicProfile,
    LocationData,
    SentimentDemographicResult,
    TopicDemographicResult,
    TrendDemographicResult,
)
from app.schemas.sentiment import SentimentResult
from app.schemas.topic import ExtractedTopic
from app.schemas.trend import TopicTrendResult
from app.services.demographic.base import BaseDemographicEngine
from app.services.demographic.engine import RuleBasedDemographicEngine


class DemographicAnalysisService:
    """
    Demographic Intelligence Service for Phase 3.
    Aggregates user demographic metadata across Age, Gender, and Location
    in a privacy-preserving manner without fabricating non-existent data.
    """

    def __init__(self, engine: Optional[BaseDemographicEngine] = None):
        self.engine = engine or RuleBasedDemographicEngine()

    def extract_profiles_from_posts(
        self,
        posts: List[AnalyticsReadyPost],
    ) -> List[DemographicProfile]:
        """
        Extracts available demographic metadata from AnalyticsReadyPost instances.
        Reads from post.metadata (e.g. 'demographics', 'age', 'gender', 'location', 'country')
        without fabricating missing information.
        """
        profiles: List[DemographicProfile] = []

        for post in posts:
            if not isinstance(post, AnalyticsReadyPost):
                continue

            meta = post.metadata or {}
            demo_data = meta.get("demographics") or meta.get("user_demographics")
            if not isinstance(demo_data, dict):
                demo_data = {}

            age = demo_data.get("age") if "age" in demo_data else meta.get("age")
            age_group = demo_data.get("age_group") if "age_group" in demo_data else meta.get("age_group")
            gender = demo_data.get("gender") if "gender" in demo_data else meta.get("gender")

            loc_raw = demo_data.get("location") if "location" in demo_data else meta.get("location")
            country = demo_data.get("country") if "country" in demo_data else meta.get("country")
            region = demo_data.get("region") or demo_data.get("state") if ("region" in demo_data or "state" in demo_data) else (meta.get("region") or meta.get("state"))
            city = demo_data.get("city") if "city" in demo_data else meta.get("city")

            # Build location structure
            location_val: Optional[Union[LocationData, str]] = None
            if isinstance(loc_raw, (LocationData, str)):
                location_val = loc_raw
            elif country or region or city:
                location_val = LocationData(country=country, region=region, city=city)

            profile = DemographicProfile(
                post_id=post.id,
                external_post_id=post.external_post_id,
                author_username=post.author_username,
                age=age,
                age_group=age_group,
                gender=gender,
                location=location_val,
                metadata={k: v for k, v in meta.items() if k not in {"demographics", "age", "gender", "location"}},
            )
            profiles.append(profile)


        return profiles

    def _ensure_profiles(
        self,
        input_data: Union[List[DemographicProfile], List[AnalyticsReadyPost]],
    ) -> List[DemographicProfile]:
        """Converts AnalyticsReadyPost list to DemographicProfile list if necessary."""
        if not isinstance(input_data, list):
            raise TypeError(f"Expected list of DemographicProfile or AnalyticsReadyPost, got {type(input_data).__name__}")

        if not input_data:
            return []

        first = input_data[0]
        if isinstance(first, DemographicProfile):
            for item in input_data:
                if not isinstance(item, DemographicProfile):
                    raise TypeError(f"Inconsistent list types: expected DemographicProfile, got {type(item).__name__}")
            return input_data  # type: ignore

        elif isinstance(first, AnalyticsReadyPost):
            return self.extract_profiles_from_posts(input_data)  # type: ignore

        else:
            raise TypeError(f"Unsupported item type in demographic analysis: {type(first).__name__}")

    def aggregate_distribution(
        self,
        data: Union[List[DemographicProfile], List[AnalyticsReadyPost]],
    ) -> DemographicDistribution:
        """
        Aggregates overall demographic distributions across Age, Gender, and Geography.
        """
        profiles = self._ensure_profiles(data)
        return self.engine.aggregate_distribution(profiles)

    def analyze_topic_demographics(
        self,
        topic: ExtractedTopic,
        data: Union[List[DemographicProfile], List[AnalyticsReadyPost]],
    ) -> TopicDemographicResult:
        """
        Calculates demographic composition for an extracted topic.
        """
        if not isinstance(topic, ExtractedTopic):
            raise TypeError(f"Expected ExtractedTopic, got {type(topic).__name__}")

        profiles = self._ensure_profiles(data)
        return self.engine.analyze_topic_demographics(topic, profiles)

    def analyze_sentiment_demographics(
        self,
        sentiment_label: str,
        data: Union[List[DemographicProfile], List[AnalyticsReadyPost]],
    ) -> SentimentDemographicResult:
        """
        Calculates demographic distributions associated with a sentiment category.
        """
        profiles = self._ensure_profiles(data)
        return self.engine.analyze_sentiment_demographics(sentiment_label, profiles)

    def analyze_trend_demographics(
        self,
        trend: TopicTrendResult,
        data: Union[List[DemographicProfile], List[AnalyticsReadyPost]],
    ) -> TrendDemographicResult:
        """
        Calculates demographic distributions driving a trending topic.
        """
        if not isinstance(trend, TopicTrendResult):
            raise TypeError(f"Expected TopicTrendResult, got {type(trend).__name__}")

        profiles = self._ensure_profiles(data)
        return self.engine.analyze_trend_demographics(trend, profiles)

    def analyze_batch(
        self,
        data: Union[List[DemographicProfile], List[AnalyticsReadyPost]],
        topics: Optional[List[ExtractedTopic]] = None,
        sentiment_results: Optional[List[SentimentResult]] = None,
        trend_results: Optional[List[TopicTrendResult]] = None,
    ) -> BatchDemographicResult:
        """
        Generates comprehensive multi-dimensional demographic intelligence report.
        """
        profiles = self._ensure_profiles(data)
        return self.engine.analyze_batch(
            profiles=profiles,
            topics=topics,
            sentiment_results=sentiment_results,
            trend_results=trend_results,
        )


# Global default service instance
_default_demographic_analyzer = DemographicAnalysisService()


def get_demographic_analyzer() -> DemographicAnalysisService:
    """Provides singleton instance of DemographicAnalysisService."""
    return _default_demographic_analyzer
