"""Report formatting and output utilities."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown


console = Console()


def print_report(report: str) -> None:
    """Print a markdown report to the terminal with rich formatting."""
    md = Markdown(report)
    console.print()
    console.print(md)
    console.print()


def save_report(
    report: str,
    path: str | None = None,
    topic: str = "",
    fmt: str = "markdown",
) -> str:
    """Save a report to a file. Returns the path used.

    Formats: markdown (default), text, json
    """
    if path is None:
        slug = _slugify(topic) if topic else "research"
        ext = {"markdown": ".md", "text": ".txt", "json": ".json"}.get(fmt, ".md")
        path = f"{slug}{ext}"

    filepath = Path(path)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "json":
        data = {"topic": topic, "report": report}
        filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    elif fmt == "text":
        # Strip markdown formatting for plain text
        plain = _markdown_to_text(report)
        filepath.write_text(plain, encoding="utf-8")
    else:
        filepath.write_text(report, encoding="utf-8")

    return str(filepath)


def _markdown_to_text(md: str) -> str:
    """Basic markdown to plain text conversion."""
    import re
    text = md
    # Remove headers markup
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Remove bold/italic
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    # Remove links, keep text
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    # Remove code blocks
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'`(.+?)`', r'\1', text)
    return text


def _slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    import re
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text[:60].strip('-')
