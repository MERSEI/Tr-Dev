"""Formatter tests — verifies summary is built from AnalysisResult, not ad-hoc."""
import pytest

from app.bot.formatters import format_summary
from app.schemas.analysis import AnalysisResult, BloggerInfo, AnalysisWindow, PipelineStatus


class TestFormatSummary:
    def test_contains_handle(self, sample_result):
        text = format_summary(sample_result)
        assert "test_user" in text

    def test_contains_block_headers(self, sample_result):
        text = format_summary(sample_result)
        assert "A. Краткая сводка" in text
        assert "B. Ключевые факты" in text
        assert "C. Словарь и стиль" in text

    def test_contains_topics(self, sample_result):
        text = format_summary(sample_result)
        assert "продуктивность" in text
        assert "утренняя рутина" in text

    def test_contains_mood(self, sample_result):
        text = format_summary(sample_result)
        assert "энергичный" in text

    def test_contains_fact(self, sample_result):
        text = format_summary(sample_result)
        assert "Блогер встаёт в 6 утра" in text

    def test_contains_frequent_words(self, sample_result):
        text = format_summary(sample_result)
        assert "продуктивность" in text

    def test_pipeline_status_shown(self, sample_result):
        text = format_summary(sample_result)
        assert "Статус пайплайна" in text
        assert "✅" in text  # success status

    def test_warnings_shown(self, sample_result):
        text = format_summary(sample_result)
        assert "OCR: часть кадров не распознана" in text

    def test_minimal_result_does_not_crash(self, analysis_window):
        minimal = AnalysisResult(
            blogger=BloggerInfo(input="@nobody"),
            analysis_window=analysis_window,
        )
        text = format_summary(minimal)
        assert "nobody" in text
        assert "Статус пайплайна" in text

    def test_all_failed_pipeline(self, analysis_window):
        result = AnalysisResult(
            blogger=BloggerInfo(input="@x", resolved_handle="x"),
            analysis_window=analysis_window,
            pipeline_status=PipelineStatus(
                collector="failed", stt="failed", ocr="failed", llm="failed"
            ),
            warnings=["Полная ошибка пайплайна"],
        )
        text = format_summary(result)
        assert "❌" in text
        assert "Полная ошибка пайплайна" in text

    def test_is_html_safe(self, sample_result):
        text = format_summary(sample_result)
        # Should use HTML tags, not markdown
        assert "<b>" in text
