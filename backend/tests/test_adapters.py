import unittest

from app.database import SessionLocal
from app.models.metric import PostMetric
from app.models.post import Post
from app.schemas.post import NormalizedPost, RawPostPayload
from app.services.adapters import (
    BasePlatformAdapter,
    RedditAdapter,
    TelegramAdapter,
    XAdapter,
    YouTubeAdapter,
    detect_adapter,
    get_adapter,
)
from app.services.ingestion import IngestionService
from app.services.normalizer import DataNormalizer


class TestAdapters(unittest.TestCase):
    """
    Unit and integration tests for Component 6 Platform Adapters.
    """

    def test_1_base_adapter_contract(self):
        # Cannot instantiate ABC directly
        with self.assertRaises(TypeError):
            BasePlatformAdapter()

        # get_adapter factory
        x_adapter = get_adapter("X")
        self.assertIsInstance(x_adapter, XAdapter)
        self.assertEqual(x_adapter.platform_name, "X")

        tg_adapter = get_adapter("telegram")
        self.assertIsInstance(tg_adapter, TelegramAdapter)

        red_adapter = get_adapter("reddit")
        self.assertIsInstance(red_adapter, RedditAdapter)

        yt_adapter = get_adapter("youtube")
        self.assertIsInstance(yt_adapter, YouTubeAdapter)

        # Unsupported platform raises ValueError
        with self.assertRaises(ValueError):
            get_adapter("unknown_platform_xyz")

    def test_2_x_adapter_mapping(self):
        adapter = XAdapter()
        raw_tweet = {
            "id": "1832049281048",
            "text": "Announcing InsightX platform adapter layer! #SIH2026",
            "author": {"username": "insightx_dev", "name": "InsightX Developer"},
            "created_at": "2026-09-08T01:00:00Z",
            "lang": "en",
            "public_metrics": {
                "like_count": 250,
                "reply_count": 15,
                "retweet_count": 45,
                "impression_count": 6200,
            },
            "conversation_id": "1832049281048",
        }

        payload = adapter.to_raw_payload(raw_tweet)
        self.assertIsInstance(payload, RawPostPayload)
        self.assertEqual(payload.platform, "X")
        self.assertEqual(payload.external_id, "1832049281048")
        self.assertEqual(payload.text, "Announcing InsightX platform adapter layer! #SIH2026")
        self.assertEqual(payload.author_username, "insightx_dev")
        self.assertEqual(payload.author_display_name, "InsightX Developer")
        self.assertEqual(payload.url, "https://x.com/insightx_dev/status/1832049281048")
        self.assertEqual(payload.metrics.likes, 250)
        self.assertEqual(payload.metrics.comments, 15)
        self.assertEqual(payload.metrics.shares, 45)
        self.assertEqual(payload.metrics.views, 6200)
        self.assertEqual(payload.metadata.get("conversation_id"), "1832049281048")
        self.assertIn("conversation_id", payload.raw_payload)

    def test_3_telegram_adapter_mapping(self):
        adapter = TelegramAdapter()
        raw_msg = {
            "message_id": 99482,
            "message": "Breaking news: New tech corridor inaugurated.",
            "from": {"username": "telugu_bulletin", "title": "Telugu Bulletin News"},
            "date": 1788812400,
            "views": 18500,
            "forwards": 320,
            "chat_id": -1001234567890,
        }

        payload = adapter.to_raw_payload(raw_msg)
        self.assertIsInstance(payload, RawPostPayload)
        self.assertEqual(payload.platform, "Telegram")
        self.assertEqual(payload.external_id, "99482")
        self.assertEqual(payload.text, "Breaking news: New tech corridor inaugurated.")
        self.assertEqual(payload.author_username, "telugu_bulletin")
        self.assertEqual(payload.author_display_name, "Telugu Bulletin News")
        self.assertEqual(payload.url, "https://t.me/telugu_bulletin/99482")
        self.assertEqual(payload.metrics.views, 18500)
        self.assertEqual(payload.metrics.shares, 320)
        self.assertEqual(payload.metadata.get("chat_id"), -1001234567890)

    def test_4_reddit_adapter_mapping(self):
        adapter = RedditAdapter()
        raw_submission = {
            "name": "t3_k9876",
            "title": "FastAPI with PostgreSQL Architecture Advice",
            "selftext": "How do you structure social media analytics ingestion for high concurrency?",
            "author": "u/dev_architect",
            "created_utc": 1788813000,
            "permalink": "/r/webdev/comments/k9876/fastapi_with_postgresql/",
            "score": 380,
            "num_comments": 45,
            "subreddit": "r/webdev",
            "link_flair_text": "Discussion",
        }

        payload = adapter.to_raw_payload(raw_submission)
        self.assertIsInstance(payload, RawPostPayload)
        self.assertEqual(payload.platform, "Reddit")
        self.assertEqual(payload.external_id, "k9876")
        self.assertIn("FastAPI with PostgreSQL Architecture Advice", payload.text)
        self.assertIn("How do you structure social media analytics", payload.text)
        self.assertEqual(payload.author_username, "dev_architect")
        self.assertEqual(payload.url, "https://reddit.com/r/webdev/comments/k9876/fastapi_with_postgresql/")
        self.assertEqual(payload.metrics.likes, 380)
        self.assertEqual(payload.metrics.comments, 45)
        self.assertEqual(payload.metadata.get("subreddit"), "r/webdev")
        self.assertEqual(payload.metadata.get("flair"), "Discussion")

    def test_5_youtube_adapter_mapping(self):
        adapter = YouTubeAdapter()
        raw_yt = {
            "videoId": "yt_vid_abc123",
            "snippet": {
                "title": "Building a Real-time Analytics System from Scratch",
                "description": "In this tutorial we build an end-to-end ingestion pipeline.",
                "channelId": "UC_code_craft",
                "channelTitle": "CodeCraft Academy",
                "publishedAt": "2026-09-08T00:00:00Z",
                "defaultLanguage": "en",
                "tags": ["python", "fastapi", "sih2026"],
            },
            "statistics": {
                "viewCount": "48000",
                "likeCount": "3200",
                "commentCount": "190",
            },
            "duration_seconds": 2150,
        }

        payload = adapter.to_raw_payload(raw_yt)
        self.assertIsInstance(payload, RawPostPayload)
        self.assertEqual(payload.platform, "YouTube")
        self.assertEqual(payload.external_id, "yt_vid_abc123")
        self.assertIn("Building a Real-time Analytics System", payload.text)
        self.assertEqual(payload.author_username, "UC_code_craft")
        self.assertEqual(payload.author_display_name, "CodeCraft Academy")
        self.assertEqual(payload.url, "https://youtube.com/watch?v=yt_vid_abc123")
        self.assertEqual(payload.language, "en")
        self.assertEqual(payload.metrics.views, 48000)
        self.assertEqual(payload.metrics.likes, 3200)
        self.assertEqual(payload.metrics.comments, 190)
        self.assertEqual(payload.metadata.get("duration_seconds"), 2150)

    def test_6_required_id_handling(self):
        # Missing id on X
        with self.assertRaises(ValueError):
            XAdapter().to_raw_payload({"text": "Missing id tweet"})

        # Missing message_id on Telegram
        with self.assertRaises(ValueError):
            TelegramAdapter().to_raw_payload({"message": "Missing id telegram"})

        # Missing id/name on Reddit
        with self.assertRaises(ValueError):
            RedditAdapter().to_raw_payload({"title": "Missing id reddit"})

        # Missing videoId on YouTube
        with self.assertRaises(ValueError):
            YouTubeAdapter().to_raw_payload({"title": "Missing id youtube"})

    def test_7_detect_adapter_heuristics(self):
        self.assertIsInstance(detect_adapter({"platform": "twitter"}), XAdapter)
        self.assertIsInstance(detect_adapter({"platform": "telegram"}), TelegramAdapter)
        self.assertIsInstance(detect_adapter({"platform": "reddit"}), RedditAdapter)
        self.assertIsInstance(detect_adapter({"platform": "youtube"}), YouTubeAdapter)

        # Heuristic detection without explicit platform key
        self.assertIsInstance(detect_adapter({"tweet_id": "123"}), XAdapter)
        self.assertIsInstance(detect_adapter({"message_id": "456"}), TelegramAdapter)
        self.assertIsInstance(detect_adapter({"subreddit": "r/python", "id": "789"}), RedditAdapter)
        self.assertIsInstance(detect_adapter({"videoId": "abc"}), YouTubeAdapter)

    def test_8_optional_fields_and_malformed_input_rejection(self):
        adapter = XAdapter()
        # Non-dictionary input
        with self.assertRaises(ValueError):
            adapter.to_raw_payload("invalid string")

        # Minimal valid tweet without author, metrics, url
        minimal = adapter.to_raw_payload({"id": "x_min_001", "text": "Minimal tweet"})
        self.assertEqual(minimal.external_id, "x_min_001")
        self.assertIsNone(minimal.author_username)
        self.assertIsNone(minimal.metrics)
        self.assertIsNone(minimal.url)

    def test_9_end_to_end_adapter_to_database_pipeline(self):
        """
        Integration test verifying full flow:
        Platform-specific input -> Adapter -> RawPostPayload -> DataNormalizer -> IngestionService -> PostgreSQL
        """
        test_ext_id = "adapter_flow_test_001"
        raw_yt_video = {
            "videoId": test_ext_id,
            "snippet": {
                "title": "InsightX Pipeline Verification Video",
                "description": "Demonstrating end-to-end adapter to PostgreSQL integration.",
                "channelTitle": "InsightX Test Channel",
                "publishedAt": "2026-09-08T01:30:00Z",
                "defaultLanguage": "en",
            },
            "statistics": {
                "viewCount": "1250",
                "likeCount": "85",
            },
            "custom_internal_tag": "adapter_verification",
        }

        # 1. Adapter mapping
        adapter = detect_adapter(raw_yt_video)
        self.assertIsNotNone(adapter)
        raw_payload = adapter.to_raw_payload(raw_yt_video)
        self.assertEqual(raw_payload.platform, "YouTube")

        # 2. DataNormalizer
        normalized = DataNormalizer.normalize(raw_payload)
        self.assertIsInstance(normalized, NormalizedPost)
        self.assertEqual(normalized.platform_name, "YouTube")
        self.assertEqual(normalized.external_post_id, test_ext_id)
        self.assertEqual(normalized.metrics.views, 1250)

        # 3. IngestionService to PostgreSQL
        db = SessionLocal()
        try:
            service = IngestionService(db)
            resp = service.ingest_post(normalized)

            self.assertEqual(resp.status, "success")
            self.assertFalse(resp.is_duplicate)
            self.assertIsNotNone(resp.post_id)

            # Query from DB to verify persistence
            db_post = db.query(Post).filter_by(id=resp.post_id).first()
            self.assertIsNotNone(db_post)
            self.assertEqual(db_post.external_post_id, test_ext_id)
            self.assertEqual(db_post.platform.name, "YouTube")
            self.assertEqual(len(db_post.metrics), 1)
            self.assertEqual(db_post.metrics[0].views, 1250)
            self.assertEqual(db_post.raw_payload.get("custom_internal_tag"), "adapter_verification")

            # Clean up test post (cascades to metrics)
            db.delete(db_post)
            db.commit()

        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
