"""Advanced markdown formatting utilities.

Format documents with consistent styling: list formatting,
table alignment, code block decoration, blockquote handling,
emphasis normalization, and document templating.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ListStyle(Enum):
    """Markdown list marker styles."""
    DASH = "-"
    ASTERISK = "*"
    PLUS = "+"


class EmphasisStyle(Enum):
    """Emphasis marker style."""
    ASTERISK = "asterisk"
    UNDERSCORE = "underscore"


class TableAlignment(Enum):
    """Column alignment for tables."""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


@dataclass
class FormatOptions:
    """Global formatting options."""

    list_style: ListStyle = ListStyle.DASH
    emphasis_style: EmphasisStyle = EmphasisStyle.ASTERISK
    heading_style: str = "atx"  # "atx" (#) or "setext" (underline) for h1/h2
    code_fence: str = "```"  # or ~~~
    line_width: int = 0  # 0 = no wrap
    table_padding: int = 1
    blank_lines_around_headings: int = 1
    trailing_newline: bool = True


@dataclass
class FormatResult:
    """Result of formatting."""

    original: str
    formatted: str
    changes: int = 0

    @property
    def changed(self) -> bool:
        return self.original != self.formatted


# ---------------------------------------------------------------------------
# List formatting
# ---------------------------------------------------------------------------

def normalize_lists(text: str, style: ListStyle = ListStyle.DASH) -> FormatResult:
    """Normalize list marker style."""
    original = text
    marker = style.value
    changes = 0

    def _replace_marker(m: re.Match) -> str:
        nonlocal changes
        indent = m.group(1)
        old_marker = m.group(2)
        content = m.group(3)
        if old_marker != marker:
            changes += 1
        return f"{indent}{marker} {content}"

    result = re.sub(
        r"^(\s*)([-*+])\s+(.+)$",
        _replace_marker,
        text,
        flags=re.MULTILINE,
    )

    return FormatResult(original=original, formatted=result, changes=changes)


def sort_list(text: str, reverse: bool = False) -> FormatResult:
    """Sort a markdown list alphabetically."""
    lines = text.splitlines()
    list_items: List[str] = []
    non_list: List[Tuple[int, str]] = []

    for i, line in enumerate(lines):
        if re.match(r"^\s*[-*+]\s+", line):
            list_items.append(line)
        else:
            non_list.append((i, line))

    sorted_items = sorted(
        list_items,
        key=lambda x: re.sub(r"^\s*[-*+]\s+", "", x).lower(),
        reverse=reverse,
    )

    # Rebuild: replace list items in order
    result_lines: List[str] = []
    list_idx = 0
    for i, line in enumerate(lines):
        if re.match(r"^\s*[-*+]\s+", line):
            if list_idx < len(sorted_items):
                result_lines.append(sorted_items[list_idx])
                list_idx += 1
        else:
            result_lines.append(line)

    return FormatResult(
        original=text,
        formatted="\n".join(result_lines),
        changes=1 if sorted_items != list_items else 0,
    )


# ---------------------------------------------------------------------------
# Table formatting
# ---------------------------------------------------------------------------

def format_table(text: str, alignment: TableAlignment = TableAlignment.LEFT) -> FormatResult:
    """Format markdown tables with consistent column widths and alignment."""
    lines = text.splitlines()
    table_groups: List[Tuple[int, int, List[List[str]]]] = []

    i = 0
    while i < len(lines):
        if "|" in lines[i]:
            start = i
            rows: List[List[str]] = []
            while i < len(lines) and "|" in lines[i]:
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                # Skip separator row
                if all(re.match(r"^[-:]+$", c.strip()) for c in cells if c.strip()):
                    i += 1
                    continue
                rows.append(cells)
                i += 1
            table_groups.append((start, i, rows))
        else:
            i += 1

    if not table_groups:
        return FormatResult(original=text, formatted=text, changes=0)

    result_lines = list(lines)
    changes = 0

    for start, end, rows in reversed(table_groups):
        if not rows:
            continue

        # Compute column widths
        num_cols = max(len(r) for r in rows)
        col_widths = [0] * num_cols
        for row in rows:
            for j, cell in enumerate(row):
                if j < num_cols:
                    col_widths[j] = max(col_widths[j], len(cell))

        # Ensure minimum width
        col_widths = [max(w, 3) for w in col_widths]

        # Build formatted table
        formatted: List[str] = []
        for ri, row in enumerate(rows):
            cells: List[str] = []
            for j in range(num_cols):
                cell = row[j] if j < len(row) else ""
                if alignment == TableAlignment.RIGHT:
                    cells.append(cell.rjust(col_widths[j]))
                elif alignment == TableAlignment.CENTER:
                    cells.append(cell.center(col_widths[j]))
                else:
                    cells.append(cell.ljust(col_widths[j]))
            formatted.append("| " + " | ".join(cells) + " |")

            # Add separator after header row
            if ri == 0:
                seps: List[str] = []
                for j in range(num_cols):
                    if alignment == TableAlignment.RIGHT:
                        seps.append("-" * (col_widths[j] - 1) + ":")
                    elif alignment == TableAlignment.CENTER:
                        seps.append(":" + "-" * (col_widths[j] - 2) + ":")
                    else:
                        seps.append("-" * col_widths[j])
                formatted.append("| " + " | ".join(seps) + " |")

        result_lines[start:end] = formatted
        changes += 1

    return FormatResult(
        original=text,
        formatted="\n".join(result_lines),
        changes=changes,
    )


# ---------------------------------------------------------------------------
# Emphasis normalization
# ---------------------------------------------------------------------------

def normalize_emphasis(
    text: str,
    style: EmphasisStyle = EmphasisStyle.ASTERISK,
) -> FormatResult:
    """Normalize bold/italic markers to consistent style."""
    original = text
    changes = 0

    if style == EmphasisStyle.ASTERISK:
        # Convert __bold__ to **bold** and _italic_ to *italic*
        def _fix_bold_under(m: re.Match) -> str:
            nonlocal changes
            changes += 1
            return f"**{m.group(1)}**"

        def _fix_italic_under(m: re.Match) -> str:
            nonlocal changes
            changes += 1
            return f"*{m.group(1)}*"

        result = re.sub(r"__([^_]+)__", _fix_bold_under, text)
        result = re.sub(r"(?<!\*)_([^_]+)_(?!\*)", _fix_italic_under, result)
    else:
        # Convert **bold** to __bold__ and *italic* to _italic_
        def _fix_bold_star(m: re.Match) -> str:
            nonlocal changes
            changes += 1
            return f"__{m.group(1)}__"

        def _fix_italic_star(m: re.Match) -> str:
            nonlocal changes
            changes += 1
            return f"_{m.group(1)}_"

        result = re.sub(r"\*\*([^*]+)\*\*", _fix_bold_star, text)
        result = re.sub(r"(?<!_)\*([^*]+)\*(?!_)", _fix_italic_star, result)

    return FormatResult(original=original, formatted=result, changes=changes)


# ---------------------------------------------------------------------------
# Code block formatting
# ---------------------------------------------------------------------------

def normalize_code_fences(text: str, fence: str = "```") -> FormatResult:
    """Normalize code fence markers."""
    original = text
    changes = 0
    alt_fence = "~~~" if fence == "```" else "```"

    lines = text.splitlines()
    result: List[str] = []
    for line in lines:
        if line.strip().startswith(alt_fence):
            result.append(line.replace(alt_fence, fence, 1))
            changes += 1
        else:
            result.append(line)

    return FormatResult(
        original=original,
        formatted="\n".join(result),
        changes=changes,
    )


def add_language_labels(text: str, default_lang: str = "") -> FormatResult:
    """Add language labels to unlabeled code blocks."""
    original = text
    changes = 0
    lines = text.splitlines()
    result: List[str] = []
    in_code_block = False

    for line in lines:
        if re.match(r"^```\s*$", line):
            if not in_code_block and default_lang:
                result.append(f"```{default_lang}")
                changes += 1
                in_code_block = True
            else:
                result.append(line)
                in_code_block = False
        elif re.match(r"^```\S", line):
            result.append(line)
            in_code_block = True
        else:
            result.append(line)

    return FormatResult(
        original=original,
        formatted="\n".join(result),
        changes=changes,
    )


# ---------------------------------------------------------------------------
# Blockquote formatting
# ---------------------------------------------------------------------------

def normalize_blockquotes(text: str) -> FormatResult:
    """Normalize blockquote formatting."""
    original = text
    changes = 0
    lines = text.splitlines()
    result: List[str] = []

    for line in lines:
        match = re.match(r"^(\s*)(>{1,})\s*(.*)", line)
        if match:
            indent = match.group(1)
            markers = match.group(2)
            content = match.group(3)
            normalized = indent + "> " * len(markers)
            if len(markers) > 1:
                normalized = indent + "> " * len(markers)
            else:
                normalized = indent + "> "
            new_line = normalized + content
            if new_line != line:
                changes += 1
            result.append(new_line)
        else:
            result.append(line)

    return FormatResult(
        original=original,
        formatted="\n".join(result),
        changes=changes,
    )


# ---------------------------------------------------------------------------
# Heading formatting
# ---------------------------------------------------------------------------

def add_heading_ids(text: str) -> FormatResult:
    """Add anchor IDs to headings."""
    original = text
    changes = 0
    lines = text.splitlines()
    result: List[str] = []

    for line in lines:
        match = re.match(r"^(#{1,6})\s+(.+?)(?:\s+\{#[\w-]+\})?\s*$", line)
        if match:
            hashes = match.group(1)
            title = match.group(2).strip()
            # Strip any existing {#id} from the title text
            title = re.sub(r"\s*\{#[\w-]+\}\s*", "", title).strip()
            slug = re.sub(r"[^\w\s-]", "", title.lower())
            slug = re.sub(r"[\s]+", "-", slug).strip("-")
            new_line = f"{hashes} {title} {{#{slug}}}"
            if new_line != line:
                changes += 1
            result.append(new_line)
        else:
            result.append(line)

    return FormatResult(
        original=original,
        formatted="\n".join(result),
        changes=changes,
    )


def ensure_blank_lines_around_headings(
    text: str,
    count: int = 1,
) -> FormatResult:
    """Ensure blank lines before and after headings."""
    lines = text.splitlines()
    result: List[str] = []
    changes = 0
    blank = [""] * count

    for i, line in enumerate(lines):
        is_heading = bool(re.match(r"^#{1,6}\s+", line))

        if is_heading:
            # Ensure blank lines before (unless first line)
            if result and result[-1] != "":
                result.extend(blank)
                changes += 1
            result.append(line)
            # Mark to add blank after
        else:
            # If previous was heading and this isn't blank
            if result and re.match(r"^#{1,6}\s+", result[-1]) and line != "":
                result.extend(blank)
                changes += 1
            result.append(line)

    return FormatResult(
        original=text,
        formatted="\n".join(result),
        changes=changes,
    )


# ---------------------------------------------------------------------------
# Full document formatter
# ---------------------------------------------------------------------------

def format_document(
    text: str,
    options: Optional[FormatOptions] = None,
) -> FormatResult:
    """Apply comprehensive formatting to a markdown document."""
    if options is None:
        options = FormatOptions()

    result = text
    total_changes = 0

    # Normalize lists
    r = normalize_lists(result, options.list_style)
    result = r.formatted
    total_changes += r.changes

    # Normalize emphasis
    r = normalize_emphasis(result, options.emphasis_style)
    result = r.formatted
    total_changes += r.changes

    # Normalize code fences
    r = normalize_code_fences(result, options.code_fence)
    result = r.formatted
    total_changes += r.changes

    # Normalize blockquotes
    r = normalize_blockquotes(result)
    result = r.formatted
    total_changes += r.changes

    # Blank lines around headings
    if options.blank_lines_around_headings:
        r = ensure_blank_lines_around_headings(
            result, options.blank_lines_around_headings
        )
        result = r.formatted
        total_changes += r.changes

    # Trailing newline
    if options.trailing_newline and result and not result.endswith("\n"):
        result += "\n"
        total_changes += 1

    return FormatResult(original=text, formatted=result, changes=total_changes)


def create_format_options(**kwargs: Any) -> FormatOptions:
    """Create format options from keyword arguments."""
    opts = FormatOptions()
    for key, val in kwargs.items():
        if hasattr(opts, key):
            setattr(opts, key, val)
    return opts
