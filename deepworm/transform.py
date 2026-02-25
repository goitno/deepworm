"""Document text transformation utilities.

Programmatic text transformations for markdown documents:
case conversion, whitespace normalization, markdown cleanup,
find-and-replace, text wrapping, and structural transforms.
"""

from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class TransformType(Enum):
    """Types of text transformations."""
    CASE = "case"
    WHITESPACE = "whitespace"
    MARKDOWN = "markdown"
    REPLACE = "replace"
    STRUCTURE = "structure"
    CUSTOM = "custom"


@dataclass
class TransformResult:
    """Result of a transformation."""

    original: str
    transformed: str
    changes_made: int = 0
    transform_type: TransformType = TransformType.CUSTOM
    description: str = ""

    @property
    def changed(self) -> bool:
        return self.original != self.transformed

    @property
    def diff_ratio(self) -> float:
        if not self.original:
            return 0.0
        orig_len = len(self.original)
        new_len = len(self.transformed)
        return abs(new_len - orig_len) / max(orig_len, 1)


@dataclass
class TransformChainResult:
    """Result of a chain of transformations."""

    original: str
    final: str
    steps: List[TransformResult] = field(default_factory=list)

    @property
    def total_changes(self) -> int:
        return sum(s.changes_made for s in self.steps)

    @property
    def changed(self) -> bool:
        return self.original != self.final

    def to_dict(self) -> Dict[str, Any]:
        return {
            "changed": self.changed,
            "total_changes": self.total_changes,
            "steps": len(self.steps),
            "original_length": len(self.original),
            "final_length": len(self.final),
        }


# ---------------------------------------------------------------------------
# Case transforms
# ---------------------------------------------------------------------------

def to_title_case(text: str) -> TransformResult:
    """Convert headings to title case."""
    lines = text.splitlines()
    result_lines: List[str] = []
    changes = 0

    _small_words = {
        "a", "an", "the", "and", "but", "or", "nor", "for", "yet", "so",
        "in", "on", "at", "to", "by", "of", "up", "as", "is", "it",
    }

    for line in lines:
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if match:
            hashes, title = match.group(1), match.group(2)
            words = title.split()
            new_words: List[str] = []
            for i, w in enumerate(words):
                if i == 0 or w.lower() not in _small_words:
                    new_words.append(w.capitalize())
                else:
                    new_words.append(w.lower())
            new_title = " ".join(new_words)
            if new_title != title:
                changes += 1
            result_lines.append(f"{hashes} {new_title}")
        else:
            result_lines.append(line)

    return TransformResult(
        original=text,
        transformed="\n".join(result_lines),
        changes_made=changes,
        transform_type=TransformType.CASE,
        description="Convert headings to title case",
    )


def to_sentence_case(text: str) -> TransformResult:
    """Convert headings to sentence case."""
    lines = text.splitlines()
    result_lines: List[str] = []
    changes = 0

    for line in lines:
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if match:
            hashes, title = match.group(1), match.group(2)
            words = title.split()
            if words:
                new_words = [words[0].capitalize()] + [w.lower() for w in words[1:]]
                new_title = " ".join(new_words)
                if new_title != title:
                    changes += 1
                result_lines.append(f"{hashes} {new_title}")
            else:
                result_lines.append(line)
        else:
            result_lines.append(line)

    return TransformResult(
        original=text,
        transformed="\n".join(result_lines),
        changes_made=changes,
        transform_type=TransformType.CASE,
        description="Convert headings to sentence case",
    )


# ---------------------------------------------------------------------------
# Whitespace transforms
# ---------------------------------------------------------------------------

def normalize_whitespace(text: str) -> TransformResult:
    """Normalize whitespace: trim trailing spaces, collapse blank lines."""
    original = text
    lines = text.splitlines()
    changes = 0

    # Trim trailing whitespace
    trimmed: List[str] = []
    for line in lines:
        stripped = line.rstrip()
        if stripped != line:
            changes += 1
        trimmed.append(stripped)

    # Collapse 2+ consecutive blank lines to 1
    result: List[str] = []
    blank_count = 0
    for line in trimmed:
        if line == "":
            blank_count += 1
            if blank_count <= 1:
                result.append(line)
            else:
                changes += 1
        else:
            blank_count = 0
            result.append(line)

    # Ensure trailing newline
    output = "\n".join(result)
    if output and not output.endswith("\n"):
        output += "\n"

    return TransformResult(
        original=original,
        transformed=output,
        changes_made=changes,
        transform_type=TransformType.WHITESPACE,
        description="Normalize whitespace",
    )


def fix_indentation(text: str, indent: int = 4) -> TransformResult:
    """Normalize indentation in code blocks."""
    lines = text.splitlines()
    result: List[str] = []
    in_code_block = False
    changes = 0
    code_indent = " " * indent

    for line in lines:
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            result.append(line)
            continue

        if in_code_block and line.strip():
            # Normalize leading whitespace
            stripped = line.lstrip()
            leading = len(line) - len(stripped)
            if leading > 0:
                # Round to indent multiples
                new_leading = round(leading / indent) * indent
                new_line = " " * new_leading + stripped
                if new_line != line:
                    changes += 1
                result.append(new_line)
            else:
                result.append(line)
        else:
            result.append(line)

    return TransformResult(
        original=text,
        transformed="\n".join(result),
        changes_made=changes,
        transform_type=TransformType.WHITESPACE,
        description="Fix code block indentation",
    )


# ---------------------------------------------------------------------------
# Markdown transforms
# ---------------------------------------------------------------------------

def normalize_headings(text: str, max_level: int = 6) -> TransformResult:
    """Ensure heading levels start at 1 and don't skip levels."""
    lines = text.splitlines()
    headings = []
    for i, line in enumerate(lines):
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if match:
            headings.append((i, len(match.group(1)), match.group(2)))

    if not headings:
        return TransformResult(original=text, transformed=text)

    # Find min level
    min_level = min(h[1] for h in headings)
    offset = min_level - 1
    changes = 0
    result = list(lines)

    for idx, level, title in headings:
        new_level = min(level - offset, max_level)
        new_line = "#" * new_level + " " + title
        if new_line != lines[idx]:
            changes += 1
        result[idx] = new_line

    return TransformResult(
        original=text,
        transformed="\n".join(result),
        changes_made=changes,
        transform_type=TransformType.MARKDOWN,
        description="Normalize heading levels",
    )


def strip_html(text: str) -> TransformResult:
    """Remove HTML tags from markdown."""
    original = text
    # Count tags
    tags = re.findall(r"<[^>]+>", text)
    changes = len(tags)
    cleaned = re.sub(r"<[^>]+>", "", text)

    return TransformResult(
        original=original,
        transformed=cleaned,
        changes_made=changes,
        transform_type=TransformType.MARKDOWN,
        description="Strip HTML tags",
    )


def normalize_links(text: str) -> TransformResult:
    """Normalize markdown link formatting."""
    original = text
    changes = 0

    # Fix spaces in link text [text ](url) → [text](url)
    def _fix_link(m: re.Match) -> str:
        nonlocal changes
        link_text = m.group(1).strip()
        url = m.group(2).strip()
        original_match = m.group(0)
        fixed = f"[{link_text}]({url})"
        if fixed != original_match:
            changes += 1
        return fixed

    result = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _fix_link, text)

    return TransformResult(
        original=original,
        transformed=result,
        changes_made=changes,
        transform_type=TransformType.MARKDOWN,
        description="Normalize link formatting",
    )


def strip_comments(text: str) -> TransformResult:
    """Remove HTML comments from markdown."""
    original = text
    comments = re.findall(r"<!--.*?-->", text, re.DOTALL)
    changes = len(comments)
    result = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    return TransformResult(
        original=original,
        transformed=result,
        changes_made=changes,
        transform_type=TransformType.MARKDOWN,
        description="Strip HTML comments",
    )


# ---------------------------------------------------------------------------
# Find-and-replace transforms
# ---------------------------------------------------------------------------

def find_replace(
    text: str,
    pattern: str,
    replacement: str,
    regex: bool = False,
    case_sensitive: bool = True,
) -> TransformResult:
    """Find and replace text."""
    original = text
    if regex:
        flags = 0 if case_sensitive else re.IGNORECASE
        matches = re.findall(pattern, text, flags)
        changes = len(matches)
        result = re.sub(pattern, replacement, text, flags=flags)
    else:
        if case_sensitive:
            changes = text.count(pattern)
            result = text.replace(pattern, replacement)
        else:
            lower_text = text.lower()
            lower_pattern = pattern.lower()
            changes = lower_text.count(lower_pattern)
            # Case-insensitive replace
            idx = 0
            parts: List[str] = []
            while True:
                found = lower_text.find(lower_pattern, idx)
                if found == -1:
                    parts.append(text[idx:])
                    break
                parts.append(text[idx:found])
                parts.append(replacement)
                idx = found + len(pattern)
            result = "".join(parts)

    return TransformResult(
        original=original,
        transformed=result,
        changes_made=changes,
        transform_type=TransformType.REPLACE,
        description=f"Replace '{pattern}' with '{replacement}'",
    )


def find_replace_batch(
    text: str,
    replacements: List[Tuple[str, str]],
) -> TransformResult:
    """Apply multiple find-and-replace operations."""
    result = text
    total_changes = 0
    for pattern, replacement in replacements:
        count = result.count(pattern)
        total_changes += count
        result = result.replace(pattern, replacement)

    return TransformResult(
        original=text,
        transformed=result,
        changes_made=total_changes,
        transform_type=TransformType.REPLACE,
        description=f"Batch replace ({len(replacements)} rules)",
    )


# ---------------------------------------------------------------------------
# Structure transforms
# ---------------------------------------------------------------------------

def wrap_text(text: str, width: int = 80) -> TransformResult:
    """Wrap long lines preserving markdown structure."""
    lines = text.splitlines()
    result: List[str] = []
    changes = 0
    in_code = False

    for line in lines:
        if line.strip().startswith("```"):
            in_code = not in_code
            result.append(line)
            continue

        # Don't wrap code blocks, headings, lists, or tables
        if in_code or re.match(r"^#{1,6}\s", line) or re.match(r"^\s*[-*+]\s", line) or "|" in line:
            result.append(line)
            continue

        if len(line) > width:
            wrapped = textwrap.fill(line, width=width)
            result.append(wrapped)
            changes += 1
        else:
            result.append(line)

    return TransformResult(
        original=text,
        transformed="\n".join(result),
        changes_made=changes,
        transform_type=TransformType.STRUCTURE,
        description=f"Wrap text at {width} characters",
    )


def extract_section(text: str, heading: str) -> TransformResult:
    """Extract a section by heading name."""
    lines = text.splitlines()
    result: List[str] = []
    collecting = False
    collect_level = 0

    for line in lines:
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            if title.lower() == heading.lower():
                collecting = True
                collect_level = level
                result.append(line)
                continue
            elif collecting and level <= collect_level:
                break
        if collecting:
            result.append(line)

    extracted = "\n".join(result).strip()
    return TransformResult(
        original=text,
        transformed=extracted,
        changes_made=1 if extracted else 0,
        transform_type=TransformType.STRUCTURE,
        description=f"Extract section: {heading}",
    )


def remove_section(text: str, heading: str) -> TransformResult:
    """Remove a section by heading name."""
    lines = text.splitlines()
    result: List[str] = []
    skipping = False
    skip_level = 0
    changes = 0

    for line in lines:
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            if title.lower() == heading.lower():
                skipping = True
                skip_level = level
                changes += 1
                continue
            elif skipping and level <= skip_level:
                skipping = False
        if not skipping:
            result.append(line)

    return TransformResult(
        original=text,
        transformed="\n".join(result),
        changes_made=changes,
        transform_type=TransformType.STRUCTURE,
        description=f"Remove section: {heading}",
    )


def reorder_sections(text: str, order: List[str]) -> TransformResult:
    """Reorder top-level sections by heading name."""
    lines = text.splitlines()

    # Parse into sections
    sections: Dict[str, List[str]] = {}
    preamble: List[str] = []
    current_heading: Optional[str] = None
    current_lines: List[str] = []

    for line in lines:
        match = re.match(r"^(#{1,2})\s+(.+)$", line)
        if match and len(match.group(1)) <= 2:
            if current_heading:
                sections[current_heading] = current_lines
            elif current_lines:
                preamble = current_lines
            current_heading = match.group(2).strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_heading:
        sections[current_heading] = current_lines

    # Build reordered
    result_lines = list(preamble)
    used: set = set()
    for heading in order:
        for key, content in sections.items():
            if key.lower() == heading.lower():
                if result_lines and result_lines[-1] != "":
                    result_lines.append("")
                result_lines.extend(content)
                used.add(key)
                break

    # Append remaining sections not in order
    for key, content in sections.items():
        if key not in used:
            if result_lines and result_lines[-1] != "":
                result_lines.append("")
            result_lines.extend(content)

    return TransformResult(
        original=text,
        transformed="\n".join(result_lines),
        changes_made=len(order),
        transform_type=TransformType.STRUCTURE,
        description="Reorder sections",
    )


# ---------------------------------------------------------------------------
# Transform chain
# ---------------------------------------------------------------------------

class TransformChain:
    """Chain multiple transforms together."""

    def __init__(self) -> None:
        self._transforms: List[Tuple[str, Callable[[str], TransformResult]]] = []

    def add(
        self,
        name: str,
        func: Callable[[str], TransformResult],
    ) -> "TransformChain":
        self._transforms.append((name, func))
        return self

    def execute(self, text: str) -> TransformChainResult:
        """Execute all transforms in order."""
        chain_result = TransformChainResult(original=text, final=text)
        current = text

        for name, func in self._transforms:
            result = func(current)
            chain_result.steps.append(result)
            current = result.transformed

        chain_result.final = current
        return chain_result

    @property
    def count(self) -> int:
        return len(self._transforms)


def create_transform_chain(
    transforms: Optional[List[Tuple[str, Callable[[str], TransformResult]]]] = None,
) -> TransformChain:
    """Create a transform chain with optional initial transforms."""
    chain = TransformChain()
    if transforms:
        for name, func in transforms:
            chain.add(name, func)
    return chain


def cleanup_transform() -> TransformChain:
    """Create a standard cleanup transform chain."""
    chain = TransformChain()
    chain.add("whitespace", normalize_whitespace)
    chain.add("links", normalize_links)
    chain.add("comments", strip_comments)
    return chain
