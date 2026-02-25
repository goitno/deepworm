"""Tests for deepworm.outline."""

from __future__ import annotations

import pytest

from deepworm.outline import (
    OutlineSection,
    ReportOutline,
    _count_sections,
    generate_outline,
    outline_from_report,
)


class TestOutlineSection:
    def test_defaults(self):
        s = OutlineSection(title="Intro", level=1)
        assert s.title == "Intro"
        assert s.level == 1
        assert s.key_points == []
        assert s.children == []
        assert s.estimated_words == 0

    def test_to_dict(self):
        s = OutlineSection(
            title="Test", level=1,
            key_points=["point1"],
            estimated_words=100,
            children=[OutlineSection(title="Sub", level=2)],
        )
        d = s.to_dict()
        assert d["title"] == "Test"
        assert len(d["children"]) == 1
        assert d["children"][0]["title"] == "Sub"


class TestReportOutline:
    def test_to_markdown(self):
        outline = ReportOutline(
            title="Test Topic",
            sections=[
                OutlineSection(title="Intro", level=1, key_points=["Define topic"]),
                OutlineSection(title="Analysis", level=1, estimated_words=500),
            ],
            total_estimated_words=800,
            style="comprehensive",
        )
        md = outline.to_markdown()
        assert "# Outline: Test Topic" in md
        assert "Intro" in md
        assert "Analysis" in md
        assert "comprehensive" in md

    def test_to_dict(self):
        outline = ReportOutline(
            title="Test",
            sections=[OutlineSection(title="S1", level=1)],
            total_estimated_words=500,
        )
        d = outline.to_dict()
        assert d["title"] == "Test"
        assert len(d["sections"]) == 1

    def test_section_count(self):
        outline = ReportOutline(
            title="Test",
            sections=[
                OutlineSection(
                    title="Parent", level=1,
                    children=[
                        OutlineSection(title="Child1", level=2),
                        OutlineSection(title="Child2", level=2),
                    ],
                ),
                OutlineSection(title="Other", level=1),
            ],
        )
        assert outline.section_count == 4  # 2 top + 2 children


class TestGenerateOutline:
    def test_comprehensive(self):
        outline = generate_outline("quantum computing", style="comprehensive")
        assert outline.style == "comprehensive"
        assert len(outline.sections) > 0
        assert outline.total_estimated_words > 0

    def test_brief(self):
        outline = generate_outline("AI ethics", style="brief")
        assert outline.style == "brief"
        assert len(outline.sections) <= 3

    def test_academic(self):
        outline = generate_outline("neural networks", style="academic")
        assert outline.style == "academic"
        titles = [s.title for s in outline.sections]
        assert "Abstract" in titles
        assert "Literature Review" in titles

    def test_comparison_topic(self):
        outline = generate_outline("Python vs JavaScript")
        titles = [s.title for s in outline.sections]
        assert "Detailed Comparison" in titles or "Overview" in titles

    def test_custom_sections(self):
        outline = generate_outline("topic", num_sections=2)
        assert len(outline.sections) == 2

    def test_invalid_style_defaults_comprehensive(self):
        outline = generate_outline("topic", style="unknown")
        assert outline.style == "comprehensive"


class TestOutlineFromReport:
    def test_extracts_sections(self):
        report = """# Main Title

## Introduction
Some intro text here.

## Methods
Methods paragraph.

### Data Collection
Data details.

## Results
Results text.
"""
        outline = outline_from_report(report)
        assert outline.title == "Main Title"
        assert len(outline.sections) == 3

    def test_nested_sections(self):
        report = """# Title

## Section A

### Sub A1

### Sub A2

## Section B
"""
        outline = outline_from_report(report)
        section_a = outline.sections[0]
        assert section_a.title == "Section A"
        assert len(section_a.children) == 2

    def test_empty_report(self):
        outline = outline_from_report("")
        assert outline.sections == []

    def test_word_estimation(self):
        report = """# Title

## Section One
Word one two three four five six seven eight nine ten.

## Section Two
Another set of words here.
"""
        outline = outline_from_report(report)
        assert outline.total_estimated_words > 0


class TestCountSections:
    def test_flat(self):
        sections = [
            OutlineSection(title="A", level=1),
            OutlineSection(title="B", level=1),
        ]
        assert _count_sections(sections) == 2

    def test_nested(self):
        sections = [
            OutlineSection(
                title="A", level=1,
                children=[
                    OutlineSection(title="A1", level=2),
                    OutlineSection(
                        title="A2", level=2,
                        children=[OutlineSection(title="A2a", level=3)],
                    ),
                ],
            ),
        ]
        assert _count_sections(sections) == 4
