from datetime import datetime, timedelta, timezone
import re
from typing import Any, Dict, Iterable, List, Optional, Union
import unicodedata

from app.models.post import Post
from app.schemas.analytics import PostSummary
from app.schemas.data_quality import (
    AnalyticsReadyPost,
    BatchDataQualityResult,
    DataQualityResult,
    RejectedRecord,
)
from app.schemas.post import NormalizedPost, PostMetricsSchema
from app.services.normalizer import DataNormalizer


# Zero-width and invisible control characters to strip
INVISIBLE_CHARS_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u200b-\u200f\ufeff\u202a-\u202e]")
# Emoji detection range (covers common emoji planes & symbols)
EMOJI_PATTERN = re.compile(
    r"[\U0001F600-\U0001F64F"  # emoticons
    r"\U0001F300-\U0001F5FF"  # symbols & pictographs
    r"\U0001F680-\U0001F6FF"  # transport & map
    r"\U0001F1E0-\U0001F1FF"  # flags (iOS)
    r"\U00002702-\U000027B0"  # dingbats
    r"\U000024C2-\U0001F251"  # enclosed characters
    r"\U0001F900-\U0001F9FF"  # supplemental symbols and pictographs
    r"\U0001FA00-\U0001FA6F"  # chess symbols
    r"\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-a
    r"\U00002600-\U000026FF"  # miscellaneous symbols
    r"]+",
    flags=re.UNICODE,
)
HASHTAG_PATTERN = re.compile(r"#\w+", re.UNICODE)
MENTION_PATTERN = re.compile(r"@\w+", re.UNICODE)
URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)


class DataQualityService:
    """
    Data Quality and Analytics Input Layer for Phase 3.
    Validates, sanitizes, and structures social media records from Phase 2
    into clean, deterministic, analytics-ready inputs for downstream AI/NLP components.
    """

    @classmethod
    def clean_text(cls, text: Optional[str]) -> Optional[str]:
        """
        Sanitizes text content for downstream NLP models:
        - Normalizes Unicode to standard NFC form.
        - Strips zero-width and unprintable control characters.
        - Preserves emojis, hashtags, user mentions, and punctuation.
        - Standardizes line endings (\r\n -> \n).
        - Collapses duplicate horizontal whitespace while preserving paragraph structure.
        - Strips leading/trailing whitespace.
        """
        if text is None:
            return None

        # 1. Unicode NFC normalization
        normalized = unicodedata.normalize("NFC", str(text))

        # 2. Strip non-printable and zero-width characters
        cleaned = INVISIBLE_CHARS_PATTERN.sub("", normalized)

        # 3. Standardize line breaks
        cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")

        # 4. Collapse consecutive horizontal whitespace on each line
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in cleaned.split("\n")]

        # 5. Rejoin lines (removing excessive blank lines) and strip outer padding
        final_text = "\n".join(line for line in lines if line is not None).strip()

        return final_text if final_text else None

    @classmethod
    def extract_quality_flags(cls, text: str) -> List[str]:
        """
        Detects structural and semantic characteristics of text for analytics.
        """
        flags = []
        if EMOJI_PATTERN.search(text):
            flags.append("has_emojis")
        if HASHTAG_PATTERN.search(text):
            flags.append("has_hashtags")
        if MENTION_PATTERN.search(text):
            flags.append("has_mentions")
        if URL_PATTERN.search(text):
            flags.append("has_urls")
        if len(text) < 10:
            flags.append("short_text")
        return flags

    @classmethod
    def _extract_fields(cls, record: Union[NormalizedPost, PostSummary, Post, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extracts raw fields generically from NormalizedPost, PostSummary, ORM Post, or dict.
        """
        if isinstance(record, NormalizedPost):
            return {
                "id": None,
                "platform": record.platform_name,
                "external_post_id": record.external_post_id,
                "text": record.text,
                "author_username": record.author_username,
                "author_display_name": record.author_display_name,
                "posted_at": record.posted_at,
                "collected_at": record.collected_at,
                "url": record.url,
                "language": record.language,
                "metrics": record.metrics,
                "metadata": record.metadata or {},
            }

        if isinstance(record, PostSummary):
            return {
                "id": record.id,
                "platform": record.platform,
                "external_post_id": record.external_post_id,
                "text": record.text,
                "author_username": record.author_username,
                "author_display_name": record.author_display_name,
                "posted_at": record.posted_at,
                "collected_at": record.collected_at,
                "url": record.url,
                "language": record.language,
                "metrics": record.metrics,
                "metadata": record.metadata or {},
            }

        if isinstance(record, Post):
            platform_name = record.platform.name if record.platform else None
            author_user = record.user.username if record.user else None
            author_display = record.user.display_name if record.user else None
            metrics_schema = None
            if record.metrics:
                # Use latest metric if available
                latest_metric = sorted(record.metrics, key=lambda m: (m.collected_at or datetime.min, m.id or 0), reverse=True)[0]
                metrics_schema = PostMetricsSchema(
                    likes=latest_metric.likes or 0,
                    comments=latest_metric.comments or 0,
                    shares=latest_metric.shares or 0,
                    views=latest_metric.views or 0,
                    collected_at=latest_metric.collected_at,
                )
            return {
                "id": record.id,
                "platform": platform_name,
                "external_post_id": record.external_post_id,
                "text": record.text,
                "author_username": author_user,
                "author_display_name": author_display,
                "posted_at": record.posted_at,
                "collected_at": record.collected_at,
                "url": record.url,
                "language": record.language,
                "metrics": metrics_schema,
                "metadata": record.metadata_ or {},
            }

        if isinstance(record, dict):
            # Dict support
            metrics_raw = record.get("metrics")
            metrics_obj = None
            if isinstance(metrics_raw, PostMetricsSchema):
                metrics_obj = metrics_raw
            elif isinstance(metrics_raw, dict):
                try:
                    metrics_obj = PostMetricsSchema(**metrics_raw)
                except Exception:
                    metrics_obj = None

            text_val = None
            for k in ("text", "content", "message", "caption"):
                if k in record:
                    text_val = record[k]
                    break

            ext_id_val = None
            for k in ("external_post_id", "external_id", "id", "post_id"):
                if k in record:
                    ext_id_val = record[k]
                    break

            platform_val = None
            for k in ("platform", "platform_name"):
                if k in record:
                    platform_val = record[k]
                    break

            posted_at_val = None
            for k in ("posted_at", "created_at", "timestamp"):
                if k in record:
                    posted_at_val = record[k]
                    break

            author_user_val = None
            for k in ("author_username", "username"):
                if k in record and (isinstance(record[k], str) or record[k] is None):
                    author_user_val = record[k]
                    break

            author_disp_val = None
            for k in ("author_display_name", "display_name", "name"):
                if k in record and (isinstance(record[k], str) or record[k] is None):
                    author_disp_val = record[k]
                    break

            return {
                "id": record.get("id"),
                "platform": platform_val,
                "external_post_id": ext_id_val,
                "text": text_val,
                "author_username": author_user_val,
                "author_display_name": author_disp_val,
                "posted_at": posted_at_val,
                "collected_at": record.get("collected_at"),
                "url": record.get("url"),
                "language": record.get("language") or record.get("lang"),
                "metrics": metrics_obj,
                "metadata": record.get("metadata") or {},
            }

        raise TypeError(f"Unsupported record type: {type(record).__name__}")

    @classmethod
    def validate_and_prepare(
        cls,
        record: Union[NormalizedPost, PostSummary, Post, Dict[str, Any]],
    ) -> DataQualityResult:
        """
        Validates a single social media record and returns a DataQualityResult.
        If valid, attaches a clean AnalyticsReadyPost ready for AI/NLP inference.
        If invalid, provides detailed error reasons.
        """
        errors: List[str] = []
        warnings: List[str] = []

        try:
            fields = cls._extract_fields(record)
        except Exception as exc:
            return DataQualityResult(
                is_valid=False,
                errors=[f"Failed to parse input record: {str(exc)}"],
                warnings=[],
                post=None,
            )

        # 1. Validate Platform
        raw_platform = fields.get("platform")
        if not raw_platform or not str(raw_platform).strip():
            errors.append("Missing platform identifier.")
            platform = "Unknown"
        else:
            try:
                platform = DataNormalizer.canonicalize_platform(str(raw_platform))
            except Exception:
                platform = str(raw_platform).strip()

        # 2. Validate External Post ID
        raw_ext_id = fields.get("external_post_id")
        if not raw_ext_id or not str(raw_ext_id).strip():
            errors.append("Missing external post identifier.")
            external_post_id = ""
        else:
            external_post_id = str(raw_ext_id).strip()

        # 3. Validate and Clean Text Content
        raw_text = fields.get("text")
        if raw_text is None:
            errors.append("Missing required text content.")
            cleaned_text = ""
        else:
            cleaned_text = cls.clean_text(raw_text)
            if not cleaned_text:
                errors.append("Text content is empty or contains only whitespace/unprintable characters.")

        # 4. Validate Timestamp (posted_at)
        raw_posted_at = fields.get("posted_at")
        posted_at_dt: Optional[datetime] = None
        if raw_posted_at is None:
            errors.append("Missing post timestamp (posted_at).")
        else:
            parsed_dt, was_inferred = DataNormalizer.parse_timestamp(raw_posted_at)
            if was_inferred and not isinstance(raw_posted_at, (datetime, str, int, float)):
                errors.append("Invalid timestamp format for posted_at.")
            else:
                # Range checks: post cannot be more than 24 hours in the future
                now_utc = datetime.now(timezone.utc)
                if parsed_dt > now_utc + timedelta(hours=24):
                    errors.append(f"Timestamp is in the distant future: {parsed_dt.isoformat()}.")
                elif parsed_dt.year < 2000:
                    errors.append(f"Timestamp precedes social media era (< 2000): {parsed_dt.isoformat()}.")
                else:
                    posted_at_dt = parsed_dt

        # 5. Non-fatal warnings
        if cleaned_text and len(cleaned_text) < 5:
            warnings.append("Text content is extremely short (< 5 characters).")

        raw_lang = fields.get("language")
        language = DataNormalizer.normalize_language(raw_lang) if raw_lang else None
        if not language:
            warnings.append("Language code is missing or unspecified.")

        # If any validation errors occurred, return failure
        if errors or cleaned_text is None or posted_at_dt is None:
            return DataQualityResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                post=None,
            )

        # 6. Extract quality flags & metrics
        quality_flags = cls.extract_quality_flags(cleaned_text)
        word_count = len(cleaned_text.split())
        char_count = len(cleaned_text)

        collected_at_raw = fields.get("collected_at")
        collected_at_dt = (
            DataNormalizer.parse_timestamp(collected_at_raw)[0]
            if collected_at_raw
            else None
        )

        analytics_post = AnalyticsReadyPost(
            id=fields.get("id"),
            platform=platform,
            external_post_id=external_post_id,
            text=cleaned_text,
            raw_text=str(raw_text) if raw_text is not None else None,
            author_username=DataNormalizer.normalize_username(fields.get("author_username")),
            author_display_name=fields.get("author_display_name"),
            posted_at=posted_at_dt,
            collected_at=collected_at_dt,
            url=DataNormalizer.normalize_url(fields.get("url")),
            language=language,
            metrics=fields.get("metrics"),
            metadata=fields.get("metadata") or {},
            char_count=char_count,
            word_count=word_count,
            quality_flags=quality_flags,
        )

        return DataQualityResult(
            is_valid=True,
            errors=[],
            warnings=warnings,
            post=analytics_post,
        )

    @classmethod
    def validate_batch(
        cls,
        records: Iterable[Union[NormalizedPost, PostSummary, Post, Dict[str, Any]]],
    ) -> BatchDataQualityResult:
        """
        Validates an iterable of social media records, separating quality-approved
        posts from rejected records with detailed diagnostics.
        """
        valid_posts: List[AnalyticsReadyPost] = []
        rejected_records: List[RejectedRecord] = []
        total = 0

        for record in records:
            total += 1
            result = cls.validate_and_prepare(record)
            if result.is_valid and result.post is not None:
                valid_posts.append(result.post)
            else:
                # Build diagnostic excerpt
                ext_id = None
                platform = None
                raw_excerpt = None
                try:
                    fields = cls._extract_fields(record)
                    ext_id = str(fields.get("external_post_id") or "")
                    platform = str(fields.get("platform") or "")
                    text_snippet = str(fields.get("text") or "")
                    raw_excerpt = text_snippet[:100] if text_snippet else None
                except Exception:
                    pass

                rejected_records.append(
                    RejectedRecord(
                        external_post_id=ext_id if ext_id else None,
                        platform=platform if platform else None,
                        errors=result.errors,
                        raw_excerpt=raw_excerpt,
                    )
                )

        return BatchDataQualityResult(
            total_evaluated=total,
            valid_count=len(valid_posts),
            invalid_count=len(rejected_records),
            valid_posts=valid_posts,
            rejected_records=rejected_records,
        )


# Global singleton factory
_default_data_quality_service = DataQualityService()


def get_data_quality_service() -> DataQualityService:
    """Provides the singleton instance of DataQualityService."""
    return _default_data_quality_service
