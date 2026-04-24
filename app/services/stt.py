"""Speech-to-text via faster-whisper. Returns timestamped segments."""
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

STTStatus = Literal["success", "partial", "failed", "skipped"]


@dataclass
class STTSegment:
    start: float
    end: float
    text: str

    def timecode(self) -> str:
        def fmt(s: float) -> str:
            m, sec = divmod(int(s), 60)
            return f"{m:02d}:{sec:02d}"
        return f"{fmt(self.start)}-{fmt(self.end)}"


@dataclass
class STTResult:
    status: STTStatus
    segments: list[STTSegment]
    language: str | None
    error: str | None = None

    @property
    def full_text(self) -> str:
        return " ".join(s.text.strip() for s in self.segments)


_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel(
            settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
        logger.info("whisper_model_loaded", model=settings.whisper_model)
    return _model


async def transcribe(audio_path: str | Path) -> STTResult:
    import asyncio

    path = Path(audio_path)
    if not path.exists():
        return STTResult(status="skipped", segments=[], language=None, error="audio file not found")

    try:
        return await asyncio.get_event_loop().run_in_executor(
            None, _transcribe_sync, path
        )
    except Exception as exc:
        logger.error("stt_error", path=str(path), error=str(exc))
        return STTResult(status="failed", segments=[], language=None, error=str(exc))


def _transcribe_sync(path: Path) -> STTResult:
    try:
        model = _get_model()
        segments_gen, info = model.transcribe(
            str(path),
            beam_size=5,
            word_timestamps=False,
            vad_filter=True,
        )
        segments = [
            STTSegment(start=s.start, end=s.end, text=s.text)
            for s in segments_gen
        ]
        logger.info("stt_done", segments=len(segments), language=info.language)
        status: STTStatus = "success" if segments else "partial"
        return STTResult(status=status, segments=segments, language=info.language)
    except Exception as exc:
        logger.error("stt_sync_error", error=str(exc))
        return STTResult(status="failed", segments=[], language=None, error=str(exc))
