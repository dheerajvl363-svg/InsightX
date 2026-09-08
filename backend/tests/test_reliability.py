import asyncio
from datetime import datetime, timedelta, timezone
import json
import time
import unittest
from pydantic import ValidationError

from app.main import app
from app.schemas.analytics_api import (
    CombinedAnalyticsResponse,
    CombinedAnalyzeRequest,
)
from app.schemas.data_quality import AnalyticsReadyPost, BatchDataQualityResult
from app.schemas.demographic import (
    AgeGroup,
    BatchDemographicResult,
    GenderCategory,
)
from app.schemas.emotion import BatchEmotionResult
from app.schemas.post import NormalizedPost, RawPostPayload
from app.schemas.sentiment import BatchSentimentResult, SentimentLabel
from app.schemas.topic import BatchTopicResult, ExtractedTopic
from app.schemas.trend import BatchTrendResult, TrendDirection
from app.services.data_quality import DataQualityService
from app.services.demographic import DemographicAnalysisService
from app.services.demographic.engine import RuleBasedDemographicEngine
from app.services.emotion import EmotionAnalysisService
from app.services.normalizer import DataNormalizer
from app.services.sentiment import SentimentAnalysisService
from app.services.topic import TopicAnalysisService
from app.services.trend import TrendAnalysisService


def call_api(method: str, path: str, body: dict = None) -> tuple[int, dict]:
    """Native ASGI caller for testing FastAPI pipeline without network dependencies."""
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


class TestPhase3ReliabilityAndQuality(unittest.TestCase):
    """
    Stress-tests Phase 1-3 components for robustness, edge cases,
    data quality validation, cross-service isolation, determinism,
    and large-batch execution.
    """

    def setUp(self):
        self.ref_time = datetime(2026, 9, 8, 12, 0, 0, tzinfo=timezone.utc)
        self.window_duration = timedelta(hours=1)

    # =========================================================================
    # A. Input Robustness Tests
    # =========================================================================

    def test_01_input_robustness_missing_and_blank_identifiers(self):
        """Verifies schema and service rejection of blank/missing platform and ID."""
        # 1. Blank platform in RawPostPayload raises ValidationError
        with self.assertRaises(ValidationError):
            RawPostPayload(platform="   ", external_id="ext_101", text="Valid text")

        # 2. Blank external_id raises ValidationError
        with self.assertRaises(ValidationError):
            RawPostPayload(platform="X", external_id="   ", text="Valid text")

        # 3. DataQualityService handles missing platform in raw dict gracefully
        dq_res1 = DataQualityService.validate_and_prepare({
            "platform": "",
            "external_id": "ext_102",
            "text": "Sample text",
            "posted_at": "2026-09-08T10:00:00Z",
        })
        self.assertFalse(dq_res1.is_valid)
        self.assertIn("Missing platform identifier.", dq_res1.errors)

        # 4. DataQualityService handles missing external_post_id gracefully
        dq_res2 = DataQualityService.validate_and_prepare({
            "platform": "X",
            "external_id": "   ",
            "text": "Sample text",
            "posted_at": "2026-09-08T10:00:00Z",
        })
        self.assertFalse(dq_res2.is_valid)
        self.assertIn("Missing external post identifier.", dq_res2.errors)

    def test_02_input_robustness_text_sanitization_and_quality_flags(self):
        """Tests zero-width characters, emojis, hashtags, mentions, and long text handling."""
        # Text containing zero-width spaces, emojis, mentions, hashtags, and whitespace
        complex_text = "  \u200b\ufeff🚀 Breaking alert from @InsightX: New AI update released! #Tech #AI \t\r\n\r\nCheck details.   "
        cleaned = DataQualityService.clean_text(complex_text)

        self.assertNotIn("\u200b", cleaned)
        self.assertNotIn("\ufeff", cleaned)
        self.assertIn("🚀", cleaned)
        self.assertIn("@InsightX", cleaned)
        self.assertIn("#Tech", cleaned)

        flags = DataQualityService.extract_quality_flags(cleaned)
        self.assertIn("has_emojis", flags)
        self.assertIn("has_hashtags", flags)
        self.assertIn("has_mentions", flags)

        # Very long text (5,000+ characters)
        long_text = ("InsightX continuous stream monitoring for urban transit intelligence. " * 80)
        long_cleaned = DataQualityService.clean_text(long_text)
        self.assertGreater(len(long_cleaned), 5000)

        # Ensure validation and flag extraction handle long text without crashing
        dq_res = DataQualityService.validate_and_prepare({
            "platform": "X",
            "external_id": "long_post_01",
            "text": long_cleaned,
            "posted_at": "2026-09-08T11:00:00Z",
        })
        self.assertTrue(dq_res.is_valid)
        self.assertGreater(dq_res.post.char_count, 5000)
        self.assertGreater(dq_res.post.word_count, 500)

    def test_03_input_robustness_malformed_and_boundary_timestamps(self):
        """Verifies boundary timestamps (future, pre-2000, explicit offsets)."""
        now_utc = datetime.now(timezone.utc)

        # Future timestamp (>24h ahead)
        future_ts = (now_utc + timedelta(days=5)).isoformat()
        dq_future = DataQualityService.validate_and_prepare({
            "platform": "X",
            "external_id": "future_01",
            "text": "Future message",
            "posted_at": future_ts,
        })
        self.assertFalse(dq_future.is_valid)
        self.assertTrue(any("distant future" in e for e in dq_future.errors))

        # Pre-2000 timestamp
        dq_past = DataQualityService.validate_and_prepare({
            "platform": "X",
            "external_id": "past_01",
            "text": "Pre-social media message",
            "posted_at": "1995-05-12T10:00:00Z",
        })
        self.assertFalse(dq_past.is_valid)
        self.assertTrue(any("social media era" in e for e in dq_past.errors))

        # Explicit offset (+05:30) standardized to UTC
        parsed_dt, inferred = DataNormalizer.parse_timestamp("2026-09-08T17:30:00+05:30")
        self.assertFalse(inferred)
        self.assertEqual(parsed_dt.tzinfo, timezone.utc)
        self.assertEqual(parsed_dt.hour, 12)
        self.assertEqual(parsed_dt.minute, 0)

    # =========================================================================
    # B. Data-Quality Robustness Tests
    # =========================================================================

    def test_04_data_quality_batch_isolation_and_no_contamination(self):
        """Ensures rejected batch records do not contaminate valid posts."""
        mixed_batch = [
            # 3 Valid posts
            {"platform": "X", "external_id": "valid_01", "text": "Valid post one", "posted_at": "2026-09-08T10:00:00Z"},
            {"platform": "Reddit", "external_id": "valid_02", "text": "Valid post two", "posted_at": "2026-09-08T10:10:00Z"},
            {"platform": "Telegram", "external_id": "valid_03", "text": "Valid post three", "posted_at": "2026-09-08T10:20:00Z"},
            # 3 Invalid posts
            {"platform": "X", "external_id": "invalid_empty", "text": "   \n\t  ", "posted_at": "2026-09-08T10:00:00Z"},
            {"platform": "", "external_id": "invalid_noplatform", "text": "Text without platform", "posted_at": "2026-09-08T10:00:00Z"},
            {"platform": "X", "external_id": "invalid_future", "text": "Text from 2099", "posted_at": "2099-01-01T00:00:00Z"},
        ]

        batch_result = DataQualityService.validate_batch(mixed_batch)

        self.assertEqual(batch_result.total_evaluated, 6)
        self.assertEqual(batch_result.valid_count, 3)
        self.assertEqual(batch_result.invalid_count, 3)

        valid_ids = [p.external_post_id for p in batch_result.valid_posts]
        self.assertEqual(valid_ids, ["valid_01", "valid_02", "valid_03"])

        rejected_ids = [r.external_post_id for r in batch_result.rejected_records]
        self.assertIn("invalid_empty", rejected_ids)
        self.assertIn("invalid_future", rejected_ids)

        # Valid posts can be analyzed immediately without error
        sent_res = SentimentAnalysisService().analyze_batch(batch_result.valid_posts)
        self.assertEqual(sent_res.total_analyzed, 3)

    def test_05_data_quality_empty_and_whitespace_batches(self):
        """Verifies handling of empty batches and whitespace-only batches."""
        # Empty batch
        empty_res = DataQualityService.validate_batch([])
        self.assertEqual(empty_res.total_evaluated, 0)
        self.assertEqual(empty_res.valid_count, 0)
        self.assertEqual(empty_res.invalid_count, 0)
        self.assertEqual(empty_res.valid_posts, [])

        # Whitespace-only batch
        whitespace_batch = [
            {"platform": "X", "external_id": f"ws_{i}", "text": "   ", "posted_at": "2026-09-08T10:00:00Z"}
            for i in range(4)
        ]
        ws_res = DataQualityService.validate_batch(whitespace_batch)
        self.assertEqual(ws_res.total_evaluated, 4)
        self.assertEqual(ws_res.valid_count, 0)
        self.assertEqual(ws_res.invalid_count, 4)

    # =========================================================================
    # C. Analytics Engine Edge Cases
    # =========================================================================

    def test_06_sentiment_edge_cases_negation_caps_punctuation(self):
        """Tests sentiment engine with negation, extreme caps, punctuation, and neutral text."""
        svc = SentimentAnalysisService()

        # 1. Negation handling: "not good" should have lower score than "good"
        p_good = AnalyticsReadyPost(
            platform="X", external_post_id="p_good", text="This is good.",
            posted_at=self.ref_time,
        )
        p_not_good = AnalyticsReadyPost(
            platform="X", external_post_id="p_not_good", text="This is not good at all.",
            posted_at=self.ref_time,
        )
        res_good = svc.analyze(p_good)
        res_not_good = svc.analyze(p_not_good)
        self.assertGreater(res_good.score, res_not_good.score)

        # 2. Extreme caps and punctuation
        p_caps = AnalyticsReadyPost(
            platform="X", external_post_id="p_caps", text="ABSOLUTELY TERRIBLE AND UNACCEPTABLE FAILURE!!!!",
            posted_at=self.ref_time,
        )
        res_caps = svc.analyze(p_caps)
        self.assertEqual(res_caps.label.value if hasattr(res_caps.label, "value") else str(res_caps.label), "negative")
        self.assertLess(res_caps.score, 0.0)

        # 3. Neutral objective text
        p_neutral = AnalyticsReadyPost(
            platform="X", external_post_id="p_neu",
            text="The city committee meeting was held at the municipal office at 10:00 AM.",
            posted_at=self.ref_time,
        )
        res_neu = svc.analyze(p_neutral)
        self.assertEqual(res_neu.label.value if hasattr(res_neu.label, "value") else str(res_neu.label), "neutral")
        self.assertEqual(res_neu.score, 0.0)

    def test_07_emotion_edge_cases_neutral_and_extreme(self):
        """Tests emotion classification with neutral text and high-intensity anger text."""
        svc = EmotionAnalysisService()

        # 1. Neutral factual text
        p_factual = AnalyticsReadyPost(
            platform="X", external_post_id="p_fact",
            text="The schedule for tomorrow was posted on the board.",
            posted_at=self.ref_time,
        )
        res_fact = svc.analyze(p_factual)
        self.assertEqual(res_fact.primary_emotion, "neutral")

        # 2. Furious angry text
        p_furious = AnalyticsReadyPost(
            platform="X", external_post_id="p_furious",
            text="I am completely furious and outraged by this terrible service!",
            posted_at=self.ref_time,
        )
        res_furious = svc.analyze(p_furious)
        self.assertIn(res_furious.primary_emotion, ["anger", "disgust"])
        self.assertGreaterEqual(res_furious.confidence, 0.0)
        self.assertLessEqual(res_furious.confidence, 1.0)

    def test_08_topic_edge_cases_sparse_and_duplicates(self):
        """Tests topic engine on single-post batch, duplicate posts, and empty-keyword scenarios."""
        topic_svc = TopicAnalysisService()

        # 1. Single post batch
        single_post = [AnalyticsReadyPost(
            platform="X", external_post_id="single_01",
            text="Single post discussing metro transportation.",
            posted_at=self.ref_time,
        )]
        res_single = topic_svc.extract_topics(single_post)
        self.assertIsInstance(res_single, BatchTopicResult)
        self.assertGreaterEqual(res_single.total_topics_found, 1)

        # 2. Duplicate identical posts
        dup_posts = [
            AnalyticsReadyPost(
                platform="X", external_post_id=f"dup_{i}",
                text="Identical post discussing urban metro rail transit expansion.",
                posted_at=self.ref_time,
            )
            for i in range(4)
        ]
        res_dups = topic_svc.extract_topics(dup_posts)
        # All 4 duplicates should cluster into a single coherent topic
        self.assertEqual(res_dups.total_topics_found, 1)
        self.assertEqual(res_dups.topics[0].post_count, 4)

    def test_09_trend_edge_cases_boundary_conditions(self):
        """Tests trend detection with zero baseline (EMERGING), zero current (DECLINING), and equal volume (STABLE)."""
        trend_svc = TrendAnalysisService()
        test_topic = ExtractedTopic(
            topic_id="topic_test_boundary",
            label="Boundary Topic",
            keywords=["boundary", "test"],
            post_ids=[],
            external_post_ids=["p_curr_1", "p_curr_2", "p_base_1", "p_base_2"],
            post_count=4,
        )

        # 1. Zero baseline, positive current -> EMERGING
        emerging_posts = [
            AnalyticsReadyPost(
                platform="X", external_post_id="p_curr_1", text="Emerging trend post one",
                posted_at=self.ref_time - timedelta(minutes=20),
            ),
            AnalyticsReadyPost(
                platform="X", external_post_id="p_curr_2", text="Emerging trend post two",
                posted_at=self.ref_time - timedelta(minutes=10),
            ),
        ]
        res_emerging = trend_svc.analyze_topic(
            topic=test_topic, posts=emerging_posts, reference_time=self.ref_time, window_duration=self.window_duration,
        )
        self.assertEqual(res_emerging.direction, TrendDirection.EMERGING)
        self.assertEqual(res_emerging.baseline_volume, 0)
        self.assertEqual(res_emerging.current_volume, 2)

        # 2. Positive baseline, zero current -> DECLINING
        declining_posts = [
            AnalyticsReadyPost(
                platform="X", external_post_id="p_base_1", text="Baseline post one",
                posted_at=self.ref_time - timedelta(minutes=90),
            ),
            AnalyticsReadyPost(
                platform="X", external_post_id="p_base_2", text="Baseline post two",
                posted_at=self.ref_time - timedelta(minutes=80),
            ),
        ]
        res_declining = trend_svc.analyze_topic(
            topic=test_topic, posts=declining_posts, reference_time=self.ref_time, window_duration=self.window_duration,
        )
        self.assertEqual(res_declining.direction, TrendDirection.DECLINING)
        self.assertEqual(res_declining.current_volume, 0)
        self.assertEqual(res_declining.baseline_volume, 2)

        # 3. Equal volumes: baseline=2, current=2 -> STABLE
        stable_posts = emerging_posts + declining_posts
        res_stable = trend_svc.analyze_topic(
            topic=test_topic, posts=stable_posts, reference_time=self.ref_time, window_duration=self.window_duration,
        )
        self.assertEqual(res_stable.direction, TrendDirection.STABLE)
        self.assertEqual(res_stable.growth_rate, 0.0)

    def test_10_demographic_edge_cases_unknowns_and_boundaries(self):
        """Tests demographic intelligence with all-unknown attributes, age boundaries, and suppression."""
        engine = RuleBasedDemographicEngine()

        # 1. All demographic fields unknown
        posts_unknown = [
            AnalyticsReadyPost(
                platform="X", external_post_id=f"unk_{i}", text="Message text",
                posted_at=self.ref_time, metadata={},
            )
            for i in range(5)
        ]
        demo_res_unk = DemographicAnalysisService(engine=engine).analyze_batch(data=posts_unknown)
        self.assertEqual(demo_res_unk.total_profiles_analyzed, 5)
        self.assertEqual(demo_res_unk.overall_distribution.age_groups.total_known, 0)
        self.assertEqual(demo_res_unk.overall_distribution.age_groups.total_unknown, 5)
        self.assertEqual(demo_res_unk.overall_distribution.gender.total_known, 0)

        # 2. Age boundary tests
        self.assertEqual(engine.normalize_age_group(-5, None), AgeGroup.UNKNOWN.value)
        self.assertEqual(engine.normalize_age_group(150, None), AgeGroup.UNKNOWN.value)
        self.assertEqual(engine.normalize_age_group(17, None), AgeGroup.UNDER_18.value)
        self.assertEqual(engine.normalize_age_group(18, None), AgeGroup.AGE_18_24.value)
        self.assertEqual(engine.normalize_age_group(24, None), AgeGroup.AGE_18_24.value)
        self.assertEqual(engine.normalize_age_group(25, None), AgeGroup.AGE_25_34.value)
        self.assertEqual(engine.normalize_age_group(55, None), AgeGroup.AGE_55_PLUS.value)

        # 3. Gender normalization variants
        self.assertEqual(engine.normalize_gender("f"), GenderCategory.FEMALE.value)
        self.assertEqual(engine.normalize_gender("woman"), GenderCategory.FEMALE.value)
        self.assertEqual(engine.normalize_gender("M"), GenderCategory.MALE.value)
        self.assertEqual(engine.normalize_gender("non-binary"), GenderCategory.NON_BINARY.value)
        self.assertEqual(engine.normalize_gender("trans"), GenderCategory.OTHER.value)
        self.assertEqual(engine.normalize_gender("unknown"), GenderCategory.UNKNOWN.value)

        # 4. Privacy suppression test with min_group_size=5
        suppress_engine = RuleBasedDemographicEngine(min_group_size=5)
        sparse_posts = [
            AnalyticsReadyPost(
                platform="X", external_post_id="p1", text="Text", posted_at=self.ref_time,
                metadata={"demographics": {"city": "Hyderabad", "age": 22}},
            ),
            AnalyticsReadyPost(
                platform="X", external_post_id="p2", text="Text", posted_at=self.ref_time,
                metadata={"demographics": {"city": "Bengaluru", "age": 28}},
            ),
        ]
        sparse_res = DemographicAnalysisService(engine=suppress_engine).analyze_batch(data=sparse_posts)
        # With min_group_size=5, cities with only 1 count must be suppressed
        self.assertIn("suppressed", sparse_res.overall_distribution.cities.counts)

    # =========================================================================
    # D. Unified API Robustness Tests
    # =========================================================================

    def test_11_api_robustness_all_flags_disabled(self):
        """Tests POST /api/v1/analytics/analyze when all feature flags are False."""
        payload = {
            "raw_posts": [
                {"platform": "X", "external_id": "p_flags_01", "text": "Valid test post.", "posted_at": "2026-09-08T11:00:00Z"},
            ],
            "include_sentiment": False,
            "include_emotion": False,
            "include_topics": False,
            "include_trends": False,
            "include_demographics": False,
        }
        status_code, data = call_api("POST", "/api/v1/analytics/analyze", payload)
        self.assertEqual(status_code, 200)
        self.assertEqual(data["total_posts_evaluated"], 1)
        self.assertEqual(data["valid_posts_count"], 1)
        self.assertIsNotNone(data["data_quality"])
        self.assertIsNone(data["sentiment"])
        self.assertIsNone(data["emotion"])
        self.assertIsNone(data["topics"])
        self.assertIsNone(data["trends"])
        self.assertIsNone(data["demographics"])

    def test_12_api_robustness_dependent_and_sparse_features(self):
        """Tests trends when topics are disabled (trends requires topics) and demographics with no explicit metadata."""
        # When include_trends=True but include_topics=False, API executes gracefully without error
        payload_trends_notopics = {
            "raw_posts": [
                {"platform": "X", "external_id": "p_dep_01", "text": "Testing dependent trends.", "posted_at": "2026-09-08T11:00:00Z"},
            ],
            "include_sentiment": False,
            "include_emotion": False,
            "include_topics": False,
            "include_trends": True,
            "include_demographics": False,
        }
        status_code, data = call_api("POST", "/api/v1/analytics/analyze", payload_trends_notopics)
        self.assertEqual(status_code, 200)
        self.assertIsNone(data["topics"])
        self.assertIsNone(data["trends"])  # Trends omitted since no topics were generated

        # Demographics on posts lacking demographic metadata
        payload_demo_sparse = {
            "raw_posts": [
                {"platform": "X", "external_id": "p_sparse_01", "text": "Post without user demographics.", "posted_at": "2026-09-08T11:00:00Z"},
            ],
            "include_sentiment": False,
            "include_emotion": False,
            "include_topics": False,
            "include_trends": False,
            "include_demographics": True,
        }
        s2, d2 = call_api("POST", "/api/v1/analytics/analyze", payload_demo_sparse)
        self.assertEqual(s2, 200)
        self.assertIsNotNone(d2["demographics"])
        self.assertEqual(d2["demographics"]["total_profiles_analyzed"], 1)
        self.assertEqual(d2["demographics"]["overall_distribution"]["age_groups"]["total_unknown"], 1)

    def test_13_api_robustness_error_handling(self):
        """Tests client error responses for empty or missing payloads."""
        # Empty body
        s1, d1 = call_api("POST", "/api/v1/analytics/analyze", {})
        self.assertEqual(s1, 400)
        self.assertIn("detail", d1)

        # Empty raw_posts
        s2, d2 = call_api("POST", "/api/v1/analytics/analyze", {"raw_posts": []})
        self.assertEqual(s2, 400)
        self.assertEqual(d2["detail"], "Empty post list provided for analysis.")

        # Individual endpoint with no input
        s3, d3 = call_api("POST", "/api/v1/analytics/sentiment", {})
        self.assertEqual(s3, 400)

    # =========================================================================
    # E. Cross-Service Isolation Tests
    # =========================================================================

    def test_14_cross_service_isolation_immutability(self):
        """Verifies that running analytics engines does not mutate input AnalyticsReadyPost objects."""
        original_post = AnalyticsReadyPost(
            platform="X",
            external_post_id="immut_001",
            text="Testing post immutability across all analytics engines.",
            raw_text="Testing post immutability across all analytics engines.",
            author_username="immut_user",
            posted_at=self.ref_time,
            metrics=None,
            metadata={"test_tag": "preserve_me"},
            char_count=52,
            word_count=7,
            quality_flags=["has_test_flag"],
        )
        post_list = [original_post]

        # Snapshot of fields before execution
        before_dict = original_post.model_dump()

        # Run all engines in sequence
        sent_res = SentimentAnalysisService().analyze_batch(post_list)
        emo_res = EmotionAnalysisService().analyze_batch(post_list)
        topic_res = TopicAnalysisService().extract_topics(post_list)
        trend_res = TrendAnalysisService().analyze_trends(
            topics=topic_res.topics, posts=post_list, reference_time=self.ref_time, window_duration=self.window_duration,
        )
        demo_res = DemographicAnalysisService().analyze_batch(data=post_list)

        # Snapshot after execution
        after_dict = original_post.model_dump()

        # Verify exact equality (no in-place mutation)
        self.assertEqual(before_dict, after_dict)

        # Verify order independence: running sentiment alone produces identical result
        sent_res_solo = SentimentAnalysisService().analyze_batch(post_list)
        self.assertEqual(sent_res.results[0].score, sent_res_solo.results[0].score)
        self.assertEqual(sent_res.results[0].label, sent_res_solo.results[0].label)

    # =========================================================================
    # F. Determinism Tests
    # =========================================================================

    def test_15_end_to_end_determinism_multi_run(self):
        """Verifies that running unified analytics 3 times produces strictly identical results."""
        payload = {
            "raw_posts": [
                {"platform": "X", "external_id": "det_01", "text": "Excited for the new AI updates!", "posted_at": "2026-09-08T11:10:00Z"},
                {"platform": "Reddit", "external_id": "det_02", "text": "Metro fares are way too expensive.", "posted_at": "2026-09-08T11:20:00Z"},
                {"platform": "Telegram", "external_id": "det_03", "text": "University exams schedule announced.", "posted_at": "2026-09-08T11:30:00Z"},
            ],
            "include_sentiment": True,
            "include_emotion": True,
            "include_topics": True,
            "include_trends": True,
            "include_demographics": True,
            "reference_time": "2026-09-08T12:00:00Z",
            "window_duration_seconds": 3600,
        }

        # Run 3 consecutive calls
        _, run1 = call_api("POST", "/api/v1/analytics/analyze", payload)
        _, run2 = call_api("POST", "/api/v1/analytics/analyze", payload)
        _, run3 = call_api("POST", "/api/v1/analytics/analyze", payload)

        # Sentiment counts
        self.assertEqual(run1["sentiment"]["positive_count"], run2["sentiment"]["positive_count"])
        self.assertEqual(run2["sentiment"]["positive_count"], run3["sentiment"]["positive_count"])

        # Emotion distribution
        self.assertEqual(run1["emotion"]["emotion_distribution"], run2["emotion"]["emotion_distribution"])
        self.assertEqual(run2["emotion"]["emotion_distribution"], run3["emotion"]["emotion_distribution"])

        # Topic labels
        labels1 = [t["label"] for t in run1["topics"]["topics"]]
        labels2 = [t["label"] for t in run2["topics"]["topics"]]
        labels3 = [t["label"] for t in run3["topics"]["topics"]]
        self.assertEqual(labels1, labels2)
        self.assertEqual(labels2, labels3)

        # Trend directions
        trends1 = [t["direction"] for t in run1["trends"]["trends"]]
        trends2 = [t["direction"] for t in run2["trends"]["trends"]]
        self.assertEqual(trends1, trends2)

    # =========================================================================
    # G. Large-Batch / Basic Performance Test
    # =========================================================================

    def test_16_synthetic_large_batch_performance(self):
        """Stress-tests unified analytics pipeline with a synthetic batch of 150 posts."""
        platforms = ["X", "Reddit", "Telegram", "YouTube"]
        sample_topics = [
            "Metro train fare hike and public transport ticket prices",
            "Artificial intelligence machine learning models and research advances",
            "College university semester exam schedules and hall tickets",
            "Renewable solar energy and electric vehicle battery technology",
            "Healthcare medical breakthroughs in preventive cardiology",
        ]

        batch_size = 150
        synthetic_posts = []
        base_time = datetime(2026, 9, 8, 10, 0, 0, tzinfo=timezone.utc)

        for i in range(batch_size):
            topic_text = sample_topics[i % len(sample_topics)]
            platform = platforms[i % len(platforms)]
            post_time = base_time + timedelta(minutes=(i * 45) % 120)
            synthetic_posts.append({
                "platform": platform,
                "external_id": f"perf_post_{i:04d}",
                "text": f"InsightX synthetic update #{i}: {topic_text}. Additional insights reported.",
                "author_username": f"user_{i % 25}",
                "posted_at": post_time.isoformat(),
                "metrics": {"likes": (i * 7) % 500, "shares": (i * 3) % 100},
                "metadata": {
                    "demographics": {
                        "age": 18 + (i % 50),
                        "gender": "female" if i % 2 == 0 else "male",
                        "city": "Hyderabad" if i % 3 == 0 else "Bengaluru",
                    }
                },
            })

        payload = {
            "raw_posts": synthetic_posts,
            "reference_time": "2026-09-08T12:00:00Z",
            "window_duration_seconds": 3600,
            "include_sentiment": True,
            "include_emotion": True,
            "include_topics": True,
            "include_trends": True,
            "include_demographics": True,
        }

        start_time = time.perf_counter()
        status_code, data = call_api("POST", "/api/v1/analytics/analyze", payload)
        elapsed_seconds = time.perf_counter() - start_time

        self.assertEqual(status_code, 200)
        self.assertEqual(data["total_posts_evaluated"], batch_size)
        self.assertEqual(data["valid_posts_count"], batch_size)

        # Assert all layers produced valid outputs
        self.assertEqual(len(data["sentiment"]["results"]), batch_size)
        self.assertEqual(len(data["emotion"]["results"]), batch_size)
        self.assertGreaterEqual(len(data["topics"]["topics"]), 1)
        self.assertGreaterEqual(len(data["trends"]["trends"]), 1)
        self.assertEqual(data["demographics"]["total_profiles_analyzed"], batch_size)

        # Sanity check on performance: 150 posts multi-layer analytics completes smoothly (< 10.0 seconds)
        self.assertLess(elapsed_seconds, 10.0, f"Execution took too long: {elapsed_seconds:.2f}s")


if __name__ == "__main__":
    unittest.main()
