from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from app.schemas.demographic import (
    AgeGroup,
    BatchDemographicResult,
    DemographicBreakdown,
    DemographicDistribution,
    DemographicProfile,
    GenderCategory,
    LocationData,
    SentimentDemographicResult,
    TopicDemographicResult,
    TrendDemographicResult,
)
from app.schemas.sentiment import SentimentResult
from app.schemas.topic import ExtractedTopic
from app.schemas.trend import TopicTrendResult
from app.services.demographic.base import BaseDemographicEngine


# Canonical mappings for gender normalization
GENDER_SYNONYM_MAP: Dict[str, str] = {
    "female": "female",
    "f": "female",
    "woman": "female",
    "girl": "female",
    "male": "male",
    "m": "male",
    "man": "male",
    "boy": "male",
    "non_binary": "non_binary",
    "non-binary": "non_binary",
    "nonbinary": "non_binary",
    "nb": "non_binary",
    "enby": "non_binary",
    "other": "other",
    "trans": "other",
    "transgender": "other",
    "genderfluid": "other",
    "queer": "other",
    "unknown": "unknown",
    "prefer_not_to_say": "unknown",
    "none": "unknown",
    "null": "unknown",
    "n/a": "unknown",
}


class RuleBasedDemographicEngine(BaseDemographicEngine):
    """
    Deterministic, privacy-preserving demographic aggregation engine.
    Aggregates explicit demographic attributes into age groups, gender categories,
    and geographic distributions with configurable k-anonymity suppression.
    """

    def __init__(
        self,
        min_group_size: int = 0,
    ):
        self.min_group_size = max(0, min_group_size)

    @property
    def model_name(self) -> str:
        return "insightx-demographic-rule-v1"

    def normalize_age_group(
        self,
        age: Optional[int],
        age_group: Optional[Union[AgeGroup, str]],
    ) -> str:
        """
        Maps raw age or age-group string to canonical AgeGroup enum value.
        Gracefully handles missing, boundary, and unrealistic age values.
        """
        if age_group is not None:
            val = str(age_group.value if isinstance(age_group, AgeGroup) else age_group).strip().lower()
            valid_groups = {g.value.lower(): g.value for g in AgeGroup}
            if val in valid_groups:
                return valid_groups[val]

        if age is not None:
            try:
                numeric_age = int(age)
            except (ValueError, TypeError):
                return AgeGroup.UNKNOWN.value

            if numeric_age < 0 or numeric_age > 125:
                return AgeGroup.UNKNOWN.value
            elif numeric_age < 18:
                return AgeGroup.UNDER_18.value
            elif 18 <= numeric_age <= 24:
                return AgeGroup.AGE_18_24.value
            elif 25 <= numeric_age <= 34:
                return AgeGroup.AGE_25_34.value
            elif 35 <= numeric_age <= 44:
                return AgeGroup.AGE_35_44.value
            elif 45 <= numeric_age <= 54:
                return AgeGroup.AGE_45_54.value
            else:
                return AgeGroup.AGE_55_PLUS.value

        return AgeGroup.UNKNOWN.value

    def normalize_gender(
        self,
        gender: Optional[Union[GenderCategory, str]],
    ) -> str:
        """
        Normalizes gender strings and categorical representations.
        """
        if gender is None:
            return GenderCategory.UNKNOWN.value

        if isinstance(gender, GenderCategory):
            return gender.value

        cleaned = str(gender).strip().lower().replace(" ", "_")
        if not cleaned:
            return GenderCategory.UNKNOWN.value

        return GENDER_SYNONYM_MAP.get(cleaned, cleaned)

    def extract_location_fields(
        self,
        location: Optional[Union[LocationData, str, Dict[str, Any]]],
    ) -> Tuple[str, str, str]:
        """
        Extracts normalized (country, region, city) from location metadata.
        Returns 'unknown' for absent or unparseable fields.
        """
        country = "unknown"
        region = "unknown"
        city = "unknown"

        if location is None:
            return country, region, city

        if isinstance(location, LocationData):
            if location.country and location.country.strip():
                country = location.country.strip().title()
            if location.region and location.region.strip():
                region = location.region.strip().title()
            if location.city and location.city.strip():
                city = location.city.strip().title()
            return country, region, city

        if isinstance(location, dict):
            c = location.get("country")
            r = location.get("region") or location.get("state")
            ci = location.get("city")
            if c and str(c).strip():
                country = str(c).strip().title()
            if r and str(r).strip():
                region = str(r).strip().title()
            if ci and str(ci).strip():
                city = str(ci).strip().title()
            return country, region, city

        if isinstance(location, str):
            clean_str = location.strip()
            if not clean_str or clean_str.lower() in {"unknown", "n/a", "none"}:
                return country, region, city

            # Parse comma-separated location strings (e.g. "Hyderabad, Telangana, India")
            parts = [p.strip().title() for p in clean_str.split(",") if p.strip()]
            if len(parts) == 1:
                country = parts[0]
            elif len(parts) == 2:
                city = parts[0]
                country = parts[1]
            elif len(parts) >= 3:
                city = parts[0]
                region = parts[1]
                country = parts[2]

        return country, region, city

    def _build_breakdown(
        self,
        counts: Dict[str, int],
    ) -> DemographicBreakdown:
        """
        Builds a safe, privacy-preserving DemographicBreakdown with percentages.
        Enforces minimum group size threshold suppression when configured.
        """
        processed_counts: Dict[str, int] = dict(counts)

        # Apply minimum group-size suppression to prevent identification of tiny groups
        if self.min_group_size > 0:
            suppressed_count = 0
            keys_to_suppress = []
            for k, count in processed_counts.items():
                if k not in {"unknown", "other", "suppressed"} and 0 < count < self.min_group_size:
                    suppressed_count += count
                    keys_to_suppress.append(k)

            for k in keys_to_suppress:
                del processed_counts[k]

            if suppressed_count > 0:
                processed_counts["suppressed"] = processed_counts.get("suppressed", 0) + suppressed_count

        total = sum(processed_counts.values())
        if total == 0:
            return DemographicBreakdown(
                counts={},
                percentages={},
                total_known=0,
                total_unknown=0,
                coverage_percentage=0.0,
            )

        unknown_count = processed_counts.get("unknown", 0)
        known_count = max(0, total - unknown_count)
        coverage_pct = round((known_count / float(total)) * 100.0, 2)

        percentages = {
            k: round((v / float(total)) * 100.0, 2)
            for k, v in processed_counts.items()
        }

        return DemographicBreakdown(
            counts=processed_counts,
            percentages=percentages,
            total_known=known_count,
            total_unknown=unknown_count,
            coverage_percentage=coverage_pct,
        )

    def aggregate_distribution(
        self,
        profiles: List[DemographicProfile],
    ) -> DemographicDistribution:
        """
        Aggregates demographic distributions across Age, Gender, and Location.
        """
        if not profiles:
            empty_bd = self._build_breakdown({})
            return DemographicDistribution(
                total_records_analyzed=0,
                age_groups=empty_bd,
                gender=empty_bd,
                countries=empty_bd,
                regions=empty_bd,
                cities=empty_bd,
            )

        age_counts: Dict[str, int] = defaultdict(int)
        gender_counts: Dict[str, int] = defaultdict(int)
        country_counts: Dict[str, int] = defaultdict(int)
        region_counts: Dict[str, int] = defaultdict(int)
        city_counts: Dict[str, int] = defaultdict(int)

        for p in profiles:
            age_grp = self.normalize_age_group(p.age, p.age_group)
            gender_cat = self.normalize_gender(p.gender)
            country, region, city = self.extract_location_fields(p.location)

            age_counts[age_grp] += 1
            gender_counts[gender_cat] += 1
            country_counts[country] += 1
            region_counts[region] += 1
            city_counts[city] += 1

        return DemographicDistribution(
            total_records_analyzed=len(profiles),
            age_groups=self._build_breakdown(age_counts),
            gender=self._build_breakdown(gender_counts),
            countries=self._build_breakdown(country_counts),
            regions=self._build_breakdown(region_counts),
            cities=self._build_breakdown(city_counts),
        )

    def _filter_profiles_for_post_ids(
        self,
        post_ids: List[int],
        external_post_ids: List[str],
        profiles: List[DemographicProfile],
    ) -> List[DemographicProfile]:
        """Filters demographic profiles matching specified post identifiers."""
        pid_set = set(post_ids)
        ext_set = set(external_post_ids)

        matched: List[DemographicProfile] = []
        for p in profiles:
            if p.post_id is not None and p.post_id in pid_set:
                matched.append(p)
            elif p.external_post_id and p.external_post_id in ext_set:
                matched.append(p)

        return matched

    def analyze_topic_demographics(
        self,
        topic: ExtractedTopic,
        profiles: List[DemographicProfile],
    ) -> TopicDemographicResult:
        """
        Calculates demographic distributions associated with an extracted topic cluster.
        """
        topic_profiles = self._filter_profiles_for_post_ids(
            post_ids=topic.post_ids,
            external_post_ids=topic.external_post_ids,
            profiles=profiles,
        )

        dist = self.aggregate_distribution(topic_profiles)
        return TopicDemographicResult(
            topic_id=topic.topic_id,
            topic_label=topic.label,
            post_count=topic.post_count,
            demographics=dist,
        )

    def analyze_sentiment_demographics(
        self,
        sentiment_label: str,
        profiles: List[DemographicProfile],
    ) -> SentimentDemographicResult:
        """
        Calculates demographic distributions associated with a sentiment class.
        """
        dist = self.aggregate_distribution(profiles)
        return SentimentDemographicResult(
            sentiment_label=str(sentiment_label).lower(),
            post_count=len(profiles),
            demographics=dist,
        )

    def analyze_trend_demographics(
        self,
        trend: TopicTrendResult,
        profiles: List[DemographicProfile],
    ) -> TrendDemographicResult:
        """
        Calculates demographic distributions driving a trending topic.
        """
        trend_profiles = self._filter_profiles_for_post_ids(
            post_ids=trend.post_ids,
            external_post_ids=trend.external_post_ids,
            profiles=profiles,
        )

        dist = self.aggregate_distribution(trend_profiles)
        return TrendDemographicResult(
            topic_id=trend.topic_id,
            topic_label=trend.topic_label,
            trend_direction=trend.direction.value if hasattr(trend.direction, "value") else str(trend.direction),
            growth_rate=trend.growth_rate,
            demographics=dist,
        )

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
        overall_dist = self.aggregate_distribution(profiles)

        # Topic breakdowns
        topic_breakdowns: List[TopicDemographicResult] = []
        if topics:
            for t in topics:
                topic_breakdowns.append(self.analyze_topic_demographics(t, profiles))

        # Sentiment breakdowns
        sentiment_breakdowns: List[SentimentDemographicResult] = []
        if sentiment_results:
            # Build post lookup for profiles
            sentiment_profiles_by_label: Dict[str, List[DemographicProfile]] = defaultdict(list)
            post_id_to_profile: Dict[int, DemographicProfile] = {
                p.post_id: p for p in profiles if p.post_id is not None
            }
            ext_id_to_profile: Dict[str, DemographicProfile] = {
                p.external_post_id: p for p in profiles if p.external_post_id
            }

            for s in sentiment_results:
                matched_profile = None
                if s.post_id is not None and s.post_id in post_id_to_profile:
                    matched_profile = post_id_to_profile[s.post_id]
                elif s.external_post_id and s.external_post_id in ext_id_to_profile:
                    matched_profile = ext_id_to_profile[s.external_post_id]

                if matched_profile:
                    lbl = s.label.value if hasattr(s.label, "value") else str(s.label)
                    sentiment_profiles_by_label[lbl].append(matched_profile)

            for lbl, p_list in sentiment_profiles_by_label.items():
                sentiment_breakdowns.append(self.analyze_sentiment_demographics(lbl, p_list))

        # Trend breakdowns
        trend_breakdowns: List[TrendDemographicResult] = []
        if trend_results:
            for tr in trend_results:
                trend_breakdowns.append(self.analyze_trend_demographics(tr, profiles))

        return BatchDemographicResult(
            total_profiles_analyzed=len(profiles),
            overall_distribution=overall_dist,
            topic_breakdowns=topic_breakdowns,
            sentiment_breakdowns=sentiment_breakdowns,
            trend_breakdowns=trend_breakdowns,
            model=self.model_name,
            analyzed_at=datetime.now(timezone.utc),
        )
