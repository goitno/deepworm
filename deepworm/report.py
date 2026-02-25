"""Report formatting and output utilities."""

from __future__ import annotations

import os
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown


console = Console()


def print_report(report: str) -> None:
    """Print a markdown report to the terminal with rich formatting."""
    md = Markdown(report)
    console.print()
    console.print(md)
    console.print()


def save_report(report: str, path: str | None = None, topic: str = "") -> str:
    """Save a report to a file. Returns the path used."""
    if path is None:
        # Generate a filename from the topic
        slug = _slugify(topic) if topic else "research"
        path = f"{slug}.md"

    # Handle relative paths
    filepath = Path(path)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(report, encoding="utf-8")
    return str(filepath)


def _slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    import re
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text[:60].strip('-')
