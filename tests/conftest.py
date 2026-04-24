"""Shared pytest fixtures."""
import uuid
from datetime import datetime, timezone

import pytest

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


@pytest.fixture
def now():
    return datetime.now(tz=timezone.utc)


@pytest.fixture
def analysis_window(now):
    from datetime import timedelta
    return AnalysisWindow(**{"from": now - timedelta(hours=24), "to": now})


@pytest.fixture
def sample_result(analysis_window):
    return AnalysisResult(
        blogger=BloggerInfo(input="@test_user", resolved_handle="test_user"),
        analysis_window=analysis_window,
        content_stats=ContentStats(
            items_count=3,
            videos_count=2,
            images_count=1,
            transcript_segments=15,
            ocr_fragments=8,
        ),
        summary_24h=Summary24h(
            main_topics=["продуктивность", "утренняя рутина"],
            key_events=["Вышел новый рил о лайфхаках"],
            mood=MoodInfo(labels=["энергичный", "позитивный"], description="Бодрый настрой"),
            life_triggers=["работа над собой"],
            repeated_themes=["саморазвитие", "режим дня"],
        ),
        entities_and_facts=[
            EntityFact(
                fact="Блогер встаёт в 6 утра каждый день",
                evidence=EvidenceRef(
                    source_item_id="test_user_reel_002",
                    timecode="00:05-00:12",
                    quote_or_ocr="Встаю в 6 утра каждый день",
                ),
            )
        ],
        speech_style=SpeechStyle(
            frequent_words=[
                FrequentWord(word="продуктивность", count=5),
                FrequentWord(word="понимаете", count=3),
            ],
            filler_phrases=["понимаете", "вот"],
            tone_labels=["разговорный", "мотивационный"],
            avg_phrase_length_words=8.5,
            audience_addressing_style="на «ты», дружески",
            local_slang=["база", "лайфхак"],
        ),
        pipeline_status=PipelineStatus(
            collector="success",
            stt="success",
            ocr="partial",
            llm="success",
        ),
        warnings=["OCR: часть кадров не распознана"],
    )


@pytest.fixture
def mock_content_items(now):
    return [
        ContentItem(
            item_id="test_reel_001",
            content_type="video",
            url="https://www.instagram.com/reel/test001/",
            caption="Тестовый caption видео",
            taken_at=now,
            media_urls=["https://example.com/video.mp4"],
            duration_seconds=30.0,
        ),
        ContentItem(
            item_id="test_post_002",
            content_type="image",
            url="https://www.instagram.com/p/test002/",
            caption="Тестовый caption фото",
            taken_at=now,
            media_urls=["https://example.com/image.jpg"],
        ),
    ]
