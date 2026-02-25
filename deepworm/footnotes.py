"""Footnote management for research reports.

Converts inline citations and references to numbered footnotes,
manages footnote numbering, and supports round-trip conversion.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Footnote:
    """A single footnote entry."""

    number: int
    text: str
    source_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"number": self.number, "text": self.text}
        if self.source_url:
            d["source_url"] = self.source_url
        return d


@dataclass
class FootnoteResult:
    """Result of footnote conversion."""

    body: str  # Text with footnote markers [1], [2], etc.
    footnotes: list[Footnote] = field(default_factory=list)

    def render(self, style: str = "markdown") -> str:
        """Render full document with footnotes section.

        Args:
            style: 'markdown', 'endnotes', or 'inline'.
        """
        if style == "inline":
            return self._render_inline()
        if style == "endnotes":
            return self._render_endnotes()
        return self._render_markdown()

    def _render_markdown(self) -> str:
        lines = [self.body, "", "---", "", "## Footnotes", ""]
        for fn in self.footnotes:
            entry = f"[^{fn.number}]: {fn.text}"
            if fn.source_url:
                entry += f" ({fn.source_url})"
            lines.append(entry)
        return "\n".join(lines)

    def _render_endnotes(self) -> str:
        lines = [self.body, "", "---", "", "## Notes", ""]
        for fn in self.footnotes:
            entry = f"{fn.number}. {fn.text}"
            if fn.source_url:
                entry += f" — {fn.source_url}"
            lines.append(entry)
        return "\n".join(lines)

    def _render_inline(self) -> str:
        """Put footnote content directly in parentheses inline."""
        text = self.body
        for fn in reversed(self.footnotes):
            marker = f"[^{fn.number}]"
            replacement = f" ({fn.text})"
            text = text.replace(marker, replacement)
        return text

    def to_dict(self) -> dict[str, Any]:
        return {
            "body": self.body,
            "footnotes": [f.to_dict() for f in self.footnotes],
        }


def add_footnotes(text: str) -> FootnoteResult:
    """Convert inline citations and links to numbered footnotes.

    Processes:
    - Markdown links [text](url) → text[^N] with URL footnote
    - Parenthetical citations (Author, Year) → [^N]
    - Existing reference markers like [1], [2] → renumbered

    Args:
        text: Markdown text with inline citations.

    Returns:
        FootnoteResult with converted text and footnotes list.
    """
    footnotes: list[Footnote] = []
    counter = [0]  # Mutable counter for closures

    def _next_num() -> int:
        counter[0] += 1
        return counter[0]

    body = text

    # Step 1: Convert markdown links to footnotes
    # [text](url) → text[^N]
    def _replace_link(m: re.Match) -> str:
        link_text = m.group(1)
        url = m.group(2)
        num = _next_num()
        footnotes.append(Footnote(number=num, text=link_text, source_url=url))
        return f"{link_text}[^{num}]"

    body = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", _replace_link, body)

    # Step 2: Convert parenthetical citations (Author, Year) or (Author et al., Year)
    def _replace_citation(m: re.Match) -> str:
        citation = m.group(1)
        num = _next_num()
        footnotes.append(Footnote(number=num, text=citation))
        return f"[^{num}]"

    body = re.sub(
        r"\(([A-Z][a-z]+(?:\s+(?:et\s+al\.|&\s+[A-Z][a-z]+))?,\s*\d{4})\)",
        _replace_citation,
        body,
    )

    return FootnoteResult(body=body, footnotes=footnotes)


def renumber_footnotes(text: str) -> str:
    """Renumber all footnote markers sequentially.

    Fixes gaps in footnote numbering (e.g., [^1], [^3], [^7] → [^1], [^2], [^3]).

    Args:
        text: Text with footnote markers.

    Returns:
        Text with renumbered footnotes.
    """
    # Find all existing footnote numbers
    markers = re.findall(r"\[\^(\d+)\]", text)
    if not markers:
        return text

    # Get unique numbers in order of appearance
    seen: list[int] = []
    for m in markers:
        n = int(m)
        if n not in seen:
            seen.append(n)

    # Create mapping old → new
    mapping = {old: new + 1 for new, old in enumerate(seen)}

    # Replace with temporary placeholders to avoid conflicts
    result = text
    for old_num, new_num in mapping.items():
        result = result.replace(f"[^{old_num}]", f"[^__TEMP_{new_num}__]")

    # Replace placeholders with final numbers
    for new_num in mapping.values():
        result = result.replace(f"[^__TEMP_{new_num}__]", f"[^{new_num}]")

    return result


def strip_footnotes(text: str) -> str:
    """Remove all footnote markers and footnote sections.

    Args:
        text: Text with footnotes.

    Returns:
        Clean text without footnotes.
    """
    # Remove footnote definition lines [^N]: text (before markers)
    result = re.sub(r"^\[\^\d+\]:\s+.*$", "", text, flags=re.MULTILINE)

    # Remove footnote markers [^N]
    result = re.sub(r"\[\^\d+\]", "", result)

    # Remove footnote section headers
    result = re.sub(r"^---\s*\n\s*##\s*(?:Footnotes|Notes)\s*\n", "", result, flags=re.MULTILINE)

    # Clean up extra blank lines
    result = re.sub(r"\n{3,}", "\n\n", result)

    return result.strip()


def merge_footnotes(*results: FootnoteResult) -> FootnoteResult:
    """Merge multiple FootnoteResults into one with renumbered footnotes.

    Args:
        *results: FootnoteResult objects to merge.

    Returns:
        Combined FootnoteResult with sequential numbering.
    """
    if not results:
        return FootnoteResult(body="", footnotes=[])

    merged_body_parts: list[str] = []
    merged_footnotes: list[Footnote] = []
    offset = 0

    for result in results:
        body = result.body
        for fn in result.footnotes:
            new_num = fn.number + offset
            body = body.replace(f"[^{fn.number}]", f"[^{new_num}]")
            merged_footnotes.append(
                Footnote(number=new_num, text=fn.text, source_url=fn.source_url)
            )
        merged_body_parts.append(body)
        if result.footnotes:
            offset = merged_footnotes[-1].number

    return FootnoteResult(
        body="\n\n".join(merged_body_parts),
        footnotes=merged_footnotes,
    )
