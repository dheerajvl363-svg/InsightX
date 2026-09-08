from datetime import datetime, timezone
import unittest

from app.database import SessionLocal
from app.models.metric import PostMetric
from app.models.post import Post
from app.models.user import User
from app.schemas.post import NormalizedPost, RawPostPayload
from app.services.adapters import detect_adapter, get_adapter
from app.services.analytics import AnalyticsService
from app.services.ingestion import IngestionService
from app.services.normalizer import DataNormalizer


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


if __name__ == "__main__":
    unittest.main()
