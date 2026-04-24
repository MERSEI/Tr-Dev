"""Instagram collector via instaloader — works with public profiles, no auth required."""
import asyncio
import re
from datetime import datetime, timezone
from pathlib import Path

from app.collectors.base import ContentCollector
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.collector import ContentItem

logger = get_logger(__name__)


class InstagramCollector(ContentCollector):
    platform = "instagram"

    def __init__(self) -> None:
        import instaloader

        self._il = instaloader.Instaloader(
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            quiet=True,
        )
        session_file = settings.instagram_session_file
        if session_file and Path(session_file).exists():
            try:
                self._il.load_session_from_file(
                    Path(session_file).stem, session_file
                )
                logger.info("instagram_session_loaded", file=session_file)
            except Exception as exc:
                logger.warning("instagram_session_load_failed", error=str(exc))

    async def resolve_handle(self, raw_input: str) -> str:
        clean = raw_input.strip().lstrip("@")
        if "instagram.com" in clean:
            m = re.search(r"instagram\.com/([^/?#]+)", clean)
            if m:
                return m.group(1)
        return clean.split("/")[0].split("?")[0]

    async def collect(
        self,
        handle: str,
        since: datetime,
        until: datetime,
    ) -> list[ContentItem]:
        return await asyncio.get_event_loop().run_in_executor(
            None, self._collect_sync, handle, since, until
        )

    def _collect_sync(
        self,
        handle: str,
        since: datetime,
        until: datetime,
    ) -> list[ContentItem]:
        import instaloader

        since_utc = since.replace(tzinfo=timezone.utc) if since.tzinfo is None else since
        until_utc = until.replace(tzinfo=timezone.utc) if until.tzinfo is None else until

        try:
            profile = instaloader.Profile.from_username(self._il.context, handle)
        except instaloader.exceptions.ProfileNotExistsException:
            logger.error("instagram_profile_not_found", handle=handle)
            return []
        except Exception as exc:
            logger.error("instagram_profile_error", handle=handle, error=str(exc))
            return []

        items: list[ContentItem] = []
        try:
            for post in profile.get_posts():
                taken = post.date_utc.replace(tzinfo=timezone.utc)
                if taken < since_utc:
                    break
                if taken > until_utc:
                    continue

                content_type = "video" if post.is_video else "image"
                media_urls = [post.video_url] if post.is_video else [post.url]

                items.append(
                    ContentItem(
                        item_id=post.shortcode,
                        content_type=content_type,
                        url=f"https://www.instagram.com/p/{post.shortcode}/",
                        caption=post.caption or "",
                        taken_at=taken,
                        media_urls=[u for u in media_urls if u],
                        thumbnail_url=post.url if post.is_video else None,
                        duration_seconds=post.video_duration if post.is_video else None,
                    )
                )
        except Exception as exc:
            logger.error("instagram_posts_error", handle=handle, error=str(exc))

        logger.info(
            "instagram_collected",
            handle=handle,
            count=len(items),
            since=since_utc.isoformat(),
        )
        return items
