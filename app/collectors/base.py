from abc import ABC, abstractmethod
from datetime import datetime

from app.schemas.collector import ContentItem


class ContentCollector(ABC):
    platform: str = "unknown"

    @abstractmethod
    async def collect(
        self,
        handle: str,
        since: datetime,
        until: datetime,
    ) -> list[ContentItem]:
        """Collect public content items for a given handle in [since, until]."""

    @abstractmethod
    async def resolve_handle(self, raw_input: str) -> str:
        """Normalize raw user input (URL or @handle) to a plain username."""
