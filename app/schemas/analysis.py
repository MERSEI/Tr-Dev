from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class BloggerInfo(BaseModel):
    input: str
    platform: str = "instagram"
    resolved_handle: str | None = None


class AnalysisWindow(BaseModel):
    from_: datetime = Field(..., alias="from")
    to: datetime

    model_config = {"populate_by_name": True}


class ContentStats(BaseModel):
    items_count: int = 0
    videos_count: int = 0
    images_count: int = 0
    transcript_segments: int = 0
    ocr_fragments: int = 0


class MoodInfo(BaseModel):
    labels: list[str] = Field(default_factory=list)
    description: str = ""


class Summary24h(BaseModel):
    main_topics: list[str] = Field(default_factory=list)
    key_events: list[str] = Field(default_factory=list)
    mood: MoodInfo = Field(default_factory=MoodInfo)
    life_triggers: list[str] = Field(default_factory=list)
    repeated_themes: list[str] = Field(default_factory=list)


class EvidenceRef(BaseModel):
    source_item_id: str
    timecode: str | None = None
    quote_or_ocr: str = ""


class EntityFact(BaseModel):
    fact: str
    evidence: EvidenceRef


class FrequentWord(BaseModel):
    word: str
    count: int


class SpeechStyle(BaseModel):
    frequent_words: list[FrequentWord] = Field(default_factory=list)
    filler_phrases: list[str] = Field(default_factory=list)
    tone_labels: list[str] = Field(default_factory=list)
    avg_phrase_length_words: float | None = None
    audience_addressing_style: str = ""
    local_slang: list[str] = Field(default_factory=list)


PipelineStageStatus = Literal["success", "partial", "failed", "skipped"]


class PipelineStatus(BaseModel):
    collector: PipelineStageStatus = "failed"
    stt: PipelineStageStatus = "skipped"
    ocr: PipelineStageStatus = "skipped"
    llm: PipelineStageStatus = "failed"


class AnalysisResult(BaseModel):
    blogger: BloggerInfo
    analysis_window: AnalysisWindow
    content_stats: ContentStats = Field(default_factory=ContentStats)
    summary_24h: Summary24h = Field(default_factory=Summary24h)
    entities_and_facts: list[EntityFact] = Field(default_factory=list)
    speech_style: SpeechStyle = Field(default_factory=SpeechStyle)
    pipeline_status: PipelineStatus = Field(default_factory=PipelineStatus)
    warnings: list[str] = Field(default_factory=list)
