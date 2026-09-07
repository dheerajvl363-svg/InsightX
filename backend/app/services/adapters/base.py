from abc import ABC, abstractmethod
from typing import Any, Dict

from app.schemas.post import RawPostPayload


class BasePlatformAdapter(ABC):
    """
    Abstract base interface for all social media platform adapters.
    Translates platform-specific raw dictionary payloads into a standardized RawPostPayload.
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """The canonical platform name (e.g. 'X', 'Telegram', 'Reddit', 'YouTube')."""
        pass

    @abstractmethod
    def to_raw_payload(self, data: Dict[str, Any]) -> RawPostPayload:
        """
        Converts platform-specific raw data into a validated RawPostPayload.
        Raises ValueError if required identifiers or critical structures are missing.
        """
        pass

    def can_handle(self, data: Dict[str, Any]) -> bool:
        """
        Heuristic check to determine if the adapter can process the raw data.
        Can be overridden by platform-specific implementations.
        """
        if not isinstance(data, dict):
            return False
        platform = str(data.get("platform") or "").strip().lower()
        return platform == self.platform_name.lower()
