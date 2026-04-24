"""ARQ worker entry point."""
import os

from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.workers.analyze_job import run_analysis

setup_logging()
logger = get_logger(__name__)


async def startup(ctx: dict) -> None:
    from aiogram import Bot
    bot_token = settings.telegram_bot_token
    ctx["bot"] = Bot(token=bot_token)
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
    redis_settings = settings.redis_url
    max_jobs = settings.worker_concurrency
    job_timeout = 600
    keep_result = 86400
