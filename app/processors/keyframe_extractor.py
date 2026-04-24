"""Extracts keyframes from video files using ffmpeg (1 frame per 5 seconds)."""
import asyncio
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

FRAME_INTERVAL_SECONDS = 5


async def extract_keyframes(video_path: str | Path) -> list[Path]:
    video = Path(video_path)
    if not video.exists():
        logger.warning("keyframe_missing_video", path=str(video))
        return []

    frames_dir = video.parent / f"{video.stem}_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    existing = sorted(frames_dir.glob("frame_*.jpg"))
    if existing:
        return existing

    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video),
        "-vf", f"fps=1/{FRAME_INTERVAL_SECONDS}",
        "-q:v", "3",
        str(frames_dir / "frame_%04d.jpg"),
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
                "ffmpeg_keyframe_failed",
                path=str(video),
                stderr=stderr.decode(errors="replace"),
            )
            return []
        frames = sorted(frames_dir.glob("frame_*.jpg"))
        logger.info("keyframes_extracted", count=len(frames), video=str(video))
        return frames
    except FileNotFoundError:
        logger.error("ffmpeg_not_found")
        return []
    except Exception as exc:
        logger.error("keyframe_extract_error", error=str(exc))
        return []
