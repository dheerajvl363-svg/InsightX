from datetime import datetime, timedelta, timezone
import unittest

from app.schemas.data_quality import AnalyticsReadyPost
from app.schemas.post import RawPostPayload
from app.schemas.topic import ExtractedTopic
from app.schemas.trend import (
    BatchTrendResult,
    TimeWindow,
    TopicTrendResult,
    TrendDirection,
)
from app.services.data_quality import DataQualityService
from app.services.normalizer import DataNormalizer
from app.services.topic.service import TopicAnalysisService
from app.services.trend.base import BaseTrendEngine
from app.services.trend.engine import StatisticalTrendEngine
from app.services.trend.service import (
    TrendAnalysisService,
    get_trend_analyzer,
)


class TestTrendDetectionEngine(unittest.TestCase):
    """
    Comprehensive test suite for Phase 3 Component 3.5:
    Trend Detection & Emerging Narrative Analysis Engine and Service.
    """

    def setUp(self):
        self.engine = StatisticalTrendEngine(
            default_window_duration=timedelta(hours=1),
            growth_threshold_pct=25.0,
            decline_threshold_pct=-25.0,
            spike_z_score_threshold=2.0,
            spike_growth_threshold_pct=300.0,
            min_spiking_volume=4,
            min_emerging_volume=2,
        )
        self.service = TrendAnalysisService(engine=self.engine)
        self.base_time = datetime(2026, 9, 8, 12, 0, 0, tzinfo=timezone.utc)

    def _make_post(
        self,
        text: str,
        posted_at: datetime,
        post_id: int,
        external_id: str,
    ) -> AnalyticsReadyPost:
        return AnalyticsReadyPost(
            id=post_id,
            platform="x",
            external_post_id=external_id,
            text=text,
            raw_text=text,
            author_username="testuser",
            author_display_name="Test User",
            posted_at=posted_at,
            char_count=len(text),
            word_count=len(text.split()),
        )

    # 1. Growth calculations and directions
    def test_1_strong_growth(self):
        """Calculates positive growth rate and identifies GROWING topic trajectory."""
        topic = ExtractedTopic(
            topic_id="topic_ai_tech",
            label="AI Technology",
            keywords=["ai", "technology"],
            keyphrases=["artificial intelligence"],
            post_count=15,
            post_ids=list(range(1, 16)),
            external_post_ids=[f"ext_{i}" for i in range(1, 16)],
            confidence=0.9,
        )

        posts = []
        # Baseline window (10:00 to 11:00): 4 posts
        for i in range(1, 5):
            t = self.base_time - timedelta(minutes=90)
            posts.append(self._make_post("AI research update", t, i, f"ext_{i}"))

        # Current window (11:00 to 12:00): 11 posts (+175% growth)
        for i in range(5, 16):
            t = self.base_time - timedelta(minutes=30)
            posts.append(self._make_post("AI research breakthrough", t, i, f"ext_{i}"))

        result = self.service.analyze_topic(
            topic=topic,
            posts=posts,
            reference_time=self.base_time,
            window_duration=timedelta(hours=1),
        )

        self.assertEqual(result.current_volume, 11)
        self.assertEqual(result.baseline_volume, 4)
        self.assertEqual(result.growth_rate, 175.0)
        self.assertEqual(result.direction, TrendDirection.GROWING)
        self.assertFalse(result.is_emerging)
        self.assertGreater(result.trend_score, 15.0)
        self.assertEqual(len(result.post_ids), 11)

    def test_2_volume_decline(self):
        """Calculates negative growth rate and identifies DECLINING topic trajectory."""
        topic = ExtractedTopic(
            topic_id="topic_metro_fare",
            label="Metro Fare",
            keywords=["metro", "fare"],
            keyphrases=["ticket prices"],
            post_count=12,
            post_ids=list(range(1, 13)),
            external_post_ids=[f"ext_{i}" for i in range(1, 13)],
            confidence=0.9,
        )

        posts = []
        # Baseline window: 10 posts
        for i in range(1, 11):
            t = self.base_time - timedelta(minutes=80)
            posts.append(self._make_post("Metro prices high", t, i, f"ext_{i}"))

        # Current window: 2 posts (-80% growth)
        for i in range(11, 13):
            t = self.base_time - timedelta(minutes=20)
            posts.append(self._make_post("Metro prices high", t, i, f"ext_{i}"))

        result = self.service.analyze_topic(
            topic=topic,
            posts=posts,
            reference_time=self.base_time,
            window_duration=timedelta(hours=1),
        )

        self.assertEqual(result.current_volume, 2)
        self.assertEqual(result.baseline_volume, 10)
        self.assertEqual(result.growth_rate, -80.0)
        self.assertEqual(result.direction, TrendDirection.DECLINING)
        self.assertFalse(result.is_emerging)

    def test_3_stable_volume(self):
        """Detects STABLE trajectory when volume change is minimal."""
        topic = ExtractedTopic(
            topic_id="topic_weather",
            label="City Weather",
            keywords=["weather", "rain"],
            keyphrases=["weather forecast"],
            post_count=10,
            post_ids=list(range(1, 11)),
            external_post_ids=[f"ext_{i}" for i in range(1, 11)],
            confidence=0.8,
        )

        posts = []
        # Baseline window: 5 posts
        for i in range(1, 6):
            t = self.base_time - timedelta(minutes=75)
            posts.append(self._make_post("Rain in city", t, i, f"ext_{i}"))

        # Current window: 5 posts (0% growth)
        for i in range(6, 11):
            t = self.base_time - timedelta(minutes=15)
            posts.append(self._make_post("Rain in city", t, i, f"ext_{i}"))

        result = self.service.analyze_topic(
            topic=topic,
            posts=posts,
            reference_time=self.base_time,
            window_duration=timedelta(hours=1),
        )

        self.assertEqual(result.current_volume, 5)
        self.assertEqual(result.baseline_volume, 5)
        self.assertEqual(result.growth_rate, 0.0)
        self.assertEqual(result.direction, TrendDirection.STABLE)

    def test_4_emerging_narrative_zero_baseline(self):
        """Identifies newly emerging narrative with 0 baseline volume without divide-by-zero error."""
        topic = ExtractedTopic(
            topic_id="topic_flash_strike",
            label="Flash Transport Strike",
            keywords=["strike", "transport"],
            keyphrases=["flash strike"],
            post_count=6,
            post_ids=list(range(1, 7)),
            external_post_ids=[f"ext_{i}" for i in range(1, 7)],
            confidence=0.95,
        )

        posts = []
        # Current window only: 6 posts (baseline has 0 posts)
        for i in range(1, 7):
            t = self.base_time - timedelta(minutes=5 * i)
            posts.append(self._make_post("Transport strike announced", t, i, f"ext_{i}"))


        result = self.service.analyze_topic(
            topic=topic,
            posts=posts,
            reference_time=self.base_time,
            window_duration=timedelta(hours=1),
        )

        self.assertEqual(result.current_volume, 6)
        self.assertEqual(result.baseline_volume, 0)
        self.assertGreater(result.growth_rate, 0.0)
        self.assertTrue(result.is_emerging)
        self.assertEqual(result.direction, TrendDirection.EMERGING)

    def test_5_spiking_anomaly_surge(self):
        """Detects sudden anomalous surge in volume as SPIKING."""
        topic = ExtractedTopic(
            topic_id="topic_power_outage",
            label="Power Outage",
            keywords=["power", "outage", "blackout"],
            keyphrases=["power outage"],
            post_count=32,
            post_ids=list(range(1, 33)),
            external_post_ids=[f"ext_{i}" for i in range(1, 33)],
            confidence=0.95,
        )

        posts = []
        # Historical baseline: 2 posts in baseline window
        for i in range(1, 3):
            t = self.base_time - timedelta(minutes=90)
            posts.append(self._make_post("Light flickering", t, i, f"ext_{i}"))

        # Current window: 30 posts (massive 15x spike)
        for i in range(3, 33):
            t = self.base_time - timedelta(minutes=20)
            posts.append(self._make_post("Major blackout downtown!", t, i, f"ext_{i}"))

        result = self.service.analyze_topic(
            topic=topic,
            posts=posts,
            reference_time=self.base_time,
            window_duration=timedelta(hours=1),
        )

        self.assertEqual(result.current_volume, 30)
        self.assertEqual(result.baseline_volume, 2)
        self.assertEqual(result.growth_rate, 1400.0)
        self.assertTrue(result.is_spiking)
        self.assertEqual(result.direction, TrendDirection.SPIKING)

    # 6. Multi-topic batch analysis & ranking
    def test_6_batch_topics_ranking(self):
        """Analyzes multiple topics and ranks them descending by trend score."""
        topic_a = ExtractedTopic(
            topic_id="topic_a",
            label="Topic A (Spiking)",
            post_count=22,
            post_ids=list(range(1, 23)),
            external_post_ids=[f"a_{i}" for i in range(1, 23)],
        )
        topic_b = ExtractedTopic(
            topic_id="topic_b",
            label="Topic B (Stable)",
            post_count=8,
            post_ids=list(range(23, 31)),
            external_post_ids=[f"b_{i}" for i in range(23, 31)],
        )
        topic_c = ExtractedTopic(
            topic_id="topic_c",
            label="Topic C (Declining)",
            post_count=10,
            post_ids=list(range(31, 41)),
            external_post_ids=[f"c_{i}" for i in range(31, 41)],
        )

        posts = []
        # Topic A: 2 baseline, 20 current
        for i in range(1, 3):
            posts.append(self._make_post("A baseline", self.base_time - timedelta(minutes=90), i, f"a_{i}"))
        for i in range(3, 23):
            posts.append(self._make_post("A current", self.base_time - timedelta(minutes=20), i, f"a_{i}"))

        # Topic B: 4 baseline, 4 current
        for i in range(23, 27):
            posts.append(self._make_post("B baseline", self.base_time - timedelta(minutes=90), i, f"b_{i}"))
        for i in range(27, 31):
            posts.append(self._make_post("B current", self.base_time - timedelta(minutes=20), i, f"b_{i}"))

        # Topic C: 8 baseline, 2 current
        for i in range(31, 39):
            posts.append(self._make_post("C baseline", self.base_time - timedelta(minutes=90), i, f"c_{i}"))
        for i in range(39, 41):
            posts.append(self._make_post("C current", self.base_time - timedelta(minutes=20), i, f"c_{i}"))

        batch_result = self.service.analyze_trends(
            topics=[topic_a, topic_b, topic_c],
            posts=posts,
            reference_time=self.base_time,
            window_duration=timedelta(hours=1),
        )

        self.assertIsInstance(batch_result, BatchTrendResult)
        self.assertEqual(batch_result.total_topics_evaluated, 3)
        self.assertEqual(len(batch_result.trends), 3)

        # Confirm ranking order: Spiking (A) > Stable (B) > Declining (C)
        self.assertEqual(batch_result.trends[0].topic_id, "topic_a")
        self.assertEqual(batch_result.trends[1].topic_id, "topic_b")
        self.assertEqual(batch_result.trends[2].topic_id, "topic_c")

        self.assertGreater(batch_result.trends[0].trend_score, batch_result.trends[1].trend_score)
        self.assertGreater(batch_result.trends[1].trend_score, batch_result.trends[2].trend_score)

    # 7. Time window boundary handling
    def test_7_time_window_boundaries_and_custom_duration(self):
        """Verifies configurable window duration and boundary timestamp handling."""
        topic = ExtractedTopic(
            topic_id="topic_interval",
            label="Interval Test",
            post_count=4,
            post_ids=[1, 2, 3, 4],
            external_post_ids=["p1", "p2", "p3", "p4"],
        )

        # 30-minute custom window duration
        posts = [
            # Exactly at reference_time (12:00:00) -> current window
            self._make_post("P1", self.base_time, 1, "p1"),
            # At 11:45:00 -> current window (11:30 to 12:00)
            self._make_post("P2", self.base_time - timedelta(minutes=15), 2, "p2"),
            # At 11:15:00 -> baseline window (11:00 to 11:30)
            self._make_post("P3", self.base_time - timedelta(minutes=45), 3, "p3"),
            # At 10:00:00 -> older than baseline
            self._make_post("P4", self.base_time - timedelta(minutes=120), 4, "p4"),
        ]

        result = self.service.analyze_topic(
            topic=topic,
            posts=posts,
            reference_time=self.base_time,
            window_duration=timedelta(minutes=30),
        )

        self.assertEqual(result.current_volume, 2)
        self.assertEqual(result.baseline_volume, 1)
        self.assertEqual(result.growth_rate, 100.0)
        self.assertEqual(result.details["window_duration_seconds"], 1800)

    # 8. Edge cases: empty batch and missing posts
    def test_8_empty_and_sparse_edge_cases(self):
        """Handles empty inputs and zero-observation edge cases gracefully."""
        # Empty topics list
        empty_batch = self.service.analyze_trends(topics=[], posts=[])
        self.assertEqual(empty_batch.total_topics_evaluated, 0)
        self.assertEqual(len(empty_batch.trends), 0)

        # Topic with no matching posts
        orphan_topic = ExtractedTopic(
            topic_id="topic_orphan",
            label="Orphan Topic",
            post_count=1,
            post_ids=[999],
            external_post_ids=["ext_orphan"],
        )
        res = self.service.analyze_topic(topic=orphan_topic, posts=[])
        self.assertEqual(res.current_volume, 0)
        self.assertEqual(res.baseline_volume, 0)
        self.assertEqual(res.growth_rate, 0.0)
        self.assertEqual(res.direction, TrendDirection.STABLE)

    # 9. Type validation errors
    def test_9_type_validation(self):
        """Raises TypeError when invalid objects are passed to the service."""
        with self.assertRaises(TypeError):
            self.service.analyze_topic(topic="not_a_topic", posts=[])  # type: ignore

        with self.assertRaises(TypeError):
            self.service.analyze_trends(topics="not_a_list", posts=[])  # type: ignore

    # 10. Deterministic output
    def test_10_deterministic_reproducibility(self):
        """Ensures consecutive evaluations on identical data produce identical output."""
        topic = ExtractedTopic(
            topic_id="topic_det",
            label="Deterministic",
            post_count=5,
            post_ids=[1, 2, 3, 4, 5],
            external_post_ids=[f"d_{i}" for i in range(1, 6)],
        )
        posts = [
            self._make_post("Det post", self.base_time - timedelta(minutes=10 * i), i, f"d_{i}")
            for i in range(1, 6)
        ]

        res1 = self.service.analyze_topic(topic=topic, posts=posts, reference_time=self.base_time)
        res2 = self.service.analyze_topic(topic=topic, posts=posts, reference_time=self.base_time)

        self.assertEqual(res1.growth_rate, res2.growth_rate)
        self.assertEqual(res1.trend_score, res2.trend_score)
        self.assertEqual(res1.direction, res2.direction)
        self.assertEqual(res1.details, res2.details)

    # 11. Mock engine dependency injection
    def test_11_mock_engine_injection(self):
        """Allows injecting custom BaseTrendEngine implementation into service."""
        class MockTrendEngine(BaseTrendEngine):
            @property
            def model_name(self) -> str:
                return "mock-trend-engine-v1"

            def analyze_topic_trend(self, topic, posts, reference_time=None, window_duration=None):
                return TopicTrendResult(
                    topic_id=topic.topic_id,
                    topic_label=topic.label,
                    current_volume=42,
                    baseline_volume=10,
                    growth_rate=320.0,
                    direction=TrendDirection.SPIKING,
                    trend_score=99.9,
                    is_spiking=True,
                    current_window=TimeWindow(start=datetime.now(timezone.utc), end=datetime.now(timezone.utc)),
                )

            def analyze_batch_trends(self, topics, posts, reference_time=None, window_duration=None):
                return [self.analyze_topic_trend(t, posts) for t in topics]

        mock_service = TrendAnalysisService(engine=MockTrendEngine())
        self.assertEqual(mock_service.engine.model_name, "mock-trend-engine-v1")

        topic = ExtractedTopic(topic_id="t1", label="T1", post_count=1)
        res = mock_service.analyze_topic(topic=topic, posts=[])
        self.assertEqual(res.current_volume, 42)
        self.assertEqual(res.trend_score, 99.9)

    # 12. Full end-to-end multi-layer pipeline integration test
    def test_12_end_to_end_analytics_pipeline(self):
        """
        Exercises the full cross-component Phase 3 pipeline:
        RawPostPayload -> DataNormalizer -> DataQualityService -> TopicAnalysisService -> TrendAnalysisService
        """
        normalizer = DataNormalizer()
        quality_service = DataQualityService()
        topic_service = TopicAnalysisService()
        trend_service = get_trend_analyzer()

        ref_time = datetime(2026, 9, 8, 18, 0, 0, tzinfo=timezone.utc)

        raw_payloads = [
            # Baseline period (16:00 to 17:00)
            RawPostPayload(
                platform="x",
                external_id="pipe_b1",
                text="Hyderabad metro ticket counters are crowded. #HyderabadMetro",
                posted_at=ref_time - timedelta(minutes=80),
            ),
            # Current period (17:00 to 18:00) - surge of 3 posts
            RawPostPayload(
                platform="x",
                external_id="pipe_c1",
                text="Hyderabad metro fare increase is causing outrage among commuters! #HyderabadMetro",
                posted_at=ref_time - timedelta(minutes=30),
            ),
            RawPostPayload(
                platform="x",
                external_id="pipe_c2",
                text="Why are Hyderabad metro ticket prices increasing again? #HyderabadMetro",
                posted_at=ref_time - timedelta(minutes=20),
            ),
            RawPostPayload(
                platform="x",
                external_id="pipe_c3",
                text="Huge queues at Hyderabad metro stations today due to fare changes. #HyderabadMetro",
                posted_at=ref_time - timedelta(minutes=10),
            ),
        ]

        # 1. Normalize
        normalized_posts = [normalizer.normalize(p) for p in raw_payloads]

        # 2. Quality validation
        quality_batch = quality_service.validate_batch(normalized_posts)
        self.assertEqual(quality_batch.valid_count, 4)
        ready_posts = quality_batch.valid_posts

        # 3. Topic extraction
        topic_batch = topic_service.extract_topics(ready_posts)
        self.assertGreaterEqual(topic_batch.total_topics_found, 1)

        # 4. Trend detection
        trend_batch = trend_service.analyze_trends(
            topics=topic_batch,
            posts=ready_posts,
            reference_time=ref_time,
            window_duration=timedelta(hours=1),
        )

        self.assertEqual(trend_batch.total_topics_evaluated, topic_batch.total_topics_found)
        top_trend = trend_batch.trends[0]
        self.assertIn("metro", top_trend.topic_label.lower())
        self.assertEqual(top_trend.current_volume, 3)
        self.assertEqual(top_trend.baseline_volume, 1)
        self.assertEqual(top_trend.growth_rate, 200.0)
        self.assertEqual(top_trend.direction, TrendDirection.GROWING)


if __name__ == "__main__":
    unittest.main()
