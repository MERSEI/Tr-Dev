"""Inline button callbacks."""
import json
import uuid

from aiogram import Router
from aiogram.types import BufferedInputFile, CallbackQuery

from app.core.database import AsyncSessionFactory
from app.core.logging import get_logger
from app.repos.analysis_repo import AnalysisRepo

router = Router()
logger = get_logger(__name__)


@router.callback_query(lambda c: c.data and c.data.startswith("json:"))
async def cb_get_json(callback: CallbackQuery) -> None:
    await callback.answer()

    job_id_str = callback.data.split(":", 1)[1]
    try:
        job_id = uuid.UUID(job_id_str)
    except ValueError:
        await callback.message.answer("Неверный ID задачи.")
        return

    async with AsyncSessionFactory() as session:
        repo = AnalysisRepo(session)
        analysis = await repo.get_by_job(job_id)

    if analysis is None:
        await callback.message.answer("Результат не найден.")
        return

    raw_json = json.dumps(
        analysis.result_json,
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")

    file = BufferedInputFile(raw_json, filename=f"analysis_{job_id_str[:8]}.json")
    await callback.message.answer_document(
        file,
        caption="📄 Полный JSON результата анализа",
    )
    logger.info("json_sent", job_id=job_id_str, chat_id=callback.message.chat.id)
