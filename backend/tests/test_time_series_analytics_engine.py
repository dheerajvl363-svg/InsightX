import unittest
from datetime import datetime, timedelta, timezone

from app.schemas.analytics_engine import (
    CrossPlatformTemporalReport,
    IntervalUnit,
    TemporalAnomalyDetail,
    TemporalBaselineComparison,
    TemporalDynamicsReport,
    TemporalTrajectorySignal,
    TimeSeriesBucket,
)
from app.schemas.data_quality import AnalyticsReadyPost
from app.schemas.post import PostMetricsSchema
from app.services.analytics_engine import (
    AnalyticsEngineService,
    TimeSeriesDynamicsEngine,
    floor_to_interval,
    interval_timedelta,
    parse_timestamp_to_utc,
)


class TestTimeSeriesAnalyticsEngine(unittest.TestCase):
    def setUp(self):
        self.engine = TimeSeriesDynamicsEngine()
        self.base_time = datetime(2026, 9, 8, 12, 0, 0, tzinfo=timezone.utc)

    def test_timestamp_parsing_and_flooring(self):
        # Epoch
        self.assertIsNotNone(parse_timestamp_to_utc(1788889000))
        # ISO string with Z
        iso_dt = parse_timestamp_to_utc("2026-09-08T12:34:56Z")
        self.assertEqual(iso_dt, datetime(2026, 9, 8, 12, 34, 56, tzinfo=timezone.utc))
        # None and invalid
        self.assertIsNone(parse_timestamp_to_utc(None))
        self.assertIsNone(parse_timestamp_to_utc("not-a-timestamp"))

        # Hourly flooring
        dt = datetime(2026, 9, 8, 14, 45, 30, tzinfo=timezone.utc)
        self.assertEqual(floor_to_interval(dt, IntervalUnit.HOUR), datetime(2026, 9, 8, 14, 0, 0, tzinfo=timezone.utc))
        # Daily flooring
        self.assertEqual(floor_to_interval(dt, IntervalUnit.DAY), datetime(2026, 9, 8, 0, 0, 0, tzinfo=timezone.utc))
        # Weekly flooring (Tuesday -> Monday)
        week_floor = floor_to_interval(dt, IntervalUnit.WEEK)
        self.assertEqual(week_floor.weekday(), 0)
        self.assertEqual(week_floor.hour, 0)

    def test_empty_and_single_observation_safety(self):
        empty_rep = self.engine.generate_time_series([])
        self.assertEqual(empty_rep.total_buckets, 0)
        self.assertEqual(len(empty_rep.buckets), 0)
        self.assertIsNone(empty_rep.baseline_comparison)
        self.assertGreaterEqual(len(empty_rep.temporal_insights), 1)

        single_post = [{"id": "single", "posted_at": self.base_time, "metrics": {"likes": 50}}]
        single_rep = self.engine.generate_time_series(single_post, interval_unit=IntervalUnit.HOUR)
        self.assertEqual(single_rep.total_buckets, 1)
        self.assertEqual(single_rep.buckets[0].post_count, 1)
        self.assertEqual(single_rep.buckets[0].velocity, 0.0)
        self.assertEqual(single_rep.trajectory_signal.classification, "insufficient_data")

    def test_hourly_daily_weekly_bucketing(self):
        posts = [
            {"id": "p1", "posted_at": self.base_time, "metrics": {"likes": 10}},
            {"id": "p2", "posted_at": self.base_time + timedelta(days=2), "metrics": {"likes": 20}},
            {"id": "p3", "posted_at": self.base_time + timedelta(days=9), "metrics": {"likes": 30}},
        ]
        # Daily
        daily_rep = self.engine.generate_time_series(posts, interval_unit=IntervalUnit.DAY)
        self.assertGreaterEqual(daily_rep.total_buckets, 10)
        # Weekly
        weekly_rep = self.engine.generate_time_series(posts, interval_unit=IntervalUnit.WEEK)
        self.assertGreaterEqual(weekly_rep.total_buckets, 2)

    def test_moving_average_smoothing(self):
        # 5 consecutive hourly buckets with known counts
        posts = (
            [{"posted_at": self.base_time, "metrics": {"likes": 10}}] * 2
            + [{"posted_at": self.base_time + timedelta(hours=1), "metrics": {"likes": 20}}] * 4
            + [{"posted_at": self.base_time + timedelta(hours=2), "metrics": {"likes": 30}}] * 6
        )
        report = self.engine.generate_time_series(posts, interval_unit=IntervalUnit.HOUR, rolling_window_size=3)
        self.assertEqual(report.total_buckets, 3)
        # Bucket 0: count 2 -> rolling avg = 2.0
        self.assertEqual(report.buckets[0].rolling_post_count_avg, 2.0)
        # Bucket 1: count 4 -> rolling avg = (2+4)/2 = 3.0
        self.assertEqual(report.buckets[1].rolling_post_count_avg, 3.0)
        # Bucket 2: count 6 -> rolling avg = (2+4+6)/3 = 4.0
        self.assertEqual(report.buckets[2].rolling_post_count_avg, 4.0)

    def test_temporal_velocity_and_acceleration(self):
        # Bucket 0: 2 posts, Bucket 1: 5 posts, Bucket 2: 9 posts
        posts = (
            [{"posted_at": self.base_time}] * 2
            + [{"posted_at": self.base_time + timedelta(hours=1)}] * 5
            + [{"posted_at": self.base_time + timedelta(hours=2)}] * 9
        )
        report = self.engine.generate_time_series(posts, interval_unit=IntervalUnit.HOUR)
        b0, b1, b2 = report.buckets[0], report.buckets[1], report.buckets[2]
        # b0: initial
        self.assertEqual(b0.velocity, 0.0)
        self.assertEqual(b0.acceleration, 0.0)
        # b1: v = 5 - 2 = 3.0, a = 3.0 - 0.0 = 3.0
        self.assertEqual(b1.velocity, 3.0)
        self.assertEqual(b1.acceleration, 3.0)
        # b2: v = 9 - 5 = 4.0, a = 4.0 - 3.0 = 1.0
        self.assertEqual(b2.velocity, 4.0)
        self.assertEqual(b2.acceleration, 1.0)

    def test_baseline_vs_current_comparison(self):
        # 2 baseline hours with 2 posts each (mean = 2.0), 2 current hours with 6 posts each (mean = 6.0)
        posts = (
            [{"posted_at": self.base_time, "sentiment_score": 0.5}] * 2
            + [{"posted_at": self.base_time + timedelta(hours=1), "sentiment_score": 0.5}] * 2
            + [{"posted_at": self.base_time + timedelta(hours=2), "sentiment_score": -0.5}] * 6
            + [{"posted_at": self.base_time + timedelta(hours=3), "sentiment_score": -0.5}] * 6
        )
        report = self.engine.generate_time_series(posts, interval_unit=IntervalUnit.HOUR, split_ratio=0.5)
        bc = report.baseline_comparison
        self.assertIsNotNone(bc)
        self.assertEqual(bc.baseline_mean_volume, 2.0)
        self.assertEqual(bc.current_mean_volume, 6.0)
        self.assertEqual(bc.volume_absolute_change, 4.0)
        # Growth: ((6.0 - 2.0) / 2.0) * 100 = +200%
        self.assertEqual(bc.volume_growth_rate_pct, 200.0)
        self.assertEqual(bc.direction, "rising")
        self.assertAlmostEqual(bc.sentiment_shift, -1.0, places=2)

    def test_multi_tiered_anomaly_and_spike_detection(self):
        # 10 baseline calm hours with 1 post each, 1 extreme spike hour with 25 posts
        posts = [
            {"posted_at": self.base_time + timedelta(hours=i), "metrics": {"likes": 10}}
            for i in range(10)
        ] + [
            {"posted_at": self.base_time + timedelta(hours=10), "metrics": {"likes": 500}}
            for _ in range(25)
        ]
        report = self.engine.generate_time_series(posts, interval_unit=IntervalUnit.HOUR, anomaly_threshold_z=2.0)
        self.assertGreaterEqual(report.anomalous_intervals_count, 1)
        self.assertGreaterEqual(len(report.detected_anomalies), 1)
        spike_anomaly = next(a for a in report.detected_anomalies if a.severity in {"anomalous", "extreme_spike"})
        self.assertGreaterEqual(spike_anomaly.z_score, 2.0)
        self.assertIn(spike_anomaly.affected_metric, {"volume", "engagement", "combined"})

    def test_zero_variance_and_constant_series(self):
        # Exactly 2 posts per hour for 5 hours (zero variance)
        posts = []
        for i in range(5):
            posts.extend([{"posted_at": self.base_time + timedelta(hours=i), "metrics": {"likes": 10}}] * 2)
        report = self.engine.generate_time_series(posts, interval_unit=IntervalUnit.HOUR)
        self.assertEqual(report.anomalous_intervals_count, 0)
        self.assertEqual(len(report.detected_anomalies), 0)
        for b in report.buckets:
            self.assertFalse(b.is_anomaly)
            self.assertEqual(b.anomaly_score, 0.0)

    def test_cross_platform_temporal_comparison(self):
        posts = [
            # X posts start early
            {"platform": "x", "posted_at": self.base_time, "metrics": {"likes": 50}},
            {"platform": "x", "posted_at": self.base_time + timedelta(hours=1), "metrics": {"likes": 80}},
            # Reddit posts start later but have high peak volume
            {"platform": "reddit", "posted_at": self.base_time + timedelta(hours=2), "metrics": {"likes": 500}},
            {"platform": "reddit", "posted_at": self.base_time + timedelta(hours=2), "metrics": {"likes": 600}},
            {"platform": "reddit", "posted_at": self.base_time + timedelta(hours=2), "metrics": {"likes": 700}},
        ]
        report = self.engine.generate_time_series(posts, interval_unit=IntervalUnit.HOUR)
        cp = report.platform_temporal_comparison
        self.assertIsNotNone(cp)
        self.assertEqual(cp.earliest_platform, "x")
        self.assertEqual(cp.peak_volume_platform, "reddit")
        self.assertIn("x", cp.platforms)
        self.assertIn("reddit", cp.platforms)

    def test_trajectory_signal_classification(self):
        # Accelerating series
        posts = (
            [{"posted_at": self.base_time}] * 1
            + [{"posted_at": self.base_time + timedelta(hours=1)}] * 2
            + [{"posted_at": self.base_time + timedelta(hours=2)}] * 6
            + [{"posted_at": self.base_time + timedelta(hours=3)}] * 15
        )
        report = self.engine.generate_time_series(posts, interval_unit=IntervalUnit.HOUR)
        traj = report.trajectory_signal
        self.assertIsNotNone(traj)
        self.assertIn(traj.classification, {"rising", "rapidly_rising"})
        self.assertGreater(traj.recent_velocity, 0)

    def test_analytics_ready_post_compatibility(self):
        posts = [
            AnalyticsReadyPost(
                platform="x",
                external_post_id="x_101",
                text="Exciting progress in clean energy tech.",
                posted_at=self.base_time,
                metrics=PostMetricsSchema(likes=100, comments=20, shares=10, views=1000),
                metadata={"sentiment": "positive", "sentiment_score": 0.8},
            ),
            AnalyticsReadyPost(
                platform="x",
                external_post_id="x_102",
                text="Second interval follow-up on energy grids.",
                posted_at=self.base_time + timedelta(hours=1),
                metrics=PostMetricsSchema(likes=300, comments=50, shares=30, views=3000),
                metadata={"sentiment": "positive", "sentiment_score": 0.85},
            ),
        ]
        report = self.engine.generate_time_series(posts, interval_unit=IntervalUnit.HOUR)
        self.assertEqual(report.total_buckets, 2)
        self.assertEqual(report.buckets[0].post_count, 1)
        self.assertEqual(report.buckets[1].post_count, 1)
        self.assertEqual(report.buckets[0].platform_distribution.get("x"), 1)

    def test_analytics_engine_service_integration(self):
        service = AnalyticsEngineService()
        posts = [
            {"id": "p1", "posted_at": self.base_time, "metrics": {"likes": 50}},
            {"id": "p2", "posted_at": self.base_time + timedelta(hours=1), "metrics": {"likes": 150}},
            {"id": "p3", "posted_at": self.base_time + timedelta(hours=2), "metrics": {"likes": 400}},
        ]
        report = service.analyze(posts, interval_unit=IntervalUnit.HOUR)
        self.assertIsNotNone(report.temporal_dynamics)
        td = report.temporal_dynamics
        self.assertEqual(td.total_buckets, 3)
        self.assertIsNotNone(td.baseline_comparison)
        self.assertIsNotNone(td.trajectory_signal)
        self.assertTrue(len(td.temporal_insights) >= 1)
        self.assertTrue(any("trajectory" in s.lower() or "peak" in s.lower() or "post" in s.lower() for s in report.summary_insights))


if __name__ == "__main__":
    unittest.main()
