"""Export reports to Notion-compatible formats.

Converts markdown reports to Notion block API format for easy import
via the Notion API, or exports as Notion-flavored markdown.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional


# Notion block types
PARAGRAPH = "paragraph"
HEADING_1 = "heading_1"
HEADING_2 = "heading_2"
HEADING_3 = "heading_3"
BULLETED_LIST = "bulleted_list_item"
NUMBERED_LIST = "numbered_list_item"
CODE = "code"
QUOTE = "quote"
DIVIDER = "divider"
TABLE = "table"
TABLE_ROW = "table_row"
TOGGLE = "toggle"
CALLOUT = "callout"
BOOKMARK = "bookmark"


@dataclass
class NotionBlock:
    """A single Notion block."""

    block_type: str
    content: str = ""
    children: list["NotionBlock"] = field(default_factory=list)
    language: str = ""  # For code blocks
    url: str = ""  # For bookmarks
    rich_text: list[dict[str, Any]] = field(default_factory=list)
    table_width: int = 0  # For table blocks
    cells: list[list[str]] = field(default_factory=list)  # For table rows

    def to_dict(self) -> dict[str, Any]:
        """Convert to Notion API block format."""
        block: dict[str, Any] = {"object": "block", "type": self.block_type}

        if self.block_type == DIVIDER:
            block[self.block_type] = {}
            return block

        if self.block_type == BOOKMARK:
            block[self.block_type] = {"url": self.url}
            return block

        if self.block_type == TABLE:
            block[self.block_type] = {
                "table_width": self.table_width,
                "has_column_header": True,
                "has_row_header": False,
                "children": [c.to_dict() for c in self.children],
            }
            return block

        if self.block_type == TABLE_ROW:
            block[self.block_type] = {
                "cells": [
                    [{"type": "text", "text": {"content": cell}}]
                    for cell in self.cells[0] if self.cells
                ] if self.cells else [],
            }
            return block

        rt = self.rich_text or _text_to_rich_text(self.content)

        data: dict[str, Any] = {"rich_text": rt}
        if self.block_type == CODE:
            data["language"] = self.language or "plain text"

        if self.children:
            data["children"] = [c.to_dict() for c in self.children]

        block[self.block_type] = data
        return block


@dataclass
class NotionPage:
    """A collection of Notion blocks representing a page."""

    title: str
    blocks: list[NotionBlock] = field(default_factory=list)
    icon: str = "📝"
    cover_url: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to Notion API page creation payload."""
        page: dict[str, Any] = {
            "icon": {"type": "emoji", "emoji": self.icon},
            "properties": {
                "title": {
                    "title": [
                        {"type": "text", "text": {"content": self.title}}
                    ]
                }
            },
            "children": [b.to_dict() for b in self.blocks],
        }
        if self.cover_url:
            page["cover"] = {"type": "external", "external": {"url": self.cover_url}}
        return page

    @property
    def block_count(self) -> int:
        """Total number of blocks."""
        return _count_blocks(self.blocks)


def markdown_to_notion(markdown: str) -> NotionPage:
    """Convert a markdown report to Notion page format.

    Args:
        markdown: Markdown text to convert.

    Returns:
        NotionPage with blocks ready for the Notion API.
    """
    lines = markdown.split("\n")
    blocks: list[NotionBlock] = []
    title = "Research Report"
    i = 0

    while i < len(lines):
        line = lines[i]

        # Empty line
        if not line.strip():
            i += 1
            continue

        # Headings
        heading_match = re.match(r"^(#{1,3})\s+(.+)", line)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()
            if level == 1 and not blocks:
                title = text
                i += 1
                continue
            heading_type = {1: HEADING_1, 2: HEADING_2, 3: HEADING_3}[level]
            blocks.append(NotionBlock(block_type=heading_type, content=text))
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^---+\s*$", line) or re.match(r"^\*\*\*+\s*$", line):
            blocks.append(NotionBlock(block_type=DIVIDER))
            i += 1
            continue

        # Code block
        code_match = re.match(r"^```(\w*)", line)
        if code_match:
            language = code_match.group(1) or "plain text"
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing ```
            blocks.append(NotionBlock(
                block_type=CODE,
                content="\n".join(code_lines),
                language=_normalize_language(language),
            ))
            continue

        # Blockquote
        if line.startswith("> "):
            quote_lines = []
            while i < len(lines) and lines[i].startswith("> "):
                quote_lines.append(lines[i][2:])
                i += 1
            blocks.append(NotionBlock(
                block_type=QUOTE,
                content="\n".join(quote_lines),
            ))
            continue

        # Bulleted list
        bullet_match = re.match(r"^[-*]\s+(.+)", line)
        if bullet_match:
            blocks.append(NotionBlock(
                block_type=BULLETED_LIST,
                content=bullet_match.group(1),
            ))
            i += 1
            continue

        # Numbered list
        num_match = re.match(r"^\d+\.\s+(.+)", line)
        if num_match:
            blocks.append(NotionBlock(
                block_type=NUMBERED_LIST,
                content=num_match.group(1),
            ))
            i += 1
            continue

        # Table
        if "|" in line and i + 1 < len(lines) and re.match(r"^\|[-:|]+\|", lines[i + 1]):
            table_block, i = _parse_table(lines, i)
            blocks.append(table_block)
            continue

        # Regular paragraph
        para_lines = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not _is_block_start(lines[i]):
            para_lines.append(lines[i])
            i += 1
        text = " ".join(para_lines)
        blocks.append(NotionBlock(block_type=PARAGRAPH, content=text))

    return NotionPage(title=title, blocks=blocks)


def notion_to_markdown(page: NotionPage) -> str:
    """Convert a NotionPage back to markdown.

    Args:
        page: NotionPage to convert.

    Returns:
        Markdown string.
    """
    lines = [f"# {page.title}", ""]

    for block in page.blocks:
        lines.extend(_block_to_markdown(block))

    return "\n".join(lines)


def export_notion_json(markdown: str) -> dict[str, Any]:
    """Convert markdown to a Notion API-ready JSON payload.

    Args:
        markdown: Markdown report text.

    Returns:
        Dictionary ready for Notion API page creation.
    """
    page = markdown_to_notion(markdown)
    return page.to_dict()


# ── Internal helpers ──


def _text_to_rich_text(text: str) -> list[dict[str, Any]]:
    """Convert plain text to Notion rich text array with inline formatting."""
    if not text:
        return [{"type": "text", "text": {"content": ""}}]

    result: list[dict[str, Any]] = []
    # Parse inline formatting: **bold**, *italic*, `code`, [link](url)
    pattern = re.compile(
        r"(\*\*(.+?)\*\*)"  # bold
        r"|(\*(.+?)\*)"  # italic
        r"|(`(.+?)`)"  # code
        r"|(\[(.+?)\]\((.+?)\))"  # link
    )

    last_end = 0
    for match in pattern.finditer(text):
        # Add plain text before this match
        if match.start() > last_end:
            plain = text[last_end:match.start()]
            if plain:
                result.append({"type": "text", "text": {"content": plain}})

        if match.group(2):  # bold
            result.append({
                "type": "text",
                "text": {"content": match.group(2)},
                "annotations": {"bold": True},
            })
        elif match.group(4):  # italic
            result.append({
                "type": "text",
                "text": {"content": match.group(4)},
                "annotations": {"italic": True},
            })
        elif match.group(6):  # code
            result.append({
                "type": "text",
                "text": {"content": match.group(6)},
                "annotations": {"code": True},
            })
        elif match.group(8):  # link
            result.append({
                "type": "text",
                "text": {
                    "content": match.group(8),
                    "link": {"url": match.group(9)},
                },
            })

        last_end = match.end()

    # Remaining text
    if last_end < len(text):
        remaining = text[last_end:]
        if remaining:
            result.append({"type": "text", "text": {"content": remaining}})

    return result or [{"type": "text", "text": {"content": text}}]


def _is_block_start(line: str) -> bool:
    """Check if a line starts a new block element."""
    if re.match(r"^#{1,6}\s+", line):
        return True
    if re.match(r"^[-*]\s+", line):
        return True
    if re.match(r"^\d+\.\s+", line):
        return True
    if line.startswith("```"):
        return True
    if line.startswith("> "):
        return True
    if re.match(r"^---+\s*$", line):
        return True
    if re.match(r"^\*\*\*+\s*$", line):
        return True
    return False


def _parse_table(lines: list[str], start: int) -> tuple[NotionBlock, int]:
    """Parse a markdown table into a Notion table block."""
    rows: list[list[str]] = []
    i = start

    while i < len(lines) and "|" in lines[i]:
        line = lines[i].strip()
        # Skip separator row
        if re.match(r"^\|[-:|]+\|$", line):
            i += 1
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        rows.append(cells)
        i += 1

    width = max(len(r) for r in rows) if rows else 0
    # Pad rows to same width
    for row in rows:
        while len(row) < width:
            row.append("")

    children = [
        NotionBlock(block_type=TABLE_ROW, cells=[row])
        for row in rows
    ]

    table = NotionBlock(
        block_type=TABLE,
        table_width=width,
        children=children,
    )
    return table, i


def _normalize_language(lang: str) -> str:
    """Normalize language identifier for Notion."""
    mapping = {
        "py": "python",
        "js": "javascript",
        "ts": "typescript",
        "rb": "ruby",
        "sh": "shell",
        "bash": "shell",
        "yml": "yaml",
        "md": "markdown",
        "txt": "plain text",
        "": "plain text",
    }
    return mapping.get(lang.lower(), lang.lower())


def _block_to_markdown(block: NotionBlock) -> list[str]:
    """Convert a single Notion block back to markdown."""
    if block.block_type == HEADING_1:
        return [f"# {block.content}", ""]
    elif block.block_type == HEADING_2:
        return [f"## {block.content}", ""]
    elif block.block_type == HEADING_3:
        return [f"### {block.content}", ""]
    elif block.block_type == PARAGRAPH:
        return [block.content, ""]
    elif block.block_type == BULLETED_LIST:
        return [f"- {block.content}"]
    elif block.block_type == NUMBERED_LIST:
        return [f"1. {block.content}"]
    elif block.block_type == CODE:
        lang = block.language if block.language != "plain text" else ""
        return [f"```{lang}", block.content, "```", ""]
    elif block.block_type == QUOTE:
        return [f"> {line}" for line in block.content.split("\n")] + [""]
    elif block.block_type == DIVIDER:
        return ["---", ""]
    elif block.block_type == TABLE:
        lines = []
        for idx, child in enumerate(block.children):
            if child.cells:
                cells = child.cells[0]
                lines.append("| " + " | ".join(cells) + " |")
                if idx == 0:
                    lines.append("| " + " | ".join("---" for _ in cells) + " |")
        lines.append("")
        return lines
    elif block.block_type == BOOKMARK:
        return [f"[{block.url}]({block.url})", ""]
    return [block.content, ""]


def _count_blocks(blocks: list[NotionBlock]) -> int:
    """Count total blocks recursively."""
    total = len(blocks)
    for b in blocks:
        total += _count_blocks(b.children)
    return total
