import asyncio
from datetime import datetime, timedelta, timezone
import json
import time
import unittest

from app.main import app
from app.schemas.analytics_engine import (
    IntervalUnit,
    NarrativeLifecycleStage,
    Phase4AnalyticsReport,
)
from app.schemas.post import RawPostPayload
from app.services.analytics_engine import AnalyticsEngineService
from app.services.data_quality import DataQualityService
from app.services.normalizer import DataNormalizer


def call_api(method: str, path: str, body: dict = None) -> tuple[int, dict]:
    """
    Executes a native ASGI HTTP request against the FastAPI application.
    Tests full FastAPI pipeline: routing, dependency injection, validation, and serialization.
    """
    body_bytes = json.dumps(body).encode("utf-8") if body is not None else b""
    response_headers = {}
    response_body = []
    status_code = None

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method.upper(),
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body_bytes)).encode()),
        ],
    }

    async def receive():
        return {"type": "http.request", "body": body_bytes, "more_body": False}

    async def send(message):
        nonlocal status_code
        if message["type"] == "http.response.start":
            status_code = message["status"]
            for k, v in message.get("headers", []):
                response_headers[k.decode()] = v.decode()
        elif message["type"] == "http.response.body":
            response_body.append(message.get("body", b""))

    async def run():
        await app(scope, receive, send)

    asyncio.run(run())

    raw_text = b"".join(response_body).decode("utf-8")
    try:
        data = json.loads(raw_text)
    except Exception:
        data = {"raw_text": raw_text}

    return status_code, data


def build_realistic_multiplatform_dataset() -> list[dict]:
    """
    Generates a realistic, deterministic multi-platform dataset containing:
    - Multiple platforms (Twitter/X, Reddit, Telegram, YouTube)
    - Chronological timestamps across several discrete hourly windows
    - Multiple cohesive themes (Electric Vehicles, AI Innovation, Public Transit, Cloud Outages)
    - Balanced positive, negative, and neutral sentiment
    - Divergent engagement metrics and virality
    - At least one surging trend and temporal spike
    """
    base_dt = datetime(2026, 9, 8, 8, 0, 0, tzinfo=timezone.utc)

    posts = [
        # Window 1: 08:00 - 09:00 UTC (Baseline Period)
        {
            "id": "post_ev_1",
            "external_id": "x_ev_01",
            "platform": "twitter",
            "text": "Electric vehicle battery range and charging infrastructure are improving dramatically! #EV #CleanEnergy",
            "posted_at": (base_dt + timedelta(minutes=15)).isoformat(),
            "metrics": {"likes": 150, "comments": 35, "shares": 25, "views": 2500},
            "topics": ["Electric Vehicles", "Clean Energy"],
        },
        {
            "id": "post_ai_1",
            "external_id": "reddit_ai_01",
            "platform": "reddit",
            "text": "Deep learning models are significantly improving automated code generation. Excellent progress! #AI",
            "posted_at": (base_dt + timedelta(minutes=45)).isoformat(),
            "metrics": {"likes": 220, "comments": 85, "shares": 40, "views": 3200},
            "topics": ["AI", "Tech"],
        },
        # Window 2: 09:00 - 10:00 UTC
        {
            "id": "post_ev_2",
            "external_id": "youtube_ev_02",
            "platform": "youtube",
            "text": "In-depth review of new affordable EV sedan. Battery life and fast charging are outstanding! #EV",
            "posted_at": (base_dt + timedelta(hours=1, minutes=10)).isoformat(),
            "metrics": {"likes": 540, "comments": 120, "shares": 95, "views": 15000},
            "topics": ["Electric Vehicles"],
        },
        {
            "id": "post_transit_1",
            "external_id": "telegram_transit_01",
            "platform": "telegram",
            "text": "City metro expansion announcement scheduled for next week. #Metro #Transit",
            "posted_at": (base_dt + timedelta(hours=1, minutes=30)).isoformat(),
            "metrics": {"likes": 60, "comments": 10, "shares": 5, "views": 900},
            "topics": ["Public Transit"],
        },
        # Window 3: 10:00 - 11:00 UTC (Surge / Anomaly Period)
        {
            "id": "post_outage_1",
            "external_id": "x_outage_01",
            "platform": "twitter",
            "text": "Major cloud region outage is causing critical system crash and service disruptions everywhere! Terrible downtime. #Outage #DevOps",
            "posted_at": (base_dt + timedelta(hours=2, minutes=5)).isoformat(),
            "metrics": {"likes": 1200, "comments": 450, "shares": 680, "views": 45000},
            "topics": ["Cloud Outage", "DevOps"],
        },
        {
            "id": "post_outage_2",
            "external_id": "reddit_outage_02",
            "platform": "reddit",
            "text": "Database clusters failed across availability zones during the catastrophic cloud outage. #Outage #Crash",
            "posted_at": (base_dt + timedelta(hours=2, minutes=20)).isoformat(),
            "metrics": {"likes": 890, "comments": 310, "shares": 420, "views": 28000},
            "topics": ["Cloud Outage"],
        },
        {
            "id": "post_outage_3",
            "external_id": "telegram_outage_03",
            "platform": "telegram",
            "text": "Incident response team investigating massive cloud outage. Systems failing globally. #Outage",
            "posted_at": (base_dt + timedelta(hours=2, minutes=35)).isoformat(),
            "metrics": {"likes": 410, "comments": 180, "shares": 230, "views": 12000},
            "topics": ["Cloud Outage"],
        },
        {
            "id": "post_ai_2",
            "external_id": "x_ai_02",
            "platform": "twitter",
            "text": "AI research lab announces breakthroughs in reasoning efficiency and memory footprint. #AI",
            "posted_at": (base_dt + timedelta(hours=2, minutes=50)).isoformat(),
            "metrics": {"likes": 320, "comments": 60, "shares": 50, "views": 5000},
            "topics": ["AI"],
        },
        # Window 4: 11:00 - 12:00 UTC (Decay / Stabilization Period)
        {
            "id": "post_outage_4",
            "external_id": "x_outage_04",
            "platform": "twitter",
            "text": "Cloud systems recovering after severe outage. Engineers patched network routing. #Outage",
            "posted_at": (base_dt + timedelta(hours=3, minutes=15)).isoformat(),
            "metrics": {"likes": 350, "comments": 90, "shares": 70, "views": 8000},
            "topics": ["Cloud Outage"],
        },
        {
            "id": "post_ev_3",
            "external_id": "reddit_ev_03",
            "platform": "reddit",
            "text": "Solid-state battery breakthrough announced for next generation electric vehicles. Fantastic news! #EV #CleanEnergy",
            "posted_at": (base_dt + timedelta(hours=3, minutes=40)).isoformat(),
            "metrics": {"likes": 420, "comments": 110, "shares": 65, "views": 6200},
            "topics": ["Electric Vehicles", "Clean Energy"],
        },
    ]
    return posts


class TestPhase4EndToEndIntegration(unittest.TestCase):
    """
    End-to-end integration tests connecting:
    Raw Input -> Normalization -> Quality Validation -> AnalyticsEngineService -> Comprehensive Intelligence Report.
    """

    def setUp(self):
        self.raw_fixture = build_realistic_multiplatform_dataset()
        self.quality_service = DataQualityService()
        self.engine_service = AnalyticsEngineService()

    def test_1_full_pipeline_raw_to_report(self):
        """Validates full end-to-end analytical pipeline on multi-platform data."""
        # 1. Normalization
        raw_payloads = [RawPostPayload.model_validate(p) for p in self.raw_fixture]
        normalized_posts = [DataNormalizer.normalize(p) for p in raw_payloads]
        self.assertEqual(len(normalized_posts), 10)

        # 2. Quality Validation
        quality_batch = self.quality_service.validate_batch(normalized_posts)
        self.assertEqual(quality_batch.valid_count, 10)
        ready_posts = quality_batch.valid_posts

        # 3. Analytics Engine Execution
        report: Phase4AnalyticsReport = self.engine_service.analyze(
            posts=ready_posts,
            interval_unit=IntervalUnit.HOUR,
            rolling_window_size=2,
            anomaly_threshold_z=1.5,
        )

        # 4. Verify Comprehensive Analytical Sections
        self.assertEqual(report.total_posts_evaluated, 10)
        self.assertIsNotNone(report.analyzed_at)
        self.assertIsNotNone(report.time_window_start)
        self.assertIsNotNone(report.time_window_end)

        # Engagement Breakdown
        self.assertGreater(report.engagement_analytics.total_likes, 0)
        self.assertGreater(report.engagement_analytics.weighted_engagement_score, 0)
        self.assertGreater(report.engagement_analytics.virality_index, 0)
        self.assertIsNotNone(report.detailed_engagement)

        # Sentiment Distribution
        self.assertIsNotNone(report.detailed_sentiment)
        dist = report.detailed_sentiment.overall_distribution
        self.assertGreater(dist.positive_count, 0)
        self.assertGreater(dist.negative_count, 0)

        # Trend Momentum & Spike Detection
        self.assertIsNotNone(report.detailed_trends)
        self.assertGreater(report.detailed_trends.total_trends_evaluated, 0)
        # Cloud Outage or related trend should exhibit strong momentum
        trend_names = [t.name.lower() for t in report.detailed_trends.ranked_trends]
        self.assertTrue(any("outage" in name or "#outage" in name for name in trend_names))

        # Narrative Intelligence
        self.assertIsNotNone(report.detailed_narratives)
        self.assertGreater(len(report.detailed_narratives.ranked_narratives), 0)
        self.assertIsNotNone(report.detailed_narratives.dominant_narrative)

        # Time-Series Dynamics
        self.assertGreaterEqual(report.temporal_dynamics.total_buckets, 3)
        self.assertIsNotNone(report.temporal_dynamics.trajectory_signal)

        # Actionable Text Summary Insights
        self.assertGreater(len(report.summary_insights), 3)


class TestPhase4APIEndToEndIntegration(unittest.TestCase):
    """
    End-to-end HTTP integration tests verifying FastAPI routing, schema serialization,
    and real AnalyticsEngineService execution via native ASGI requests.
    """

    def setUp(self):
        self.fixture = build_realistic_multiplatform_dataset()

    def test_1_api_comprehensive_analyze_endpoint(self):
        """Test POST /api/v1/analytics/engine/analyze with full multi-platform payload."""
        payload = {
            "posts": self.fixture,
            "interval_unit": "hour",
            "rolling_window_size": 2,
            "anomaly_threshold_z": 1.5,
            "top_k": 5,
        }
        code, data = call_api("POST", "/api/v1/analytics/engine/analyze", payload)
        self.assertEqual(code, 200)
        self.assertEqual(data["total_posts_evaluated"], 10)
        self.assertIn("engagement_analytics", data)
        self.assertIn("temporal_dynamics", data)
        self.assertIn("detailed_sentiment", data)
        self.assertIn("detailed_trends", data)
        self.assertIn("detailed_narratives", data)
        self.assertIn("summary_insights", data)
        self.assertLessEqual(len(data["detailed_trends"]["ranked_trends"]), 5)

    def test_2_api_specialized_endpoints_real_pipeline(self):
        """Test all specialized Phase 4 endpoints against real data."""
        payload = {"posts": self.fixture}

        # Engagement
        code, eng = call_api("POST", "/api/v1/analytics/engine/engagement", payload)
        self.assertEqual(code, 200)
        self.assertEqual(eng["overall"]["total_posts"], 10)
        self.assertIn("platform_comparison", eng)

        # Sentiment
        code, sent = call_api("POST", "/api/v1/analytics/engine/sentiment", payload)
        self.assertEqual(code, 200)
        self.assertEqual(sent["overall_distribution"]["total_evaluated"], 10)
        self.assertIn("temporal_sentiment", sent)

        # Trends
        code, tr = call_api("POST", "/api/v1/analytics/engine/trends", payload)
        self.assertEqual(code, 200)
        self.assertGreater(tr["total_trends_evaluated"], 0)

        # Narratives
        code, narr = call_api("POST", "/api/v1/analytics/engine/narratives", payload)
        self.assertEqual(code, 200)
        self.assertGreater(len(narr["ranked_narratives"]), 0)

        # Time-Series
        code, ts = call_api("POST", "/api/v1/analytics/engine/time-series", payload)
        self.assertEqual(code, 200)
        self.assertGreaterEqual(ts["total_buckets"], 3)


    def test_3_api_invalid_inputs_and_contract_validation(self):
        """Test API contract validation and controlled 400/422 error handling."""
        # 1. Invalid timestamp format in start_time (Pydantic validation -> 422)
        code, data = call_api(
            "POST",
            "/api/v1/analytics/engine/analyze",
            {"posts": self.fixture, "start_time": "not-a-valid-datetime"},
        )
        self.assertEqual(code, 422)

        # 2. Reversed start/end timestamps (start_time > end_time -> 400 Bad Request)
        code, data = call_api(
            "POST",
            "/api/v1/analytics/engine/analyze",
            {
                "posts": self.fixture,
                "start_time": "2026-09-08T18:00:00Z",
                "end_time": "2026-09-08T10:00:00Z",
            },
        )
        self.assertEqual(code, 400)
        self.assertIn("start_time cannot be after end_time", data["detail"])

        # 3. Invalid top_k bounds: top_k=0 (ge=1) and top_k=999 (le=500) -> 422
        code, _ = call_api(
            "POST",
            "/api/v1/analytics/engine/analyze",
            {"posts": self.fixture, "top_k": 0},
        )
        self.assertEqual(code, 422)

        code, _ = call_api(
            "POST",
            "/api/v1/analytics/engine/analyze",
            {"posts": self.fixture, "top_k": 999},
        )
        self.assertEqual(code, 422)

        # 4. Invalid rolling_window_size bounds: 0 (ge=1) and 150 (le=100) -> 422
        code, _ = call_api(
            "POST",
            "/api/v1/analytics/engine/analyze",
            {"posts": self.fixture, "rolling_window_size": 0},
        )
        self.assertEqual(code, 422)

        code, _ = call_api(
            "POST",
            "/api/v1/analytics/engine/analyze",
            {"posts": self.fixture, "rolling_window_size": 150},
        )
        self.assertEqual(code, 422)

        # 5. Invalid interval unit -> 422
        code, _ = call_api(
            "POST",
            "/api/v1/analytics/engine/analyze",
            {"posts": self.fixture, "interval_unit": "century"},
        )
        self.assertEqual(code, 422)

        # 6. Safely handles missing optional fields with default behavior -> 200
        minimal_payload = {"posts": self.fixture}
        code, data = call_api("POST", "/api/v1/analytics/engine/analyze", minimal_payload)
        self.assertEqual(code, 200)
        self.assertEqual(data["total_posts_evaluated"], 10)


class TestCrossPhaseCompatibility(unittest.TestCase):
    """
    Validates that Phase 4 Analytics Engine operates harmoniously alongside
    Phase 1 DB queries, Phase 2 Ingestion, and Phase 3 atomic NLP endpoints.
    """

    def test_1_phase3_and_phase4_api_coexistence(self):
        """Ensures Phase 3 /api/v1/analytics/analyze and Phase 4 /api/v1/analytics/engine/analyze both work."""
        p3_payload = {
            "raw_posts": [
                {
                    "platform": "twitter",
                    "external_id": "coexist_01",
                    "text": "Great innovation happening in India today! #India",
                }
            ],
            "include_sentiment": True,
            "include_topics": True,
            "include_trends": False,
            "include_demographics": False,
        }
        code_p3, data_p3 = call_api("POST", "/api/v1/analytics/analyze", p3_payload)
        self.assertEqual(code_p3, 200)
        self.assertEqual(data_p3["total_posts_evaluated"], 1)
        self.assertIsNotNone(data_p3["sentiment"])

        p4_payload = {
            "raw_posts": [
                {
                    "platform": "twitter",
                    "external_id": "coexist_02",
                    "text": "Phase 4 Analytics Engine is running smoothly! #InsightX",
                    "posted_at": "2026-09-08T12:00:00Z",
                    "metrics": {"likes": 80, "comments": 20},
                }
            ]
        }
        code_p4, data_p4 = call_api("POST", "/api/v1/analytics/engine/analyze", p4_payload)
        self.assertEqual(code_p4, 200)
        self.assertEqual(data_p4["total_posts_evaluated"], 1)
        self.assertIsNotNone(data_p4["engagement_analytics"])

    def test_2_phase2_ingestion_and_phase4_analytics_flow(self):
        """Validates that posts processed through Phase 2 normalizer flow into Phase 4 engine."""
        raw_post = RawPostPayload(
            platform="reddit",
            external_id="p2_to_p4_01",
            text="Autonomous vehicle safety testing updates published. #Autonomous #Tech",
            posted_at=datetime(2026, 9, 8, 12, 0, 0, tzinfo=timezone.utc),
            metrics={"likes": 45, "comments": 12, "shares": 6, "views": 800},
        )
        normalized = DataNormalizer.normalize(raw_post)
        service = AnalyticsEngineService()
        report = service.analyze(posts=[normalized])
        self.assertEqual(report.total_posts_evaluated, 1)
        self.assertEqual(report.engagement_analytics.total_likes, 45)


class TestAnalyticsConsistency(unittest.TestCase):
    """
    Validates cross-component mathematical and analytical consistency:
    - Engagement metrics consistency across components
    - Sentiment distribution consistency across reports
    - Temporal aggregation integrity
    """

    def setUp(self):
        self.fixture = build_realistic_multiplatform_dataset()
        self.service = AnalyticsEngineService()
        self.report = self.service.analyze(posts=self.fixture, interval_unit=IntervalUnit.HOUR)

    def test_1_engagement_consistency(self):
        """Verify engagement metrics match between summary, detailed report, and platform sums."""
        summary_eng = self.report.engagement_analytics
        detailed_eng = self.report.detailed_engagement.overall
        self.assertEqual(summary_eng.total_posts, detailed_eng.total_posts)
        self.assertEqual(summary_eng.total_likes, detailed_eng.total_likes)
        self.assertEqual(summary_eng.total_comments, detailed_eng.total_comments)
        self.assertEqual(summary_eng.total_shares, detailed_eng.total_shares)
        self.assertAlmostEqual(summary_eng.weighted_engagement_score, detailed_eng.weighted_engagement_score, places=2)

        # Platform sums equal total sum
        platform_likes_sum = sum(p.total_likes for p in self.report.platform_breakdown.values())
        self.assertEqual(summary_eng.total_likes, platform_likes_sum)

        platform_weighted_sum = sum(p.weighted_engagement_score for p in self.report.platform_breakdown.values())
        self.assertAlmostEqual(summary_eng.weighted_engagement_score, platform_weighted_sum, places=2)

    def test_2_sentiment_consistency(self):
        """Verify sentiment totals and net sentiment bounds across detailed sentiment report."""
        sent_report = self.report.detailed_sentiment
        dist = sent_report.overall_distribution
        self.assertEqual(dist.total_evaluated, self.report.total_posts_evaluated)
        self.assertEqual(dist.positive_count + dist.neutral_count + dist.negative_count, dist.total_evaluated)
        self.assertGreaterEqual(dist.net_sentiment_score, -1.0)
        self.assertLessEqual(dist.net_sentiment_score, 1.0)

    def test_3_temporal_bucket_volume_consistency(self):
        """Verify time-series discrete bucket post sums match total evaluated posts."""
        ts_report = self.report.temporal_dynamics
        bucket_post_sum = sum(b.post_count for b in ts_report.buckets)
        self.assertEqual(bucket_post_sum, self.report.total_posts_evaluated)

        bucket_likes_sum = sum(b.total_likes for b in ts_report.buckets)
        self.assertEqual(bucket_likes_sum, self.report.engagement_analytics.total_likes)


class TestEdgeCasesAndHardening(unittest.TestCase):
    """
    Validates system resilience across unusual, degenerate, and edge-case inputs:
    - Missing text, missing timestamp, missing metrics, missing platform, missing author
    - Identical timestamps, sparse/irregular timestamps, zero baseline and variance
    - Mixed positive/negative/neutral content, very short text, hashtags-only, emoji-only, punctuation-heavy
    """

    def setUp(self):
        self.service = AnalyticsEngineService()

    def test_1_empty_dataset_safe_handling(self):
        """Test analytics engine with empty list without crashes."""
        report = self.service.analyze(posts=[])
        self.assertEqual(report.total_posts_evaluated, 0)
        self.assertEqual(report.engagement_analytics.weighted_engagement_score, 0.0)
        self.assertEqual(len(report.narratives), 0)
        self.assertEqual(report.temporal_dynamics.total_buckets, 0)
        self.assertIn("No posts provided", report.summary_insights[0])

    def test_2_missing_and_sparse_fields(self):
        """Test posts with omitted text, missing timestamps, missing metrics, missing platform, missing author."""
        sparse_posts = [
            # Missing text
            {"id": "sp_1", "posted_at": "2026-09-08T10:00:00Z"},
            # None text
            {"id": "sp_2", "text": None, "posted_at": "2026-09-08T10:10:00Z"},
            # Missing timestamp
            {"id": "sp_3", "text": "Post with omitted timestamp", "metrics": {"likes": 5}},
            # None timestamp
            {"id": "sp_4", "text": "Post with None timestamp", "posted_at": None},
            # Missing metrics dictionary
            {"id": "sp_5", "text": "Post with omitted metrics", "posted_at": "2026-09-08T10:20:00Z"},
            # None metrics
            {"id": "sp_6", "text": "Post with None metrics", "metrics": None},
            # Missing platform and author
            {"id": "sp_7", "text": "Post without platform or author"},
            # Explicit None platform and author
            {"id": "sp_8", "text": "Post with None platform and author", "platform": None, "author": None},
        ]
        report = self.service.analyze(posts=sparse_posts)
        self.assertEqual(report.total_posts_evaluated, 8)
        self.assertIsNotNone(report.engagement_analytics)
        self.assertIsNotNone(report.temporal_dynamics)

    def test_3_identical_and_sparse_irregular_timestamps(self):
        """Test temporal analysis on identical timestamps and sparse irregular multi-week timestamps."""
        # 1. Identical timestamps
        identical_ts_posts = [
            {"id": f"id_ts_{i}", "text": f"Event at identical moment {i}", "posted_at": "2026-09-08T12:00:00Z"}
            for i in range(5)
        ]
        rep_identical = self.service.analyze(posts=identical_ts_posts, interval_unit=IntervalUnit.HOUR)
        self.assertEqual(rep_identical.total_posts_evaluated, 5)
        self.assertEqual(rep_identical.temporal_dynamics.total_buckets, 1)

        # 2. Sparse irregular timestamps (weeks apart, out of chronological order)
        irregular_posts = [
            {"id": "irr_3", "text": "Late post", "posted_at": "2026-09-28T10:00:00Z"},
            {"id": "irr_1", "text": "Early post", "posted_at": "2026-09-01T10:00:00Z"},
            {"id": "irr_2", "text": "Mid post", "posted_at": "2026-09-14T10:00:00Z"},
        ]
        rep_irregular = self.service.analyze(posts=irregular_posts, interval_unit=IntervalUnit.WEEK)
        self.assertEqual(rep_irregular.total_posts_evaluated, 3)
        self.assertGreaterEqual(rep_irregular.temporal_dynamics.total_buckets, 3)

    def test_4_zero_baseline_and_variance(self):
        """Test zero variance robustness across engagement and sentiment."""
        zero_variance_posts = [
            {
                "id": f"zv_{i}",
                "text": "Neutral standard message",
                "posted_at": f"2026-09-08T1{i}:00:00Z",
                "metrics": {"likes": 0, "comments": 0, "shares": 0, "views": 0},
            }
            for i in range(4)
        ]
        report = self.service.analyze(posts=zero_variance_posts)
        self.assertEqual(report.total_posts_evaluated, 4)
        self.assertEqual(report.engagement_analytics.weighted_engagement_score, 0.0)
        self.assertEqual(report.detailed_engagement.distribution.std_dev_engagement, 0.0)

    def test_5_content_extremes_and_mixed_sentiment(self):
        """Test mixed sentiments, very short text, hashtags-only, emoji-only, and punctuation-heavy text."""
        extreme_posts = [
            {"id": "c1", "text": "Awesome fantastic outstanding experience! #LoveIt"},  # positive
            {"id": "c2", "text": "Horrible disaster terrible failure! #HateIt"},         # negative
            {"id": "c3", "text": "Regular status report item number 402."},             # neutral
            {"id": "c4", "text": "k"},                                                   # very short
            {"id": "c5", "text": "hi"},                                                  # very short
            {"id": "c6", "text": "#AI #Cloud #DevOps #Innovation"},                      # hashtag-only
            {"id": "c7", "text": "🚀🔥✨👍🎉"},                                          # emoji-only
            {"id": "c8", "text": "???!!!....."},                                         # punctuation-only
        ]
        report = self.service.analyze(posts=extreme_posts)
        self.assertEqual(report.total_posts_evaluated, 8)
        dist = report.detailed_sentiment.overall_distribution
        self.assertGreater(dist.positive_count, 0)
        self.assertGreater(dist.negative_count, 0)
        self.assertGreater(dist.neutral_count, 0)


class TestDeterminismAndPerformance(unittest.TestCase):
    """
    Validates pipeline determinism and performs empirical development performance sanity checks.
    """

    def setUp(self):
        self.fixture = build_realistic_multiplatform_dataset()
        self.service = AnalyticsEngineService()

    def test_1_pipeline_determinism(self):
        """Verify that identical input produces identical reports across consecutive executions."""
        run1 = self.service.analyze(posts=self.fixture)
        run2 = self.service.analyze(posts=self.fixture)
        run3 = self.service.analyze(posts=self.fixture)

        dump1 = run1.model_dump(exclude={"analyzed_at"})
        dump2 = run2.model_dump(exclude={"analyzed_at"})
        dump3 = run3.model_dump(exclude={"analyzed_at"})

        self.assertEqual(dump1, dump2)
        self.assertEqual(dump2, dump3)

    def test_2_performance_sanity_check_multi_tier(self):
        """
        Empirical development performance sanity check across representative dataset sizes:
        ~100, ~500, and ~1000 posts.
        NOTE: This test serves as a development sanity check to guard against accidental
        quadratic blowups or infinite loops, not as a strict production benchmark.
        """
        dataset_sizes = [100, 500, 1000]
        base_time = datetime(2026, 9, 8, 0, 0, 0, tzinfo=timezone.utc)
        recorded_timings = {}

        for count in dataset_sizes:
            posts = []
            for i in range(count):
                tpl = self.fixture[i % len(self.fixture)]
                item = dict(tpl)
                item["id"] = f"perf_{count}_{i}"
                item["posted_at"] = (base_time + timedelta(minutes=i)).isoformat()
                posts.append(item)

            self.assertEqual(len(posts), count)

            start_time = time.perf_counter()
            report = self.service.analyze(posts=posts, interval_unit=IntervalUnit.HOUR)
            elapsed = time.perf_counter() - start_time
            recorded_timings[count] = elapsed

            self.assertEqual(report.total_posts_evaluated, count)
            # Generous regression sanity guard (well above typical sub-second execution)
            self.assertLess(
                elapsed,
                8.0,
                f"Analytics execution exceeded sanity threshold: {elapsed:.3f}s for {count} posts",
            )

        # Sanity check: Ensure timings recorded for all sizes
        self.assertIn(100, recorded_timings)
        self.assertIn(500, recorded_timings)
        self.assertIn(1000, recorded_timings)


if __name__ == "__main__":
    unittest.main()

