"""Core analysis pipeline — runs as ARQ background job."""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.collectors.factory import get_collector
from app.core.cache import get_cache
from app.core.config import settings
from app.core.database import AsyncSessionFactory
from app.core.logging import get_logger
from app.processors.audio_extractor import extract_audio
from app.processors.downloader import download_items
from app.processors.keyframe_extractor import extract_keyframes
from app.repos.analysis_repo import AnalysisRepo
from app.repos.job_repo import JobRepo
from app.schemas.analysis import (
    AnalysisWindow,
    ContentStats,
    PipelineStatus,
)
from app.schemas.job import JobStatusUpdate
from app.services import llm as llm_service
from app.services import ocr as ocr_service
from app.services import stt as stt_service
from app.services.ocr import OCRResult
from app.services.stt import STTResult

logger = get_logger(__name__)


async def run_analysis(ctx: dict[str, Any], job_id_str: str) -> None:
    job_id = uuid.UUID(job_id_str)
    logger.info("job_started", job_id=job_id_str)

    async with AsyncSessionFactory() as session:
        job_repo = JobRepo(session)
        analysis_repo = AnalysisRepo(session)

        job = await job_repo.get(job_id)
        if job is None:
            logger.error("job_not_found", job_id=job_id_str)
            return

        await job_repo.update_status(
            job_id, JobStatusUpdate(status="running", finished_at=None)
        )

        warnings: list[str] = []
        pipeline_status = PipelineStatus()

        try:
            # --- 1. Resolve handle and collect content ---
            collector = get_collector()
            raw_input = job.input_handle
            handle = await collector.resolve_handle(raw_input)

            now = datetime.now(tz=timezone.utc)
            since = now - timedelta(hours=settings.analysis_window_hours)
            analysis_window = AnalysisWindow(**{"from": since, "to": now})

            await analysis_repo.log_stage(job_id, "collector", "running")
            try:
                items = await collector.collect(handle, since, now)
                if items:
                    pipeline_status.collector = "success"
                else:
                    pipeline_status.collector = "partial"
                    warnings.append("Контент за последние 24 часа не найден.")
            except Exception as exc:
                logger.error("collector_failed", error=str(exc))
                pipeline_status.collector = "failed"
                warnings.append(f"Ошибка сбора контента: {exc}")
                items = []

            await analysis_repo.log_stage(job_id, "collector", pipeline_status.collector)

            content_stats = ContentStats(
                items_count=len(items),
                videos_count=sum(1 for i in items if i.content_type == "video"),
                images_count=sum(1 for i in items if i.content_type == "image"),
            )

            # --- 2. Download media ---
            if items:
                items = await download_items(items, job_id)

            # --- 3. STT + OCR (per video item, concurrently) ---
            stt_results: dict[str, STTResult] = {}
            ocr_results: dict[str, OCRResult] = {}

            video_items = [i for i in items if i.content_type == "video" and i.local_path]

            async def process_video(item) -> None:
                audio_path = await extract_audio(item.local_path)
                frames = await extract_keyframes(item.local_path)

                if audio_path:
                    stt_result = await stt_service.transcribe(audio_path)
                else:
                    stt_result = STTResult(status="skipped", segments=[], language=None, error="no audio")
                stt_results[item.item_id] = stt_result

                if frames:
                    ocr_result = await ocr_service.ocr_frames(frames)
                else:
                    ocr_result = OCRResult(status="skipped", texts=[], error="no frames")
                ocr_results[item.item_id] = ocr_result

            await asyncio.gather(*[process_video(item) for item in video_items])

            # Aggregate pipeline status for STT/OCR
            all_stt = list(stt_results.values())
            all_ocr = list(ocr_results.values())

            def aggregate_status(results):
                if not results:
                    return "skipped"
                statuses = {r.status for r in results}
                if "success" in statuses and len(statuses) == 1:
                    return "success"
                if "failed" in statuses and "success" not in statuses and "partial" not in statuses:
                    return "failed"
                return "partial"

            pipeline_status.stt = aggregate_status(all_stt)
            pipeline_status.ocr = aggregate_status(all_ocr)

            total_segments = sum(len(r.segments) for r in all_stt)
            total_ocr = sum(len(r.texts) for r in all_ocr)
            content_stats.transcript_segments = total_segments
            content_stats.ocr_fragments = total_ocr

            await analysis_repo.log_stage(job_id, "stt", pipeline_status.stt)
            await analysis_repo.log_stage(job_id, "ocr", pipeline_status.ocr)

            if pipeline_status.stt == "failed" and pipeline_status.ocr == "failed":
                warnings.append("STT и OCR недоступны. Анализ только по текстовым данным.")

            # --- 4. LLM analysis ---
            await analysis_repo.log_stage(job_id, "llm", "running")
            result = await llm_service.analyze(
                handle=handle,
                raw_input=raw_input,
                analysis_window=analysis_window,
                items=items,
                stt_results=stt_results,
                ocr_results=ocr_results,
                content_stats=content_stats,
                pipeline_status=pipeline_status,
                warnings=warnings,
            )
            await analysis_repo.log_stage(job_id, "llm", result.pipeline_status.llm)

            # --- 5. Save to DB and cache ---
            await analysis_repo.save(job_id, result)
            cache = get_cache()
            await cache.set(handle, result.model_dump(mode="json"))

            await job_repo.update_status(
                job_id,
                JobStatusUpdate(status="done", finished_at=datetime.utcnow()),
            )
            logger.info("job_done", job_id=job_id_str, handle=handle)

            # --- 6. Notify Telegram ---
            bot = ctx.get("bot")
            if bot:
                from app.bot.formatters import format_summary
                text = format_summary(result)
                from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
                kb = InlineKeyboardMarkup(
                    inline_keyboard=[[
                        InlineKeyboardButton(
                            text="📄 Получить JSON",
                            callback_data=f"json:{job_id_str}",
                        )
                    ]]
                )
                await bot.send_message(chat_id=job.chat_id, text=text, reply_markup=kb, parse_mode="HTML")

        except Exception as exc:
            logger.error("job_failed", job_id=job_id_str, error=str(exc))
            await job_repo.update_status(
                job_id,
                JobStatusUpdate(status="failed", error=str(exc), finished_at=datetime.utcnow()),
            )
            bot = ctx.get("bot")
            if bot:
                await bot.send_message(
                    chat_id=job.chat_id,
                    text=f"❌ Анализ завершился с ошибкой:\n<code>{exc}</code>",
                    parse_mode="HTML",
                )
