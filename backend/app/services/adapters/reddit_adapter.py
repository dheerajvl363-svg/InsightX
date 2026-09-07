from typing import Any, Dict, Optional

from app.schemas.post import PostMetricsSchema, RawPostPayload
from app.services.adapters.base import BasePlatformAdapter


class RedditAdapter(BasePlatformAdapter):
    """
    Adapter for Reddit submission/comment payloads (Reddit JSON API format).
    """

    @property
    def platform_name(self) -> str:
        return "Reddit"

    def can_handle(self, data: Dict[str, Any]) -> bool:
        if not isinstance(data, dict):
            return False
        platform = str(data.get("platform") or "").strip().lower()
        if platform in ("reddit", "r/", "subreddit"):
            return True
        return "subreddit" in data or "selftext" in data or "created_utc" in data

    def to_raw_payload(self, data: Dict[str, Any]) -> RawPostPayload:
        if not isinstance(data, dict):
            raise ValueError("Input data must be a dictionary.")

        # 1. External ID (id, name, post_id)
        ext_id = data.get("id") or data.get("post_id") or data.get("external_id")
        if not ext_id:
            name = data.get("name")
            if name and str(name).startswith("t3_"):
                ext_id = str(name).replace("t3_", "")
            else:
                ext_id = name

        if not ext_id or not str(ext_id).strip():
            raise ValueError("Reddit payload missing required 'id' or 'name'.")

        # 2. Text / Content (combination of title and selftext/body)
        title = (data.get("title") or "").strip()
        selftext = (data.get("selftext") or data.get("body") or data.get("text") or data.get("content") or "").strip()

        if title and selftext and title != selftext:
            text = f"{title}\n\n{selftext}"
        elif title:
            text = title
        elif selftext:
            text = selftext
        else:
            text = None

        # 3. Author info
        author_raw = data.get("author") or data.get("author_username") or data.get("username")
        author_username: Optional[str] = None
        if author_raw:
            author_username = str(author_raw).strip().lstrip("u/")

        author_display_name = data.get("author_display_name") or data.get("display_name")

        # 4. Timestamp (created_utc or posted_at)
        posted_at = data.get("created_utc") or data.get("posted_at") or data.get("created")

        # 5. URL (permalink or url)
        url = data.get("url")
        permalink = data.get("permalink")
        if permalink and not url:
            clean_link = str(permalink).strip()
            if clean_link.startswith("http"):
                url = clean_link
            else:
                url = f"https://reddit.com{clean_link}"

        # 6. Language
        language = data.get("language") or data.get("lang")

        # 7. Metrics (score, num_comments, ups)
        metrics: Optional[PostMetricsSchema] = None
        score = data.get("score") if data.get("score") is not None else data.get("ups")
        num_comments = data.get("num_comments") or data.get("comments")

        if score is not None or num_comments is not None:
            metrics = PostMetricsSchema(
                likes=max(0, int(score or 0)),
                comments=max(0, int(num_comments or 0)),
                shares=int(data.get("shares") or 0),
                views=int(data.get("views") or 0),
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
        if "subreddit" in data:
            metadata["subreddit"] = data["subreddit"]
        if "link_flair_text" in data:
            metadata["flair"] = data["link_flair_text"]
        if "upvote_ratio" in data:
            metadata["upvote_ratio"] = data["upvote_ratio"]

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
