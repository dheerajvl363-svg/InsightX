from datetime import datetime, timezone
import unittest

from app.schemas.data_quality import AnalyticsReadyPost
from app.schemas.demographic import (
    AgeGroup,
    BatchDemographicResult,
    DemographicBreakdown,
    DemographicDistribution,
    DemographicProfile,
    GenderCategory,
    LocationData,
    TopicDemographicResult,
)
from app.schemas.sentiment import (
    SentimentLabel,
    SentimentProbabilities,
    SentimentResult,
)
from app.schemas.topic import ExtractedTopic
from app.schemas.trend import (
    TimeWindow,
    TopicTrendResult,
    TrendDirection,
)
from app.services.demographic.base import BaseDemographicEngine
from app.services.demographic.engine import RuleBasedDemographicEngine
from app.services.demographic.service import (
    DemographicAnalysisService,
    get_demographic_analyzer,
)
from app.services.sentiment.service import SentimentAnalysisService


class TestDemographicIntelligenceEngine(unittest.TestCase):
    """
    Comprehensive test suite for Phase 3 Component 3.6:
    Demographic Intelligence Engine and Service.
    """

    def setUp(self):
        self.engine = RuleBasedDemographicEngine(min_group_size=0)
        self.service = DemographicAnalysisService(engine=self.engine)
        self.base_time = datetime(2026, 9, 8, 12, 0, 0, tzinfo=timezone.utc)

    # 1. Age Group Normalization and Boundaries
    def test_1_age_group_normalization(self):
        """Validates age boundary mappings to standardized AgeGroup brackets."""
        cases = [
            (15, "<18"),
            (17, "<18"),
            (18, "18-24"),
            (21, "18-24"),
            (24, "18-24"),
            (25, "25-34"),
            (30, "25-34"),
            (34, "25-34"),
            (35, "35-44"),
            (40, "35-44"),
            (44, "35-44"),
            (45, "45-54"),
            (50, "45-54"),
            (54, "45-54"),
            (55, "55+"),
            (70, "55+"),
            (120, "55+"),
            (-5, "unknown"),     # Invalid negative
            (150, "unknown"),    # Unrealistic age
            (None, "unknown"),   # Missing age
        ]

        for raw_age, expected_group in cases:
            with self.subTest(raw_age=raw_age):
                result = self.engine.normalize_age_group(age=raw_age, age_group=None)
                self.assertEqual(result, expected_group)

    def test_2_pre_bucketed_age_groups(self):
        """Preserves explicit AgeGroup enum values when provided directly."""
        self.assertEqual(self.engine.normalize_age_group(None, AgeGroup.AGE_18_24), "18-24")
        self.assertEqual(self.engine.normalize_age_group(None, "25-34"), "25-34")
        self.assertEqual(self.engine.normalize_age_group(None, "invalid_group"), "unknown")

    # 2. Gender Normalization
    def test_3_gender_normalization(self):
        """Normalizes diverse gender formats into canonical categories."""
        cases = [
            ("Female", "female"),
            ("FEMALE", "female"),
            ("f", "female"),
            ("woman", "female"),
            ("Male", "male"),
            ("m", "male"),
            ("man", "male"),
            ("non-binary", "non_binary"),
            ("Non_Binary", "non_binary"),
            ("enby", "non_binary"),
            ("transgender", "other"),
            ("genderfluid", "other"),
            ("prefer_not_to_say", "unknown"),
            ("unknown", "unknown"),
            ("", "unknown"),
            (None, "unknown"),
        ]

        for raw_gender, expected_category in cases:
            with self.subTest(raw_gender=raw_gender):
                result = self.engine.normalize_gender(raw_gender)
                self.assertEqual(result, expected_category)

    # 3. Location Extraction
    def test_4_location_extraction(self):
        """Parses structured LocationData, dicts, and comma-separated strings."""
        # Structured object
        loc_obj = LocationData(country="India", region="Telangana", city="Hyderabad")
        c, r, ci = self.engine.extract_location_fields(loc_obj)
        self.assertEqual(c, "India")
        self.assertEqual(r, "Telangana")
        self.assertEqual(ci, "Hyderabad")

        # Comma-separated string
        c, r, ci = self.engine.extract_location_fields("Hyderabad, Telangana, India")
        self.assertEqual(c, "India")
        self.assertEqual(r, "Telangana")
        self.assertEqual(ci, "Hyderabad")

        # 2-part string (City, Country)
        c, r, ci = self.engine.extract_location_fields("Bengaluru, India")
        self.assertEqual(c, "India")
        self.assertEqual(r, "unknown")
        self.assertEqual(ci, "Bengaluru")

        # Missing / blank location
        c, r, ci = self.engine.extract_location_fields(None)
        self.assertEqual(c, "unknown")
        self.assertEqual(r, "unknown")
        self.assertEqual(ci, "unknown")

    # 4. Aggregation and Percentage Calculations
    def test_5_distribution_aggregation(self):
        """Calculates accurate category counts, percentages, and coverage rates."""
        profiles = [
            DemographicProfile(age=20, gender="female", location="Hyderabad, Telangana, India"),
            DemographicProfile(age=22, gender="female", location="Hyderabad, Telangana, India"),
            DemographicProfile(age=30, gender="male", location="Bengaluru, Karnataka, India"),
            DemographicProfile(age=None, gender=None, location=None),  # Unknown
        ]

        dist = self.service.aggregate_distribution(profiles)
        self.assertEqual(dist.total_records_analyzed, 4)

        # Age Breakdown
        self.assertEqual(dist.age_groups.counts["18-24"], 2)
        self.assertEqual(dist.age_groups.counts["25-34"], 1)
        self.assertEqual(dist.age_groups.counts["unknown"], 1)
        self.assertEqual(dist.age_groups.percentages["18-24"], 50.0)
        self.assertEqual(dist.age_groups.percentages["25-34"], 25.0)
        self.assertEqual(dist.age_groups.total_known, 3)
        self.assertEqual(dist.age_groups.total_unknown, 1)
        self.assertEqual(dist.age_groups.coverage_percentage, 75.0)

        # Gender Breakdown
        self.assertEqual(dist.gender.counts["female"], 2)
        self.assertEqual(dist.gender.counts["male"], 1)
        self.assertEqual(dist.gender.percentages["female"], 50.0)
        self.assertEqual(dist.gender.percentages["male"], 25.0)
        self.assertEqual(dist.gender.coverage_percentage, 75.0)

        # Country Breakdown
        self.assertEqual(dist.countries.counts["India"], 3)
        self.assertEqual(dist.countries.counts["unknown"], 1)
        self.assertEqual(dist.countries.percentages["India"], 75.0)

    # 5. Empty and All-Unknown Datasets
    def test_6_empty_and_all_unknown_datasets(self):
        """Handles empty inputs and 100% missing data without zero-division errors."""
        # Empty list
        empty_dist = self.service.aggregate_distribution([])
        self.assertEqual(empty_dist.total_records_analyzed, 0)
        self.assertEqual(empty_dist.age_groups.total_known, 0)
        self.assertEqual(empty_dist.age_groups.coverage_percentage, 0.0)

        # All unknown
        all_unknown = [
            DemographicProfile(age=None, gender=None, location=None),
            DemographicProfile(age=None, gender=None, location=None),
        ]
        dist = self.service.aggregate_distribution(all_unknown)
        self.assertEqual(dist.total_records_analyzed, 2)
        self.assertEqual(dist.age_groups.counts["unknown"], 2)
        self.assertEqual(dist.age_groups.total_known, 0)
        self.assertEqual(dist.age_groups.total_unknown, 2)
        self.assertEqual(dist.age_groups.coverage_percentage, 0.0)

    # 6. Privacy & Group-Size Suppression
    def test_7_privacy_suppression(self):
        """Suppresses small demographic groups (< min_group_size) into 'suppressed'."""
        privacy_engine = RuleBasedDemographicEngine(min_group_size=3)
        privacy_service = DemographicAnalysisService(engine=privacy_engine)

        profiles = [
            # 5 users aged 18-24 (meets threshold >= 3)
            DemographicProfile(age=20, gender="female"),
            DemographicProfile(age=21, gender="female"),
            DemographicProfile(age=22, gender="female"),
            DemographicProfile(age=23, gender="female"),
            DemographicProfile(age=24, gender="female"),
            # 1 user aged 55+ (below threshold < 3 -> should be suppressed)
            DemographicProfile(age=60, gender="male"),
        ]

        dist = privacy_service.aggregate_distribution(profiles)
        self.assertIn("18-24", dist.age_groups.counts)
        self.assertEqual(dist.age_groups.counts["18-24"], 5)
        self.assertNotIn("55+", dist.age_groups.counts)
        self.assertIn("suppressed", dist.age_groups.counts)
        self.assertEqual(dist.age_groups.counts["suppressed"], 1)

    # 7. Post Metadata Extraction
    def test_8_extract_profiles_from_analytics_posts(self):
        """Extracts demographic metadata directly from AnalyticsReadyPost instances."""
        posts = [
            AnalyticsReadyPost(
                id=1,
                platform="x",
                external_post_id="post_1",
                text="Loving the new metro line in Hyderabad!",
                author_username="user1",
                posted_at=self.base_time,
                metadata={
                    "demographics": {
                        "age": 23,
                        "gender": "female",
                        "location": "Hyderabad, Telangana, India",
                    }
                },
            ),
            AnalyticsReadyPost(
                id=2,
                platform="x",
                external_post_id="post_2",
                text="Fares are quite high though.",
                author_username="user2",
                posted_at=self.base_time,
                metadata={"age": 42, "gender": "male", "city": "Hyderabad", "country": "India"},
            ),
        ]

        dist = self.service.aggregate_distribution(posts)
        self.assertEqual(dist.total_records_analyzed, 2)
        self.assertEqual(dist.age_groups.counts["18-24"], 1)
        self.assertEqual(dist.age_groups.counts["35-44"], 1)
        self.assertEqual(dist.gender.counts["female"], 1)
        self.assertEqual(dist.gender.counts["male"], 1)
        self.assertEqual(dist.cities.counts["Hyderabad"], 2)

    # 8. Topic Demographics Integration
    def test_9_topic_demographics_correlation(self):
        """Correlates extracted topic clusters with constituent user demographics."""
        topic = ExtractedTopic(
            topic_id="topic_metro",
            label="Hyderabad Metro",
            post_count=3,
            post_ids=[1, 2, 3],
            external_post_ids=["p1", "p2", "p3"],
        )

        profiles = [
            DemographicProfile(post_id=1, age=22, gender="female", location="Hyderabad, India"),
            DemographicProfile(post_id=2, age=24, gender="female", location="Hyderabad, India"),
            DemographicProfile(post_id=3, age=30, gender="male", location="Secunderabad, India"),
            DemographicProfile(post_id=99, age=60, gender="male", location="Delhi, India"),  # Unrelated post
        ]

        topic_demo = self.service.analyze_topic_demographics(topic, profiles)
        self.assertIsInstance(topic_demo, TopicDemographicResult)
        self.assertEqual(topic_demo.topic_id, "topic_metro")
        self.assertEqual(topic_demo.demographics.total_records_analyzed, 3)
        self.assertEqual(topic_demo.demographics.age_groups.counts["18-24"], 2)
        self.assertEqual(topic_demo.demographics.age_groups.counts["25-34"], 1)
        self.assertNotIn("55+", topic_demo.demographics.age_groups.counts)

    # 9. Sentiment Demographics Integration
    def test_10_sentiment_demographics_correlation(self):
        """Correlates sentiment results with demographic distributions."""
        sentiment_analyzer = SentimentAnalysisService()

        posts = [
            AnalyticsReadyPost(
                id=1,
                platform="x",
                external_post_id="s1",
                text="The service is absolutely wonderful and great!",
                author_username="u1",
                posted_at=self.base_time,
                metadata={"demographics": {"age": 20, "gender": "female"}},
            ),
            AnalyticsReadyPost(
                id=2,
                platform="x",
                external_post_id="s2",
                text="Terrible delay and horrible experience!",
                author_username="u2",
                posted_at=self.base_time,
                metadata={"demographics": {"age": 45, "gender": "male"}},
            ),
        ]

        sent_res1 = sentiment_analyzer.analyze(posts[0])
        sent_res2 = sentiment_analyzer.analyze(posts[1])


        batch_demo = self.service.analyze_batch(
            data=posts,
            sentiment_results=[sent_res1, sent_res2],
        )

        self.assertEqual(len(batch_demo.sentiment_breakdowns), 2)
        pos_breakdown = next(b for b in batch_demo.sentiment_breakdowns if b.sentiment_label == "positive")
        neg_breakdown = next(b for b in batch_demo.sentiment_breakdowns if b.sentiment_label == "negative")

        self.assertEqual(pos_breakdown.demographics.gender.counts["female"], 1)
        self.assertEqual(neg_breakdown.demographics.gender.counts["male"], 1)

    # 10. Trend Demographics Integration
    def test_11_trend_demographics_correlation(self):
        """Correlates trending topics with demographic distributions driving the trend."""
        trend = TopicTrendResult(
            topic_id="topic_fare_hike",
            topic_label="Metro Fare Hike",
            current_volume=3,
            baseline_volume=0,
            growth_rate=300.0,
            direction=TrendDirection.EMERGING,
            trend_score=25.0,
            is_emerging=True,
            post_ids=[10, 11, 12],
            external_post_ids=["e10", "e11", "e12"],
            current_window=TimeWindow(start=self.base_time, end=self.base_time),
        )

        profiles = [
            DemographicProfile(post_id=10, age=19, gender="non_binary", location="Hyderabad, India"),
            DemographicProfile(post_id=11, age=21, gender="female", location="Hyderabad, India"),
            DemographicProfile(post_id=12, age=23, gender="male", location="Hyderabad, India"),
        ]

        trend_demo = self.service.analyze_trend_demographics(trend, profiles)
        self.assertEqual(trend_demo.topic_id, "topic_fare_hike")
        self.assertEqual(trend_demo.trend_direction, "emerging")
        self.assertEqual(trend_demo.demographics.age_groups.counts["18-24"], 3)
        self.assertEqual(trend_demo.demographics.age_groups.percentages["18-24"], 100.0)

    # 11. Determinism and Reproducibility
    def test_12_deterministic_reproducibility(self):
        """Ensures repeated analysis on identical data produces identical results."""
        profiles = [
            DemographicProfile(age=25, gender="female", location="Mumbai, India"),
            DemographicProfile(age=35, gender="male", location="Delhi, India"),
        ]

        dist1 = self.service.aggregate_distribution(profiles)
        dist2 = self.service.aggregate_distribution(profiles)

        self.assertEqual(dist1.age_groups.counts, dist2.age_groups.counts)
        self.assertEqual(dist1.gender.counts, dist2.gender.counts)
        self.assertEqual(dist1.countries.counts, dist2.countries.counts)
        self.assertEqual(dist1.age_groups.percentages, dist2.age_groups.percentages)

    # 12. Mock Engine Injection
    def test_13_mock_engine_injection(self):
        """Verifies custom BaseDemographicEngine dependency injection."""
        class MockDemographicEngine(BaseDemographicEngine):
            @property
            def model_name(self) -> str:
                return "mock-demo-v1"

            def aggregate_distribution(self, profiles):
                empty = DemographicBreakdown()
                return DemographicDistribution(
                    total_records_analyzed=999,
                    age_groups=empty,
                    gender=empty,
                    countries=empty,
                    regions=empty,
                    cities=empty,
                )

            def analyze_topic_demographics(self, topic, profiles):
                pass

            def analyze_sentiment_demographics(self, sentiment_label, profiles):
                pass

            def analyze_trend_demographics(self, trend, profiles):
                pass

            def analyze_batch(self, profiles, topics=None, sentiment_results=None, trend_results=None):
                pass

        mock_service = DemographicAnalysisService(engine=MockDemographicEngine())
        self.assertEqual(mock_service.engine.model_name, "mock-demo-v1")
        res = mock_service.aggregate_distribution([])
        self.assertEqual(res.total_records_analyzed, 999)


if __name__ == "__main__":
    unittest.main()
