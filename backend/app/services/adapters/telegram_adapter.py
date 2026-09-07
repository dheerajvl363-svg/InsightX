from typing import Any, Dict, Optional

from app.schemas.post import PostMetricsSchema, RawPostPayload
from app.services.adapters.base import BasePlatformAdapter


class TelegramAdapter(BasePlatformAdapter):
    """
    Adapter for Telegram message payloads (Bot API or channel export format).
    """

    @property
    def platform_name(self) -> str:
        return "Telegram"

    def can_handle(self, data: Dict[str, Any]) -> bool:
        if not isinstance(data, dict):
            return False
        platform = str(data.get("platform") or "").strip().lower()
        if platform in ("telegram", "tg", "telegram_channel"):
            return True
        return "message_id" in data

    def to_raw_payload(self, data: Dict[str, Any]) -> RawPostPayload:
        if not isinstance(data, dict):
            raise ValueError("Input data must be a dictionary.")

        # 1. External ID (message_id or id)
        ext_id = data.get("message_id") or data.get("id") or data.get("external_id")
        if not ext_id or not str(ext_id).strip():
            raise ValueError("Telegram payload missing required 'message_id' or 'id'.")

        # 2. Text / Content (message, text, or caption)
        text = data.get("message") or data.get("text") or data.get("caption") or data.get("content")

        # 3. Author / Sender / Channel info
        author_username: Optional[str] = None
        author_display_name: Optional[str] = None

        sender = data.get("from") or data.get("sender") or data.get("chat") or data.get("channel")
        if isinstance(sender, dict):
            author_username = sender.get("username")
            author_display_name = sender.get("title") or sender.get("first_name")
        elif isinstance(sender, str):
            author_username = sender
        else:
            author_username = data.get("username") or data.get("author_username")
            author_display_name = data.get("display_name") or data.get("author_display_name")

        # 4. Timestamp (date or posted_at)
        posted_at = data.get("date") or data.get("posted_at")

        # 5. URL
        url = data.get("url")
        channel_name = data.get("channel_username") or (author_username if author_username else None)
        if not url and channel_name and ext_id:
            clean_chan = str(channel_name).strip().lstrip("@")
            url = f"https://t.me/{clean_chan}/{ext_id}"

        # 6. Language
        language = data.get("language") or data.get("lang")

        # 7. Metrics (views, forwards)
        metrics: Optional[PostMetricsSchema] = None
        views = data.get("views")
        forwards = data.get("forwards") or data.get("shares")
        if views is not None or forwards is not None:
            metrics = PostMetricsSchema(
                views=int(views or 0),
                shares=int(forwards or 0),
                likes=int(data.get("likes") or 0),
                comments=int(data.get("comments") or 0),
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
        if "chat_id" in data:
            metadata["chat_id"] = data["chat_id"]
        if "forward_from" in data:
            metadata["forward_from"] = data["forward_from"]

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
