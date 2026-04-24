"""LLM orchestrator — calls OpenAI with function-calling for strict JSON output.

Provider: OpenAI-compatible API (openai SDK).
Fallback: if OPENAI_API_KEY is not set or LLM_MOCK=true — returns a mock result
so the pipeline can run end-to-end without a real API key.
"""
import json
import os
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.analysis import (
    AnalysisResult,
    AnalysisWindow,
    BloggerInfo,
    ContentStats,
    EntityFact,
    EvidenceRef,
    FrequentWord,
    MoodInfo,
    PipelineStatus,
    Summary24h,
    SpeechStyle,
)
from app.schemas.collector import ContentItem
from app.services.ocr import OCRResult
from app.services.stt import STTResult

logger = get_logger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "analysis_v1.txt"

# OpenAI function-calling tool definition
ANALYSIS_FUNCTION: dict[str, Any] = {
    "name": "save_analysis",
    "description": "Сохранить структурированный анализ контента блогера",
    "parameters": {
        "type": "object",
        "required": ["summary_24h", "entities_and_facts", "speech_style"],
        "properties": {
            "summary_24h": {
                "type": "object",
                "required": ["main_topics", "key_events", "mood", "life_triggers", "repeated_themes"],
                "properties": {
                    "main_topics": {"type": "array", "items": {"type": "string"}},
                    "key_events": {"type": "array", "items": {"type": "string"}},
                    "mood": {
                        "type": "object",
                        "required": ["labels", "description"],
                        "properties": {
                            "labels": {"type": "array", "items": {"type": "string"}},
                            "description": {"type": "string"},
                        },
                    },
                    "life_triggers": {"type": "array", "items": {"type": "string"}},
                    "repeated_themes": {"type": "array", "items": {"type": "string"}},
                },
            },
            "entities_and_facts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["fact", "evidence"],
                    "properties": {
                        "fact": {"type": "string"},
                        "evidence": {
                            "type": "object",
                            "required": ["source_item_id", "quote_or_ocr"],
                            "properties": {
                                "source_item_id": {"type": "string"},
                                "timecode": {"type": ["string", "null"]},
                                "quote_or_ocr": {"type": "string"},
                            },
                        },
                    },
                },
            },
            "speech_style": {
                "type": "object",
                "required": [
                    "frequent_words",
                    "filler_phrases",
                    "tone_labels",
                    "avg_phrase_length_words",
                    "audience_addressing_style",
                    "local_slang",
                ],
                "properties": {
                    "frequent_words": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["word", "count"],
                            "properties": {
                                "word": {"type": "string"},
                                "count": {"type": "integer"},
                            },
                        },
                    },
                    "filler_phrases": {"type": "array", "items": {"type": "string"}},
                    "tone_labels": {"type": "array", "items": {"type": "string"}},
                    "avg_phrase_length_words": {"type": ["number", "null"]},
                    "audience_addressing_style": {"type": "string"},
                    "local_slang": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    },
}


def _build_content_block(
    items: list[ContentItem],
    stt_results: dict[str, STTResult],
    ocr_results: dict[str, OCRResult],
) -> str:
    parts: list[str] = []
    for item in items:
        block = [
            f"--- [{item.item_id}] {item.content_type.upper()} | "
            f"{item.taken_at.strftime('%Y-%m-%d %H:%M')} ---"
        ]
        if item.caption:
            block.append(f"Caption: {item.caption}")

        stt = stt_results.get(item.item_id)
        if stt and stt.segments:
            block.append("Транскрипт:")
            for seg in stt.segments[:30]:
                block.append(f"  [{seg.timecode()}] {seg.text.strip()}")

        ocr = ocr_results.get(item.item_id)
        if ocr and ocr.texts:
            block.append("OCR-текст с кадров:")
            block.append("  " + " | ".join(ocr.texts[:20]))

        parts.append("\n".join(block))

    return "\n\n".join(parts) if parts else "Контент отсутствует."


def _mock_result(
    raw_input: str,
    handle: str,
    analysis_window: AnalysisWindow,
    content_stats: ContentStats,
    pipeline_status: PipelineStatus,
    warnings: list[str],
) -> AnalysisResult:
    """Return a clearly-marked mock result when LLM_MOCK=true or no API key."""
    pipeline_status.llm = "partial"
    warnings.append("LLM работает в MOCK-режиме. Результат тестовый, не реальный.")
    return AnalysisResult(
        blogger=BloggerInfo(input=raw_input, resolved_handle=handle),
        analysis_window=analysis_window,
        content_stats=content_stats,
        summary_24h=Summary24h(
            main_topics=["[MOCK] тема 1", "[MOCK] тема 2"],
            key_events=["[MOCK] ключевое событие"],
            mood=MoodInfo(labels=["нейтральный"], description="[MOCK] тестовое настроение"),
            life_triggers=["[MOCK] триггер"],
            repeated_themes=["[MOCK] повторяющаяся тема"],
        ),
        entities_and_facts=[],
        speech_style=SpeechStyle(
            frequent_words=[FrequentWord(word="[mock]", count=1)],
            filler_phrases=[],
            tone_labels=["[MOCK]"],
            avg_phrase_length_words=None,
            audience_addressing_style="[MOCK]",
            local_slang=[],
        ),
        pipeline_status=pipeline_status,
        warnings=warnings,
    )


async def analyze(
    handle: str,
    raw_input: str,
    analysis_window: AnalysisWindow,
    items: list[ContentItem],
    stt_results: dict[str, STTResult],
    ocr_results: dict[str, OCRResult],
    content_stats: ContentStats,
    pipeline_status: PipelineStatus,
    warnings: list[str],
) -> AnalysisResult:
    # ── Mock mode ──────────────────────────────────────────────────────────
    if settings.llm_mock or os.getenv("LLM_MOCK", "false").lower() in ("true", "1", "yes"):
        logger.info("llm_mock_mode_enabled")
        return _mock_result(
            raw_input, handle, analysis_window,
            content_stats, pipeline_status, warnings,
        )

    # ── Real OpenAI call ────────────────────────────────────────────────────
    try:
        from openai import AsyncOpenAI
    except ImportError:
        pipeline_status.llm = "failed"
        warnings.append("openai пакет не установлен. Добавь openai в requirements.txt.")
        return _mock_result(
            raw_input, handle, analysis_window,
            content_stats, pipeline_status, warnings,
        )

    prompt_template = PROMPT_PATH.read_text(encoding="utf-8")
    content_block = _build_content_block(items, stt_results, ocr_results)

    user_prompt = prompt_template.format(
        handle=handle,
        window_from=analysis_window.from_.strftime("%Y-%m-%d %H:%M"),
        window_to=analysis_window.to.strftime("%Y-%m-%d %H:%M"),
        items_count=content_stats.items_count,
        content_block=content_block,
    )

    client = AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url or None,
    )

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.2,
            max_tokens=4096,
            tools=[{"type": "function", "function": ANALYSIS_FUNCTION}],
            tool_choice={"type": "function", "function": {"name": "save_analysis"}},
            messages=[{"role": "user", "content": user_prompt}],
        )

        tool_call = response.choices[0].message.tool_calls
        if not tool_call:
            raise ValueError("OpenAI did not return a tool_call")

        raw: dict[str, Any] = json.loads(tool_call[0].function.arguments)
        logger.info(
            "llm_response_received",
            finish_reason=response.choices[0].finish_reason,
            model=response.model,
        )

    except Exception as exc:
        logger.error("llm_failed", error=str(exc))
        pipeline_status.llm = "failed"
        warnings.append(f"LLM анализ завершился с ошибкой: {exc}")
        return AnalysisResult(
            blogger=BloggerInfo(input=raw_input, resolved_handle=handle),
            analysis_window=analysis_window,
            content_stats=content_stats,
            pipeline_status=pipeline_status,
            warnings=warnings,
        )

    # ── Parse structured response ───────────────────────────────────────────
    try:
        summary_raw = raw["summary_24h"]
        summary = Summary24h(
            main_topics=summary_raw.get("main_topics", []),
            key_events=summary_raw.get("key_events", []),
            mood=MoodInfo(**summary_raw.get("mood", {})),
            life_triggers=summary_raw.get("life_triggers", []),
            repeated_themes=summary_raw.get("repeated_themes", []),
        )

        entities = [
            EntityFact(
                fact=e["fact"],
                evidence=EvidenceRef(
                    source_item_id=e["evidence"]["source_item_id"],
                    timecode=e["evidence"].get("timecode"),
                    quote_or_ocr=e["evidence"].get("quote_or_ocr", ""),
                ),
            )
            for e in raw.get("entities_and_facts", [])
        ]

        style_raw = raw["speech_style"]
        speech_style = SpeechStyle(
            frequent_words=[FrequentWord(**w) for w in style_raw.get("frequent_words", [])],
            filler_phrases=style_raw.get("filler_phrases", []),
            tone_labels=style_raw.get("tone_labels", []),
            avg_phrase_length_words=style_raw.get("avg_phrase_length_words"),
            audience_addressing_style=style_raw.get("audience_addressing_style", ""),
            local_slang=style_raw.get("local_slang", []),
        )

        pipeline_status.llm = "success"

        return AnalysisResult(
            blogger=BloggerInfo(input=raw_input, resolved_handle=handle),
            analysis_window=analysis_window,
            content_stats=content_stats,
            summary_24h=summary,
            entities_and_facts=entities,
            speech_style=speech_style,
            pipeline_status=pipeline_status,
            warnings=warnings,
        )

    except Exception as exc:
        logger.error("llm_parse_failed", error=str(exc), raw=str(raw)[:500])
        pipeline_status.llm = "partial"
        warnings.append(f"Ошибка разбора ответа LLM: {exc}")
        return AnalysisResult(
            blogger=BloggerInfo(input=raw_input, resolved_handle=handle),
            analysis_window=analysis_window,
            content_stats=content_stats,
            pipeline_status=pipeline_status,
            warnings=warnings,
        )
