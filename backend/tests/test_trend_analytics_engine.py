import unittest
from datetime import datetime, timedelta, timezone

from app.schemas.analytics_engine import (
    DetailedTrendReport,
    PlatformTrendSummary,
    TrendItemProfile,
    TrendMomentumMetrics,
)
from app.schemas.data_quality import AnalyticsReadyPost
from app.schemas.post import PostMetricsSchema
from app.services.analytics_engine import (
    AnalyticsEngineService,
    TrendAnalyticsEngine,
    extract_hashtags_and_keywords,
)


class TestTrendAnalyticsEngine(unittest.TestCase):
    def setUp(self):
        self.engine = TrendAnalyticsEngine()
        self.base_time = datetime(2026, 9, 8, 12, 0, 0, tzinfo=timezone.utc)

    def test_hashtag_and_keyword_extraction(self):
        text = "Huge breakthrough in #QuantumComputing and #ArtificialIntelligence algorithms for cloud scaling."
        hashtags, keywords = extract_hashtags_and_keywords(text)
        self.assertIn("#quantumcomputing", hashtags)
        self.assertIn("#artificialintelligence", hashtags)
        self.assertIn("breakthrough", keywords)
        self.assertIn("algorithms", keywords)

    def test_empty_and_malformed_posts_safety(self):
        empty_trends = self.engine.analyze_trends([])
        self.assertEqual(empty_trends, [])

        malformed_posts = [
            {"text": "", "posted_at": None},
            {"text": None, "platform": None},
            {},
        ]
        report = self.engine.generate_detailed_report(malformed_posts)
        self.assertEqual(report.total_trends_evaluated, 0)
        self.assertEqual(report.ranked_trends, [])

    def test_increasing_accelerating_trend(self):
        # 1 post in baseline, 5 posts in recent window with high engagement
        posts = [
            {"id": "p_base", "posted_at": self.base_time, "text": "Discussion on #FusionEnergy progress", "metrics": {"likes": 10}},
            {"id": "p_cur1", "posted_at": self.base_time + timedelta(hours=3), "text": "Massive leap in #FusionEnergy plasma!", "metrics": {"likes": 100}},
            {"id": "p_cur2", "posted_at": self.base_time + timedelta(hours=3, minutes=10), "text": "Investment in #FusionEnergy reaches record.", "metrics": {"likes": 150}},
            {"id": "p_cur3", "posted_at": self.base_time + timedelta(hours=3, minutes=20), "text": "Startup announces new #FusionEnergy reactor.", "metrics": {"likes": 200}},
            {"id": "p_cur4", "posted_at": self.base_time + timedelta(hours=3, minutes=30), "text": "Scientists celebrate #FusionEnergy milestone.", "metrics": {"likes": 300}},
        ]
        trends = self.engine.analyze_trends(posts)
        self.assertGreaterEqual(len(trends), 1)
        fusion_trend = next(t for t in trends if t.trend_id == "#fusionenergy")
        self.assertIn(fusion_trend.momentum.direction, {"accelerating", "spiking"})
        self.assertGreater(fusion_trend.momentum.velocity, 0)
        self.assertGreater(fusion_trend.momentum.growth_rate_pct, 100.0)
        self.assertGreater(fusion_trend.momentum.momentum_score, 5.0)

    def test_decreasing_declining_trend(self):
        # 5 posts in baseline, 1 post in recent window
        posts = [
            {"id": "p_b1", "posted_at": self.base_time, "text": "#LegacyTech update 1"},
            {"id": "p_b2", "posted_at": self.base_time + timedelta(minutes=10), "text": "#LegacyTech update 2"},
            {"id": "p_b3", "posted_at": self.base_time + timedelta(minutes=20), "text": "#LegacyTech update 3"},
            {"id": "p_b4", "posted_at": self.base_time + timedelta(minutes=30), "text": "#LegacyTech update 4"},
            {"id": "p_c1", "posted_at": self.base_time + timedelta(hours=3), "text": "#LegacyTech deprecation notice"},
        ]
        trends = self.engine.analyze_trends(posts)
        trend = next(t for t in trends if t.trend_id == "#legacytech")
        self.assertEqual(trend.momentum.direction, "declining")
        self.assertLess(trend.momentum.velocity, 0)
        self.assertLess(trend.momentum.growth_rate_pct, 0.0)

    def test_stable_topic_trend(self):
        # Equal distribution across periods
        posts = [
            {"id": "p_b1", "posted_at": self.base_time, "text": "General #Weather update"},
            {"id": "p_b2", "posted_at": self.base_time + timedelta(minutes=30), "text": "General #Weather report"},
            {"id": "p_c1", "posted_at": self.base_time + timedelta(hours=3), "text": "Sunny #Weather today"},
            {"id": "p_c2", "posted_at": self.base_time + timedelta(hours=3, minutes=30), "text": "Mild #Weather expected"},
        ]
        trends = self.engine.analyze_trends(posts)
        trend = next(t for t in trends if t.trend_id == "#weather")
        self.assertEqual(trend.momentum.direction, "stable")
        self.assertEqual(trend.momentum.velocity, 0.0)

    def test_sudden_volume_spike_and_emerging_detection(self):
        # 0 baseline posts for topic, 10 immediate recent posts during spike
        posts = [
            {"id": "bg_0", "posted_at": self.base_time, "text": "Calm regular day"},
        ] + [
            {
                "id": f"spike_{i}",
                "posted_at": self.base_time + timedelta(hours=3, minutes=i),
                "text": "Breaking news emergency announcement #DisasterAlert",
                "metrics": {"likes": 50, "shares": 20},
            }
            for i in range(10)
        ]
        trends = self.engine.analyze_trends(posts)
        alert_trend = next(t for t in trends if t.trend_id == "#disasteralert")
        self.assertTrue(alert_trend.is_emerging or alert_trend.is_spiking)
        self.assertGreater(alert_trend.momentum.momentum_score, 10.0)

    def test_platform_comparison_trends(self):
        posts = [
            {"platform": "x", "text": "Breaking #AI breakthrough on X", "posted_at": self.base_time},
            {"platform": "x", "text": "Another #AI update on X", "posted_at": self.base_time + timedelta(hours=2)},
            {"platform": "reddit", "text": "Discussion on #Gaming on Reddit", "posted_at": self.base_time + timedelta(hours=2)},
        ]
        plat_summaries = self.engine.calculate_platform_trends(posts)
        self.assertIn("x", plat_summaries)
        self.assertIn("reddit", plat_summaries)
        x_trend_names = [t.name for t in plat_summaries["x"].top_trends]
        self.assertIn("#ai", x_trend_names)

    def test_trend_ranking_by_momentum_score(self):
        posts = [
            # High momentum spike (0 -> 6 posts)
            {"posted_at": self.base_time + timedelta(hours=3), "text": "Viral item #ViralSpike", "metrics": {"likes": 200}},
            {"posted_at": self.base_time + timedelta(hours=3, minutes=5), "text": "Viral item #ViralSpike", "metrics": {"likes": 200}},
            {"posted_at": self.base_time + timedelta(hours=3, minutes=10), "text": "Viral item #ViralSpike", "metrics": {"likes": 200}},
            # Low momentum static item (5 -> 5 posts)
            {"posted_at": self.base_time, "text": "Routine news #RoutineNews"},
            {"posted_at": self.base_time + timedelta(hours=3), "text": "Routine news #RoutineNews"},
        ]
        report = self.engine.generate_detailed_report(posts)
        self.assertGreaterEqual(len(report.ranked_trends), 2)
        # Verify first ranked trend is the high momentum spike
        self.assertEqual(report.ranked_trends[0].trend_id, "#viralspike")

    def test_analytics_ready_post_compatibility(self):
        post = AnalyticsReadyPost(
            platform="reddit",
            external_post_id="r_999",
            text="Major milestone reached in #CleanTech research.",
            posted_at=self.base_time,
            metrics=PostMetricsSchema(likes=100, comments=20, shares=10, views=2000),
        )
        trends = self.engine.analyze_trends([post])
        self.assertTrue(any(t.name == "#cleantech" for t in trends))

    def test_analytics_engine_service_trend_integration(self):
        service = AnalyticsEngineService()
        posts = [
            {"id": "p1", "platform": "x", "posted_at": self.base_time, "text": "Initial test for #SpaceTech"},
            {"id": "p2", "platform": "x", "posted_at": self.base_time + timedelta(hours=2), "text": "Rocket launch #SpaceTech", "metrics": {"likes": 500}},
            {"id": "p3", "platform": "x", "posted_at": self.base_time + timedelta(hours=2, minutes=15), "text": "Orbit achieved #SpaceTech", "metrics": {"likes": 800}},
        ]
        report = service.analyze(posts)
        self.assertIsNotNone(report.detailed_trends)
        trends_rep = report.detailed_trends
        self.assertGreaterEqual(trends_rep.total_trends_evaluated, 1)
        self.assertTrue(any("trend" in s.lower() or "momentum" in s.lower() for s in report.summary_insights))


if __name__ == "__main__":
    unittest.main()
