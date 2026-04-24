"""Schema validation tests."""
import json
from datetime import datetime, timedelta, timezone

import pytest

from app.schemas.analysis import (
    AnalysisResult,
    AnalysisWindow,
    BloggerInfo,
    ContentStats,
    MoodInfo,
    PipelineStatus,
    Summary24h,
    SpeechStyle,
    FrequentWord,
)
from app.schemas.collector import ContentItem
from app.schemas.job import JobCreate, JobRead, JobStatus


class TestAnalysisResult:
    def test_minimal_result_is_valid(self, analysis_window):
        result = AnalysisResult(
            blogger=BloggerInfo(input="@test"),
            analysis_window=analysis_window,
        )
        assert result.blogger.platform == "instagram"
        assert result.content_stats.items_count == 0
        assert result.pipeline_status.llm == "failed"

    def test_full_result_roundtrip(self, sample_result):
        dumped = sample_result.model_dump(mode="json")
        restored = AnalysisResult.model_validate(dumped)
        assert restored.blogger.resolved_handle == "test_user"
        assert len(restored.summary_24h.main_topics) == 2
        assert len(restored.entities_and_facts) == 1
        assert restored.speech_style.avg_phrase_length_words == pytest.approx(8.5)

    def test_result_json_serializable(self, sample_result):
        dumped = sample_result.model_dump(mode="json")
        raw = json.dumps(dumped, ensure_ascii=False)
        assert "test_user" in raw
        assert "продуктивность" in raw

    def test_analysis_window_alias(self):
        now = datetime.now(tz=timezone.utc)
        w = AnalysisWindow(**{"from": now - timedelta(hours=24), "to": now})
        assert w.from_ < w.to

    def test_pipeline_status_defaults(self):
        ps = PipelineStatus()
        assert ps.collector == "failed"
        assert ps.stt == "skipped"
        assert ps.ocr == "skipped"
        assert ps.llm == "failed"

    def test_pipeline_status_all_values(self):
        ps = PipelineStatus(
            collector="success",
            stt="partial",
            ocr="failed",
            llm="success",
        )
        assert ps.collector == "success"
        assert ps.stt == "partial"

    def test_frequent_word(self):
        w = FrequentWord(word="база", count=7)
        assert w.word == "база"
        assert w.count == 7


class TestContentItem:
    def test_video_item(self):
        from datetime import datetime, timezone
        item = ContentItem(
            item_id="abc123",
            content_type="video",
            url="https://instagram.com/reel/abc123/",
            taken_at=datetime.now(tz=timezone.utc),
            media_urls=["https://example.com/video.mp4"],
            duration_seconds=45.0,
        )
        assert item.platform == "instagram"
        assert item.local_path is None

    def test_image_item_defaults(self):
        from datetime import datetime, timezone
        item = ContentItem(
            item_id="img001",
            content_type="image",
            url="https://instagram.com/p/img001/",
            taken_at=datetime.now(tz=timezone.utc),
        )
        assert item.media_urls == []
        assert item.duration_seconds is None


class TestJobSchemas:
    def test_job_create(self):
        job = JobCreate(input_handle="@user", chat_id=123456789)
        assert job.message_id is None

    def test_job_status_literals(self):
        for status in ("pending", "running", "done", "failed"):
            job = JobCreate(input_handle="@x", chat_id=1)
            assert job.input_handle == "@x"
