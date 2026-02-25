"""Table of contents generation and management.

Generate, customize, and inject table of contents from markdown headings
with support for numbering, indentation, linking, and filtering.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class TocEntry:
    """A single table of contents entry."""

    title: str
    level: int
    anchor: str = ""
    number: str = ""
    line_number: int = 0
    children: List["TocEntry"] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.anchor:
            self.anchor = _slugify(self.title)

    @property
    def depth(self) -> int:
        """Maximum depth of this entry's subtree."""
        if not self.children:
            return 0
        return 1 + max(c.depth for c in self.children)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "level": self.level,
            "anchor": self.anchor,
            "number": self.number,
            "line_number": self.line_number,
            "children": [c.to_dict() for c in self.children],
        }


@dataclass
class TableOfContents:
    """A complete table of contents."""

    entries: List[TocEntry] = field(default_factory=list)
    title: str = "Table of Contents"
    max_depth: int = 6
    numbered: bool = False
    include_links: bool = True

    @property
    def flat(self) -> List[TocEntry]:
        """Return all entries in a flat list (depth-first)."""
        result: List[TocEntry] = []
        _flatten(self.entries, result)
        return result

    @property
    def entry_count(self) -> int:
        return len(self.flat)

    def filter_by_level(self, min_level: int = 1, max_level: int = 6) -> "TableOfContents":
        """Return a new ToC filtered by heading level."""
        filtered = TableOfContents(
            title=self.title,
            max_depth=self.max_depth,
            numbered=self.numbered,
            include_links=self.include_links,
        )
        for entry in self.flat:
            if min_level <= entry.level <= max_level:
                filtered.entries.append(TocEntry(
                    title=entry.title,
                    level=entry.level,
                    anchor=entry.anchor,
                    number=entry.number,
                    line_number=entry.line_number,
                ))
        return filtered

    def to_markdown(self) -> str:
        """Generate markdown representation of the ToC."""
        lines = [f"## {self.title}", ""]
        for entry in self.flat:
            if entry.level > self.max_depth:
                continue
            indent = "  " * (entry.level - 1)
            prefix = f"{entry.number} " if entry.number else ""
            if self.include_links:
                lines.append(f"{indent}- [{prefix}{entry.title}](#{entry.anchor})")
            else:
                lines.append(f"{indent}- {prefix}{entry.title}")
        lines.append("")
        return "\n".join(lines)

    def to_numbered_markdown(self) -> str:
        """Generate numbered markdown ToC."""
        lines = [f"## {self.title}", ""]
        numbered = _assign_numbers(self.flat)
        for entry, number in numbered:
            if entry.level > self.max_depth:
                continue
            indent = "  " * (entry.level - 1)
            if self.include_links:
                lines.append(f"{indent}- [{number} {entry.title}](#{entry.anchor})")
            else:
                lines.append(f"{indent}- {number} {entry.title}")
        lines.append("")
        return "\n".join(lines)

    def to_html(self) -> str:
        """Generate HTML representation of the ToC."""
        lines = [f"<nav><h2>{self.title}</h2>", "<ul>"]
        prev_level = 0
        for entry in self.flat:
            if entry.level > self.max_depth:
                continue
            # Handle nesting
            if entry.level > prev_level:
                lines.append("<ul>" * (entry.level - prev_level))
            elif entry.level < prev_level:
                lines.append("</ul>" * (prev_level - entry.level))
            prefix = f"{entry.number} " if entry.number else ""
            if self.include_links:
                lines.append(f'<li><a href="#{entry.anchor}">{prefix}{entry.title}</a></li>')
            else:
                lines.append(f"<li>{prefix}{entry.title}</li>")
            prev_level = entry.level
        if prev_level > 0:
            lines.append("</ul>" * prev_level)
        lines.append("</ul></nav>")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "entry_count": self.entry_count,
            "max_depth": self.max_depth,
            "numbered": self.numbered,
            "entries": [e.to_dict() for e in self.entries],
        }


def _flatten(entries: List[TocEntry], result: List[TocEntry]) -> None:
    """Flatten a nested entry list depth-first."""
    for entry in entries:
        result.append(entry)
        _flatten(entry.children, result)


def _slugify(text: str) -> str:
    """Convert heading text to a URL-compatible anchor slug."""
    # Remove markdown formatting
    text = re.sub(r"[*_`\[\]()!]", "", text)
    # Lowercase
    text = text.lower().strip()
    # Replace spaces and special chars with hyphens
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def _assign_numbers(entries: List[TocEntry]) -> List[Tuple[TocEntry, str]]:
    """Assign hierarchical numbers to entries."""
    counters: Dict[int, int] = {}
    result: List[Tuple[TocEntry, str]] = []

    for entry in entries:
        level = entry.level
        # Reset counters for deeper levels
        for k in list(counters.keys()):
            if k > level:
                del counters[k]

        counters[level] = counters.get(level, 0) + 1
        # Build number string
        parts = []
        for lv in sorted(counters.keys()):
            if lv <= level:
                parts.append(str(counters[lv]))
        number = ".".join(parts)
        result.append((entry, number))

    return result


def extract_toc(text: str, max_depth: int = 6) -> TableOfContents:
    """Extract table of contents from markdown text.

    Args:
        text: Markdown text with headings.
        max_depth: Maximum heading depth to include (1-6).

    Returns:
        TableOfContents with extracted entries.
    """
    toc = TableOfContents(max_depth=max_depth)

    # Track anchor uniqueness
    anchor_counts: Dict[str, int] = {}

    for line_num, line in enumerate(text.splitlines(), 1):
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if not match:
            continue

        level = len(match.group(1))
        title = match.group(2).strip()

        if level > max_depth:
            continue

        anchor = _slugify(title)
        # Handle duplicate anchors
        if anchor in anchor_counts:
            anchor_counts[anchor] += 1
            anchor = f"{anchor}-{anchor_counts[anchor]}"
        else:
            anchor_counts[anchor] = 0

        entry = TocEntry(
            title=title,
            level=level,
            anchor=anchor,
            line_number=line_num,
        )
        toc.entries.append(entry)

    return toc


def generate_toc(
    text: str,
    title: str = "Table of Contents",
    max_depth: int = 6,
    numbered: bool = False,
    include_links: bool = True,
) -> str:
    """Generate a markdown table of contents from text.

    Args:
        text: Markdown text with headings.
        title: Title for the ToC section.
        max_depth: Maximum heading depth.
        numbered: Whether to add hierarchical numbers.
        include_links: Whether to include anchor links.

    Returns:
        Markdown string with the table of contents.
    """
    toc = extract_toc(text, max_depth=max_depth)
    toc.title = title
    toc.numbered = numbered
    toc.include_links = include_links

    if numbered:
        return toc.to_numbered_markdown()
    return toc.to_markdown()


def inject_toc(
    text: str,
    marker: str = "<!-- TOC -->",
    title: str = "Table of Contents",
    max_depth: int = 6,
    numbered: bool = False,
) -> str:
    """Inject a table of contents into text at the marker position.

    If marker is found, replaces between two markers.
    If no marker, inserts after the first heading.

    Args:
        text: Markdown text.
        marker: Placeholder marker for ToC insertion.
        title: Title for the ToC.
        max_depth: Maximum heading depth.
        numbered: Whether to number entries.

    Returns:
        Text with injected table of contents.
    """
    toc_md = generate_toc(text, title=title, max_depth=max_depth, numbered=numbered)

    # Replace between markers
    marker_pattern = re.escape(marker)
    double_marker = re.compile(
        f"{marker_pattern}.*?{marker_pattern}",
        re.DOTALL,
    )
    if double_marker.search(text):
        return double_marker.sub(f"{marker}\n{toc_md}\n{marker}", text, count=1)

    # Single marker
    if marker in text:
        return text.replace(marker, f"{marker}\n{toc_md}\n{marker}", 1)

    # No marker — insert after first heading
    first_heading = re.search(r"^(#{1,6}\s+.+)$", text, re.MULTILINE)
    if first_heading:
        pos = first_heading.end()
        return text[:pos] + "\n\n" + toc_md + "\n" + text[pos:]

    # No headings — prepend
    return toc_md + "\n" + text


def merge_tocs(*tocs: TableOfContents) -> TableOfContents:
    """Merge multiple tables of contents into one.

    Args:
        *tocs: TableOfContents instances to merge.

    Returns:
        Combined TableOfContents.
    """
    merged = TableOfContents(title="Combined Table of Contents")
    seen_anchors = set()

    for toc in tocs:
        for entry in toc.flat:
            if entry.anchor not in seen_anchors:
                seen_anchors.add(entry.anchor)
                merged.entries.append(TocEntry(
                    title=entry.title,
                    level=entry.level,
                    anchor=entry.anchor,
                    number=entry.number,
                    line_number=entry.line_number,
                ))

    return merged
