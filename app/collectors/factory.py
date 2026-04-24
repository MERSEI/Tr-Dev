from app.collectors.base import ContentCollector
from app.core.config import settings


def get_collector() -> ContentCollector:
    if settings.collector_provider == "instagram":
        from app.collectors.instagram import InstagramCollector
        return InstagramCollector()
    from app.collectors.mock import MockCollector
    return MockCollector()
