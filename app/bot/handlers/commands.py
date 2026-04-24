"""Bot command handlers: /start /help /analyze /last"""
import json
import uuid

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.formatters import format_summary
from app.core.cache import get_cache
from app.core.database import AsyncSessionFactory
from app.core.logging import get_logger
from app.repos.analysis_repo import AnalysisRepo
from app.repos.job_repo import JobRepo
from app.schemas.analysis import AnalysisResult
from app.schemas.job import JobCreate

router = Router()
logger = get_logger(__name__)

HELP_TEXT = """
<b>Content Intelligence Bot</b>

Команды:
/analyze &lt;@хэндл или ссылка&gt; — запустить анализ блогера
/last — последняя сводка из кэша
/help — справка

Примеры:
<code>/analyze @username</code>
<code>/analyze https://www.instagram.com/username/</code>

Бот соберёт публичный контент за последние 24 часа и пришлёт сводку.
""".strip()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 Привет! Я анализирую публичный контент Instagram-блогеров.\n\n"
        + HELP_TEXT,
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, parse_mode="HTML")


@router.message(Command("analyze"))
async def cmd_analyze(message: Message) -> None:
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer(
            "Укажи хэндл или ссылку:\n<code>/analyze @username</code>",
            parse_mode="HTML",
        )
        return

    raw_input = args[1].strip()
    chat_id = message.chat.id

    async with AsyncSessionFactory() as session:
        job_repo = JobRepo(session)
        job = await job_repo.create(
            JobCreate(
                input_handle=raw_input,
                chat_id=chat_id,
                message_id=message.message_id,
            )
        )

    # Enqueue via ARQ
    from urllib.parse import urlparse
    from arq import create_pool
    from arq.connections import RedisSettings

    from app.core.config import settings

    _p = urlparse(settings.redis_url)
    _rs = RedisSettings(
        host=_p.hostname or "127.0.0.1",
        port=_p.port or 6379,
        database=int(_p.path.lstrip("/") or 0),
        password=_p.password or None,
    )
    redis_pool = await create_pool(_rs)
    await redis_pool.enqueue_job("run_analysis", str(job.id))
    await redis_pool.aclose()

    await message.answer(
        f"✅ Принято! Анализируем <b>{raw_input}</b>...\n"
        "Результат придёт в этот чат, обычно занимает 1–3 минуты.",
        parse_mode="HTML",
    )
    logger.info("job_enqueued", job_id=str(job.id), handle=raw_input)


@router.message(Command("last"))
async def cmd_last(message: Message) -> None:
    chat_id = message.chat.id

    async with AsyncSessionFactory() as session:
        job_repo = JobRepo(session)
        analysis_repo = AnalysisRepo(session)

        last_job = await job_repo.get_last_for_chat(chat_id)
        if last_job is None:
            await message.answer("Нет завершённых анализов. Запусти /analyze.")
            return

        # Try cache first
        cache = get_cache()
        cached = await cache.get(last_job.input_handle)

        if cached:
            try:
                result = AnalysisResult.model_validate(cached)
                text = format_summary(result)
                from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
                kb = InlineKeyboardMarkup(
                    inline_keyboard=[[
                        InlineKeyboardButton(
                            text="📄 Получить JSON",
                            callback_data=f"json:{last_job.id}",
                        )
                    ]]
                )
                await message.answer(
                    "📋 Последняя сводка (из кэша):\n\n" + text,
                    parse_mode="HTML",
                    reply_markup=kb,
                )
                return
            except Exception as exc:
                logger.warning("cache_parse_failed", error=str(exc))

        # Fallback: DB
        analysis = await analysis_repo.get_by_job(last_job.id)
        if analysis is None:
            await message.answer("Результат анализа не найден. Запусти /analyze заново.")
            return

        result = AnalysisResult.model_validate(analysis.result_json)
        text = format_summary(result)
        await message.answer(
            "📋 Последняя сводка:\n\n" + text,
            parse_mode="HTML",
        )
