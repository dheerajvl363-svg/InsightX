import unittest
from datetime import datetime, timedelta, timezone

from app.schemas.analytics_engine import (
    DetailedNarrativeReport,
    IntervalUnit,
    NarrativeIntelligence,
    NarrativeLifecycleStage,
    Phase4AnalyticsReport,
)
from app.schemas.data_quality import AnalyticsReadyPost
from app.schemas.post import PostMetricsSchema
from app.schemas.topic import ExtractedTopic
from app.services.analytics_engine import (
    AnalyticsEngineService,
    NarrativeDynamicsEngine,
)


class TestNarrativeAnalyticsEngine(unittest.TestCase):
    def setUp(self):
        self.engine = NarrativeDynamicsEngine()
        self.base_time = datetime(2026, 9, 8, 12, 0, 0, tzinfo=timezone.utc)

    def test_empty_and_malformed_posts_safety(self):
        empty_res = self.engine.analyze_narratives([])
        self.assertEqual(empty_res, [])

        report = self.engine.generate_detailed_report([])
        self.assertIsInstance(report, DetailedNarrativeReport)
        self.assertEqual(report.total_narratives_evaluated, 0)
        self.assertEqual(report.ranked_narratives, [])

        malformed_posts = [
            {"text": None, "posted_at": None},
            {"id": "bad_1"},
            {},
        ]
        narratives = self.engine.analyze_narratives(malformed_posts)
        self.assertGreaterEqual(len(narratives), 1)
        self.assertEqual(narratives[0].topic_id, "general")
        self.assertEqual(narratives[0].post_count, 3)

    def test_narrative_grouping_with_explicit_extracted_topics(self):
        topics = [
            ExtractedTopic(
                topic_id="topic_ev",
                label="Electric Vehicles",
                keywords=["battery", "charging", "ev"],
                post_count=2,
                external_post_ids=["ev_1", "ev_2"],
            ),
            ExtractedTopic(
                topic_id="topic_ai",
                label="Artificial Intelligence",
                keywords=["neural", "model", "ai"],
                post_count=1,
                external_post_ids=["ai_1"],
            ),
        ]
        posts = [
            {"id": "ev_1", "text": "Solid-state battery breakthrough #EV", "posted_at": self.base_time},
            {"id": "ev_2", "text": "Fast charging infrastructure rollout", "posted_at": self.base_time + timedelta(hours=1)},
            {"id": "ai_1", "text": "New AI model sets benchmark", "posted_at": self.base_time + timedelta(hours=2)},
        ]
        narratives = self.engine.analyze_narratives(posts, topics=topics)
        self.assertEqual(len(narratives), 2)
        n_map = {n.topic_id: n for n in narratives}
        self.assertIn("topic_ev", n_map)
        self.assertIn("topic_ai", n_map)
        self.assertEqual(n_map["topic_ev"].post_count, 2)
        self.assertEqual(n_map["topic_ai"].post_count, 1)

    def test_increasing_and_accelerating_narrative(self):
        # 1 post in baseline (prev), 5 posts in recent window (curr)
        posts = [
            {
                "id": "p_base",
                "posted_at": self.base_time,
                "topic": "Space Exploration",
                "sentiment": "positive",
                "sentiment_score": 0.8,
                "metrics": {"likes": 50, "shares": 10},
            },
            {
                "id": "p_cur1",
                "posted_at": self.base_time + timedelta(hours=3),
                "topic": "Space Exploration",
                "sentiment": "positive",
                "sentiment_score": 0.9,
                "metrics": {"likes": 200, "shares": 50},
            },
            {
                "id": "p_cur2",
                "posted_at": self.base_time + timedelta(hours=3, minutes=10),
                "topic": "Space Exploration",
                "sentiment": "positive",
                "sentiment_score": 0.85,
                "metrics": {"likes": 300, "shares": 80},
            },
            {
                "id": "p_cur3",
                "posted_at": self.base_time + timedelta(hours=3, minutes=20),
                "topic": "Space Exploration",
                "sentiment": "positive",
                "sentiment_score": 0.75,
                "metrics": {"likes": 150, "shares": 30},
            },
            {
                "id": "p_cur4",
                "posted_at": self.base_time + timedelta(hours=3, minutes=30),
                "topic": "Space Exploration",
                "sentiment": "positive",
                "sentiment_score": 0.95,
                "metrics": {"likes": 400, "shares": 100},
            },
            {
                "id": "p_cur5",
                "posted_at": self.base_time + timedelta(hours=3, minutes=40),
                "topic": "Space Exploration",
                "sentiment": "positive",
                "sentiment_score": 0.9,
                "metrics": {"likes": 250, "shares": 60},
            },
        ]
        narratives = self.engine.analyze_narratives(posts)
        self.assertEqual(len(narratives), 1)
        narrative = narratives[0]
        self.assertEqual(narrative.lifecycle_stage, NarrativeLifecycleStage.ACCELERATING)
        self.assertGreater(narrative.trajectory.volume_velocity, 0)
        self.assertGreater(narrative.trajectory.volume_acceleration, 0)
        self.assertGreater(narrative.trajectory.engagement_velocity, 0)
        self.assertGreater(narrative.narrative_impact_score, 10.0)

    def test_declining_and_decaying_narrative(self):
        # 5 posts in baseline, 1 post in recent window
        posts = [
            {"id": "p_b1", "posted_at": self.base_time, "topic": "Legacy Protocol", "sentiment": "neutral"},
            {"id": "p_b2", "posted_at": self.base_time + timedelta(minutes=10), "topic": "Legacy Protocol", "sentiment": "neutral"},
            {"id": "p_b3", "posted_at": self.base_time + timedelta(minutes=20), "topic": "Legacy Protocol", "sentiment": "neutral"},
            {"id": "p_b4", "posted_at": self.base_time + timedelta(minutes=30), "topic": "Legacy Protocol", "sentiment": "neutral"},
            {"id": "p_b5", "posted_at": self.base_time + timedelta(minutes=40), "topic": "Legacy Protocol", "sentiment": "neutral"},
            {"id": "p_c1", "posted_at": self.base_time + timedelta(hours=3), "topic": "Legacy Protocol", "sentiment": "negative"},
        ]
        narratives = self.engine.analyze_narratives(posts)
        narrative = narratives[0]
        self.assertEqual(narrative.lifecycle_stage, NarrativeLifecycleStage.DECAYING)
        self.assertLess(narrative.trajectory.volume_velocity, 0)

    def test_emerging_narrative_detection(self):
        # Background posts define earlier baseline; new narrative has 0 previous volume
        posts = [
            {"id": "bg_1", "posted_at": self.base_time, "topic": "Background Noise"},
            {"id": "bg_2", "posted_at": self.base_time + timedelta(minutes=30), "topic": "Background Noise"},
            {"id": "em_1", "posted_at": self.base_time + timedelta(hours=3), "topic": "Novel Discovery"},
            {"id": "em_2", "posted_at": self.base_time + timedelta(hours=3, minutes=15), "topic": "Novel Discovery"},
        ]
        narratives = self.engine.analyze_narratives(posts)
        em_narrative = next(n for n in narratives if n.topic_id == "novel_discovery")
        self.assertEqual(em_narrative.lifecycle_stage, NarrativeLifecycleStage.EMERGING)
        self.assertEqual(em_narrative.trajectory.previous_volume, 0)
        self.assertEqual(em_narrative.trajectory.current_volume, 2)

    def test_cross_temporal_sentiment_drift_and_aggregation(self):
        posts = [
            # Previous window: highly positive
            {"id": "p1", "posted_at": self.base_time, "topic": "Product Launch", "sentiment": "positive", "sentiment_score": 0.8},
            {"id": "p2", "posted_at": self.base_time + timedelta(minutes=10), "topic": "Product Launch", "sentiment": "positive", "sentiment_score": 0.6},
            # Current window: highly negative
            {"id": "p3", "posted_at": self.base_time + timedelta(hours=3), "topic": "Product Launch", "sentiment": "negative", "sentiment_score": -0.7},
            {"id": "p4", "posted_at": self.base_time + timedelta(hours=3, minutes=10), "topic": "Product Launch", "sentiment": "negative", "sentiment_score": -0.9},
        ]
        narratives = self.engine.analyze_narratives(posts)
        narrative = narratives[0]
        # Previous mean: 0.7, Current mean: -0.8 -> drift: -1.5
        self.assertAlmostEqual(narrative.trajectory.sentiment_drift, -1.5, places=2)
        self.assertEqual(narrative.positive_percentage, 50.0)
        self.assertEqual(narrative.negative_percentage, 50.0)
        self.assertEqual(narrative.net_sentiment_score, 0.0)

    def test_cross_platform_narrative_presence(self):
        posts = [
            {"id": "x_1", "platform": "x", "topic": "Cybersecurity", "posted_at": self.base_time, "metrics": {"likes": 100}},
            {"id": "r_1", "platform": "reddit", "topic": "Cybersecurity", "posted_at": self.base_time + timedelta(hours=1), "metrics": {"likes": 200}},
            {"id": "yt_1", "platform": "youtube", "topic": "Cybersecurity", "posted_at": self.base_time + timedelta(hours=2), "metrics": {"likes": 500}},
        ]
        narratives = self.engine.analyze_narratives(posts)
        narrative = narratives[0]
        self.assertCountEqual(narrative.platforms, ["x", "reddit", "youtube"])
        self.assertEqual(len(narrative.platform_breakdown), 3)
        self.assertIn("reddit", narrative.platform_breakdown)
        self.assertEqual(narrative.platform_breakdown["reddit"].post_count, 1)

    def test_generate_detailed_report_and_ranking(self):
        posts = [
            # High impact accelerating narrative
            {"id": "h_1", "platform": "x", "topic": "Quantum", "posted_at": self.base_time, "metrics": {"likes": 100}},
            {"id": "h_2", "platform": "x", "topic": "Quantum", "posted_at": self.base_time + timedelta(hours=3), "metrics": {"likes": 500}},
            {"id": "h_3", "platform": "reddit", "topic": "Quantum", "posted_at": self.base_time + timedelta(hours=3, minutes=10), "metrics": {"likes": 600}},
            {"id": "h_4", "platform": "x", "topic": "Quantum", "posted_at": self.base_time + timedelta(hours=3, minutes=20), "metrics": {"likes": 800}},
            # Low impact static narrative
            {"id": "l_1", "platform": "x", "topic": "Old News", "posted_at": self.base_time, "metrics": {"likes": 1}},
        ]
        report = self.engine.generate_detailed_report(posts)
        self.assertGreaterEqual(report.total_narratives_evaluated, 2)
        self.assertIsNotNone(report.dominant_narrative)
        self.assertEqual(report.dominant_narrative.topic_id, "quantum")
        self.assertEqual(report.fastest_growing_narrative.topic_id, "quantum")
        self.assertEqual(report.highest_engagement_narrative.topic_id, "quantum")
        self.assertTrue(len(report.cross_platform_narratives) >= 1)

    def test_analytics_ready_post_compatibility(self):
        post = AnalyticsReadyPost(
            platform="youtube",
            external_post_id="yt_999",
            text="Comprehensive breakdown of next-gen #FusionTech reactor designs.",
            posted_at=self.base_time,
            metrics=PostMetricsSchema(likes=1000, comments=250, shares=150, views=50000),
            metadata={
                "topic": "Fusion Tech",
                "sentiment": "positive",
                "sentiment_score": 0.9,
                "emotion": "joy",
            },
        )
        narratives = self.engine.analyze_narratives([post])
        self.assertEqual(len(narratives), 1)
        self.assertEqual(narratives[0].label, "Fusion Tech")
        self.assertEqual(narratives[0].sample_post_ids, ["yt_999"])
        self.assertGreater(narratives[0].total_engagement, 1000)

    def test_analytics_engine_service_narrative_integration(self):
        service = AnalyticsEngineService()
        posts = [
            {"id": "p1", "platform": "x", "topic": "Autonomous Agents", "posted_at": self.base_time, "metrics": {"likes": 150}},
            {"id": "p2", "platform": "x", "topic": "Autonomous Agents", "posted_at": self.base_time + timedelta(hours=2), "metrics": {"likes": 400}},
            {"id": "p3", "platform": "reddit", "topic": "Autonomous Agents", "posted_at": self.base_time + timedelta(hours=2, minutes=10), "metrics": {"likes": 600}},
        ]
        report = service.analyze(posts)
        self.assertIsNotNone(report.detailed_narratives)
        self.assertEqual(report.detailed_narratives.total_narratives_evaluated, 1)
        self.assertEqual(len(report.narratives), 1)
        self.assertTrue(any("narrative" in s.lower() for s in report.summary_insights))


if __name__ == "__main__":
    unittest.main()
