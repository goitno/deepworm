"""Tests for deepworm.formatter – advanced markdown formatting."""

import pytest

from deepworm.formatter import (
    EmphasisStyle,
    FormatOptions,
    FormatResult,
    ListStyle,
    TableAlignment,
    add_heading_ids,
    add_language_labels,
    create_format_options,
    ensure_blank_lines_around_headings,
    format_document,
    format_table,
    normalize_blockquotes,
    normalize_code_fences,
    normalize_emphasis,
    normalize_lists,
    sort_list,
)


# ---------------------------------------------------------------------------
# FormatResult
# ---------------------------------------------------------------------------

class TestFormatResult:
    def test_changed(self):
        r = FormatResult(original="a", formatted="b", changes=1)
        assert r.changed is True

    def test_not_changed(self):
        r = FormatResult(original="a", formatted="a")
        assert r.changed is False


# ---------------------------------------------------------------------------
# List formatting
# ---------------------------------------------------------------------------

class TestNormalizeLists:
    def test_asterisk_to_dash(self):
        text = "* item1\n* item2"
        result = normalize_lists(text, ListStyle.DASH)
        assert "- item1" in result.formatted
        assert result.changes == 2

    def test_mixed_to_plus(self):
        text = "- a\n* b\n+ c"
        result = normalize_lists(text, ListStyle.PLUS)
        assert all("+ " in line for line in result.formatted.splitlines())

    def test_already_normalized(self):
        text = "- a\n- b"
        result = normalize_lists(text, ListStyle.DASH)
        assert result.changes == 0


class TestSortList:
    def test_alphabetical(self):
        text = "- cherry\n- apple\n- banana"
        result = sort_list(text)
        lines = result.formatted.splitlines()
        assert "apple" in lines[0]
        assert "banana" in lines[1]

    def test_reverse(self):
        text = "- a\n- c\n- b"
        result = sort_list(text, reverse=True)
        lines = result.formatted.splitlines()
        assert "c" in lines[0]


# ---------------------------------------------------------------------------
# Table formatting
# ---------------------------------------------------------------------------

class TestFormatTable:
    def test_basic(self):
        text = "| a | b |\n|---|---|\n| 1 | 2 |"
        result = format_table(text)
        assert "|" in result.formatted

    def test_alignment_center(self):
        text = "| h1 | h2 |\n|---|---|\n| data | x |"
        result = format_table(text, TableAlignment.CENTER)
        assert ":" in result.formatted

    def test_no_table(self):
        text = "Just text, no table."
        result = format_table(text)
        assert result.changes == 0


# ---------------------------------------------------------------------------
# Emphasis normalization
# ---------------------------------------------------------------------------

class TestNormalizeEmphasis:
    def test_underscore_to_asterisk(self):
        text = "__bold__ and _italic_"
        result = normalize_emphasis(text, EmphasisStyle.ASTERISK)
        assert "**bold**" in result.formatted
        assert "*italic*" in result.formatted

    def test_asterisk_to_underscore(self):
        text = "**bold** and *italic*"
        result = normalize_emphasis(text, EmphasisStyle.UNDERSCORE)
        assert "__bold__" in result.formatted
        assert "_italic_" in result.formatted

    def test_no_change(self):
        text = "**bold** and *italic*"
        result = normalize_emphasis(text, EmphasisStyle.ASTERISK)
        assert result.changes == 0


# ---------------------------------------------------------------------------
# Code fences
# ---------------------------------------------------------------------------

class TestCodeFences:
    def test_tilde_to_backtick(self):
        text = "~~~python\nprint('hi')\n~~~"
        result = normalize_code_fences(text, "```")
        assert "```python" in result.formatted
        assert result.changes == 2

    def test_no_alternates(self):
        text = "```python\nprint('hi')\n```"
        result = normalize_code_fences(text, "```")
        assert result.changes == 0


class TestAddLanguageLabels:
    def test_adds_label(self):
        text = "```\ncode\n```"
        result = add_language_labels(text, "python")
        assert "```python" in result.formatted
        assert result.changes == 1

    def test_no_default(self):
        text = "```\ncode\n```"
        result = add_language_labels(text, "")
        assert result.changes == 0


# ---------------------------------------------------------------------------
# Blockquotes
# ---------------------------------------------------------------------------

class TestNormalizeBlockquotes:
    def test_normalize(self):
        text = ">  hello"
        result = normalize_blockquotes(text)
        assert result.formatted == "> hello"

    def test_nested(self):
        text = ">> nested"
        result = normalize_blockquotes(text)
        assert "> > " in result.formatted


# ---------------------------------------------------------------------------
# Heading formatting
# ---------------------------------------------------------------------------

class TestAddHeadingIds:
    def test_adds_ids(self):
        text = "# My Heading\n## Another One"
        result = add_heading_ids(text)
        assert "{#my-heading}" in result.formatted
        assert "{#another-one}" in result.formatted

    def test_existing_id_replaced(self):
        text = "# Title {#old-id}"
        result = add_heading_ids(text)
        assert "{#title}" in result.formatted


class TestBlankLinesAroundHeadings:
    def test_adds_blanks(self):
        text = "text\n# Heading\nmore text"
        result = ensure_blank_lines_around_headings(text)
        lines = result.formatted.splitlines()
        heading_idx = next(i for i, l in enumerate(lines) if l.startswith("#"))
        assert lines[heading_idx - 1] == ""
        assert lines[heading_idx + 1] == ""

    def test_already_has_blanks(self):
        text = "text\n\n# Heading\n\nmore text"
        result = ensure_blank_lines_around_headings(text)
        assert result.changes == 0


# ---------------------------------------------------------------------------
# Full document formatting
# ---------------------------------------------------------------------------

class TestFormatDocument:
    def test_default_options(self):
        text = "* item\n# Heading\ntext"
        result = format_document(text)
        assert "- item" in result.formatted
        assert result.formatted.endswith("\n")

    def test_custom_options(self):
        opts = FormatOptions(
            list_style=ListStyle.ASTERISK,
            emphasis_style=EmphasisStyle.UNDERSCORE,
        )
        text = "- item\n**bold**"
        result = format_document(text, opts)
        assert "* item" in result.formatted
        assert "__bold__" in result.formatted


class TestCreateFormatOptions:
    def test_kwargs(self):
        opts = create_format_options(line_width=100, trailing_newline=False)
        assert opts.line_width == 100
        assert opts.trailing_newline is False

    def test_default(self):
        opts = create_format_options()
        assert opts.list_style == ListStyle.DASH
