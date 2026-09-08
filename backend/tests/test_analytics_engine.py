import unittest
from datetime import datetime, timedelta, timezone

from app.schemas.analytics_engine import (
    EngagementScoreBreakdown,
    IntervalUnit,
    NarrativeIntelligence,
    NarrativeLifecycleStage,
    Phase4AnalyticsReport,
    TemporalDynamicsReport,
    TimeSeriesBucket,
)
from app.schemas.data_quality import AnalyticsReadyPost
from app.schemas.post import PostMetricsSchema
from app.services.analytics_engine import (
    AnalyticsEngineService,
    EngagementEngine,
    NarrativeDynamicsEngine,
    TimeSeriesDynamicsEngine,
    extract_post_metrics,
    extract_post_timestamp,
    floor_to_interval,
    parse_timestamp_to_utc,
)


class TestEngagementEngine(unittest.TestCase):
    def setUp(self):
        self.engine = EngagementEngine(weight_like=1.0, weight_comment=2.0, weight_share=3.0)

    def test_empty_posts_engagement(self):
        breakdown = self.engine.calculate_engagement([])
        self.assertEqual(breakdown.total_posts, 0)
        self.assertEqual(breakdown.total_likes, 0)
        self.assertEqual(breakdown.weighted_engagement_score, 0.0)
        self.assertEqual(breakdown.virality_index, 0.0)
        self.assertEqual(breakdown.discussion_depth, 0.0)
        self.assertEqual(breakdown.engagement_rate_per_impression, 0.0)
        self.assertEqual(breakdown.average_post_engagement, 0.0)

    def test_single_post_metrics_calculation(self):
        post = {
            "platform": "twitter",
            "metrics": {
                "likes": 100,
                "comments": 20,
                "shares": 10,
                "views": 2000,
            }
        }
        breakdown = self.engine.calculate_engagement([post])
        # Weighted score: 100*1 + 20*2 + 10*3 = 100 + 40 + 30 = 170.0
        self.assertEqual(breakdown.total_posts, 1)
        self.assertEqual(breakdown.total_likes, 100)
        self.assertEqual(breakdown.total_comments, 20)
        self.assertEqual(breakdown.total_shares, 10)
        self.assertEqual(breakdown.total_views, 2000)
        self.assertEqual(breakdown.weighted_engagement_score, 170.0)
        self.assertEqual(breakdown.virality_index, 0.1)  # 10 / 100
        self.assertEqual(breakdown.discussion_depth, 0.2)  # 20 / 100
        # (100 + 20 + 10) / 2000 = 130 / 2000 = 0.065
        self.assertEqual(breakdown.engagement_rate_per_impression, 0.065)
        self.assertEqual(breakdown.average_post_engagement, 170.0)

    def test_zero_likes_and_zero_views_safety(self):
        post = {
            "platform": "telegram",
            "metrics": {
                "likes": 0,
                "comments": 5,
                "shares": 10,
                "views": 0,
            }
        }
        breakdown = self.engine.calculate_engagement([post])
        # Weighted score: 0 + 10 + 30 = 40.0
        self.assertEqual(breakdown.weighted_engagement_score, 40.0)
        self.assertEqual(breakdown.virality_index, 10.0)  # 10 / max(0, 1)
        self.assertEqual(breakdown.discussion_depth, 5.0)  # 5 / max(0, 1)
        self.assertEqual(breakdown.engagement_rate_per_impression, 0.0)

    def test_platform_breakdown(self):
        posts = [
            {"platform": "x", "metrics": {"likes": 50, "comments": 10, "shares": 5, "views": 500}},
            {"platform": "x", "metrics": {"likes": 50, "comments": 10, "shares": 5, "views": 500}},
            {"platform": "reddit", "metrics": {"likes": 200, "comments": 50, "shares": 10, "views": 1000}},
        ]
        breakdowns = self.engine.calculate_platform_breakdown(posts)
        self.assertIn("x", breakdowns)
        self.assertIn("reddit", breakdowns)
        self.assertEqual(breakdowns["x"].total_posts, 2)
        self.assertEqual(breakdowns["x"].total_likes, 100)
        self.assertEqual(breakdowns["reddit"].total_posts, 1)
        self.assertEqual(breakdowns["reddit"].total_likes, 200)

    def test_analytics_ready_post_compatibility(self):
        ready_post = AnalyticsReadyPost(
            platform="youtube",
            external_post_id="yt_123",
            text="Clean sample post text",
            posted_at=datetime(2026, 9, 8, 12, 0, 0, tzinfo=timezone.utc),
            metrics=PostMetricsSchema(likes=300, comments=40, shares=15, views=5000),
        )
        breakdown = self.engine.calculate_engagement([ready_post])
        self.assertEqual(breakdown.total_posts, 1)
        self.assertEqual(breakdown.total_likes, 300)
        self.assertEqual(breakdown.total_comments, 40)
        self.assertEqual(breakdown.total_shares, 15)
        self.assertEqual(breakdown.total_views, 5000)
        expected_score = 300 * 1.0 + 40 * 2.0 + 15 * 3.0
        self.assertEqual(breakdown.weighted_engagement_score, expected_score)


class TestTimeSeriesDynamicsEngine(unittest.TestCase):
    def setUp(self):
        self.engine = TimeSeriesDynamicsEngine()
        self.base_time = datetime(2026, 9, 8, 10, 0, 0, tzinfo=timezone.utc)

    def test_timestamp_parsing_and_flooring(self):
        dt_str = "2026-09-08T14:35:22Z"
        parsed = parse_timestamp_to_utc(dt_str)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.hour, 14)
        self.assertEqual(parsed.minute, 35)

        floored_hour = floor_to_interval(parsed, IntervalUnit.HOUR)
        self.assertEqual(floored_hour, datetime(2026, 9, 8, 14, 0, 0, tzinfo=timezone.utc))

        floored_day = floor_to_interval(parsed, IntervalUnit.DAY)
        self.assertEqual(floored_day, datetime(2026, 9, 8, 0, 0, 0, tzinfo=timezone.utc))

    def test_empty_time_series(self):
        report = self.engine.generate_time_series([])
        self.assertEqual(report.total_buckets, 0)
        self.assertEqual(report.buckets, [])
        self.assertIsNone(report.peak_bucket_start)
        self.assertEqual(report.peak_bucket_volume, 0)

    def test_hourly_bucketing_and_rolling_average(self):
        posts = [
            {"posted_at": self.base_time, "metrics": {"likes": 10}, "sentiment": "positive", "sentiment_score": 0.8},
            {"posted_at": self.base_time + timedelta(minutes=15), "metrics": {"likes": 20}, "sentiment": "positive", "sentiment_score": 0.6},
            {"posted_at": self.base_time + timedelta(hours=1, minutes=10), "metrics": {"likes": 30}, "sentiment": "negative", "sentiment_score": -0.5},
            {"posted_at": self.base_time + timedelta(hours=2, minutes=5), "metrics": {"likes": 50}, "sentiment": "neutral", "sentiment_score": 0.0},
        ]
        report = self.engine.generate_time_series(posts, interval_unit=IntervalUnit.HOUR, rolling_window_size=2)
        self.assertEqual(report.total_buckets, 3)
        self.assertEqual(report.buckets[0].post_count, 2)
        self.assertEqual(report.buckets[1].post_count, 1)
        self.assertEqual(report.buckets[2].post_count, 1)

        # First bucket rolling avg (window 2): 2 / 1 = 2.0
        self.assertEqual(report.buckets[0].rolling_post_count_avg, 2.0)
        # Second bucket rolling avg (window 2): (2 + 1) / 2 = 1.5
        self.assertEqual(report.buckets[1].rolling_post_count_avg, 1.5)
        # Third bucket rolling avg (window 2): (1 + 1) / 2 = 1.0
        self.assertEqual(report.buckets[2].rolling_post_count_avg, 1.0)

        # Sentiment averages
        self.assertAlmostEqual(report.buckets[0].avg_sentiment_polarity, 0.7)
        self.assertEqual(report.buckets[0].dominant_sentiment, "positive")
        self.assertEqual(report.buckets[1].dominant_sentiment, "negative")

    def test_anomaly_spike_detection(self):
        posts = []
        # Create baseline of 1 post per hour for 5 hours
        for h in range(5):
            posts.append({
                "posted_at": self.base_time + timedelta(hours=h),
                "metrics": {"likes": 5}
            })
        # Add huge spike at hour 5 (20 posts)
        for _ in range(20):
            posts.append({
                "posted_at": self.base_time + timedelta(hours=5),
                "metrics": {"likes": 50}
            })

        report = self.engine.generate_time_series(
            posts,
            interval_unit=IntervalUnit.HOUR,
            anomaly_threshold_z=1.5
        )
        self.assertEqual(report.total_buckets, 6)
        self.assertEqual(report.anomalous_intervals_count, 1)
        spike_bucket = report.buckets[5]
        self.assertTrue(spike_bucket.is_anomaly)
        self.assertGreater(spike_bucket.anomaly_score, 1.5)
        self.assertEqual(report.peak_bucket_volume, 20)
        self.assertEqual(report.peak_bucket_start, spike_bucket.bucket_start)


class TestNarrativeDynamicsEngine(unittest.TestCase):
    def setUp(self):
        self.engine = NarrativeDynamicsEngine()
        self.base_time = datetime(2026, 9, 8, 10, 0, 0, tzinfo=timezone.utc)

    def test_lifecycle_stage_classification(self):
        # Emerging: 0 -> 10
        self.assertEqual(
            self.engine.classify_lifecycle_stage(current_volume=10, previous_volume=0, velocity=10.0, acceleration=10.0),
            NarrativeLifecycleStage.EMERGING,
        )
        # Accelerating: 5 -> 15 (velocity 10, accel 5)
        self.assertEqual(
            self.engine.classify_lifecycle_stage(current_volume=15, previous_volume=5, velocity=10.0, acceleration=5.0),
            NarrativeLifecycleStage.ACCELERATING,
        )
        # Peak: 10 -> 12 (velocity 2, accel -8)
        self.assertEqual(
            self.engine.classify_lifecycle_stage(current_volume=12, previous_volume=10, velocity=2.0, acceleration=-8.0),
            NarrativeLifecycleStage.PEAK,
        )
        # Decaying: 20 -> 5 (velocity -15)
        self.assertEqual(
            self.engine.classify_lifecycle_stage(current_volume=5, previous_volume=20, velocity=-15.0, acceleration=-35.0),
            NarrativeLifecycleStage.DECAYING,
        )
        # Dormant: 0 -> 0
        self.assertEqual(
            self.engine.classify_lifecycle_stage(current_volume=0, previous_volume=0, velocity=0.0, acceleration=0.0),
            NarrativeLifecycleStage.DORMANT,
        )

    def test_narrative_analysis_with_timestamps_and_sentiment_drift(self):
        posts = [
            # Previous period: positive posts
            {
                "id": "p1",
                "posted_at": self.base_time,
                "topic": "Renewable Energy",
                "sentiment": "positive",
                "sentiment_score": 0.8,
                "metrics": {"likes": 10},
            },
            {
                "id": "p2",
                "posted_at": self.base_time + timedelta(hours=1),
                "topic": "Renewable Energy",
                "sentiment": "positive",
                "sentiment_score": 0.6,
                "metrics": {"likes": 10},
            },
            # Current period: 4 negative posts (rapid growth + negative shift)
            {
                "id": "p3",
                "posted_at": self.base_time + timedelta(hours=3),
                "topic": "Renewable Energy",
                "sentiment": "negative",
                "sentiment_score": -0.6,
                "metrics": {"likes": 50},
            },
            {
                "id": "p4",
                "posted_at": self.base_time + timedelta(hours=3, minutes=10),
                "topic": "Renewable Energy",
                "sentiment": "negative",
                "sentiment_score": -0.8,
                "metrics": {"likes": 50},
            },
            {
                "id": "p5",
                "posted_at": self.base_time + timedelta(hours=3, minutes=20),
                "topic": "Renewable Energy",
                "sentiment": "negative",
                "sentiment_score": -0.4,
                "metrics": {"likes": 50},
            },
            {
                "id": "p6",
                "posted_at": self.base_time + timedelta(hours=3, minutes=30),
                "topic": "Renewable Energy",
                "sentiment": "negative",
                "sentiment_score": -0.6,
                "metrics": {"likes": 50},
            },
        ]

        narratives = self.engine.analyze_narratives(posts)
        self.assertEqual(len(narratives), 1)
        narrative = narratives[0]
        self.assertEqual(narrative.label, "Renewable Energy")
        self.assertEqual(narrative.post_count, 6)
        self.assertEqual(narrative.dominant_sentiment, "negative")
        # Trajectory
        self.assertEqual(narrative.trajectory.previous_volume, 2)
        self.assertEqual(narrative.trajectory.current_volume, 4)
        self.assertGreater(narrative.trajectory.volume_velocity, 0)
        # Previous mean polarity: (0.8+0.6)/2 = 0.7; Current: (-0.6-0.8-0.4-0.6)/4 = -0.6
        # Sentiment drift: -0.6 - 0.7 = -1.3
        self.assertAlmostEqual(narrative.trajectory.sentiment_drift, -1.3, places=2)


class TestAnalyticsEngineService(unittest.TestCase):
    def setUp(self):
        self.service = AnalyticsEngineService()
        self.base_time = datetime(2026, 9, 8, 12, 0, 0, tzinfo=timezone.utc)

    def test_empty_posts_analysis(self):
        report = self.service.analyze([])
        self.assertIsInstance(report, Phase4AnalyticsReport)
        self.assertEqual(report.total_posts_evaluated, 0)
        self.assertEqual(report.engagement_analytics.total_posts, 0)
        self.assertEqual(len(report.summary_insights), 1)

    def test_full_pipeline_multi_dimensional_report(self):
        posts = [
            AnalyticsReadyPost(
                platform="x",
                external_post_id="x_101",
                text="Exciting breakthrough in quantum computing algorithms!",
                posted_at=self.base_time,
                metrics=PostMetricsSchema(likes=120, comments=25, shares=40, views=3000),
                metadata={
                    "sentiment": "positive",
                    "sentiment_score": 0.85,
                    "emotion": "joy",
                    "topic": "Quantum Computing",
                    "keywords": ["quantum", "computing", "algorithms"],
                },
            ),
            AnalyticsReadyPost(
                platform="x",
                external_post_id="x_102",
                text="Quantum computing hardware shows high error rate in test.",
                posted_at=self.base_time + timedelta(hours=1),
                metrics=PostMetricsSchema(likes=80, comments=30, shares=15, views=2000),
                metadata={
                    "sentiment": "negative",
                    "sentiment_score": -0.45,
                    "emotion": "disgust",
                    "topic": "Quantum Computing",
                    "keywords": ["quantum", "error", "hardware"],
                },
            ),
            AnalyticsReadyPost(
                platform="reddit",
                external_post_id="r_201",
                text="Discussion on clean energy micro-grids in rural regions.",
                posted_at=self.base_time + timedelta(hours=2),
                metrics=PostMetricsSchema(likes=250, comments=75, shares=10, views=4000),
                metadata={
                    "sentiment": "neutral",
                    "sentiment_score": 0.05,
                    "emotion": "neutral",
                    "topic": "Clean Energy",
                    "keywords": ["energy", "clean", "grid"],
                },
            ),
        ]

        report = self.service.analyze(posts, interval_unit=IntervalUnit.HOUR)

        self.assertEqual(report.total_posts_evaluated, 3)
        self.assertIsNotNone(report.analyzed_at)
        self.assertEqual(report.time_window_start, self.base_time)
        self.assertEqual(report.time_window_end, self.base_time + timedelta(hours=2))

        # Engagement verification
        eng = report.engagement_analytics
        self.assertEqual(eng.total_posts, 3)
        self.assertEqual(eng.total_likes, 120 + 80 + 250)
        self.assertEqual(eng.total_comments, 25 + 30 + 75)
        self.assertEqual(eng.total_shares, 40 + 15 + 10)
        self.assertEqual(eng.total_views, 3000 + 2000 + 4000)

        # Platform breakdown
        self.assertIn("x", report.platform_breakdown)
        self.assertIn("reddit", report.platform_breakdown)
        self.assertEqual(report.platform_breakdown["x"].total_posts, 2)
        self.assertEqual(report.platform_breakdown["reddit"].total_posts, 1)

        # Temporal dynamics
        self.assertEqual(report.temporal_dynamics.total_buckets, 3)
        self.assertEqual(report.temporal_dynamics.peak_bucket_volume, 1)

        # Narratives
        self.assertEqual(len(report.narratives), 2)
        narrative_labels = [n.label for n in report.narratives]
        self.assertIn("Quantum Computing", narrative_labels)
        self.assertIn("Clean Energy", narrative_labels)

        # Insights
        self.assertGreaterEqual(len(report.summary_insights), 3)

    def test_daily_and_weekly_bucketing(self):
        day1 = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
        day2 = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
        day8 = datetime(2026, 9, 8, 14, 0, 0, tzinfo=timezone.utc)

        posts = [
            {"posted_at": day1, "metrics": {"likes": 10}},
            {"posted_at": day2, "metrics": {"likes": 20}},
            {"posted_at": day8, "metrics": {"likes": 30}},
        ]

        # Daily
        daily_report = self.service.time_series_engine.generate_time_series(posts, interval_unit=IntervalUnit.DAY)
        self.assertEqual(daily_report.total_buckets, 8)  # Sept 1 to Sept 8 inclusive
        self.assertEqual(daily_report.buckets[0].post_count, 1)
        self.assertEqual(daily_report.buckets[1].post_count, 1)
        self.assertEqual(daily_report.buckets[2].post_count, 0)

        # Weekly
        weekly_report = self.service.time_series_engine.generate_time_series(posts, interval_unit=IntervalUnit.WEEK)
        self.assertGreaterEqual(weekly_report.total_buckets, 2)

    def test_narrative_with_explicit_extracted_topics(self):
        from app.schemas.topic import ExtractedTopic

        explicit_topics = [
            ExtractedTopic(
                topic_id="topic_ai_infra",
                label="AI Infrastructure",
                keywords=["gpu", "cluster", "datacenter"],
                post_count=2,
                external_post_ids=["p_1", "p_2"],
            )
        ]

        posts = [
            {"id": "p_1", "posted_at": self.base_time, "metrics": {"likes": 100}, "sentiment": "positive", "sentiment_score": 0.9},
            {"id": "p_2", "posted_at": self.base_time + timedelta(hours=1), "metrics": {"likes": 200}, "sentiment": "positive", "sentiment_score": 0.8},
            {"id": "p_3", "posted_at": self.base_time + timedelta(hours=2), "metrics": {"likes": 50}, "sentiment": "negative", "sentiment_score": -0.5},
        ]

        narratives = self.service.narrative_engine.analyze_narratives(posts, topics=explicit_topics)
        self.assertEqual(len(narratives), 2)  # 1 explicit + 1 general fallback
        ai_narrative = next(n for n in narratives if n.topic_id == "topic_ai_infra")
        self.assertEqual(ai_narrative.label, "AI Infrastructure")
        self.assertEqual(ai_narrative.post_count, 2)
        self.assertIn("gpu", ai_narrative.keywords)


if __name__ == "__main__":
    unittest.main()
