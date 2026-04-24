"""OCR via easyocr — reads text from keyframe images."""
import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

OCRStatus = Literal["success", "partial", "failed", "skipped"]


@dataclass
class OCRResult:
    status: OCRStatus
    texts: list[str]
    error: str | None = None

    @property
    def combined_text(self) -> str:
        return " ".join(t.strip() for t in self.texts if t.strip())


_reader = None


def _get_reader():
    global _reader
    if _reader is None:
        import easyocr
        _reader = easyocr.Reader(
            settings.ocr_languages,
            gpu=False,
            verbose=False,
        )
        logger.info("easyocr_reader_loaded", languages=settings.ocr_languages)
    return _reader


async def ocr_frames(frame_paths: list[Path]) -> OCRResult:
    if not frame_paths:
        return OCRResult(status="skipped", texts=[], error="no frames provided")

    try:
        return await asyncio.get_event_loop().run_in_executor(
            None, _ocr_sync, frame_paths
        )
    except Exception as exc:
        logger.error("ocr_error", error=str(exc))
        return OCRResult(status="failed", texts=[], error=str(exc))


def _ocr_sync(frame_paths: list[Path]) -> OCRResult:
    try:
        reader = _get_reader()
        texts: list[str] = []
        failed = 0

        for frame in frame_paths:
            if not frame.exists():
                continue
            try:
                results = reader.readtext(str(frame), detail=0, paragraph=True)
                texts.extend(r for r in results if r.strip())
            except Exception as exc:
                logger.warning("ocr_frame_failed", frame=str(frame), error=str(exc))
                failed += 1

        status: OCRStatus
        if not texts and failed > 0:
            status = "failed"
        elif failed > 0:
            status = "partial"
        elif texts:
            status = "success"
        else:
            status = "partial"

        logger.info("ocr_done", texts_extracted=len(texts), frames_failed=failed)
        return OCRResult(status=status, texts=texts)
    except Exception as exc:
        logger.error("ocr_sync_error", error=str(exc))
        return OCRResult(status="failed", texts=[], error=str(exc))
