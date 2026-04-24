"""ARQ worker entry point."""
from urllib.parse import urlparse

from arq.connections import RedisSettings

from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.workers.analyze_job import run_analysis

setup_logging()
logger = get_logger(__name__)


def _redis_settings_from_url(url: str) -> RedisSettings:
    """Parse redis://host:port/db into arq RedisSettings."""
    parsed = urlparse(url)
    return RedisSettings(
        host=parsed.hostname or "127.0.0.1",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or 0),
        password=parsed.password or None,
    )


async def startup(ctx: dict) -> None:
    from aiogram import Bot
    ctx["bot"] = Bot(token=settings.telegram_bot_token)
    logger.info("worker_started")


async def shutdown(ctx: dict) -> None:
    bot = ctx.get("bot")
    if bot:
        await bot.session.close()
    logger.info("worker_stopped")


class WorkerSettings:
    functions = [run_analysis]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = _redis_settings_from_url(settings.redis_url)
    max_jobs = settings.worker_concurrency
    job_timeout = 600
    keep_result = 86400
