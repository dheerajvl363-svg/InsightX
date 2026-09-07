from typing import Any, Dict, Optional

from app.schemas.post import PostMetricsSchema, RawPostPayload
from app.services.adapters.base import BasePlatformAdapter


class YouTubeAdapter(BasePlatformAdapter):
    """
    Adapter for YouTube video and comment payloads (YouTube Data API v3 format).
    """

    @property
    def platform_name(self) -> str:
        return "YouTube"

    def can_handle(self, data: Dict[str, Any]) -> bool:
        if not isinstance(data, dict):
            return False
        platform = str(data.get("platform") or "").strip().lower()
        if platform in ("youtube", "yt", "yt_video"):
            return True
        return "videoId" in data or ("snippet" in data and "statistics" in data)

    def to_raw_payload(self, data: Dict[str, Any]) -> RawPostPayload:
        if not isinstance(data, dict):
            raise ValueError("Input data must be a dictionary.")

        # 1. External ID (videoId, id, post_id)
        ext_id = data.get("videoId") or data.get("id") or data.get("post_id") or data.get("external_id")
        if isinstance(ext_id, dict):  # YouTube API id object: {"kind": "...", "videoId": "..."}
            ext_id = ext_id.get("videoId")

        if not ext_id or not str(ext_id).strip():
            raise ValueError("YouTube payload missing required 'videoId' or 'id'.")

        # 2. Text / Content (title and description from snippet or flat)
        snippet = data.get("snippet") if isinstance(data.get("snippet"), dict) else {}

        title = (snippet.get("title") or data.get("title") or data.get("caption") or "").strip()
        description = (snippet.get("description") or data.get("description") or data.get("text") or data.get("content") or "").strip()

        if title and description and title != description:
            text = f"{title}\n\n{description}"
        elif title:
            text = title
        elif description:
            text = description
        else:
            text = None

        # 3. Author info (channelTitle, channelId)
        author_username = (
            snippet.get("channelId")
            or data.get("channel_id")
            or data.get("author_username")
            or data.get("username")
        )
        author_display_name = (
            snippet.get("channelTitle")
            or data.get("channel_title")
            or data.get("author_display_name")
            or data.get("display_name")
            or data.get("author")
        )

        # 4. Timestamp (publishedAt)
        posted_at = snippet.get("publishedAt") or data.get("publishedAt") or data.get("posted_at")

        # 5. URL
        url = data.get("url")
        if not url and ext_id:
            url = f"https://youtube.com/watch?v={ext_id}"

        # 6. Language
        language = (
            snippet.get("defaultLanguage")
            or snippet.get("defaultAudioLanguage")
            or data.get("language")
            or data.get("lang")
        )

        # 7. Metrics (statistics object or flat)
        stats = data.get("statistics") if isinstance(data.get("statistics"), dict) else {}
        metrics: Optional[PostMetricsSchema] = None

        views = stats.get("viewCount") or data.get("views")
        likes = stats.get("likeCount") or data.get("likes")
        comments = stats.get("commentCount") or data.get("comments")

        if views is not None or likes is not None or comments is not None:
            metrics = PostMetricsSchema(
                views=int(views or 0),
                likes=int(likes or 0),
                comments=int(comments or 0),
                shares=int(data.get("shares") or 0),
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
        if "tags" in snippet:
            metadata["tags"] = snippet["tags"]
        if "duration_seconds" in data:
            metadata["duration_seconds"] = data["duration_seconds"]

        return RawPostPayload(
            platform=self.platform_name,
            external_id=str(ext_id).strip(),
            text=text,
            author_username=str(author_username).strip() if author_username else None,
            author_display_name=str(author_display_name).strip() if author_display_name else None,
            posted_at=posted_at,
            url=url,
            language=language,
            metrics=metrics,
            metadata=metadata,
            raw_payload=dict(data),
        )
