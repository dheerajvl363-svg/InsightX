import asyncio
from datetime import datetime, timedelta, timezone
import json
import unittest

from app.database import SessionLocal
from app.main import app
from app.models.metric import PostMetric
from app.models.post import Post
from app.models.user import User
from app.schemas.analytics_api import (
    CombinedAnalyticsResponse,
    CombinedAnalyzeRequest,
)
from app.schemas.data_quality import AnalyticsReadyPost, BatchDataQualityResult
from app.schemas.demographic import (
    BatchDemographicResult,
    DemographicDistribution,
    DemographicProfile,
)
from app.schemas.emotion import BatchEmotionResult
from app.schemas.post import NormalizedPost, RawPostPayload
from app.schemas.sentiment import BatchSentimentResult
from app.schemas.topic import BatchTopicResult
from app.schemas.trend import BatchTrendResult, TrendDirection
from app.services.adapters import detect_adapter, get_adapter
from app.services.analytics import AnalyticsService
from app.services.data_quality import DataQualityService
from app.services.demographic import DemographicAnalysisService
from app.services.demographic.engine import RuleBasedDemographicEngine
from app.services.emotion import EmotionAnalysisService
from app.services.ingestion import IngestionService
from app.services.normalizer import DataNormalizer
from app.services.sentiment import SentimentAnalysisService
from app.services.topic import TopicAnalysisService
from app.services.trend import TrendAnalysisService


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


class TestEndToEndPipeline(unittest.TestCase):
    """
    End-to-end integration test verifying the entire InsightX Phase 2 data pipeline:
    Realistic Raw Platform Payload
      -> Platform Adapter (to_raw_payload)
      -> RawPostPayload validation
      -> DataNormalizer (normalize)
      -> IngestionService (ingest_post)
      -> PostgreSQL persistence
      -> AnalyticsService query & aggregations
      -> Expected analytical results
    """

    def setUp(self):
        self.db = SessionLocal()
        self.ingestion_service = IngestionService(self.db)
        self.analytics_service = AnalyticsService(self.db)
        self.created_post_ids = []
        self.created_usernames = []

    def tearDown(self):
        # Clean up test metrics and posts
        if self.created_post_ids:
            self.db.query(PostMetric).filter(
                PostMetric.post_id.in_(self.created_post_ids)
            ).delete(synchronize_session=False)
            self.db.query(Post).filter(
                Post.id.in_(self.created_post_ids)
            ).delete(synchronize_session=False)

        # Clean up test user
        if self.created_usernames:
            self.db.query(User).filter(
                User.username.in_(self.created_usernames)
            ).delete(synchronize_session=False)

        self.db.commit()
        self.db.close()

    def test_complete_data_pipeline_end_to_end(self):
        """
        Executes and asserts the complete lifecycle of social media intelligence:
        1. Raw Twitter/X API-like JSON payload
        2. Adapter detection and mapping into RawPostPayload
        3. Normalization into canonical NormalizedPost
        4. Ingestion into PostgreSQL with user and metrics linkage
        5. Verification of DB records and foreign keys
        6. Analytics layer queries (post search, engagement summary, author summary, time series)
        7. Verification that returned analytics match original input metrics
        """
        test_external_id = "x_e2e_pipeline_test_987654"
        test_username = "e2e_analyst_prime"

        # 1. Realistic raw Twitter/X post payload
        raw_platform_payload = {
            "id": test_external_id,
            "text": "InsightX end-to-end integration pipeline verification for SIH 2026! #Analytics #AI",
            "author": {
                "username": test_username,
                "name": "E2E Lead Analyst",
            },
            "created_at": "2026-09-08T10:00:00Z",
            "lang": "en",
            "public_metrics": {
                "like_count": 450,
                "reply_count": 35,
                "retweet_count": 85,
                "impression_count": 12500,
            },
            "url": f"https://x.com/{test_username}/status/{test_external_id}",
        }

        # 2. Platform Adapter Layer
        adapter = detect_adapter(raw_platform_payload)
        self.assertIsNotNone(adapter, "Adapter detection failed for X payload")
        self.assertEqual(adapter.platform_name, "X")

        raw_post_payload = adapter.to_raw_payload(raw_platform_payload)
        self.assertIsInstance(raw_post_payload, RawPostPayload)
        self.assertEqual(raw_post_payload.platform, "X")
        self.assertEqual(raw_post_payload.external_id, test_external_id)
        self.assertEqual(raw_post_payload.author_username, test_username)
        self.assertEqual(raw_post_payload.author_display_name, "E2E Lead Analyst")
        self.assertEqual(raw_post_payload.metrics.likes, 450)
        self.assertEqual(raw_post_payload.metrics.comments, 35)
        self.assertEqual(raw_post_payload.metrics.shares, 85)
        self.assertEqual(raw_post_payload.metrics.views, 12500)

        # 3. Data Normalization Layer
        normalized_post = DataNormalizer.normalize(raw_post_payload)
        self.assertIsInstance(normalized_post, NormalizedPost)
        self.assertEqual(normalized_post.platform_name, "X")
        self.assertEqual(normalized_post.external_post_id, test_external_id)
        self.assertEqual(normalized_post.author_username, test_username)
        self.assertEqual(normalized_post.author_display_name, "E2E Lead Analyst")
        self.assertEqual(normalized_post.language, "en")
        self.assertEqual(
            normalized_post.posted_at,
            datetime(2026, 9, 8, 10, 0, 0, tzinfo=timezone.utc),
        )
        self.assertIsNotNone(normalized_post.metrics)
        self.assertEqual(normalized_post.metrics.likes, 450)
        self.assertEqual(normalized_post.metrics.comments, 35)
        self.assertEqual(normalized_post.metrics.shares, 85)
        self.assertEqual(normalized_post.metrics.views, 12500)

        # 4. Ingestion & Persistence Layer
        ingest_response = self.ingestion_service.ingest_post(normalized_post)
        self.assertEqual(ingest_response.status, "success")
        self.assertFalse(ingest_response.is_duplicate)
        self.assertIsNotNone(ingest_response.post_id)

        # Register for automated teardown
        post_id = ingest_response.post_id
        self.created_post_ids.append(post_id)
        self.created_usernames.append(test_username)

        # 5. Database Direct Integrity Verification
        persisted_post = self.db.query(Post).filter_by(id=post_id).first()
        self.assertIsNotNone(persisted_post)
        self.assertEqual(persisted_post.external_post_id, test_external_id)
        self.assertEqual(persisted_post.platform.name, "X")
        self.assertIsNotNone(persisted_post.user)
        self.assertEqual(persisted_post.user.username, test_username)
        self.assertEqual(persisted_post.user.display_name, "E2E Lead Analyst")
        self.assertEqual(len(persisted_post.metrics), 1)
        self.assertEqual(persisted_post.metrics[0].likes, 450)
        self.assertEqual(persisted_post.metrics[0].comments, 35)
        self.assertEqual(persisted_post.metrics[0].shares, 85)
        self.assertEqual(persisted_post.metrics[0].views, 12500)

        # 6. Analytics Layer Verification
        # 6.1 Filtered post query with text search and engagement threshold
        posts_result = self.analytics_service.get_posts(
            platform="X",
            author_username=test_username,
            search="SIH 2026",
            min_likes=400,
        )
        self.assertEqual(posts_result.total, 1)
        self.assertEqual(len(posts_result.items), 1)
        queried_post = posts_result.items[0]
        self.assertEqual(queried_post.id, post_id)
        self.assertEqual(queried_post.platform, "X")
        self.assertEqual(queried_post.author_username, test_username)
        self.assertIsNotNone(queried_post.metrics)
        self.assertEqual(queried_post.metrics.likes, 450)
        self.assertEqual(queried_post.metrics.comments, 35)
        self.assertEqual(queried_post.metrics.shares, 85)
        self.assertEqual(queried_post.metrics.views, 12500)

        # 6.2 Author Analytics summary
        author_result = self.analytics_service.get_author_summary(
            platform="X",
            search="SIH 2026",
        )
        self.assertEqual(author_result.total, 1)
        self.assertEqual(len(author_result.items), 1)
        author_summary = author_result.items[0]
        self.assertEqual(author_summary.username, test_username)
        self.assertEqual(author_summary.display_name, "E2E Lead Analyst")
        self.assertEqual(author_summary.post_count, 1)
        self.assertEqual(author_summary.total_likes, 450)
        self.assertEqual(author_summary.total_comments, 35)
        self.assertEqual(author_summary.total_shares, 85)
        self.assertEqual(author_summary.total_views, 12500)

        # 6.3 Engagement summary aggregation
        from datetime import timedelta

        start_t = persisted_post.posted_at - timedelta(hours=1)
        end_t = persisted_post.posted_at + timedelta(hours=1)
        engagement_summary = self.analytics_service.get_engagement_summary(
            platform="X",
            start_time=start_t,
            end_time=end_t,
        )
        self.assertGreaterEqual(engagement_summary.total_posts_analyzed, 1)
        self.assertGreaterEqual(engagement_summary.posts_with_metrics, 1)
        self.assertGreaterEqual(engagement_summary.total_likes, 450)
        self.assertGreaterEqual(engagement_summary.total_comments, 35)
        self.assertGreaterEqual(engagement_summary.total_shares, 85)
        self.assertGreaterEqual(engagement_summary.total_views, 12500)

        # 6.4 Engagement Time-Series aggregation
        timeseries_result = self.analytics_service.get_engagement_time_series(
            platform="X",
            author=test_username,
        )
        self.assertEqual(timeseries_result.total_points, 1)
        self.assertEqual(len(timeseries_result.points), 1)
        ts_point = timeseries_result.points[0]
        self.assertEqual(ts_point.date, "2026-09-08")
        self.assertEqual(ts_point.post_count, 1)
        self.assertEqual(ts_point.total_likes, 450)
        self.assertEqual(ts_point.total_comments, 35)
        self.assertEqual(ts_point.total_shares, 85)
        self.assertEqual(ts_point.total_views, 12500)
        self.assertEqual(ts_point.avg_likes, 450.0)
        self.assertEqual(ts_point.avg_views, 12500.0)


class TestPhase3AnalyticsIntegration(unittest.TestCase):
    """
    End-to-end integration test suite verifying the complete InsightX Phase 3
    analytics pipeline and Phase 2 -> Phase 3 integration boundary:
      Raw Platform Payloads
        -> DataNormalizer
        -> NormalizedPost
        -> DataQualityService
        -> AnalyticsReadyPost
        -> SentimentAnalysisService
        -> EmotionAnalysisService
        -> TopicAnalysisService
        -> TrendAnalysisService
        -> DemographicAnalysisService
        -> Unified Analytics API (POST /api/v1/analytics/analyze)
    """

    def setUp(self):
        self.reference_time = datetime(2026, 9, 8, 12, 0, 0, tzinfo=timezone.utc)
        self.window_duration = timedelta(hours=1)

        # 17 realistic posts spanning 3 topics, 4 platforms, and temporal windows:
        # - Baseline Window: (2026-09-08T10:00:00Z, 2026-09-08T11:00:00Z]
        # - Current Window:  (2026-09-08T11:00:00Z, 2026-09-08T12:00:00Z]
        self.raw_posts_data = [
            # -------------------------------------------------------------
            # Topic 1: Metro Rail Fares (Baseline: 2 posts, Current: 8 posts -> 300% growth -> SPIKING)
            # -------------------------------------------------------------
            {
                "platform": "X",
                "external_id": "metro_base_001",
                "text": "Metro train ticket prices are reasonably priced today. Good commute.",
                "author_username": "commuter_one",
                "posted_at": "2026-09-08T10:30:00Z",
                "metrics": {"likes": 12, "shares": 2, "comments": 1},
                "metadata": {"demographics": {"age": 24, "gender": "female", "city": "Hyderabad"}},
            },
            {
                "platform": "Telegram",
                "external_id": "metro_base_002",
                "text": "Looking forward to using the metro transit line this morning for travel.",
                "author_username": "transit_fan",
                "posted_at": "2026-09-08T10:45:00Z",
                "metrics": {"likes": 5, "shares": 0, "comments": 0},
                "metadata": {"demographics": {"age": 32, "gender": "male", "city": "Hyderabad"}},
            },
            {
                "platform": "X",
                "external_id": "metro_curr_001",
                "text": "Hyderabad metro rail fares increased drastically today! Completely outrageous! #MetroFares",
                "author_username": "angry_rider",
                "posted_at": "2026-09-08T11:05:00Z",
                "metrics": {"likes": 120, "shares": 45, "comments": 22},
                "metadata": {"demographics": {"age": 22, "gender": "female", "city": "Hyderabad"}},
            },
            {
                "platform": "Reddit",
                "external_id": "metro_curr_002",
                "text": "Metro train ticket fares are way too expensive now. Very frustrating and terrible experience!",
                "author_username": "daily_rider99",
                "posted_at": "2026-09-08T11:15:00Z",
                "metrics": {"likes": 88, "shares": 15, "comments": 34},
                "metadata": {"demographics": {"age": 28, "gender": "male", "city": "Hyderabad"}},
            },
            {
                "platform": "X",
                "external_id": "metro_curr_003",
                "text": "Sudden price hike on metro tickets makes public transit completely unaffordable! #MetroFares",
                "author_username": "city_voice",
                "posted_at": "2026-09-08T11:25:00Z",
                "metrics": {"likes": 210, "shares": 65, "comments": 40},
                "metadata": {"demographics": {"age": 26, "gender": "female", "city": "Hyderabad"}},
            },
            {
                "platform": "YouTube",
                "external_id": "metro_curr_004",
                "text": "Daily metro rail commuters protesting against massive fare increase outside stations.",
                "author_username": "yt_news_daily",
                "posted_at": "2026-09-08T11:35:00Z",
                "metrics": {"likes": 350, "shares": 50, "comments": 95},
                "metadata": {"demographics": {"age": 35, "gender": "male", "city": "Hyderabad"}},
            },
            {
                "platform": "X",
                "external_id": "metro_curr_005",
                "text": "Higher metro fares announced without prior public notice. Completely unfair and unacceptable!",
                "author_username": "metro_watcher",
                "posted_at": "2026-09-08T11:42:00Z",
                "metrics": {"likes": 95, "shares": 30, "comments": 18},
                "metadata": {"demographics": {"age": 23, "gender": "female", "city": "Hyderabad"}},
            },
            {
                "platform": "Reddit",
                "external_id": "metro_curr_006",
                "text": "Commuting by metro is getting impossible due to severe fare inflation across the city.",
                "author_username": "subway_surfer",
                "posted_at": "2026-09-08T11:48:00Z",
                "metrics": {"likes": 140, "shares": 22, "comments": 28},
                "metadata": {"demographics": {"age": 30, "gender": "male", "city": "Hyderabad"}},
            },
            {
                "platform": "Telegram",
                "external_id": "metro_curr_007",
                "text": "Alert: Metro ticket vending machines reflect new higher fares starting this hour.",
                "author_username": "city_alerts_tg",
                "posted_at": "2026-09-08T11:52:00Z",
                "metrics": {"likes": 40, "shares": 10, "comments": 5},
                "metadata": {"demographics": {"age": 29, "gender": "male", "city": "Hyderabad"}},
            },
            {
                "platform": "X",
                "external_id": "metro_curr_008",
                "text": "Shocked by the doubling of metro fares! How can students and workers afford this hike? #MetroFares",
                "author_username": "student_union_hyd",
                "posted_at": "2026-09-08T11:57:00Z",
                "metrics": {"likes": 320, "shares": 90, "comments": 55},
                "metadata": {"demographics": {"age": 20, "gender": "female", "city": "Hyderabad"}},
            },

            # -------------------------------------------------------------
            # Topic 2: AI Technology & Machine Learning (Baseline: 2, Current: 2 -> 0% growth -> STABLE)
            # -------------------------------------------------------------
            {
                "platform": "X",
                "external_id": "ai_base_001",
                "text": "Excited about new artificial intelligence technology and machine learning models research.",
                "author_username": "ai_researcher",
                "posted_at": "2026-09-08T10:15:00Z",
                "metrics": {"likes": 45, "shares": 10, "comments": 4},
                "metadata": {"demographics": {"age": 29, "gender": "male", "city": "Bengaluru"}},
            },
            {
                "platform": "Reddit",
                "external_id": "ai_base_002",
                "text": "Interesting discussion on artificial intelligence safety frameworks and responsible machine learning.",
                "author_username": "tech_thinker",
                "posted_at": "2026-09-08T10:50:00Z",
                "metrics": {"likes": 60, "shares": 12, "comments": 15},
                "metadata": {"demographics": {"age": 34, "gender": "female", "city": "Bengaluru"}},
            },
            {
                "platform": "X",
                "external_id": "ai_curr_001",
                "text": "Attending the national summit on artificial intelligence technology and machine learning innovations.",
                "author_username": "ai_attendee",
                "posted_at": "2026-09-08T11:20:00Z",
                "metrics": {"likes": 80, "shares": 18, "comments": 9},
                "metadata": {"demographics": {"age": 27, "gender": "male", "city": "Bengaluru"}},
            },
            {
                "platform": "YouTube",
                "external_id": "ai_curr_002",
                "text": "Deep learning breakthroughs and ethical artificial intelligence development guidelines tutorial.",
                "author_username": "ai_educator",
                "posted_at": "2026-09-08T11:45:00Z",
                "metrics": {"likes": 150, "shares": 25, "comments": 30},
                "metadata": {"demographics": {"age": 31, "gender": "female", "city": "Bengaluru"}},
            },

            # -------------------------------------------------------------
            # Topic 3: College Exams (Baseline: 2, Current: 1 -> -50% growth -> DECLINING)
            # -------------------------------------------------------------
            {
                "platform": "Telegram",
                "external_id": "exam_base_001",
                "text": "Final semester college university exam schedules published online today.",
                "author_username": "campus_bulletin",
                "posted_at": "2026-09-08T10:20:00Z",
                "metrics": {"likes": 30, "shares": 8, "comments": 2},
                "metadata": {},  # Unknown demographics
            },
            {
                "platform": "Reddit",
                "external_id": "exam_base_002",
                "text": "Students preparing for college university semester exams across all departments.",
                "author_username": "college_study",
                "posted_at": "2026-09-08T10:40:00Z",
                "metrics": {"likes": 25, "shares": 4, "comments": 6},
                "metadata": {},  # Unknown demographics
            },
            {
                "platform": "YouTube",
                "external_id": "exam_curr_001",
                "text": "University exam hall ticket download portal is now officially active for students.",
                "author_username": "exam_guide",
                "posted_at": "2026-09-08T11:30:00Z",
                "metrics": {"likes": 75, "shares": 15, "comments": 12},
                "metadata": {"demographics": {"age": 21, "gender": "male", "city": "Delhi"}},
            },
        ]

    def test_01_raw_to_normalization(self):
        """STEP 3: Verify RawPostPayload -> DataNormalizer -> NormalizedPost."""
        raw_payloads = [RawPostPayload(**d) for d in self.raw_posts_data]
        self.assertEqual(len(raw_payloads), 17)

        normalized_posts = [DataNormalizer.normalize(r) for r in raw_payloads]
        self.assertEqual(len(normalized_posts), 17)

        for raw_orig, norm in zip(self.raw_posts_data, normalized_posts):
            self.assertIsInstance(norm, NormalizedPost)
            self.assertEqual(norm.external_post_id, raw_orig["external_id"])
            self.assertIn(norm.platform_name, ["X", "Reddit", "Telegram", "YouTube"])
            self.assertIsNotNone(norm.text)
            self.assertEqual(norm.posted_at.tzinfo, timezone.utc)
            self.assertIsNotNone(norm.metrics)
            if "demographics" in raw_orig.get("metadata", {}):
                self.assertIn("demographics", norm.metadata)

    def test_02_normalization_to_data_quality(self):
        """STEP 4: Verify NormalizedPost -> DataQualityService -> AnalyticsReadyPost."""
        raw_payloads = [RawPostPayload(**d) for d in self.raw_posts_data]
        normalized_posts = [DataNormalizer.normalize(r) for r in raw_payloads]

        # Append one intentionally invalid post (whitespace only)
        invalid_raw = RawPostPayload(platform="X", external_id="invalid_blank", text="   \t  \n  ")
        invalid_norm = DataNormalizer.normalize(invalid_raw)
        batch_input = normalized_posts + [invalid_norm]

        quality_svc = DataQualityService()
        dq_result = quality_svc.validate_batch(batch_input)

        self.assertEqual(dq_result.total_evaluated, 18)
        self.assertEqual(dq_result.valid_count, 17)
        self.assertEqual(dq_result.invalid_count, 1)
        self.assertEqual(len(dq_result.valid_posts), 17)
        self.assertEqual(len(dq_result.rejected_records), 1)
        self.assertEqual(dq_result.rejected_records[0].external_post_id, "invalid_blank")

        # Validate AnalyticsReadyPost structure
        for post in dq_result.valid_posts:
            self.assertIsInstance(post, AnalyticsReadyPost)
            self.assertTrue(len(post.text) > 0)
            self.assertIsNotNone(post.raw_text)
            self.assertGreater(post.word_count, 0)
            self.assertEqual(post.posted_at.tzinfo, timezone.utc)

        # Check hashtag extraction flag
        metro_p3 = next(p for p in dq_result.valid_posts if p.external_post_id == "metro_curr_001")
        self.assertIn("has_hashtags", metro_p3.quality_flags)

    def test_03_analytics_services_coexist(self):
        """STEP 5: Verify all 5 Phase 3 analytics engines operate together on identical posts."""
        raw_payloads = [RawPostPayload(**d) for d in self.raw_posts_data]
        norm_posts = [DataNormalizer.normalize(r) for r in raw_payloads]
        quality_svc = DataQualityService()
        dq_result = quality_svc.validate_batch(norm_posts)
        posts = dq_result.valid_posts

        # Run all 5 analytics engines
        sentiment_svc = SentimentAnalysisService()
        emotion_svc = EmotionAnalysisService()
        topic_svc = TopicAnalysisService()
        trend_svc = TrendAnalysisService()
        demographic_svc = DemographicAnalysisService()

        sent_res = sentiment_svc.analyze_batch(posts)
        emo_res = emotion_svc.analyze_batch(posts)
        topic_res = topic_svc.extract_topics(posts)
        trend_res = trend_svc.analyze_trends(
            topics=topic_res.topics,
            posts=posts,
            reference_time=self.reference_time,
            window_duration=self.window_duration,
        )
        demo_res = demographic_svc.analyze_batch(
            data=posts,
            topics=topic_res.topics,
            sentiment_results=sent_res.results,
            trend_results=trend_res.trends,
        )

        self.assertEqual(sent_res.total_analyzed, 17)
        self.assertEqual(emo_res.total_analyzed, 17)
        self.assertGreaterEqual(topic_res.total_topics_found, 2)
        self.assertGreaterEqual(trend_res.total_topics_evaluated, 2)
        self.assertEqual(demo_res.total_profiles_analyzed, 17)

    def test_04_sentiment_and_emotion_consistency(self):
        """STEP 6: Verify sentiment and emotion outputs maintain stable contracts and post links."""
        raw_payloads = [RawPostPayload(**d) for d in self.raw_posts_data]
        norm_posts = [DataNormalizer.normalize(r) for r in raw_payloads]
        posts = DataQualityService().validate_batch(norm_posts).valid_posts

        sent_res = SentimentAnalysisService().analyze_batch(posts)
        emo_res = EmotionAnalysisService().analyze_batch(posts)

        self.assertEqual(len(sent_res.results), 17)
        self.assertEqual(len(emo_res.results), 17)

        # Check strongly negative post
        neg_post_sent = next(r for r in sent_res.results if r.external_post_id == "metro_curr_002")
        self.assertEqual(neg_post_sent.label.value if hasattr(neg_post_sent.label, "value") else str(neg_post_sent.label), "negative")
        self.assertLess(neg_post_sent.score, 0.0)

        # Check positive post
        pos_post_sent = next(r for r in sent_res.results if r.external_post_id == "ai_base_001")
        self.assertEqual(pos_post_sent.label.value if hasattr(pos_post_sent.label, "value") else str(pos_post_sent.label), "positive")
        self.assertGreater(pos_post_sent.score, 0.0)

        # Verify emotion outputs map correctly
        emo_post_ids = {r.external_post_id for r in emo_res.results}
        self.assertEqual(len(emo_post_ids), 17)
        self.assertIn("metro_curr_001", emo_post_ids)

    def test_05_topic_extraction_deterministic(self):
        """STEP 7: Verify topic clustering is deterministic and correctly clusters post IDs."""
        raw_payloads = [RawPostPayload(**d) for d in self.raw_posts_data]
        norm_posts = [DataNormalizer.normalize(r) for r in raw_payloads]
        posts = DataQualityService().validate_batch(norm_posts).valid_posts

        topic_svc = TopicAnalysisService()
        res1 = topic_svc.extract_topics(posts)
        res2 = topic_svc.extract_topics(posts)

        self.assertEqual(res1.total_topics_found, res2.total_topics_found)
        self.assertEqual([t.label for t in res1.topics], [t.label for t in res2.topics])

        # Verify that Metro posts clustered together
        metro_topic = next((t for t in res1.topics if any(k in t.label.lower() for k in ["metro", "train", "transit"])), None)
        self.assertIsNotNone(metro_topic, "Metro topic cluster was not identified")
        self.assertTrue(len(metro_topic.external_post_ids) >= 5)
        self.assertIn("metro_curr_001", metro_topic.external_post_ids)

    def test_06_topic_to_trend_spike_detection(self):
        """STEP 8: Verify Topic -> Trend correctly classifies SPIKING, STABLE, and DECLINING topics."""
        raw_payloads = [RawPostPayload(**d) for d in self.raw_posts_data]
        norm_posts = [DataNormalizer.normalize(r) for r in raw_payloads]
        posts = DataQualityService().validate_batch(norm_posts).valid_posts

        topic_res = TopicAnalysisService().extract_topics(posts)
        trend_svc = TrendAnalysisService()

        trend_res = trend_svc.analyze_trends(
            topics=topic_res.topics,
            posts=posts,
            reference_time=self.reference_time,
            window_duration=self.window_duration,
        )

        trend_map = {t.topic_label.lower(): t for t in trend_res.trends}

        # 1. Metro topic: baseline=2, current=8 -> 300% growth -> SPIKING
        metro_key = next((k for k in trend_map if "metro" in k or "train" in k), None)
        self.assertIsNotNone(metro_key)
        metro_trend = trend_map[metro_key]
        self.assertEqual(metro_trend.direction, TrendDirection.SPIKING)
        self.assertEqual(metro_trend.current_volume, 8)
        self.assertEqual(metro_trend.baseline_volume, 2)
        self.assertAlmostEqual(metro_trend.growth_rate, 300.0, places=1)
        self.assertIn("metro_curr_001", metro_trend.external_post_ids)

        # 2. AI topic: baseline=2, current=2 -> 0% growth -> STABLE
        ai_key = next((k for k in trend_map if "artificial" in k or "intelligence" in k or "ai" in k.split()), None)
        self.assertIsNotNone(ai_key)
        ai_trend = trend_map[ai_key]
        self.assertEqual(ai_trend.direction, TrendDirection.STABLE)
        self.assertEqual(ai_trend.current_volume, 2)
        self.assertEqual(ai_trend.baseline_volume, 2)
        self.assertAlmostEqual(ai_trend.growth_rate, 0.0, places=1)

        # 3. College topic: baseline=2, current=1 -> -50% growth -> DECLINING
        college_key = next((k for k in trend_map if "college" in k or "university" in k or "exam" in k), None)
        self.assertIsNotNone(college_key)
        college_trend = trend_map[college_key]
        self.assertEqual(college_trend.direction, TrendDirection.DECLINING)
        self.assertEqual(college_trend.current_volume, 1)
        self.assertEqual(college_trend.baseline_volume, 2)
        self.assertAlmostEqual(college_trend.growth_rate, -50.0, places=1)

    def test_07_demographic_correlations(self):
        """STEP 9: Verify Demographic Intelligence correlates with topics, sentiment, and trends with privacy."""
        raw_payloads = [RawPostPayload(**d) for d in self.raw_posts_data]
        norm_posts = [DataNormalizer.normalize(r) for r in raw_payloads]
        posts = DataQualityService().validate_batch(norm_posts).valid_posts

        topic_res = TopicAnalysisService().extract_topics(posts)
        sent_res = SentimentAnalysisService().analyze_batch(posts)
        trend_res = TrendAnalysisService().analyze_trends(
            topics=topic_res.topics,
            posts=posts,
            reference_time=self.reference_time,
            window_duration=self.window_duration,
        )

        demo_svc = DemographicAnalysisService()
        demo_res = demo_svc.analyze_batch(
            data=posts,
            topics=topic_res.topics,
            sentiment_results=sent_res.results,
            trend_results=trend_res.trends,
        )

        self.assertEqual(demo_res.total_profiles_analyzed, 17)
        self.assertGreater(demo_res.overall_distribution.age_groups.total_known, 0)
        self.assertGreater(demo_res.overall_distribution.age_groups.total_unknown, 0)
        self.assertGreater(demo_res.overall_distribution.gender.total_known, 0)
        self.assertGreater(demo_res.overall_distribution.cities.total_known, 0)

        # Cross-correlations
        self.assertGreater(len(demo_res.topic_breakdowns), 0)
        self.assertGreater(len(demo_res.sentiment_breakdowns), 0)
        self.assertGreater(len(demo_res.trend_breakdowns), 0)

        # Privacy suppression test: min_group_size=5 suppresses small cohorts into 'suppressed'
        privacy_engine = RuleBasedDemographicEngine(min_group_size=5)
        privacy_demo_svc = DemographicAnalysisService(engine=privacy_engine)
        privacy_res = privacy_demo_svc.analyze_batch(data=posts)
        self.assertIn("suppressed", privacy_res.overall_distribution.cities.counts)

    def test_08_full_unified_api_pipeline(self):
        """STEP 10: Verify POST /api/v1/analytics/analyze executes full multi-layer pipeline."""
        payload = {
            "raw_posts": self.raw_posts_data,
            "reference_time": self.reference_time.isoformat(),
            "window_duration_seconds": 3600,
            "include_sentiment": True,
            "include_emotion": True,
            "include_topics": True,
            "include_trends": True,
            "include_demographics": True,
        }

        status_code, data = call_api("POST", "/api/v1/analytics/analyze", payload)

        self.assertEqual(status_code, 200)
        self.assertEqual(data["total_posts_evaluated"], 17)
        self.assertEqual(data["valid_posts_count"], 17)
        self.assertIsNotNone(data["data_quality"])
        self.assertIsNotNone(data["sentiment"])
        self.assertIsNotNone(data["emotion"])
        self.assertIsNotNone(data["topics"])
        self.assertIsNotNone(data["trends"])
        self.assertIsNotNone(data["demographics"])

        # Nested assertions
        self.assertEqual(len(data["sentiment"]["results"]), 17)
        self.assertEqual(len(data["emotion"]["results"]), 17)
        self.assertGreaterEqual(len(data["topics"]["topics"]), 2)
        self.assertGreaterEqual(len(data["trends"]["trends"]), 2)
        self.assertEqual(data["demographics"]["total_profiles_analyzed"], 17)

    def test_09_feature_flags(self):
        """STEP 11: Verify selective execution through request feature flags."""
        base_payload = {
            "raw_posts": self.raw_posts_data[:5],
            "reference_time": self.reference_time.isoformat(),
        }

        # Test A: All enabled
        payload_a = {
            **base_payload,
            "include_sentiment": True,
            "include_emotion": True,
            "include_topics": True,
            "include_trends": True,
            "include_demographics": True,
        }
        s_a, d_a = call_api("POST", "/api/v1/analytics/analyze", payload_a)
        self.assertEqual(s_a, 200)
        self.assertIsNotNone(d_a["sentiment"])
        self.assertIsNotNone(d_a["emotion"])
        self.assertIsNotNone(d_a["topics"])
        self.assertIsNotNone(d_a["trends"])
        self.assertIsNotNone(d_a["demographics"])

        # Test B: Only sentiment
        payload_b = {
            **base_payload,
            "include_sentiment": True,
            "include_emotion": False,
            "include_topics": False,
            "include_trends": False,
            "include_demographics": False,
        }
        s_b, d_b = call_api("POST", "/api/v1/analytics/analyze", payload_b)
        self.assertEqual(s_b, 200)
        self.assertIsNotNone(d_b["sentiment"])
        self.assertIsNone(d_b["emotion"])
        self.assertIsNone(d_b["topics"])
        self.assertIsNone(d_b["trends"])
        self.assertIsNone(d_b["demographics"])

        # Test C: Topics + trends
        payload_c = {
            **base_payload,
            "include_sentiment": False,
            "include_emotion": False,
            "include_topics": True,
            "include_trends": True,
            "include_demographics": False,
        }
        s_c, d_c = call_api("POST", "/api/v1/analytics/analyze", payload_c)
        self.assertEqual(s_c, 200)
        self.assertIsNone(d_c["sentiment"])
        self.assertIsNone(d_c["emotion"])
        self.assertIsNotNone(d_c["topics"])
        self.assertIsNotNone(d_c["trends"])
        self.assertIsNone(d_c["demographics"])

    def test_10_empty_and_invalid_api_payload(self):
        """STEP 12: Verify empty and malformed payloads return HTTP 400 errors."""
        # 1. Empty request body
        s1, d1 = call_api("POST", "/api/v1/analytics/analyze", {})
        self.assertEqual(s1, 400)
        self.assertIn("detail", d1)

        # 2. Empty raw_posts list (verifying Phase 3.8.1 fix 5145449)
        s2, d2 = call_api("POST", "/api/v1/analytics/analyze", {"raw_posts": []})
        self.assertEqual(s2, 400)
        self.assertEqual(d2["detail"], "Empty post list provided for analysis.")

        # 3. Empty posts list
        s3, d3 = call_api("POST", "/api/v1/analytics/analyze", {"posts": []})
        self.assertEqual(s3, 400)
        self.assertEqual(d3["detail"], "Empty post list provided for analysis.")

    def test_11_identifier_integrity_across_pipeline(self):
        """STEP 13: Verify unbroken identifier traceability from raw input through all analytics layers."""
        target_id = "metro_curr_001"

        raw_payloads = [RawPostPayload(**d) for d in self.raw_posts_data]
        norm_posts = [DataNormalizer.normalize(r) for r in raw_payloads]
        posts = DataQualityService().validate_batch(norm_posts).valid_posts

        # 1. NormalizedPost
        norm_post = next(p for p in norm_posts if p.external_post_id == target_id)
        self.assertEqual(norm_post.external_post_id, target_id)

        # 2. AnalyticsReadyPost
        ready_post = next(p for p in posts if p.external_post_id == target_id)
        self.assertEqual(ready_post.external_post_id, target_id)

        # 3. SentimentResult
        sent_res = SentimentAnalysisService().analyze_batch(posts)
        sent_item = next(r for r in sent_res.results if r.external_post_id == target_id)
        self.assertEqual(sent_item.external_post_id, target_id)

        # 4. EmotionResult
        emo_res = EmotionAnalysisService().analyze_batch(posts)
        emo_item = next(r for r in emo_res.results if r.external_post_id == target_id)
        self.assertEqual(emo_item.external_post_id, target_id)

        # 5. TopicResult
        topic_res = TopicAnalysisService().extract_topics(posts)
        topic_containing_target = next(t for t in topic_res.topics if target_id in t.external_post_ids)
        self.assertIn(target_id, topic_containing_target.external_post_ids)

        # 6. TrendResult
        trend_res = TrendAnalysisService().analyze_trends(
            topics=topic_res.topics,
            posts=posts,
            reference_time=self.reference_time,
            window_duration=self.window_duration,
        )
        trend_item = next(tr for tr in trend_res.trends if tr.topic_id == topic_containing_target.topic_id)
        self.assertIn(target_id, trend_item.external_post_ids)

        # 7. DemographicProfile
        profiles = DemographicAnalysisService().extract_profiles_from_posts(posts)
        demo_profile = next(p for p in profiles if p.external_post_id == target_id)
        self.assertEqual(demo_profile.external_post_id, target_id)

    def test_12_timestamp_timezone_integrity(self):
        """STEP 14: Verify timestamps with non-UTC explicit offsets are standardized and trend-safe."""
        offset_payloads = [
            {
                "platform": "x",
                "external_id": "tz_ist_001",
                "text": "Commuter feedback from Hyderabad IST timezone. #Transit",
                "posted_at": "2026-09-08T17:00:00+05:30",  # Equivalent to 11:30:00 UTC
            },
            {
                "platform": "reddit",
                "external_id": "tz_edt_001",
                "text": "Commuter feedback from New York EDT timezone. #Transit",
                "posted_at": "2026-09-08T07:30:00-04:00",  # Equivalent to 11:30:00 UTC
            },
            {
                "platform": "telegram",
                "external_id": "tz_utc_001",
                "text": "Commuter feedback from London UTC timezone. #Transit",
                "posted_at": "2026-09-08T11:30:00Z",       # 11:30:00 UTC
            },
        ]

        normalized = [DataNormalizer.normalize(RawPostPayload(**p)) for p in offset_payloads]
        for p in normalized:
            self.assertEqual(p.posted_at.tzinfo, timezone.utc)
            self.assertEqual(p.posted_at.hour, 11)
            self.assertEqual(p.posted_at.minute, 30)

        # Ensure trend analysis calculates sliding windows without naive/aware errors
        posts = DataQualityService().validate_batch(normalized).valid_posts
        topics = TopicAnalysisService().extract_topics(posts).topics
        trend_res = TrendAnalysisService().analyze_trends(
            topics=topics,
            posts=posts,
            reference_time=self.reference_time,
            window_duration=self.window_duration,
        )
        self.assertGreaterEqual(trend_res.total_topics_evaluated, 1)

    def test_13_deterministic_repeatability(self):
        """STEP 15: Verify running the complete pipeline twice yields equivalent analytical outcomes."""
        payload = {
            "raw_posts": self.raw_posts_data,
            "reference_time": self.reference_time.isoformat(),
            "window_duration_seconds": 3600,
            "include_sentiment": True,
            "include_emotion": True,
            "include_topics": True,
            "include_trends": True,
            "include_demographics": True,
        }

        s1, d1 = call_api("POST", "/api/v1/analytics/analyze", payload)
        s2, d2 = call_api("POST", "/api/v1/analytics/analyze", payload)

        self.assertEqual(s1, 200)
        self.assertEqual(s2, 200)
        self.assertEqual(d1["total_posts_evaluated"], d2["total_posts_evaluated"])
        self.assertEqual(d1["valid_posts_count"], d2["valid_posts_count"])

        # Compare sentiment outcomes
        self.assertEqual(d1["sentiment"]["positive_count"], d2["sentiment"]["positive_count"])
        self.assertEqual(d1["sentiment"]["negative_count"], d2["sentiment"]["negative_count"])
        self.assertEqual(d1["sentiment"]["neutral_count"], d2["sentiment"]["neutral_count"])

        # Compare emotion distributions
        self.assertEqual(d1["emotion"]["emotion_distribution"], d2["emotion"]["emotion_distribution"])

        # Compare topic clustering
        self.assertEqual(d1["topics"]["total_topics_found"], d2["topics"]["total_topics_found"])
        self.assertEqual(
            [t["label"] for t in d1["topics"]["topics"]],
            [t["label"] for t in d2["topics"]["topics"]],
        )

        # Compare trend directions
        self.assertEqual(
            [t["direction"] for t in d1["trends"]["trends"]],
            [t["direction"] for t in d2["trends"]["trends"]],
        )

        # Compare demographic counts
        self.assertEqual(
            d1["demographics"]["overall_distribution"]["age_groups"]["counts"],
            d2["demographics"]["overall_distribution"]["age_groups"]["counts"],
        )
        self.assertEqual(
            d1["demographics"]["overall_distribution"]["gender"]["counts"],
            d2["demographics"]["overall_distribution"]["gender"]["counts"],
        )


if __name__ == "__main__":
    unittest.main()
