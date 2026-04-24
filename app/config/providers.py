"""Model and provider settings — single source of truth for AI config."""
from dataclasses import dataclass


@dataclass(frozen=True)
class WhisperConfig:
    model: str = "small"
    device: str = "cpu"
    compute_type: str = "int8"
    vad_filter: bool = True
    beam_size: int = 5


@dataclass(frozen=True)
class OpenAIConfig:
    model: str = "gpt-4o"
    max_tokens: int = 4096
    temperature: float = 0.2


@dataclass(frozen=True)
class OCRConfig:
    languages: tuple[str, ...] = ("ru", "en")
    gpu: bool = False


WHISPER = WhisperConfig()
OPENAI = OpenAIConfig()
OCR = OCRConfig()
