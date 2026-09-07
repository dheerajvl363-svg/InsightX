from datetime import datetime, timezone
import re
from typing import Any, Dict, Optional, Union
import unicodedata

from app.schemas.post import NormalizedPost, PostMetricsSchema, RawPostPayload


# Canonical mapping for supported social media platforms
PLATFORM_CANONICAL_MAP = {
    "x": "X",
    "twitter": "X",
    "x.com": "X",
    "tweet": "X",
    "telegram": "Telegram",
    "tg": "Telegram",
    "telegram_channel": "Telegram",
    "reddit": "Reddit",
    "r/": "Reddit",
    "subreddit": "Reddit",
    "youtube": "YouTube",
    "yt": "YouTube",
    "yt_video": "YouTube",
}


class DataNormalizer:
    """
    Deterministic normalization service for social media data.
    Converts diverse raw payloads into uniform, standardized NormalizedPost instances.
    """

    @staticmethod
    def canonicalize_platform(raw_platform: str) -> str:
        """
        Standardize platform name to canonical form (e.g., 'twitter' -> 'X').
        """
        if not raw_platform or not raw_platform.strip():
            raise ValueError("Platform name cannot be empty")
        cleaned = raw_platform.strip().lower()
        return PLATFORM_CANONICAL_MAP.get(cleaned, raw_platform.strip().title())

    @staticmethod
    def normalize_text(text: Optional[str]) -> Optional[str]:
        """
        Clean and normalize text content:
        - Unicode NFC normalization
        - Standardize line endings (\r\n -> \n)
        - Collapse multiple spaces/tabs while preserving paragraphs
        - Strip leading and trailing whitespace
        """
        if text is None:
            return None

        # Unicode NFC normalization
        normalized = unicodedata.normalize("NFC", str(text))

        # Standardize line endings
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")

        # Collapse multiple horizontal whitespace on each line
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in normalized.split("\n")]

        # Re-join lines and strip outer whitespace
        cleaned = "\n".join(lines).strip()
        return cleaned if cleaned else None

    @staticmethod
    def parse_timestamp(raw_ts: Optional[Union[datetime, str, int, float]]) -> tuple[datetime, bool]:
        """
        Parse diverse timestamp representations into a timezone-aware UTC datetime.
        Returns a tuple: (standardized_datetime, was_inferred).
        """
        if raw_ts is None:
            return datetime.now(timezone.utc), True

        if isinstance(raw_ts, datetime):
            if raw_ts.tzinfo is None:
                return raw_ts.replace(tzinfo=timezone.utc), False
            return raw_ts.astimezone(timezone.utc), False

        if isinstance(raw_ts, (int, float)):
            # Distinguish milliseconds vs seconds epoch
            ts = float(raw_ts)
            if ts > 1e11:  # Milliseconds epoch
                ts = ts / 1000.0
            return datetime.fromtimestamp(ts, tz=timezone.utc), False

        if isinstance(raw_ts, str):
            clean_str = raw_ts.strip()
            if not clean_str:
                return datetime.now(timezone.utc), True

            # Attempt ISO format parsing (e.g. 2026-09-08T01:00:00Z)
            iso_candidate = clean_str.replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(iso_candidate)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc), False
            except ValueError:
                pass

            # Common fallback social date patterns
            date_formats = [
                "%Y-%m-%d %H:%M:%S%z",
                "%Y-%m-%d %H:%M:%S",
                "%Y/%m/%d %H:%M:%S",
                "%a %b %d %H:%M:%S %z %Y",  # Standard Twitter/X format
                "%d-%m-%Y %H:%M:%S",
            ]
            for fmt in date_formats:
                try:
                    dt = datetime.strptime(clean_str, fmt)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt.astimezone(timezone.utc), False
                except ValueError:
                    continue

        # Inferred fallback if unable to parse
        return datetime.now(timezone.utc), True

    @staticmethod
    def normalize_username(username: Optional[str]) -> Optional[str]:
        """
        Normalize author username:
        - Strip whitespace
        - Remove leading '@'
        """
        if not username:
            return None
        cleaned = username.strip().lstrip("@")
        return cleaned if cleaned else None

    @staticmethod
    def normalize_url(url: Optional[str]) -> Optional[str]:
        """
        Validate and clean URL string.
        """
        if not url:
            return None
        cleaned = url.strip()
        if cleaned.startswith("http://") or cleaned.startswith("https://"):
            return cleaned
        return None

    @staticmethod
    def normalize_language(lang: Optional[str]) -> Optional[str]:
        """
        Normalize language code to lowercase ISO code (e.g. 'EN' -> 'en', 'en-US' -> 'en').
        """
        if not lang:
            return None
        cleaned = lang.strip().lower()
        # Take primary language subtag if hyphenated/underscored
        primary = re.split(r"[-_]", cleaned)[0]
        return primary[:10] if primary else None

    @classmethod
    def normalize(cls, payload: RawPostPayload) -> NormalizedPost:
        """
        Transforms a validated RawPostPayload into a standardized NormalizedPost.
        """
        # 1. Canonicalize platform
        platform_name = cls.canonicalize_platform(payload.platform)

        # 2. Sanitize external post ID
        external_post_id = str(payload.external_id).strip()

        # 3. Clean text content
        text = cls.normalize_text(payload.text)

        # 4. Standardize timestamps
        posted_at, was_inferred = cls.parse_timestamp(payload.posted_at)
        collected_at = datetime.now(timezone.utc)

        # 5. Normalize author information
        author_username = cls.normalize_username(payload.author_username)
        author_display_name = (
            unicodedata.normalize("NFC", payload.author_display_name.strip())
            if payload.author_display_name and payload.author_display_name.strip()
            else None
        )

        # 6. Normalize URL & Language
        url = cls.normalize_url(payload.url)
        language = cls.normalize_language(payload.language)

        # 7. Normalize metrics
        metrics: Optional[PostMetricsSchema] = None
        if payload.metrics:
            if isinstance(payload.metrics, PostMetricsSchema):
                metrics = payload.metrics
            elif isinstance(payload.metrics, dict):
                metrics = PostMetricsSchema(**payload.metrics)

        # 8. Build metadata and preserve raw payload
        meta = dict(payload.metadata or {})
        if was_inferred:
            meta["posted_at_inferred"] = True

        # Preserve all incoming raw fields
        raw = dict(payload.raw_payload or {})
        dumped = payload.model_dump(exclude={"raw_payload"})
        for k, v in dumped.items():
            if k not in raw and v is not None:
                # Convert non-serializable objects (like datetime) to isoformat
                if isinstance(v, datetime):
                    raw[k] = v.isoformat()
                else:
                    raw[k] = v

        return NormalizedPost(
            platform_name=platform_name,
            external_post_id=external_post_id,
            text=text,
            author_username=author_username,
            author_display_name=author_display_name,
            posted_at=posted_at,
            collected_at=collected_at,
            url=url,
            language=language,
            metrics=metrics,
            metadata=meta,
            raw_payload=raw,
        )
