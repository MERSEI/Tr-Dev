"""Mock collector — returns fixture data for local testing without real Instagram."""
import re
from datetime import datetime, timezone

from app.collectors.base import ContentCollector
from app.schemas.collector import ContentItem


class MockCollector(ContentCollector):
    platform = "instagram"

    async def resolve_handle(self, raw_input: str) -> str:
        handle = raw_input.strip().lstrip("@").split("/")[-1].split("?")[0]
        return handle or "mock_user"

    async def collect(
        self,
        handle: str,
        since: datetime,
        until: datetime,
    ) -> list[ContentItem]:
        now = until.replace(tzinfo=timezone.utc) if until.tzinfo is None else until
        items = [
            ContentItem(
                item_id=f"{handle}_reel_001",
                content_type="video",
                url=f"https://www.instagram.com/reel/mock001/",
                caption=(
                    "Привет всем! Сегодня разбираем топ-5 лайфхаков для продуктивности. "
                    "Пишите в комментах, что думаете! #продуктивность #лайфхак"
                ),
                taken_at=now,
                media_urls=["https://example.com/mock_video_001.mp4"],
                duration_seconds=45.0,
                local_path=None,
            ),
            ContentItem(
                item_id=f"{handle}_reel_002",
                content_type="video",
                url=f"https://www.instagram.com/reel/mock002/",
                caption=(
                    "Утренняя рутина — база. Без неё никак. "
                    "Встаю в 6 утра каждый день, и вот что это даёт 👇"
                ),
                taken_at=now,
                media_urls=["https://example.com/mock_video_002.mp4"],
                duration_seconds=30.0,
                local_path=None,
            ),
            ContentItem(
                item_id=f"{handle}_post_003",
                content_type="image",
                url=f"https://www.instagram.com/p/mock003/",
                caption=(
                    "Работа над собой — это не спринт, это марафон. "
                    "Главное — не останавливаться, понимаете? Каждый день маленький шаг."
                ),
                taken_at=now,
                media_urls=["https://example.com/mock_image_003.jpg"],
                local_path=None,
            ),
        ]
        return items
