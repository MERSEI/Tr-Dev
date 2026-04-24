"""Downloads media files from URLs using httpx with retry logic."""
import asyncio
import uuid
from pathlib import Path

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.collector import ContentItem

logger = get_logger(__name__)

_TIMEOUT = httpx.Timeout(60.0, connect=10.0)
_RETRIES = 3


async def _download_file(client: httpx.AsyncClient, url: str, dest: Path) -> bool:
    for attempt in range(1, _RETRIES + 1):
        try:
            async with client.stream("GET", url, timeout=_TIMEOUT) as resp:
                resp.raise_for_status()
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open("wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=65536):
                        f.write(chunk)
            return True
        except Exception as exc:
            logger.warning("download_attempt_failed", url=url, attempt=attempt, error=str(exc))
            if attempt < _RETRIES:
                await asyncio.sleep(2**attempt)
    return False


async def download_items(
    items: list[ContentItem],
    job_id: uuid.UUID,
) -> list[ContentItem]:
    job_dir = settings.media_root / str(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)

    updated: list[ContentItem] = []
    async with httpx.AsyncClient(follow_redirects=True) as client:
        for item in items:
            if not item.media_urls:
                updated.append(item)
                continue

            url = item.media_urls[0]
            suffix = ".mp4" if item.content_type == "video" else ".jpg"
            dest = job_dir / f"{item.item_id}{suffix}"

            if dest.exists():
                updated.append(item.model_copy(update={"local_path": str(dest)}))
                continue

            ok = await _download_file(client, url, dest)
            if ok:
                logger.info("downloaded", item_id=item.item_id, path=str(dest))
                updated.append(item.model_copy(update={"local_path": str(dest)}))
            else:
                logger.error("download_failed", item_id=item.item_id, url=url)
                updated.append(item)

    return updated
