"""Extracts audio track from video files using ffmpeg."""
import asyncio
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)


async def extract_audio(video_path: str | Path) -> Path | None:
    video = Path(video_path)
    if not video.exists():
        logger.warning("audio_extract_missing_video", path=str(video))
        return None

    audio_path = video.with_suffix(".wav")
    if audio_path.exists():
        return audio_path

    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(audio_path),
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            logger.error(
                "ffmpeg_audio_failed",
                path=str(video),
                stderr=stderr.decode(errors="replace"),
            )
            return None
        logger.info("audio_extracted", path=str(audio_path))
        return audio_path
    except FileNotFoundError:
        logger.error("ffmpeg_not_found")
        return None
    except Exception as exc:
        logger.error("audio_extract_error", error=str(exc))
        return None
