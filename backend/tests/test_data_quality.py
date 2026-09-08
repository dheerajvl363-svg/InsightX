from datetime import datetime, timedelta, timezone
import unittest

from app.models.metric import PostMetric
from app.models.platform import Platform
from app.models.post import Post
from app.models.user import User
from app.schemas.analytics import PostSummary
from app.schemas.data_quality import (
    AnalyticsReadyPost,
    BatchDataQualityResult,
    DataQualityResult,
)
from app.schemas.post import NormalizedPost, PostMetricsSchema
from app.services.data_quality import DataQualityService


class TestDataQualityService(unittest.TestCase):
    """
    Unit tests for Phase 3 Component 3.1: Data Quality & Analytics Input Layer.
    """

    def _create_sample_normalized_post(
        self,
        text: str = "InsightX AI analytics pipeline is operational! 🚀 #AI #SIH2026",
        platform: str = "X",
        external_id: str = "test_post_001",
        posted_at: datetime = None,
        language: str = "en",
    ) -> NormalizedPost:
        if posted_at is None:
            posted_at = datetime(2026, 9, 8, 12, 0, 0, tzinfo=timezone.utc)
        return NormalizedPost(
            platform_name=platform,
            external_post_id=external_id,
            text=text,
            author_username="test_user",
            author_display_name="Test User",
            posted_at=posted_at,
            collected_at=datetime(2026, 9, 8, 12, 5, 0, tzinfo=timezone.utc),
            url="https://x.com/test_user/status/test_post_001",
            language=language,
            metrics=PostMetricsSchema(likes=100, comments=10, shares=25, views=1500),
            metadata={"category": "tech"},
            raw_payload={"original_id": "test_post_001"},
        )

    def test_1_valid_normalized_record(self):
        """Valid normalized record passes quality check and produces clean AnalyticsReadyPost."""
        norm_post = self._create_sample_normalized_post()
        result = DataQualityService.validate_and_prepare(norm_post)

        self.assertIsInstance(result, DataQualityResult)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
        self.assertIsNotNone(result.post)
        self.assertIsInstance(result.post, AnalyticsReadyPost)

        post = result.post
        self.assertEqual(post.platform, "X")
        self.assertEqual(post.external_post_id, "test_post_001")
        self.assertEqual(post.text, "InsightX AI analytics pipeline is operational! 🚀 #AI #SIH2026")
        self.assertEqual(post.raw_text, "InsightX AI analytics pipeline is operational! 🚀 #AI #SIH2026")
        self.assertEqual(post.author_username, "test_user")
        self.assertEqual(post.language, "en")
        self.assertEqual(post.metrics.likes, 100)
        self.assertEqual(post.char_count, len(post.text))
        self.assertGreater(post.word_count, 5)
        self.assertIn("has_emojis", post.quality_flags)
        self.assertIn("has_hashtags", post.quality_flags)

    def test_2_missing_and_none_text_rejected(self):
        """Record with None text is rejected with clear error message."""
        norm_post = self._create_sample_normalized_post(text=None)
        result = DataQualityService.validate_and_prepare(norm_post)

        self.assertFalse(result.is_valid)
        self.assertIsNone(result.post)
        self.assertIn("Missing required text content.", result.errors)

    def test_3_empty_and_whitespace_only_text_rejected(self):
        """Record with empty or whitespace-only text is rejected."""
        whitespace_cases = ["", "   ", "\n\t  \r\n", "\u200b\u200b", "   \x00   "]
        for case in whitespace_cases:
            record = {
                "platform": "Telegram",
                "external_id": "tg_empty_1",
                "text": case,
                "posted_at": "2026-09-08T10:00:00Z",
            }
            result = DataQualityService.validate_and_prepare(record)
            self.assertFalse(result.is_valid, f"Failed to reject case: {repr(case)}")
            self.assertIsNone(result.post)
            self.assertTrue(any("empty" in err.lower() or "whitespace" in err.lower() for err in result.errors))

    def test_4_invalid_and_missing_platform_rejected(self):
        """Missing or blank platform produces validation failure."""
        record = {
            "platform": "  ",
            "external_id": "ext_999",
            "text": "Some valid content text",
            "posted_at": "2026-09-08T10:00:00Z",
        }
        result = DataQualityService.validate_and_prepare(record)
        self.assertFalse(result.is_valid)
        self.assertIn("Missing platform identifier.", result.errors)

    def test_5_invalid_and_missing_external_id_rejected(self):
        """Missing external post identifier produces validation failure."""
        record = {
            "platform": "Reddit",
            "external_id": "",
            "text": "Valid discussion topic",
            "posted_at": "2026-09-08T10:00:00Z",
        }
        result = DataQualityService.validate_and_prepare(record)
        self.assertFalse(result.is_valid)
        self.assertIn("Missing external post identifier.", result.errors)

    def test_6_timestamp_validation_and_bounds(self):
        """Timestamps in the distant future or ancient past are rejected."""
        # Missing timestamp
        rec_missing_ts = {
            "platform": "YouTube",
            "external_id": "yt_001",
            "text": "Video title and description",
            "posted_at": None,
        }
        res1 = DataQualityService.validate_and_prepare(rec_missing_ts)
        self.assertFalse(res1.is_valid)
        self.assertIn("Missing post timestamp (posted_at).", res1.errors)

        # Future timestamp (> 24h from now)
        future_time = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        rec_future = {
            "platform": "YouTube",
            "external_id": "yt_002",
            "text": "Future video",
            "posted_at": future_time,
        }
        res2 = DataQualityService.validate_and_prepare(rec_future)
        self.assertFalse(res2.is_valid)
        self.assertTrue(any("future" in err.lower() for err in res2.errors))

        # Pre-social media era timestamp (< year 2000)
        rec_ancient = {
            "platform": "YouTube",
            "external_id": "yt_003",
            "text": "Ancient post",
            "posted_at": "1995-05-10T12:00:00Z",
        }
        res3 = DataQualityService.validate_and_prepare(rec_ancient)
        self.assertFalse(res3.is_valid)
        self.assertTrue(any("2000" in err for err in res3.errors))

    def test_7_text_cleaning_and_preservation(self):
        """Text cleaning removes invisible control characters while preserving emojis, hashtags, mentions."""
        raw_dirty_text = "\u200b  Hello \x00 world! \t\t Check this out @lead_analyst #InsightX 🌟\r\n\r\nVisit https://insightx.ai  "
        cleaned = DataQualityService.clean_text(raw_dirty_text)

        expected = "Hello world! Check this out @lead_analyst #InsightX 🌟\n\nVisit https://insightx.ai"
        self.assertEqual(cleaned, expected)
        self.assertNotIn("\u200b", cleaned)
        self.assertNotIn("\x00", cleaned)
        self.assertIn("🌟", cleaned)
        self.assertIn("#InsightX", cleaned)
        self.assertIn("@lead_analyst", cleaned)

    def test_8_quality_flags_extraction(self):
        """Quality flags accurately detect text characteristics."""
        flags = DataQualityService.extract_quality_flags(
            "Breaking news from @reuters: AI advances rapidly! 🔥 #Tech #AI https://example.com"
        )
        self.assertIn("has_emojis", flags)
        self.assertIn("has_hashtags", flags)
        self.assertIn("has_mentions", flags)
        self.assertIn("has_urls", flags)
        self.assertNotIn("short_text", flags)

        short_flags = DataQualityService.extract_quality_flags("Hi! 👋")
        self.assertIn("has_emojis", short_flags)
        self.assertIn("short_text", short_flags)

    def test_9_post_summary_and_dict_support(self):
        """Accepts PostSummary and dictionary representations seamlessly."""
        summary = PostSummary(
            id=42,
            platform="X",
            external_post_id="post_summary_042",
            text="Clean post summary content for sentiment evaluation.",
            author_username="analyst_bob",
            author_display_name="Bob",
            posted_at=datetime(2026, 9, 8, 14, 0, 0, tzinfo=timezone.utc),
            collected_at=datetime(2026, 9, 8, 14, 2, 0, tzinfo=timezone.utc),
            url="https://x.com/analyst_bob/status/post_summary_042",
            language="en",
            metrics=PostMetricsSchema(likes=50, comments=5, shares=2, views=400),
            metadata={"source": "api"},
        )

        result = DataQualityService.validate_and_prepare(summary)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.post.id, 42)
        self.assertEqual(result.post.platform, "X")
        self.assertEqual(result.post.text, "Clean post summary content for sentiment evaluation.")
        self.assertEqual(result.post.author_username, "analyst_bob")
        self.assertEqual(result.post.metrics.likes, 50)

    def test_10_batch_quality_validation(self):
        """Batch validation correctly partitions valid records and rejected records."""
        records = [
            # 1. Valid record
            {
                "platform": "X",
                "external_id": "batch_valid_1",
                "text": "First valid social update for Phase 3 analytics.",
                "posted_at": "2026-09-08T10:00:00Z",
                "language": "en",
            },
            # 2. Invalid record (missing text)
            {
                "platform": "Telegram",
                "external_id": "batch_invalid_2",
                "text": None,
                "posted_at": "2026-09-08T10:00:00Z",
            },
            # 3. Valid record
            {
                "platform": "Reddit",
                "external_id": "batch_valid_3",
                "text": "Second valid community discussion thread.",
                "posted_at": "2026-09-08T10:05:00Z",
                "language": "en",
            },
            # 4. Invalid record (missing platform)
            {
                "platform": "",
                "external_id": "batch_invalid_4",
                "text": "Orphaned text without platform",
                "posted_at": "2026-09-08T10:10:00Z",
            },
        ]

        batch_result = DataQualityService.validate_batch(records)
        self.assertIsInstance(batch_result, BatchDataQualityResult)
        self.assertEqual(batch_result.total_evaluated, 4)
        self.assertEqual(batch_result.valid_count, 2)
        self.assertEqual(batch_result.invalid_count, 2)
        self.assertEqual(len(batch_result.valid_posts), 2)
        self.assertEqual(len(batch_result.rejected_records), 2)

        self.assertEqual(batch_result.valid_posts[0].external_post_id, "batch_valid_1")
        self.assertEqual(batch_result.valid_posts[1].external_post_id, "batch_valid_3")

        self.assertEqual(batch_result.rejected_records[0].external_post_id, "batch_invalid_2")
        self.assertIn("Missing required text content.", batch_result.rejected_records[0].errors)

        self.assertEqual(batch_result.rejected_records[1].external_post_id, "batch_invalid_4")
        self.assertIn("Missing platform identifier.", batch_result.rejected_records[1].errors)

    def test_11_warnings_for_short_text_and_missing_language(self):
        """Non-fatal warnings are generated for extremely short text and missing language."""
        record = {
            "platform": "Telegram",
            "external_id": "tg_short_01",
            "text": "OK",
            "posted_at": "2026-09-08T10:00:00Z",
            "language": None,
        }
        result = DataQualityService.validate_and_prepare(record)
        self.assertTrue(result.is_valid)
        self.assertIsNotNone(result.post)
        self.assertEqual(result.post.text, "OK")
        self.assertTrue(any("short" in w.lower() for w in result.warnings))
        self.assertTrue(any("language" in w.lower() for w in result.warnings))

    def test_12_orm_post_model_support(self):
        """Accepts SQLAlchemy Post ORM model instances."""
        plat = Platform(name="YouTube")
        user = User(username="tech_channel", display_name="Tech Channel")
        orm_post = Post(
            id=101,
            platform=plat,
            user=user,
            external_post_id="yt_orm_101",
            text="New video on machine learning pipelines.",
            posted_at=datetime(2026, 9, 8, 15, 0, 0, tzinfo=timezone.utc),
            collected_at=datetime(2026, 9, 8, 15, 1, 0, tzinfo=timezone.utc),
            url="https://youtube.com/watch?v=yt_orm_101",
            language="en",
            metadata_={"views_count": 5000},
        )
        metric = PostMetric(likes=350, comments=45, shares=12, views=5000, collected_at=orm_post.collected_at)
        orm_post.metrics = [metric]

        result = DataQualityService.validate_and_prepare(orm_post)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.post.id, 101)
        self.assertEqual(result.post.platform, "YouTube")
        self.assertEqual(result.post.author_username, "tech_channel")
        self.assertEqual(result.post.metrics.likes, 350)
        self.assertEqual(result.post.metrics.views, 5000)

    def test_13_unsupported_record_type_raises_or_fails(self):
        """Unsupported record type returns clean validation failure."""
        result = DataQualityService.validate_and_prepare(["invalid", "list", "input"])
        self.assertFalse(result.is_valid)
        self.assertTrue(any("Unsupported record type" in err for err in result.errors))

    def test_14_unicode_nfc_normalization(self):
        """Decomposed Unicode sequences are normalized to canonical NFC form."""
        # 'e' + combining acute accent = é in NFD form
        decomposed_str = "Caf\u0065\u0301 analytics and r\u00e9sum\u00e9"
        result = DataQualityService.clean_text(decomposed_str)
        self.assertEqual(result, "Café analytics and résumé")

    def test_15_already_clean_valid_text_unchanged(self):
        """Already clean text remains identical."""
        pristine_text = "InsightX provides real-time social intelligence across multi-modal data streams."
        cleaned = DataQualityService.clean_text(pristine_text)
        self.assertEqual(cleaned, pristine_text)


if __name__ == "__main__":
    unittest.main()
