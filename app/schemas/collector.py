from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ContentType = Literal["video", "image", "carousel"]


class ContentItem(BaseModel):
    item_id: str
    platform: str = "instagram"
    content_type: ContentType
    url: str
    caption: str = ""
    taken_at: datetime
    media_urls: list[str] = Field(default_factory=list)
    thumbnail_url: str | None = None
    duration_seconds: float | None = None
    local_path: str | None = None
