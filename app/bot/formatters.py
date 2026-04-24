"""Builds human-readable Telegram messages from validated AnalysisResult."""
from app.schemas.analysis import AnalysisResult, PipelineStatus

_STATUS_EMOJI = {
    "success": "✅",
    "partial": "⚠️",
    "failed": "❌",
    "skipped": "⏭",
}


def _status(s: str) -> str:
    return _STATUS_EMOJI.get(s, "❓")


def format_summary(result: AnalysisResult) -> str:
    r = result
    b = r.blogger
    w = r.analysis_window
    s = r.summary_24h
    ss = r.speech_style
    ps = r.pipeline_status

    lines: list[str] = []

    # Header
    handle = b.resolved_handle or b.input
    lines.append(f"<b>📊 Анализ @{handle} (Instagram)</b>")
    lines.append(
        f"🕐 {w.from_.strftime('%d.%m %H:%M')} — {w.to.strftime('%d.%m %H:%M')}"
    )
    stats = r.content_stats
    lines.append(
        f"📦 Контент: {stats.items_count} ед. "
        f"({stats.videos_count} видео, {stats.images_count} фото)"
    )
    lines.append("")

    # Block A — Summary
    lines.append("<b>🔹 A. Краткая сводка за 24 часа</b>")
    if s.main_topics:
        lines.append("<b>Главные темы:</b>")
        for t in s.main_topics:
            lines.append(f"  • {t}")
    if s.key_events:
        lines.append("<b>Ключевые события:</b>")
        for e in s.key_events:
            lines.append(f"  • {e}")
    if s.mood.labels:
        mood_str = ", ".join(s.mood.labels)
        lines.append(f"<b>Настроение:</b> {mood_str}")
        if s.mood.description:
            lines.append(f"  {s.mood.description}")
    if s.repeated_themes:
        lines.append("<b>Повторяющиеся темы:</b>")
        for t in s.repeated_themes[:5]:
            lines.append(f"  • {t}")
    lines.append("")

    # Block B — Entities & Facts
    lines.append("<b>🔹 B. Ключевые факты</b>")
    if r.entities_and_facts:
        for ef in r.entities_and_facts[:8]:
            ev = ef.evidence
            tc = f" [{ev.timecode}]" if ev.timecode else ""
            lines.append(f"  • {ef.fact}")
            if ev.quote_or_ocr:
                lines.append(f"    <i>«{ev.quote_or_ocr[:120]}»{tc}</i>")
    else:
        lines.append("  Данных недостаточно.")
    lines.append("")

    # Block C — Speech Style
    lines.append("<b>🔹 C. Словарь и стиль</b>")
    if ss.frequent_words:
        top = ", ".join(f"{w.word} ({w.count})" for w in ss.frequent_words[:8])
        lines.append(f"<b>Частые слова:</b> {top}")
    if ss.filler_phrases:
        lines.append(f"<b>Слова-паразиты:</b> {', '.join(ss.filler_phrases[:6])}")
    if ss.tone_labels:
        lines.append(f"<b>Тон:</b> {', '.join(ss.tone_labels)}")
    if ss.audience_addressing_style:
        lines.append(f"<b>Обращение к аудитории:</b> {ss.audience_addressing_style}")
    if ss.local_slang:
        lines.append(f"<b>Сленг:</b> {', '.join(ss.local_slang[:6])}")
    if ss.avg_phrase_length_words:
        lines.append(f"<b>Средняя длина фразы:</b> {ss.avg_phrase_length_words:.1f} слов")
    lines.append("")

    # Pipeline status
    lines.append("<b>⚙️ Статус пайплайна</b>")
    lines.append(
        f"  Сбор: {_status(ps.collector)} | "
        f"STT: {_status(ps.stt)} | "
        f"OCR: {_status(ps.ocr)} | "
        f"LLM: {_status(ps.llm)}"
    )

    if r.warnings:
        lines.append("")
        lines.append("<b>⚠️ Предупреждения:</b>")
        for w_msg in r.warnings:
            lines.append(f"  • {w_msg}")

    return "\n".join(lines)
