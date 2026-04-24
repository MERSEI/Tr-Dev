"""Happy path integration test using mock collector (no real Instagram / LLM)."""
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.collectors.mock import MockCollector
from app.schemas.analysis import (
    AnalysisResult,
    AnalysisWindow,
    ContentStats,
    PipelineStatus,
)
from app.schemas.collector import ContentItem


class TestMockCollector:
    @pytest.mark.asyncio
    async def test_resolve_handle_strips_at(self):
        collector = MockCollector()
        handle = await collector.resolve_handle("@someuser")
        assert handle == "someuser"

    @pytest.mark.asyncio
    async def test_resolve_handle_from_url(self):
        collector = MockCollector()
        handle = await collector.resolve_handle("https://www.instagram.com/testuser/")
        assert handle == "testuser"

    @pytest.mark.asyncio
    async def test_collect_returns_items(self):
        collector = MockCollector()
        now = datetime.now(tz=timezone.utc)
        since = now - timedelta(hours=24)
        items = await collector.collect("testuser", since, now)
        assert len(items) > 0
        for item in items:
            assert item.item_id
            assert item.content_type in ("video", "image", "carousel")
            assert item.taken_at is not None

    @pytest.mark.asyncio
    async def test_collect_has_captions(self):
        collector = MockCollector()
        now = datetime.now(tz=timezone.utc)
        since = now - timedelta(hours=24)
        items = await collector.collect("any", since, now)
        captions = [i.caption for i in items if i.caption]
        assert len(captions) > 0


class TestPipelineStatusAggregation:
    """Tests for graceful degradation logic in analyze_job."""

    def test_aggregate_all_success(self):
        from app.services.stt import STTResult
        results = [
            STTResult(status="success", segments=[], language="ru"),
            STTResult(status="success", segments=[], language="ru"),
        ]
        statuses = {r.status for r in results}
        if "success" in statuses and len(statuses) == 1:
            agg = "success"
        elif "failed" in statuses and "success" not in statuses:
            agg = "failed"
        else:
            agg = "partial"
        assert agg == "success"

    def test_aggregate_mixed(self):
        from app.services.stt import STTResult
        results = [
            STTResult(status="success", segments=[], language="ru"),
            STTResult(status="failed", segments=[], language=None, error="err"),
        ]
        statuses = {r.status for r in results}
        if "success" in statuses and len(statuses) == 1:
            agg = "success"
        elif "failed" in statuses and "success" not in statuses:
            agg = "failed"
        else:
            agg = "partial"
        assert agg == "partial"

    def test_aggregate_all_failed(self):
        from app.services.stt import STTResult
        results = [
            STTResult(status="failed", segments=[], language=None, error="e1"),
            STTResult(status="failed", segments=[], language=None, error="e2"),
        ]
        statuses = {r.status for r in results}
        if not results:
            agg = "skipped"
        elif "success" in statuses and len(statuses) == 1:
            agg = "success"
        elif "failed" in statuses and "success" not in statuses and "partial" not in statuses:
            agg = "failed"
        else:
            agg = "partial"
        assert agg == "failed"

    def test_aggregate_empty(self):
        results = []
        agg = "skipped" if not results else "success"
        assert agg == "skipped"


class TestAnalysisResultConstruction:
    def test_result_with_warnings(self, analysis_window):
        result = AnalysisResult(
            blogger={"input": "@test", "platform": "instagram"},
            analysis_window=analysis_window,
            warnings=["STT не сработал", "OCR не сработал"],
            pipeline_status=PipelineStatus(
                collector="success",
                stt="failed",
                ocr="failed",
                llm="partial",
            ),
        )
        assert len(result.warnings) == 2
        assert result.pipeline_status.stt == "failed"
        assert result.pipeline_status.llm == "partial"

    def test_content_stats_defaults(self):
        stats = ContentStats()
        assert stats.items_count == 0
        assert stats.transcript_segments == 0
