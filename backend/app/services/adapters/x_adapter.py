from typing import Any, Dict, Optional

from app.schemas.post import PostMetricsSchema, RawPostPayload
from app.services.adapters.base import BasePlatformAdapter


class XAdapter(BasePlatformAdapter):
    """
    Adapter for X / Twitter payloads (v2 API style or flat raw exports).
    """

    @property
    def platform_name(self) -> str:
        return "X"

    def can_handle(self, data: Dict[str, Any]) -> bool:
        if not isinstance(data, dict):
            return False
        platform = str(data.get("platform") or "").strip().lower()
        if platform in ("x", "twitter", "x.com", "tweet"):
            return True
        # Heuristic: has tweet_id or (id and public_metrics)
        return "tweet_id" in data or ("public_metrics" in data and "id" in data)

    def to_raw_payload(self, data: Dict[str, Any]) -> RawPostPayload:
        if not isinstance(data, dict):
            raise ValueError("Input data must be a dictionary.")

        # 1. External ID
        ext_id = data.get("id") or data.get("tweet_id") or data.get("external_id")
        if not ext_id or not str(ext_id).strip():
            raise ValueError("X payload missing required 'id' or 'tweet_id'.")

        # 2. Text / Content
        text = data.get("text") or data.get("content")

        # 3. Author info
        author_username: Optional[str] = None
        author_display_name: Optional[str] = None

        author_raw = data.get("author") or data.get("user")
        if isinstance(author_raw, dict):
            author_username = author_raw.get("username")
            author_display_name = author_raw.get("name") or author_raw.get("display_name")
        elif isinstance(author_raw, str):
            author_username = author_raw
        else:
            author_username = data.get("author_username") or data.get("username")
            author_display_name = data.get("author_display_name") or data.get("display_name")

        # 4. Timestamp
        posted_at = data.get("created_at") or data.get("posted_at")

        # 5. URL
        url = data.get("url")
        if not url and author_username and ext_id:
            clean_user = str(author_username).strip().lstrip("@")
            url = f"https://x.com/{clean_user}/status/{ext_id}"

        # 6. Language
        language = data.get("lang") or data.get("language")

        # 7. Metrics (public_metrics or standard metrics dict)
        metrics: Optional[PostMetricsSchema] = None
        pub_metrics = data.get("public_metrics")
        if isinstance(pub_metrics, dict):
            metrics = PostMetricsSchema(
                likes=pub_metrics.get("like_count", 0),
                comments=pub_metrics.get("reply_count", 0),
                shares=pub_metrics.get("retweet_count", 0),
                views=pub_metrics.get("impression_count", 0),
            )
        elif isinstance(data.get("metrics"), dict):
            m = data["metrics"]
            metrics = PostMetricsSchema(
                likes=m.get("likes", 0),
                comments=m.get("comments", 0),
                shares=m.get("shares", 0),
                views=m.get("views", 0),
            )

        # 8. Metadata
        metadata = dict(data.get("metadata") or {})
        if "entities" in data:
            metadata["entities"] = data["entities"]
        if "conversation_id" in data:
            metadata["conversation_id"] = data["conversation_id"]

        return RawPostPayload(
            platform=self.platform_name,
            external_id=str(ext_id).strip(),
            text=text,
            author_username=author_username,
            author_display_name=author_display_name,
            posted_at=posted_at,
            url=url,
            language=language,
            metrics=metrics,
            metadata=metadata,
            raw_payload=dict(data),
        )
