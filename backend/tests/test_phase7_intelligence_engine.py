from datetime import datetime, timedelta, timezone
import unittest

from app.schemas.dashboard import (
    DashboardOverviewResponse,
    PlatformComparisonItem,
    PlatformComparisonResponse,
)
from app.schemas.data_quality import AnalyticsReadyPost
from app.schemas.intelligence import (
    BatchInsightResult,
    InsightItem,
    InsightSeverity,
    InsightType,
)
from app.schemas.sentiment import BatchSentimentResult
from app.schemas.topic import BatchTopicResult, ExtractedTopic
from app.schemas.trend import (
    BatchTrendResult,
    TimeWindow,
    TopicTrendResult,
    TrendDirection,
)
from app.services.intelligence.engine import DeterministicIntelligenceEngine
from app.services.intelligence.service import (
    IntelligenceAnalysisService,
    get_intelligence_analyzer,
)


class TestPhase7IntelligenceEngine(unittest.TestCase):
    """
    Comprehensive test suite for Phase 7.2.2 Deterministic Evidence-Grounded Insight Generation Engine.
    """

    def setUp(self):
        self.engine = DeterministicIntelligenceEngine()
        self.now = datetime.now(timezone.utc)
        self.window = TimeWindow(
            start=self.now - timedelta(hours=2),
            end=self.now,
        )
        self.baseline_window = TimeWindow(
            start=self.now - timedelta(hours=4),
            end=self.now - timedelta(hours=2),
        )

    # 1. Emerging trend generates an insight
    def test_emerging_trend_generates_insight(self):
        trend = TopicTrendResult(
            topic_id="top_ai_01",
            topic_label="Autonomous AI Agents",
            current_volume=18,
            baseline_volume=4,
            growth_rate=350.0,
            direction=TrendDirection.EMERGING,
            trend_score=8.5,
            is_emerging=True,
            is_spiking=False,
            post_ids=[101, 102, 103],
            external_post_ids=["ext_1", "ext_2"],
            current_window=self.window,
            baseline_window=self.baseline_window,
            details={"z_score": 1.8},
        )

        res = self.engine.generate_insights(trends=[trend])
        self.assertEqual(res.total_insights, 1)
        insight = res.insights[0]
        self.assertEqual(insight.type, InsightType.EMERGING_TREND)
        self.assertEqual(insight.affected_topic, "Autonomous AI Agents")
        self.assertEqual(insight.evidence.current_volume, 18)
        self.assertEqual(insight.evidence.baseline_volume, 4)
        self.assertEqual(insight.evidence.growth_rate, 350.0)
        self.assertEqual(insight.evidence.post_ids, [101, 102, 103])
        self.assertGreaterEqual(insight.confidence, 0.70)
        self.assertIn("Autonomous AI Agents", insight.title)

    # 2. Weak trend does not generate an insight
    def test_weak_trend_does_not_generate_insight(self):
        weak_trend = TopicTrendResult(
            topic_id="top_weak_01",
            topic_label="Minor Discussion",
            current_volume=3,
            baseline_volume=3,
            growth_rate=0.0,
            direction=TrendDirection.STABLE,
            trend_score=0.5,
            is_emerging=False,
            is_spiking=False,
            current_window=self.window,
            baseline_window=self.baseline_window,
            details={"z_score": 0.1},
        )

        res = self.engine.generate_insights(trends=[weak_trend])
        self.assertEqual(res.total_insights, 0)

    # 3. Anomalous spike generates an insight
    def test_anomalous_spike_generates_insight(self):
        trend = TopicTrendResult(
            topic_id="top_spike_01",
            topic_label="Breaking Security Vulnerability",
            current_volume=45,
            baseline_volume=5,
            growth_rate=800.0,
            direction=TrendDirection.SPIKING,
            trend_score=15.2,
            is_emerging=False,
            is_spiking=True,
            post_ids=[201, 202, 203, 204],
            current_window=self.window,
            baseline_window=self.baseline_window,
            details={"z_score": 3.85},
        )

        res = self.engine.generate_insights(trends=[trend])
        self.assertGreaterEqual(res.total_insights, 1)
        spike_insight = next((i for i in res.insights if i.type == InsightType.ANOMALOUS_SPIKE), None)
        self.assertIsNotNone(spike_insight)
        self.assertEqual(spike_insight.evidence.z_score, 3.85)
        self.assertEqual(spike_insight.severity, InsightSeverity.CRITICAL)
        self.assertGreaterEqual(spike_insight.confidence, 0.85)

    # 4. Insufficient anomaly evidence does not generate spike insight
    def test_insufficient_anomaly_evidence_does_not_generate_spike(self):
        low_z_trend = TopicTrendResult(
            topic_id="top_normal_01",
            topic_label="Normal Routine Chat",
            current_volume=6,
            baseline_volume=5,
            growth_rate=20.0,
            direction=TrendDirection.STABLE,
            trend_score=1.1,
            is_emerging=False,
            is_spiking=False,
            current_window=self.window,
            baseline_window=self.baseline_window,
            details={"z_score": 0.4},
        )

        res = self.engine.generate_insights(trends=[low_z_trend])
        spike_insights = [i for i in res.insights if i.type == InsightType.ANOMALOUS_SPIKE]
        self.assertEqual(len(spike_insights), 0)

    # 5. Negative sentiment shift generation
    def test_negative_sentiment_shift_generation(self):
        sentiment = BatchSentimentResult(
            total_analyzed=40,
            positive_count=4,
            neutral_count=12,
            negative_count=24,
            average_score=-0.52,
        )

        res = self.engine.generate_insights(sentiment=sentiment)
        self.assertEqual(res.total_insights, 1)
        insight = res.insights[0]
        self.assertEqual(insight.type, InsightType.SENTIMENT_SHIFT)
        self.assertEqual(insight.evidence.dominant_sentiment, "negative")
        self.assertEqual(insight.evidence.sentiment_score, -0.52)
        self.assertEqual(insight.severity, InsightSeverity.HIGH)
        self.assertIn("Negative Tone", insight.title)

    # 6. Positive sentiment concentration generation
    def test_positive_sentiment_concentration_generation(self):
        sentiment = BatchSentimentResult(
            total_analyzed=30,
            positive_count=25,
            neutral_count=4,
            negative_count=1,
            average_score=0.68,
        )

        res = self.engine.generate_insights(sentiment=sentiment)
        self.assertEqual(res.total_insights, 1)
        insight = res.insights[0]
        self.assertEqual(insight.type, InsightType.SENTIMENT_SHIFT)
        self.assertEqual(insight.evidence.dominant_sentiment, "positive")
        self.assertEqual(insight.severity, InsightSeverity.LOW)

    # 7. Cross-platform narrative generation from posts
    def test_cross_platform_narrative_generation(self):
        topics = [
            ExtractedTopic(
                topic_id="top_cross_01",
                label="Renewable Energy Policy",
                keywords=["energy", "solar", "policy"],
                keyphrases=["renewable energy transition"],
                post_count=6,
                post_ids=[301, 302, 303, 304, 305],
                confidence=0.9,
            )
        ]
        posts = [
            AnalyticsReadyPost(id=301, platform="X", external_post_id="x_301", posted_at=self.now, text="Solar policy #Energy", raw_text="Solar policy #Energy"),
            AnalyticsReadyPost(id=302, platform="X", external_post_id="x_302", posted_at=self.now, text="Wind investment #Energy", raw_text="Wind investment #Energy"),
            AnalyticsReadyPost(id=303, platform="Reddit", external_post_id="rd_303", posted_at=self.now, text="Discussion on energy bills", raw_text="Discussion on energy bills"),
            AnalyticsReadyPost(id=304, platform="Telegram", external_post_id="tg_304", posted_at=self.now, text="Flash update energy regulation", raw_text="Flash update energy regulation"),
            AnalyticsReadyPost(id=305, platform="YouTube", external_post_id="yt_305", posted_at=self.now, text="Video analysis of solar grids", raw_text="Video analysis of solar grids"),
        ]

        res = self.engine.generate_insights(topics=topics, posts=posts)
        self.assertEqual(res.total_insights, 1)
        insight = res.insights[0]
        self.assertEqual(insight.type, InsightType.CROSS_PLATFORM_PROPAGATION)
        self.assertEqual(insight.affected_topic, "Renewable Energy Policy")
        self.assertIn("Reddit", insight.evidence.platforms)
        self.assertIn("Telegram", insight.evidence.platforms)
        self.assertIn("X", insight.evidence.platforms)
        self.assertIn("YouTube", insight.evidence.platforms)
        self.assertEqual(len(insight.evidence.platforms), 4)

    # 8. Cross-platform multi-stream activity from PlatformComparisonResponse
    def test_cross_platform_from_platform_comparison(self):
        comp = PlatformComparisonResponse(
            total_platforms=3,
            platforms=[
                PlatformComparisonItem(platform="X", post_count=50),
                PlatformComparisonItem(platform="Reddit", post_count=35),
                PlatformComparisonItem(platform="Telegram", post_count=20),
            ],
            generated_at=self.now,
        )

        res = self.engine.generate_insights(platform_comparison=comp)
        self.assertEqual(res.total_insights, 1)
        insight = res.insights[0]
        self.assertEqual(insight.type, InsightType.CROSS_PLATFORM_PROPAGATION)
        self.assertEqual(len(insight.evidence.platforms), 3)

    # 9. Confidence calculation boundary and scaling
    def test_confidence_calculation_bounds(self):
        trend = TopicTrendResult(
            topic_id="top_conf_01",
            topic_label="High Confidence Trend",
            current_volume=100,
            baseline_volume=10,
            growth_rate=500.0,
            direction=TrendDirection.SPIKING,
            trend_score=20.0,
            is_emerging=True,
            is_spiking=True,
            post_ids=list(range(1, 25)),
            current_window=self.window,
            baseline_window=self.baseline_window,
            details={"z_score": 4.5},
        )

        res = self.engine.generate_insights(trends=[trend])
        for insight in res.insights:
            self.assertGreaterEqual(insight.confidence, 0.0)
            self.assertLessEqual(insight.confidence, 1.0)
            self.assertGreater(insight.confidence, 0.80)

    # 10. Severity classification hierarchy
    def test_severity_classification_hierarchy(self):
        # Critical spike
        crit_trend = TopicTrendResult(
            topic_id="top_crit",
            topic_label="Critical Event",
            current_volume=50,
            baseline_volume=2,
            growth_rate=1200.0,
            direction=TrendDirection.SPIKING,
            trend_score=30.0,
            is_spiking=True,
            current_window=self.window,
            details={"z_score": 4.2},
        )
        res = self.engine.generate_insights(trends=[crit_trend])
        spike_insight = next(i for i in res.insights if i.type == InsightType.ANOMALOUS_SPIKE)
        self.assertEqual(spike_insight.severity, InsightSeverity.CRITICAL)

        # Medium emerging
        med_trend = TopicTrendResult(
            topic_id="top_med",
            topic_label="Moderate Growth",
            current_volume=6,
            baseline_volume=4,
            growth_rate=50.0,
            direction=TrendDirection.EMERGING,
            trend_score=4.0,
            is_emerging=True,
            current_window=self.window,
            details={"z_score": 1.2},
        )
        res_med = self.engine.generate_insights(trends=[med_trend])
        emerge_insight = next(i for i in res_med.insights if i.type == InsightType.EMERGING_TREND)
        self.assertEqual(emerge_insight.severity, InsightSeverity.MEDIUM)

    # 11. Deterministic insight IDs and idempotency
    def test_deterministic_insight_ids_idempotency(self):
        trend = TopicTrendResult(
            topic_id="top_idempotent",
            topic_label="Idempotency Check",
            current_volume=15,
            baseline_volume=3,
            growth_rate=400.0,
            direction=TrendDirection.EMERGING,
            trend_score=9.0,
            is_emerging=True,
            current_window=self.window,
        )

        res1 = self.engine.generate_insights(trends=[trend])
        res2 = self.engine.generate_insights(trends=[trend])

        self.assertEqual(res1.total_insights, res2.total_insights)
        self.assertEqual(res1.insights[0].id, res2.insights[0].id)
        self.assertEqual(res1.insights[0].confidence, res2.insights[0].confidence)

    # 12. Duplicate prevention when processing identical trends
    def test_duplicate_prevention(self):
        trend1 = TopicTrendResult(
            topic_id="top_dup",
            topic_label="Duplicate Topic",
            current_volume=12,
            baseline_volume=2,
            growth_rate=300.0,
            direction=TrendDirection.EMERGING,
            trend_score=7.0,
            is_emerging=True,
            current_window=self.window,
        )
        # Duplicate of trend1
        trend2 = TopicTrendResult(
            topic_id="top_dup",
            topic_label="Duplicate Topic",
            current_volume=12,
            baseline_volume=2,
            growth_rate=300.0,
            direction=TrendDirection.EMERGING,
            trend_score=7.0,
            is_emerging=True,
            current_window=self.window,
        )

        res = self.engine.generate_insights(trends=[trend1, trend2])
        emerging_insights = [i for i in res.insights if i.type == InsightType.EMERGING_TREND]
        self.assertEqual(len(emerging_insights), 1)

    # 13. Empty analytics graceful handling
    def test_empty_analytics_graceful_handling(self):
        res = self.engine.generate_insights()
        self.assertEqual(res.total_insights, 0)
        self.assertEqual(len(res.insights), 0)
        self.assertEqual(res.critical_count, 0)
        self.assertEqual(res.model, self.engine.model_name)

    # 14. Incomplete analytics / None fields handling
    def test_incomplete_analytics_safe_handling(self):
        incomplete_trend = TopicTrendResult(
            topic_id="top_incomplete",
            topic_label="Sparse Trend",
            current_volume=10,
            baseline_volume=0,
            growth_rate=100.0,
            direction=TrendDirection.GROWING,
            trend_score=3.0,
            is_emerging=True,
            post_ids=[],
            external_post_ids=[],
            current_window=self.window,
            baseline_window=None,
            details={},
        )

        res = self.engine.generate_insights(trends=[incomplete_trend])
        self.assertGreaterEqual(res.total_insights, 1)
        self.assertEqual(res.insights[0].evidence.baseline_volume, 0)

    # 15. Zero baseline handling
    def test_zero_baseline_handling(self):
        zero_base_trend = TopicTrendResult(
            topic_id="top_zero_base",
            topic_label="Newly Discovered Story",
            current_volume=8,
            baseline_volume=0,
            growth_rate=800.0,
            direction=TrendDirection.EMERGING,
            trend_score=6.5,
            is_emerging=True,
            current_window=self.window,
            baseline_window=None,
        )

        res = self.engine.generate_insights(trends=[zero_base_trend])
        self.assertEqual(res.total_insights, 1)
        self.assertEqual(res.insights[0].evidence.baseline_volume, 0)

    # 16. Multiple insights in one batch with priority sorting
    def test_multiple_insights_in_one_batch_priority_sorting(self):
        crit_spike = TopicTrendResult(
            topic_id="top_c",
            topic_label="Critical Anomaly",
            current_volume=60,
            baseline_volume=5,
            growth_rate=1100.0,
            direction=TrendDirection.SPIKING,
            trend_score=25.0,
            is_spiking=True,
            current_window=self.window,
            details={"z_score": 4.1},
        )
        med_emerge = TopicTrendResult(
            topic_id="top_m",
            topic_label="Moderate Emergence",
            current_volume=7,
            baseline_volume=4,
            growth_rate=45.0,
            direction=TrendDirection.EMERGING,
            trend_score=3.5,
            is_emerging=True,
            current_window=self.window,
            details={"z_score": 1.1},
        )
        sentiment = BatchSentimentResult(
            total_analyzed=50,
            positive_count=5,
            neutral_count=10,
            negative_count=35,
            average_score=-0.58,
        )

        res = self.engine.generate_insights(
            trends=[crit_spike, med_emerge],
            sentiment=sentiment,
        )

        self.assertGreaterEqual(res.total_insights, 3)
        # Verify first item is CRITICAL
        self.assertEqual(res.insights[0].severity, InsightSeverity.CRITICAL)
        self.assertGreaterEqual(res.critical_count, 1)
        self.assertGreaterEqual(res.high_count, 1)

    # 17. IntelligenceAnalysisService and Singleton Provider
    def test_intelligence_service_wrapper_and_provider(self):
        svc = get_intelligence_analyzer()
        self.assertIsInstance(svc, IntelligenceAnalysisService)
        self.assertEqual(svc.model_name, "insightx-intelligence-deterministic-v1")

        res = svc.generate_insights()
        self.assertIsInstance(res, BatchInsightResult)
        self.assertEqual(res.total_insights, 0)


if __name__ == "__main__":
    unittest.main()
