"""Report diffing — compare two research reports.

Generates a textual diff showing added, removed, and changed sections
between two reports. Useful for tracking how research evolves over time.

Usage:
    deepworm --diff report_v1.md report_v2.md
"""

from __future__ import annotations

import difflib
from typing import Optional


def diff_reports(
    old: str,
    new: str,
    old_label: str = "previous",
    new_label: str = "current",
    context_lines: int = 3,
) -> str:
    """Generate a unified diff between two reports.

    Args:
        old: Previous report content.
        new: Current report content.
        old_label: Label for the old report.
        new_label: Label for the new report.
        context_lines: Number of context lines around changes.

    Returns:
        Unified diff string. Empty string if reports are identical.
    """
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)

    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=old_label,
        tofile=new_label,
        n=context_lines,
    )

    return "".join(diff)


def diff_summary(old: str, new: str) -> dict:
    """Generate a summary of differences between two reports.

    Returns:
        Dict with 'added_lines', 'removed_lines', 'changed_sections',
        'similarity_ratio'.
    """
    old_lines = old.splitlines()
    new_lines = new.splitlines()

    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    ratio = matcher.ratio()

    added = 0
    removed = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "insert":
            added += j2 - j1
        elif tag == "delete":
            removed += i2 - i1
        elif tag == "replace":
            added += j2 - j1
            removed += i2 - i1

    # Identify changed sections by heading
    import re
    old_headings = set(re.findall(r'^#{1,6}\s+(.+)$', old, re.MULTILINE))
    new_headings = set(re.findall(r'^#{1,6}\s+(.+)$', new, re.MULTILINE))

    added_sections = new_headings - old_headings
    removed_sections = old_headings - new_headings

    return {
        "added_lines": added,
        "removed_lines": removed,
        "added_sections": sorted(added_sections),
        "removed_sections": sorted(removed_sections),
        "similarity_ratio": round(ratio, 3),
    }


def side_by_side(old: str, new: str, width: int = 80) -> str:
    """Generate a side-by-side comparison of two reports.

    Returns:
        Formatted comparison string.
    """
    old_lines = old.splitlines()
    new_lines = new.splitlines()

    # Pad to same length
    max_len = max(len(old_lines), len(new_lines))
    old_lines += [""] * (max_len - len(old_lines))
    new_lines += [""] * (max_len - len(new_lines))

    half = width // 2 - 2
    divider = "│"

    result = []
    result.append(f"{'OLD':^{half}} {divider} {'NEW':^{half}}")
    result.append("─" * half + "┼" + "─" * half)

    for old_line, new_line in zip(old_lines, new_lines):
        left = old_line[:half].ljust(half)
        right = new_line[:half].ljust(half)
        marker = divider if old_line == new_line else "│"
        result.append(f"{left} {marker} {right}")

    return "\n".join(result)
