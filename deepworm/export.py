"""Unified research export hub.

Provides a single interface to export research reports to multiple
formats: Markdown, HTML, JSON, Notion, and plain text.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ExportFormat(str, Enum):
    """Supported export formats."""

    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"
    TEXT = "text"
    NOTION = "notion"
    CSV = "csv"


@dataclass
class ExportOptions:
    """Options controlling export behavior."""

    include_toc: bool = True
    include_metadata: bool = True
    include_sources: bool = True
    include_timestamps: bool = False
    max_heading_depth: int = 3
    wrap_width: int = 80  # For plain text
    css_class: str = "deepworm-report"

    def to_dict(self) -> dict[str, Any]:
        return {
            "include_toc": self.include_toc,
            "include_metadata": self.include_metadata,
            "include_sources": self.include_sources,
            "include_timestamps": self.include_timestamps,
            "max_heading_depth": self.max_heading_depth,
            "wrap_width": self.wrap_width,
            "css_class": self.css_class,
        }


@dataclass
class ExportResult:
    """Result of an export operation."""

    content: str
    format: ExportFormat
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def size_bytes(self) -> int:
        return len(self.content.encode("utf-8"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": self.format.value,
            "size_bytes": self.size_bytes,
            "metadata": self.metadata,
            "warnings": self.warnings,
        }


def export_report(
    markdown: str,
    fmt: ExportFormat = ExportFormat.MARKDOWN,
    title: str = "",
    options: Optional[ExportOptions] = None,
) -> ExportResult:
    """Export a research report to a specified format.

    Args:
        markdown: Source markdown content.
        fmt: Target export format.
        title: Report title (auto-detected from H1 if empty).
        options: Export options.

    Returns:
        ExportResult with converted content.
    """
    opts = options or ExportOptions()

    if not title:
        title = _extract_title(markdown)

    metadata = {"title": title, "format": fmt.value}

    if fmt == ExportFormat.MARKDOWN:
        content = _export_markdown(markdown, title, opts)
    elif fmt == ExportFormat.HTML:
        content = _export_html(markdown, title, opts)
    elif fmt == ExportFormat.JSON:
        content = _export_json(markdown, title, opts)
    elif fmt == ExportFormat.TEXT:
        content = _export_text(markdown, title, opts)
    elif fmt == ExportFormat.NOTION:
        content = _export_notion(markdown, title, opts)
    elif fmt == ExportFormat.CSV:
        content = _export_csv(markdown, title, opts)
    else:
        content = markdown

    return ExportResult(
        content=content,
        format=fmt,
        metadata=metadata,
    )


def batch_export(
    markdown: str,
    formats: list[ExportFormat],
    title: str = "",
    options: Optional[ExportOptions] = None,
) -> dict[ExportFormat, ExportResult]:
    """Export to multiple formats at once.

    Args:
        markdown: Source markdown content.
        formats: List of target formats.
        title: Report title.
        options: Export options.

    Returns:
        Dict mapping format to ExportResult.
    """
    results: dict[ExportFormat, ExportResult] = {}
    for fmt in formats:
        results[fmt] = export_report(markdown, fmt, title, options)
    return results


# ── Format-specific exporters ──


def _export_markdown(text: str, title: str, opts: ExportOptions) -> str:
    """Export as clean markdown."""
    parts: list[str] = []

    if opts.include_metadata and title:
        parts.append(f"# {title}")
        parts.append("")

    if opts.include_toc:
        toc = _generate_toc(text, opts.max_heading_depth)
        if toc:
            parts.append("## Table of Contents")
            parts.append("")
            parts.append(toc)
            parts.append("")

    # Add the body (skip first H1 if we added title)
    body = text
    if opts.include_metadata and title:
        body = re.sub(r"^#\s+.*\n?", "", body, count=1).lstrip()

    parts.append(body)

    return "\n".join(parts)


def _export_html(text: str, title: str, opts: ExportOptions) -> str:
    """Convert markdown to basic HTML."""
    body_html = _markdown_to_html(text)

    parts = [
        "<!DOCTYPE html>",
        "<html lang=\"en\">",
        "<head>",
        "  <meta charset=\"UTF-8\">",
        f"  <title>{_html_escape(title)}</title>",
        "  <style>",
        f"    .{opts.css_class} {{ max-width: 800px; margin: 0 auto; "
        "font-family: -apple-system, sans-serif; line-height: 1.6; padding: 2rem; }}",
        f"    .{opts.css_class} h1 {{ border-bottom: 2px solid #333; padding-bottom: 0.3em; }}",
        f"    .{opts.css_class} h2 {{ border-bottom: 1px solid #ddd; padding-bottom: 0.2em; }}",
        f"    .{opts.css_class} code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }}",
        f"    .{opts.css_class} pre {{ background: #f4f4f4; padding: 1em; border-radius: 5px; overflow-x: auto; }}",
        f"    .{opts.css_class} blockquote {{ border-left: 4px solid #ddd; margin: 0; padding-left: 1em; color: #666; }}",
        f"    .{opts.css_class} table {{ border-collapse: collapse; width: 100%; }}",
        f"    .{opts.css_class} th, .{opts.css_class} td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}",
        f"    .{opts.css_class} th {{ background: #f4f4f4; }}",
        "  </style>",
        "</head>",
        "<body>",
        f"  <div class=\"{opts.css_class}\">",
        f"    {body_html}",
        "  </div>",
        "</body>",
        "</html>",
    ]

    return "\n".join(parts)


def _export_json(text: str, title: str, opts: ExportOptions) -> str:
    """Export as structured JSON."""
    sections = _parse_sections(text)

    data: dict[str, Any] = {
        "title": title,
        "sections": sections,
    }

    if opts.include_metadata:
        data["metadata"] = {
            "word_count": len(text.split()),
            "section_count": len(sections),
        }

    return json.dumps(data, indent=2, ensure_ascii=False)


def _export_text(text: str, title: str, opts: ExportOptions) -> str:
    """Export as plain text with word wrapping."""
    # Strip markdown formatting
    plain = _strip_to_plain(text)

    if opts.include_metadata and title:
        header = title.upper()
        plain = f"{header}\n{'=' * len(header)}\n\n{plain}"

    # Word wrap
    if opts.wrap_width > 0:
        plain = _word_wrap(plain, opts.wrap_width)

    return plain


def _export_notion(text: str, title: str, opts: ExportOptions) -> str:
    """Export as Notion-compatible JSON structure."""
    blocks: list[dict[str, Any]] = []

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue

        heading_match = re.match(r"^(#{1,3})\s+(.+)$", stripped)
        if heading_match:
            level = len(heading_match.group(1))
            blocks.append({
                "type": f"heading_{level}",
                f"heading_{level}": {
                    "rich_text": [{"type": "text", "text": {"content": heading_match.group(2)}}],
                },
            })
        elif stripped.startswith("- ") or stripped.startswith("* "):
            blocks.append({
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": stripped[2:]}}],
                },
            })
        elif re.match(r"^\d+\.\s+", stripped):
            content = re.sub(r"^\d+\.\s+", "", stripped)
            blocks.append({
                "type": "numbered_list_item",
                "numbered_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": content}}],
                },
            })
        elif stripped.startswith("> "):
            blocks.append({
                "type": "quote",
                "quote": {
                    "rich_text": [{"type": "text", "text": {"content": stripped[2:]}}],
                },
            })
        else:
            blocks.append({
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": stripped}}],
                },
            })

    data = {
        "parent": {"type": "page_id", "page_id": ""},
        "properties": {
            "title": [{"type": "text", "text": {"content": title}}],
        },
        "children": blocks,
    }

    return json.dumps(data, indent=2, ensure_ascii=False)


def _export_csv(text: str, title: str, opts: ExportOptions) -> str:
    """Export sections as CSV."""
    sections = _parse_sections(text)
    lines = ["section,level,content"]
    for sec in sections:
        heading = sec.get("heading", "").replace('"', '""')
        level = sec.get("level", 0)
        content = sec.get("content", "").replace('"', '""').replace("\n", " ")
        lines.append(f'"{heading}",{level},"{content}"')
    return "\n".join(lines)


# ── Internal helpers ──


def _extract_title(text: str) -> str:
    """Extract title from first H1 heading."""
    m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else "Untitled Report"


def _generate_toc(text: str, max_depth: int) -> str:
    """Generate table of contents from headings."""
    lines: list[str] = []
    for m in re.finditer(r"^(#{2,6})\s+(.+)$", text, re.MULTILINE):
        level = len(m.group(1))
        if level > max_depth + 1:  # +1 because ToC starts at H2
            continue
        heading = m.group(2).strip()
        anchor = re.sub(r"[^\w\s-]", "", heading.lower()).replace(" ", "-")
        indent = "  " * (level - 2)
        lines.append(f"{indent}- [{heading}](#{anchor})")
    return "\n".join(lines)


def _markdown_to_html(text: str) -> str:
    """Basic markdown to HTML conversion."""
    html = text

    # Code blocks (before inline processing)
    html = re.sub(
        r"```(\w*)\n([\s\S]*?)```",
        lambda m: f"<pre><code class=\"language-{m.group(1)}\">{_html_escape(m.group(2))}</code></pre>",
        html,
    )

    # Inline code
    html = re.sub(r"`([^`]+)`", r"<code>\1</code>", html)

    # Headings
    for i in range(6, 0, -1):
        html = re.sub(
            rf"^{'#' * i}\s+(.+)$",
            rf"<h{i}>\1</h{i}>",
            html,
            flags=re.MULTILINE,
        )

    # Bold and italic
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)

    # Links
    html = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', html)

    # Blockquotes
    html = re.sub(r"^>\s*(.+)$", r"<blockquote>\1</blockquote>", html, flags=re.MULTILINE)

    # Lists
    html = re.sub(r"^[-*+]\s+(.+)$", r"<li>\1</li>", html, flags=re.MULTILINE)

    # Paragraphs (lines not already wrapped in tags)
    lines = html.split("\n")
    result: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not re.match(r"<(?:h[1-6]|li|blockquote|pre|code|ul|ol|div|table)", stripped):
            result.append(f"<p>{stripped}</p>")
        else:
            result.append(line)

    return "\n".join(result)


def _html_escape(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _parse_sections(text: str) -> list[dict[str, Any]]:
    """Parse markdown into sections."""
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] = {"heading": "", "level": 0, "content": ""}

    for line in text.split("\n"):
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            if current["heading"] or current["content"].strip():
                sections.append(current)
            current = {
                "heading": heading_match.group(2).strip(),
                "level": len(heading_match.group(1)),
                "content": "",
            }
        else:
            current["content"] += line + "\n"

    if current["heading"] or current["content"].strip():
        sections.append(current)

    # Clean up trailing whitespace in content
    for sec in sections:
        sec["content"] = sec["content"].strip()

    return sections


def _strip_to_plain(text: str) -> str:
    """Strip markdown to plain text."""
    result = text
    result = re.sub(r"```[\s\S]*?```", "", result)
    result = re.sub(r"`([^`]+)`", r"\1", result)
    result = re.sub(r"^#{1,6}\s+(.+)$", r"\1", result, flags=re.MULTILINE)
    result = re.sub(r"\*\*(.+?)\*\*", r"\1", result)
    result = re.sub(r"\*(.+?)\*", r"\1", result)
    result = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", result)
    result = re.sub(r"!\[([^\]]*)\]\([^)]+\)", "", result)
    result = re.sub(r"<[^>]+>", "", result)
    result = re.sub(r"^\|.*\|$", "", result, flags=re.MULTILINE)
    result = re.sub(r"^[-*+]\s+", "• ", result, flags=re.MULTILINE)
    result = re.sub(r"^>\s*", "", result, flags=re.MULTILINE)
    return result


def _word_wrap(text: str, width: int) -> str:
    """Wrap text at word boundaries."""
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if len(paragraph) <= width:
            lines.append(paragraph)
            continue
        words = paragraph.split()
        current_line: list[str] = []
        current_len = 0
        for word in words:
            if current_len + len(word) + (1 if current_line else 0) > width:
                lines.append(" ".join(current_line))
                current_line = [word]
                current_len = len(word)
            else:
                current_line.append(word)
                current_len += len(word) + (1 if len(current_line) > 1 else 0)
        if current_line:
            lines.append(" ".join(current_line))
    return "\n".join(lines)
