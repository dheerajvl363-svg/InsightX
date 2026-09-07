from datetime import datetime, timezone
import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy import text

from app.database import SessionLocal
from app.models.metric import PostMetric
from app.models.platform import Platform
from app.models.post import Post
from app.models.user import User
from app.schemas.post import NormalizedPost, PostMetricsSchema
from app.services.ingestion import IngestionService


class TestIngestionService(unittest.TestCase):
    """
    Comprehensive tests for IngestionService against the live PostgreSQL database.
    Ensures safe persistence, deduplication, author/platform resolution, and rollback behavior.
    """

    TEST_PREFIX = "test_ingest_svc_"

    def setUp(self):
        self.db = SessionLocal()
        self.service = IngestionService(self.db)
        self.created_post_ids = []
        self.created_platform_names = []
        self.created_usernames = []

    def tearDown(self):
        # Clean up test posts and metric cascades
        if self.created_post_ids:
            self.db.query(PostMetric).filter(PostMetric.post_id.in_(self.created_post_ids)).delete(
                synchronize_session=False
            )
            self.db.query(Post).filter(Post.id.in_(self.created_post_ids)).delete(
                synchronize_session=False
            )

        # Clean up test users
        if self.created_usernames:
            self.db.query(User).filter(User.username.in_(self.created_usernames)).delete(
                synchronize_session=False
            )

        # Clean up test platforms
        if self.created_platform_names:
            self.db.query(Platform).filter(Platform.name.in_(self.created_platform_names)).delete(
                synchronize_session=False
            )

        self.db.commit()
        self.db.close()

    def _make_normalized_post(
        self,
        external_id: str,
        platform_name: str = "X",
        text_content: str = "Sample post text",
        author_username: str = None,
        author_display_name: str = None,
        metrics: PostMetricsSchema = None,
        url: str = None,
        language: str = "en",
        metadata: dict = None,
        raw_payload: dict = None,
    ) -> NormalizedPost:
        return NormalizedPost(
            platform_name=platform_name,
            external_post_id=external_id,
            text=text_content,
            author_username=author_username,
            author_display_name=author_display_name,
            posted_at=datetime.now(timezone.utc),
            collected_at=datetime.now(timezone.utc),
            url=url,
            language=language,
            metrics=metrics,
            metadata=metadata or {},
            raw_payload=raw_payload or {"source": "unit_test"},
        )

    def test_1_new_post_is_inserted(self):
        ext_id = f"{self.TEST_PREFIX}001"
        post_data = self._make_normalized_post(ext_id, platform_name="X", text_content="Testing new post insertion")
        resp = self.service.ingest_post(post_data)

        self.assertEqual(resp.status, "success")
        self.assertFalse(resp.is_duplicate)
        self.assertIsNotNone(resp.post_id)
        self.created_post_ids.append(resp.post_id)

        # Verify in DB
        db_post = self.db.query(Post).filter_by(id=resp.post_id).first()
        self.assertIsNotNone(db_post)
        self.assertEqual(db_post.external_post_id, ext_id)
        self.assertEqual(db_post.text, "Testing new post insertion")

    def test_2_existing_platform_is_reused(self):
        initial_platforms_count = self.db.query(Platform).filter_by(name="X").count()
        self.assertGreaterEqual(initial_platforms_count, 1)

        platform = self.service.get_or_create_platform("X")
        self.assertEqual(platform.name, "X")

        final_count = self.db.query(Platform).filter_by(name="X").count()
        self.assertEqual(initial_platforms_count, final_count)

    def test_3_missing_platform_can_be_created(self):
        new_platform_name = f"TestPlatform_{int(datetime.now().timestamp())}"
        self.created_platform_names.append(new_platform_name)

        platform = self.service.get_or_create_platform(new_platform_name)
        self.db.commit()

        self.assertIsNotNone(platform.id)
        self.assertEqual(platform.name, new_platform_name)

        # Ingest post on this newly registered platform
        ext_id = f"{self.TEST_PREFIX}on_new_platform"
        post_data = self._make_normalized_post(ext_id, platform_name=new_platform_name)
        resp = self.service.ingest_post(post_data)
        self.created_post_ids.append(resp.post_id)
        self.assertEqual(resp.status, "success")

    def test_4_author_user_is_created_when_appropriate(self):
        uname = f"user_{self.TEST_PREFIX}004"
        self.created_usernames.append(uname)

        ext_id = f"{self.TEST_PREFIX}004"
        post_data = self._make_normalized_post(
            ext_id,
            platform_name="X",
            author_username=uname,
            author_display_name="Test User 004",
        )
        resp = self.service.ingest_post(post_data)
        self.created_post_ids.append(resp.post_id)

        user = self.db.query(User).filter_by(username=uname).first()
        self.assertIsNotNone(user)
        self.assertEqual(user.display_name, "Test User 004")

        db_post = self.db.query(Post).filter_by(id=resp.post_id).first()
        self.assertEqual(db_post.user_id, user.id)

    def test_5_existing_author_user_is_reused(self):
        uname = f"user_{self.TEST_PREFIX}005"
        self.created_usernames.append(uname)

        post1 = self._make_normalized_post(f"{self.TEST_PREFIX}005_a", author_username=uname)
        resp1 = self.service.ingest_post(post1)
        self.created_post_ids.append(resp1.post_id)

        post2 = self._make_normalized_post(f"{self.TEST_PREFIX}005_b", author_username=uname)
        resp2 = self.service.ingest_post(post2)
        self.created_post_ids.append(resp2.post_id)

        user_count = self.db.query(User).filter_by(username=uname).count()
        self.assertEqual(user_count, 1)

        db_post1 = self.db.query(Post).filter_by(id=resp1.post_id).first()
        db_post2 = self.db.query(Post).filter_by(id=resp2.post_id).first()
        self.assertEqual(db_post1.user_id, db_post2.user_id)

    def test_6_anonymous_post_works_with_user_id_none(self):
        ext_id = f"{self.TEST_PREFIX}anon_006"
        post_data = self._make_normalized_post(ext_id, author_username=None, author_display_name=None)
        resp = self.service.ingest_post(post_data)
        self.created_post_ids.append(resp.post_id)

        db_post = self.db.query(Post).filter_by(id=resp.post_id).first()
        self.assertIsNone(db_post.user_id)

    def test_7_duplicate_external_post_id_does_not_create_second_post(self):
        ext_id = f"{self.TEST_PREFIX}dup_007"
        post_data = self._make_normalized_post(ext_id, text_content="Original post")
        resp1 = self.service.ingest_post(post_data)
        self.created_post_ids.append(resp1.post_id)
        self.assertEqual(resp1.status, "success")

        # Ingest again with same external_id and platform
        dup_data = self._make_normalized_post(ext_id, text_content="Duplicate submission attempt")
        resp2 = self.service.ingest_post(dup_data)

        self.assertEqual(resp2.status, "duplicate_ignored")
        self.assertTrue(resp2.is_duplicate)
        self.assertEqual(resp2.post_id, resp1.post_id)

        # Check total count in DB
        count = self.db.query(Post).filter_by(external_post_id=ext_id).count()
        self.assertEqual(count, 1)

    def test_8_metrics_persisted_and_updated_on_duplicate(self):
        ext_id = f"{self.TEST_PREFIX}metrics_008"
        initial_metrics = PostMetricsSchema(likes=100, comments=10, shares=5, views=1000)
        post_data = self._make_normalized_post(ext_id, metrics=initial_metrics)
        resp1 = self.service.ingest_post(post_data)
        self.created_post_ids.append(resp1.post_id)

        # Verify initial metric snapshot
        metrics = self.db.query(PostMetric).filter_by(post_id=resp1.post_id).all()
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0].likes, 100)

        # Send duplicate post with updated engagement metrics
        updated_metrics = PostMetricsSchema(likes=250, comments=25, shares=12, views=3500)
        dup_data = self._make_normalized_post(ext_id, metrics=updated_metrics)
        resp2 = self.service.ingest_post(dup_data)
        self.assertTrue(resp2.is_duplicate)

        # Verify historical snapshots: should now have 2 metric snapshots
        all_metrics = self.db.query(PostMetric).filter_by(post_id=resp1.post_id).order_by(PostMetric.id).all()
        self.assertEqual(len(all_metrics), 2)
        self.assertEqual(all_metrics[0].likes, 100)
        self.assertEqual(all_metrics[1].likes, 250)

    def test_9_optional_fields_are_persisted(self):
        ext_id = f"{self.TEST_PREFIX}optional_009"
        url = "https://x.com/insightx/status/998877"
        metadata = {"geo_country": "IN", "hashtags": ["#AI", "#SIH2026"]}
        raw_payload = {"api_version": "2", "raw_id": 998877}

        post_data = self._make_normalized_post(
            ext_id,
            url=url,
            language="hi",
            metadata=metadata,
            raw_payload=raw_payload,
        )
        resp = self.service.ingest_post(post_data)
        self.created_post_ids.append(resp.post_id)

        db_post = self.db.query(Post).filter_by(id=resp.post_id).first()
        self.assertEqual(db_post.url, url)
        self.assertEqual(db_post.language, "hi")
        self.assertEqual(db_post.post_metadata.get("geo_country"), "IN")
        self.assertEqual(db_post.raw_payload.get("raw_id"), 998877)

    def test_10_batch_ingestion_counts(self):
        ext1 = f"{self.TEST_PREFIX}batch_1"
        ext2 = f"{self.TEST_PREFIX}batch_2"
        ext3 = f"{self.TEST_PREFIX}batch_3"

        # Pre-create ext2 so it acts as duplicate in the batch
        pre = self.service.ingest_post(self._make_normalized_post(ext2))
        self.created_post_ids.append(pre.post_id)

        # Batch: 1 new (ext1), 1 duplicate (ext2), 1 post that causes DB error (empty platform name)
        valid_new = self._make_normalized_post(ext1)
        valid_dup = self._make_normalized_post(ext2)
        invalid_post = self._make_normalized_post(ext3, platform_name="   ")

        batch_result = self.service.ingest_batch([valid_new, valid_dup, invalid_post])

        self.assertEqual(batch_result.total_received, 3)
        self.assertEqual(batch_result.successful, 1)
        self.assertEqual(batch_result.duplicates, 1)
        self.assertEqual(batch_result.failed, 1)

        # Collect created id for cleanup
        for r in batch_result.results:
            if r.post_id and r.post_id not in self.created_post_ids:
                self.created_post_ids.append(r.post_id)

        # Verify valid_new was saved even though invalid_post failed
        p1 = self.db.query(Post).filter_by(external_post_id=ext1).first()
        self.assertIsNotNone(p1)

    def test_11_database_rollback_on_failure(self):
        ext_id = f"{self.TEST_PREFIX}fail_rollback_011"
        post_data = self._make_normalized_post(ext_id)

        # Simulate unexpected DB error during post add
        with patch.object(self.db, "flush", side_effect=Exception("Simulated DB flush crash")):
            with self.assertRaises(Exception):
                self.service.ingest_post(post_data)

        # Check DB to verify no partial record remains
        orphaned = self.db.query(Post).filter_by(external_post_id=ext_id).first()
        self.assertIsNone(orphaned)


if __name__ == "__main__":
    unittest.main()
