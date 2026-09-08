import unittest
from datetime import datetime, timedelta, timezone

from app.schemas.analytics_engine import (
    DetailedSentimentReport,
    IntervalUnit,
    Phase4AnalyticsReport,
    PlatformSentimentSummary,
    PostSentimentProfile,
    SentimentDistributionSummary,
    TemporalSentimentPoint,
)
from app.schemas.data_quality import AnalyticsReadyPost
from app.schemas.post import PostMetricsSchema
from app.services.analytics_engine import (
    AnalyticsEngineService,
    SentimentAnalyticsEngine,
    extract_post_text,
)


class TestSentimentAnalyticsEngine(unittest.TestCase):
    def setUp(self):
        self.engine = SentimentAnalyticsEngine()
        self.base_time = datetime(2026, 9, 8, 12, 0, 0, tzinfo=timezone.utc)

    def test_positive_text_classification(self):
        text = "This breakthrough in quantum computing is amazing and fantastic!"
        profile = self.engine.analyze_post(text)
        self.assertEqual(profile.label, "positive")
        self.assertGreater(profile.score, 0.3)
        self.assertGreater(profile.confidence, 0.5)

    def test_negative_text_classification(self):
        text = "The outage was a total failure and disaster. Terrible service."
        profile = self.engine.analyze_post(text)
        self.assertEqual(profile.label, "negative")
        self.assertLess(profile.score, -0.3)
        self.assertGreater(profile.confidence, 0.5)

    def test_neutral_text_classification(self):
        text = "The quarterly technical documentation was published at 10 AM."
        profile = self.engine.analyze_post(text)
        self.assertEqual(profile.label, "neutral")
        self.assertAlmostEqual(profile.score, 0.0, places=1)

    def test_empty_and_missing_text_safety(self):
        empty_prof = self.engine.analyze_post("")
        self.assertEqual(empty_prof.label, "neutral")
        self.assertEqual(empty_prof.score, 0.0)
        self.assertEqual(empty_prof.confidence, 0.0)

        none_dict_prof = self.engine.analyze_post({"text": None, "platform": "x"})
        self.assertEqual(none_dict_prof.label, "neutral")
        self.assertEqual(none_dict_prof.score, 0.0)

        whitespace_prof = self.engine.analyze_post("   \n\t  ")
        self.assertEqual(whitespace_prof.label, "neutral")
        self.assertEqual(whitespace_prof.score, 0.0)

    def test_sentiment_distribution_aggregation(self):
        posts = [
            {"id": "p1", "text": "Outstanding work, loving the new features!"},
            {"id": "p2", "text": "Super happy and excited for the launch."},
            {"id": "p3", "text": "Meeting scheduled for Monday."},
            {"id": "p4", "text": "Awful crash, horrible bug, very bad experience."},
        ]
        dist = self.engine.calculate_distribution(posts)
        self.assertEqual(dist.total_evaluated, 4)
        self.assertEqual(dist.positive_count, 2)
        self.assertEqual(dist.neutral_count, 1)
        self.assertEqual(dist.negative_count, 1)
        self.assertEqual(dist.positive_percentage, 50.0)
        self.assertEqual(dist.neutral_percentage, 25.0)
        self.assertEqual(dist.negative_percentage, 25.0)
        # Net sentiment: (2 - 1) / 4 = 0.25
        self.assertEqual(dist.net_sentiment_score, 0.25)
        self.assertEqual(dist.dominant_sentiment, "positive")

    def test_empty_posts_distribution(self):
        dist = self.engine.calculate_distribution([])
        self.assertEqual(dist.total_evaluated, 0)
        self.assertEqual(dist.positive_count, 0)
        self.assertEqual(dist.net_sentiment_score, 0.0)
        self.assertEqual(dist.dominant_sentiment, "neutral")

    def test_platform_grouping_sentiment(self):
        posts = [
            {"platform": "x", "text": "Great success, brilliant upgrade!"},
            {"platform": "x", "text": "Awesome performance improvements."},
            {"platform": "reddit", "text": "Terrible glitch, awful crash."},
        ]
        plat_summaries = self.engine.calculate_platform_sentiment(posts)
        self.assertIn("x", plat_summaries)
        self.assertIn("reddit", plat_summaries)
        self.assertEqual(plat_summaries["x"].dominant_sentiment, "positive")
        self.assertGreater(plat_summaries["x"].net_sentiment_score, 0.5)
        self.assertEqual(plat_summaries["reddit"].dominant_sentiment, "negative")
        self.assertLess(plat_summaries["reddit"].net_sentiment_score, -0.5)

    def test_temporal_aggregation_sentiment(self):
        posts = [
            {"posted_at": self.base_time, "text": "Incredible achievement!"},
            {"posted_at": self.base_time + timedelta(minutes=30), "text": "Brilliant and wonderful!"},
            {"posted_at": self.base_time + timedelta(hours=1, minutes=10), "text": "Regular status update."},
            {"posted_at": self.base_time + timedelta(hours=2, minutes=5), "text": "Horrible bug and terrible crash."},
        ]
        temporal_points = self.engine.calculate_temporal_sentiment(posts, interval_unit=IntervalUnit.HOUR)
        self.assertEqual(len(temporal_points), 3)
        self.assertEqual(temporal_points[0].post_count, 2)
        self.assertEqual(temporal_points[0].dominant_sentiment, "positive")
        self.assertEqual(temporal_points[1].dominant_sentiment, "neutral")
        self.assertEqual(temporal_points[2].dominant_sentiment, "negative")

    def test_extreme_posts_extraction(self):
        posts = [
            {"id": "pos1", "text": "Brilliant and outstanding masterpiece!"},
            {"id": "neu1", "text": "Standard documentation."},
            {"id": "neg1", "text": "Disastrous, horrible, terrible failure."},
        ]
        top_pos, top_neg = self.engine.extract_extreme_posts(posts, limit=2)
        self.assertEqual(len(top_pos), 1)
        self.assertEqual(top_pos[0].post_id, "pos1")
        self.assertEqual(len(top_neg), 1)
        self.assertEqual(top_neg[0].post_id, "neg1")

    def test_analytics_ready_post_compatibility(self):
        post = AnalyticsReadyPost(
            platform="telegram",
            external_post_id="tg_999",
            text="Clean and safe update delivered smoothly.",
            posted_at=self.base_time,
            metrics=PostMetricsSchema(likes=50, comments=5, shares=2, views=400),
        )
        profile = self.engine.analyze_post(post)
        self.assertEqual(profile.platform, "telegram")
        self.assertEqual(profile.post_id, "tg_999")
        self.assertEqual(profile.label, "positive")

    def test_analytics_engine_service_sentiment_integration(self):
        service = AnalyticsEngineService()
        posts = [
            AnalyticsReadyPost(
                platform="x",
                external_post_id="x_201",
                text="Exciting progress on machine learning models!",
                posted_at=self.base_time,
                metrics=PostMetricsSchema(likes=100, comments=10, shares=20, views=1500),
            ),
            AnalyticsReadyPost(
                platform="reddit",
                external_post_id="r_202",
                text="System offline due to catastrophic server crash.",
                posted_at=self.base_time + timedelta(hours=1),
                metrics=PostMetricsSchema(likes=50, comments=30, shares=5, views=1000),
            ),
        ]
        report = service.analyze(posts)
        self.assertIsNotNone(report.detailed_sentiment)
        det_sent = report.detailed_sentiment
        self.assertEqual(det_sent.overall_distribution.total_evaluated, 2)
        self.assertEqual(det_sent.overall_distribution.positive_count, 1)
        self.assertEqual(det_sent.overall_distribution.negative_count, 1)
        self.assertIn("x", det_sent.platform_sentiment)
        self.assertIn("reddit", det_sent.platform_sentiment)
        # Verify sentiment summary insight inclusion
        self.assertTrue(any("sentiment" in s.lower() for s in report.summary_insights))


if __name__ == "__main__":
    unittest.main()
