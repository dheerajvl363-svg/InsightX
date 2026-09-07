from typing import Any, Dict, Optional

from app.services.adapters.base import BasePlatformAdapter
from app.services.adapters.reddit_adapter import RedditAdapter
from app.services.adapters.telegram_adapter import TelegramAdapter
from app.services.adapters.x_adapter import XAdapter
from app.services.adapters.youtube_adapter import YouTubeAdapter

ADAPTERS = {
    "x": XAdapter(),
    "twitter": XAdapter(),
    "telegram": TelegramAdapter(),
    "reddit": RedditAdapter(),
    "youtube": YouTubeAdapter(),
}


def get_adapter(platform_name: str) -> BasePlatformAdapter:
    """
    Returns the adapter instance for a given platform name.
    Raises ValueError if the platform is unsupported.
    """
    if not platform_name:
        raise ValueError("Platform name cannot be empty.")
    key = platform_name.strip().lower()
    adapter = ADAPTERS.get(key)
    if not adapter:
        raise ValueError(f"No adapter registered for platform: '{platform_name}'.")
    return adapter


def detect_adapter(data: Dict[str, Any]) -> Optional[BasePlatformAdapter]:
    """
    Detects and returns the appropriate adapter for a raw data payload.
    """
    if not isinstance(data, dict):
        return None

    # 1. Direct platform key check
    platform = data.get("platform")
    if platform and str(platform).strip().lower() in ADAPTERS:
        return ADAPTERS[str(platform).strip().lower()]

    # 2. Heuristic check across registered adapters
    for adapter in [XAdapter(), TelegramAdapter(), RedditAdapter(), YouTubeAdapter()]:
        if adapter.can_handle(data):
            return adapter

    return None


__all__ = [
    "BasePlatformAdapter",
    "XAdapter",
    "TelegramAdapter",
    "RedditAdapter",
    "YouTubeAdapter",
    "get_adapter",
    "detect_adapter",
]
