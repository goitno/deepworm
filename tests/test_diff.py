"""Tests for deepworm.diff."""

from deepworm.diff import diff_reports, diff_summary, side_by_side


OLD_REPORT = """# Research on Topic A

## Summary

This is the original summary.

## Findings

Finding 1: Something important.
Finding 2: Another detail.

## Sources

- https://example.com/1
"""

NEW_REPORT = """# Research on Topic A

## Summary

This is the updated summary with more detail.

## Findings

Finding 1: Something important.
Finding 3: A completely new finding.

## New Section

Added new analysis here.

## Sources

- https://example.com/1
- https://example.com/2
"""


def test_diff_reports_shows_changes():
    diff = diff_reports(OLD_REPORT, NEW_REPORT)
    assert len(diff) > 0
    assert "+" in diff  # Added lines
    assert "-" in diff  # Removed lines


def test_diff_reports_identical():
    diff = diff_reports(OLD_REPORT, OLD_REPORT)
    assert diff == ""


def test_diff_reports_labels():
    diff = diff_reports(OLD_REPORT, NEW_REPORT, old_label="v1.md", new_label="v2.md")
    assert "v1.md" in diff
    assert "v2.md" in diff


def test_diff_summary_counts():
    summary = diff_summary(OLD_REPORT, NEW_REPORT)
    assert summary["added_lines"] > 0
    assert summary["removed_lines"] > 0
    assert 0 < summary["similarity_ratio"] < 1


def test_diff_summary_sections():
    summary = diff_summary(OLD_REPORT, NEW_REPORT)
    assert "New Section" in summary["added_sections"]


def test_diff_summary_identical():
    summary = diff_summary(OLD_REPORT, OLD_REPORT)
    assert summary["added_lines"] == 0
    assert summary["removed_lines"] == 0
    assert summary["similarity_ratio"] == 1.0


def test_side_by_side():
    result = side_by_side(OLD_REPORT, NEW_REPORT)
    assert "OLD" in result
    assert "NEW" in result
    assert "│" in result


def test_side_by_side_width():
    result = side_by_side("line1\nline2", "line1\nline3", width=60)
    lines = result.splitlines()
    assert len(lines) >= 3  # header + divider + content
