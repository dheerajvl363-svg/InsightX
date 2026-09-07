from datetime import datetime, timezone
import unittest
from pydantic import ValidationError

from app.schemas.post import (
    BatchIngestionResponse,
    IngestionResponse,
    NormalizedPost,
    PostMetricsSchema,
    RawPostPayload,
)
from app.services.normalizer import DataNormalizer


class TestSchemas(unittest.TestCase):
    """Test Pydantic schemas for social media post ingestion."""

    def test_valid_raw_post_payload(self):
        payload = RawPostPayload(
            platform="X",
            external_id="123456789",
            text="Hello world from InsightX!",
            author_username="@insightx_team",
            author_display_name="InsightX Team",
            posted_at="2026-09-08T00:30:00Z",
            url="https://x.com/insightx_team/status/123456789",
            language="EN",
            metrics={"likes": 10, "comments": 2, "shares": 5, "views": 100},
        )
        self.assertEqual(payload.platform, "X")
        self.assertEqual(payload.external_id, "123456789")
        self.assertEqual(payload.author_username, "@insightx_team")

    def test_alias_mapping_in_raw_post_payload(self):
        """Verify common field aliases (content, id, username) are mapped."""
        data = {
            "platform": "telegram",
            "id": 98765,
            "content": "A message from Telegram channel",
            "username": "tg_channel",
        }
        payload = RawPostPayload(**data)
        self.assertEqual(payload.external_id, "98765")
        self.assertEqual(payload.text, "A message from Telegram channel")
        self.assertEqual(payload.author_username, "tg_channel")

    def test_reject_blank_platform(self):
        with self.assertRaises(ValidationError):
            RawPostPayload(platform="   ", external_id="123")

    def test_reject_blank_external_id(self):
        with self.assertRaises(ValidationError):
            RawPostPayload(platform="X", external_id="")

    def test_metrics_schema_validation(self):
        metrics = PostMetricsSchema(likes=5, comments=0, shares=1)
        self.assertEqual(metrics.likes, 5)
        self.assertEqual(metrics.views, 0)

        # Negative count should fail validation
        with self.assertRaises(ValidationError):
            PostMetricsSchema(likes=-1)

    def test_ingestion_response_schema(self):
        resp = IngestionResponse(
            status="success",
            post_id=42,
            external_post_id="ext_999",
            platform="X",
            is_duplicate=False,
            message="Post successfully ingested.",
        )
        self.assertEqual(resp.post_id, 42)
        self.assertFalse(resp.is_duplicate)

    def test_batch_ingestion_response_schema(self):
        batch = BatchIngestionResponse(
            total_received=2,
            successful=1,
            duplicates=1,
            failed=0,
            results=[
                IngestionResponse(
                    status="success",
                    post_id=1,
                    external_post_id="1",
                    platform="X",
                    message="Ingested",
                ),
                IngestionResponse(
                    status="duplicate_ignored",
                    post_id=2,
                    external_post_id="2",
                    platform="X",
                    is_duplicate=True,
                    message="Duplicate ignored",
                ),
            ],
        )
        self.assertEqual(batch.total_received, 2)
        self.assertEqual(batch.duplicates, 1)


class TestNormalizer(unittest.TestCase):
    """Test DataNormalizer rules and standardization."""

    def test_canonicalize_platform(self):
        self.assertEqual(DataNormalizer.canonicalize_platform("twitter"), "X")
        self.assertEqual(DataNormalizer.canonicalize_platform("X.com"), "X")
        self.assertEqual(DataNormalizer.canonicalize_platform("tg"), "Telegram")
        self.assertEqual(DataNormalizer.canonicalize_platform("telegram_channel"), "Telegram")
        self.assertEqual(DataNormalizer.canonicalize_platform("r/"), "Reddit")
        self.assertEqual(DataNormalizer.canonicalize_platform("yt"), "YouTube")
        self.assertEqual(DataNormalizer.canonicalize_platform("mastodon"), "Mastodon")

        with self.assertRaises(ValueError):
            DataNormalizer.canonicalize_platform("")

    def test_normalize_text(self):
        raw = "  Hello \t\t world!  \r\n\r\nThis   is  InsightX.   "
        cleaned = DataNormalizer.normalize_text(raw)
        self.assertEqual(cleaned, "Hello world!\n\nThis is InsightX.")
        self.assertIsNone(DataNormalizer.normalize_text(None))
        self.assertIsNone(DataNormalizer.normalize_text("   \n  \t "))

    def test_normalize_username(self):
        self.assertEqual(DataNormalizer.normalize_username("@elonmusk"), "elonmusk")
        self.assertEqual(DataNormalizer.normalize_username("  @user_name  "), "user_name")
        self.assertIsNone(DataNormalizer.normalize_username(None))
        self.assertIsNone(DataNormalizer.normalize_username("   "))

    def test_normalize_url(self):
        self.assertEqual(DataNormalizer.normalize_url("  https://x.com/post/1 "), "https://x.com/post/1")
        self.assertIsNone(DataNormalizer.normalize_url("ftp://invalid-scheme.com"))
        self.assertIsNone(DataNormalizer.normalize_url(None))

    def test_normalize_language(self):
        self.assertEqual(DataNormalizer.normalize_language("EN"), "en")
        self.assertEqual(DataNormalizer.normalize_language("hi-IN"), "hi")
        self.assertEqual(DataNormalizer.normalize_language("es_ES"), "es")
        self.assertIsNone(DataNormalizer.normalize_language(None))

    def test_parse_timestamp_formats(self):
        # ISO format
        dt, inferred = DataNormalizer.parse_timestamp("2026-09-08T01:15:30Z")
        self.assertFalse(inferred)
        self.assertEqual(dt.tzinfo, timezone.utc)
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 9)

        # Unix seconds epoch
        dt_epoch, inferred2 = DataNormalizer.parse_timestamp(1725676800)
        self.assertFalse(inferred2)
        self.assertEqual(dt_epoch.tzinfo, timezone.utc)

        # Unix milliseconds epoch
        dt_milli, inferred3 = DataNormalizer.parse_timestamp(1725676800000)
        self.assertFalse(inferred3)
        self.assertEqual(dt_milli, dt_epoch)

        # None / missing timestamp -> fallback to inferred
        dt_fallback, inferred4 = DataNormalizer.parse_timestamp(None)
        self.assertTrue(inferred4)
        self.assertEqual(dt_fallback.tzinfo, timezone.utc)

    def test_full_normalize_pipeline(self):
        raw = RawPostPayload(
            platform="twitter",
            external_id=55443322,
            content="   Breaking: InsightX Phase 2 Normalization working! \r\nCheck https://example.com   ",
            username="@insightx_bot",
            posted_at="2026-09-08T01:00:00Z",
            language="EN-US",
            metrics={"likes": 150, "shares": 25},
            metadata={"custom_flag": "test_tag"},
            source_client="web_client",
        )

        normalized = DataNormalizer.normalize(raw)
        self.assertIsInstance(normalized, NormalizedPost)
        self.assertEqual(normalized.platform_name, "X")
        self.assertEqual(normalized.external_post_id, "55443322")
        self.assertEqual(normalized.author_username, "insightx_bot")
        self.assertEqual(normalized.language, "en")
        self.assertEqual(normalized.posted_at.tzinfo, timezone.utc)
        self.assertEqual(normalized.collected_at.tzinfo, timezone.utc)
        self.assertEqual(normalized.metrics.likes, 150)
        self.assertEqual(normalized.metadata.get("custom_flag"), "test_tag")
        # Ensure extra fields from raw input are preserved in raw_payload
        self.assertIn("source_client", normalized.raw_payload)
        self.assertEqual(normalized.raw_payload["source_client"], "web_client")


if __name__ == "__main__":
    unittest.main()
