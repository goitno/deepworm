"""Tests for table of contents module."""

import pytest
from deepworm.toc import (
    TocEntry,
    TableOfContents,
    extract_toc,
    generate_toc,
    inject_toc,
    merge_tocs,
    _slugify,
    _assign_numbers,
)


SAMPLE_DOC = """# Introduction

Some intro text.

## Background

Background info.

## Methods

### Data Collection

Details about data.

### Analysis

Analysis methods.

## Results

The results.

## Conclusion

Final thoughts.
"""


# --- TocEntry ---

class TestTocEntry:
    def test_basic(self):
        entry = TocEntry(title="Hello World", level=1)
        assert entry.title == "Hello World"
        assert entry.level == 1

    def test_auto_anchor(self):
        entry = TocEntry(title="Hello World", level=1)
        assert entry.anchor == "hello-world"

    def test_custom_anchor(self):
        entry = TocEntry(title="Test", level=1, anchor="custom-anchor")
        assert entry.anchor == "custom-anchor"

    def test_depth_no_children(self):
        entry = TocEntry(title="Leaf", level=1)
        assert entry.depth == 0

    def test_depth_with_children(self):
        entry = TocEntry(
            title="Parent", level=1,
            children=[TocEntry(title="Child", level=2)],
        )
        assert entry.depth == 1

    def test_to_dict(self):
        entry = TocEntry(title="Test", level=2, line_number=5)
        d = entry.to_dict()
        assert d["title"] == "Test"
        assert d["level"] == 2
        assert d["line_number"] == 5


# --- TableOfContents ---

class TestTableOfContents:
    def test_empty(self):
        toc = TableOfContents()
        assert toc.entry_count == 0

    def test_flat(self):
        toc = TableOfContents(entries=[
            TocEntry("A", 1),
            TocEntry("B", 2),
            TocEntry("C", 1),
        ])
        assert len(toc.flat) == 3

    def test_filter_by_level(self):
        toc = TableOfContents(entries=[
            TocEntry("H1", 1),
            TocEntry("H2", 2),
            TocEntry("H3", 3),
        ])
        filtered = toc.filter_by_level(min_level=1, max_level=2)
        assert filtered.entry_count == 2

    def test_to_markdown(self):
        toc = TableOfContents(entries=[
            TocEntry("Intro", 1),
            TocEntry("Methods", 2),
        ])
        md = toc.to_markdown()
        assert "Table of Contents" in md
        assert "[Intro](#intro)" in md
        assert "[Methods](#methods)" in md

    def test_to_markdown_no_links(self):
        toc = TableOfContents(
            entries=[TocEntry("Test", 1)],
            include_links=False,
        )
        md = toc.to_markdown()
        assert "Test" in md
        assert "#" not in md.split("\n", 2)[-1]  # No anchor links in body

    def test_to_numbered_markdown(self):
        toc = TableOfContents(entries=[
            TocEntry("A", 1),
            TocEntry("B", 1),
            TocEntry("C", 2),
        ])
        md = toc.to_numbered_markdown()
        assert "1 A" in md
        assert "2 B" in md

    def test_to_html(self):
        toc = TableOfContents(entries=[
            TocEntry("Intro", 1),
        ])
        html = toc.to_html()
        assert "<nav>" in html
        assert "Intro" in html

    def test_to_dict(self):
        toc = TableOfContents(entries=[TocEntry("A", 1)])
        d = toc.to_dict()
        assert d["entry_count"] == 1

    def test_max_depth(self):
        toc = TableOfContents(
            max_depth=2,
            entries=[
                TocEntry("H1", 1),
                TocEntry("H2", 2),
                TocEntry("H3", 3),
            ],
        )
        md = toc.to_markdown()
        assert "H3" not in md


# --- extract_toc ---

class TestExtractToc:
    def test_basic(self):
        toc = extract_toc(SAMPLE_DOC)
        assert toc.entry_count >= 5

    def test_levels(self):
        toc = extract_toc(SAMPLE_DOC)
        entries = toc.flat
        assert entries[0].level == 1  # Introduction
        assert entries[1].level == 2  # Background

    def test_titles(self):
        toc = extract_toc(SAMPLE_DOC)
        titles = [e.title for e in toc.flat]
        assert "Introduction" in titles
        assert "Methods" in titles
        assert "Conclusion" in titles

    def test_line_numbers(self):
        toc = extract_toc(SAMPLE_DOC)
        for entry in toc.flat:
            assert entry.line_number > 0

    def test_max_depth(self):
        toc = extract_toc(SAMPLE_DOC, max_depth=2)
        for entry in toc.flat:
            assert entry.level <= 2

    def test_duplicate_anchors(self):
        text = "# Test\n\n## Test\n\n### Test\n"
        toc = extract_toc(text)
        anchors = [e.anchor for e in toc.flat]
        assert len(set(anchors)) == len(anchors)  # All unique

    def test_no_headings(self):
        toc = extract_toc("Just plain text without headings.")
        assert toc.entry_count == 0

    def test_anchor_generation(self):
        toc = extract_toc("# Hello World\n")
        assert toc.flat[0].anchor == "hello-world"


# --- generate_toc ---

class TestGenerateToc:
    def test_basic(self):
        result = generate_toc(SAMPLE_DOC)
        assert "Table of Contents" in result
        assert "Introduction" in result

    def test_custom_title(self):
        result = generate_toc(SAMPLE_DOC, title="Contents")
        assert "Contents" in result

    def test_numbered(self):
        result = generate_toc(SAMPLE_DOC, numbered=True)
        assert "1" in result

    def test_max_depth(self):
        result = generate_toc(SAMPLE_DOC, max_depth=1)
        assert "Introduction" in result
        assert "Data Collection" not in result


# --- inject_toc ---

class TestInjectToc:
    def test_with_marker(self):
        text = "# Title\n\n<!-- TOC -->\n\n## Section 1\n\n## Section 2\n"
        result = inject_toc(text)
        assert "Table of Contents" in result
        assert "<!-- TOC -->" in result

    def test_double_marker_replace(self):
        text = "# Title\n\n<!-- TOC -->\nOld TOC\n<!-- TOC -->\n\n## Section\n"
        result = inject_toc(text)
        assert "Old TOC" not in result
        assert "Table of Contents" in result

    def test_no_marker_after_heading(self):
        text = "# Main Title\n\nSome text.\n\n## Section\n"
        result = inject_toc(text)
        assert "Table of Contents" in result

    def test_no_headings(self):
        text = "Just text without any headings."
        result = inject_toc(text)
        assert "Table of Contents" in result

    def test_numbered(self):
        text = "<!-- TOC -->\n# A\n## B\n"
        result = inject_toc(text, numbered=True)
        assert "1" in result


# --- merge_tocs ---

class TestMergeTocs:
    def test_merge(self):
        toc_a = extract_toc("# A\n## B\n")
        toc_b = extract_toc("# C\n## D\n")
        merged = merge_tocs(toc_a, toc_b)
        titles = [e.title for e in merged.flat]
        assert "A" in titles
        assert "C" in titles

    def test_merge_dedup(self):
        toc_a = extract_toc("# Same Title\n")
        toc_b = extract_toc("# Same Title\n")
        merged = merge_tocs(toc_a, toc_b)
        # Same anchor → deduplicated (but second has -1 suffix)
        assert merged.entry_count <= 2


# --- Helpers ---

class TestHelpers:
    def test_slugify(self):
        assert _slugify("Hello World") == "hello-world"
        assert _slugify("Test 123!") == "test-123"
        assert _slugify("  Spaces  ") == "spaces"

    def test_slugify_special_chars(self):
        assert _slugify("What's New?") == "whats-new"
        assert _slugify("a/b/c") == "abc"

    def test_assign_numbers(self):
        entries = [
            TocEntry("A", 1),
            TocEntry("B", 2),
            TocEntry("C", 2),
            TocEntry("D", 1),
        ]
        result = _assign_numbers(entries)
        numbers = [n for _, n in result]
        assert numbers[0] == "1"
        assert numbers[1] == "1.1"
        assert numbers[2] == "1.2"
        assert numbers[3] == "2"
