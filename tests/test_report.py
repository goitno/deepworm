"""Tests for deepworm.report."""

import os
import tempfile

from deepworm.report import (
    _slugify,
    extract_links,
    extract_sections,
    extract_toc,
    generate_toc_markdown,
    inject_toc,
    markdown_to_html,
    report_stats,
    report_summary,
    save_report,
)


def test_slugify():
    assert _slugify("Hello World!") == "hello-world"
    assert _slugify("AI & Machine Learning") == "ai-machine-learning"
    assert _slugify("  spaces  ") == "spaces"


def test_slugify_long():
    long_text = "a" * 100
    assert len(_slugify(long_text)) <= 60


def test_save_report():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = save_report("# Test Report\n\nContent here.", os.path.join(tmpdir, "test.md"))
        assert os.path.exists(path)
        with open(path) as f:
            content = f.read()
        assert "# Test Report" in content


def test_save_report_auto_name():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = save_report(
            "# Report",
            os.path.join(tmpdir, "auto.md"),
            topic="quantum computing",
        )
        assert os.path.exists(path)


def test_markdown_to_html_basic():
    """Should convert markdown to standalone HTML."""
    md = "# Hello World\n\nThis is a **test** report.\n\n- Item 1\n- Item 2"
    html = markdown_to_html(md, topic="Test")
    assert "<!DOCTYPE html>" in html
    assert "<h1>Hello World</h1>" in html
    assert "<strong>test</strong>" in html
    assert "<li>Item 1</li>" in html
    assert "deepworm" in html  # footer


def test_markdown_to_html_code_block():
    """Should handle code blocks."""
    md = "# Code\n\n```python\nprint('hello')\n```"
    html = markdown_to_html(md)
    assert "&lt;" not in html or "print" in html  # code preserved
    assert '<pre><code' in html


def test_markdown_to_html_links():
    """Should convert markdown links to HTML links."""
    md = "Check [this link](https://example.com) for more."
    html = markdown_to_html(md)
    assert '<a href="https://example.com">this link</a>' in html


def test_save_report_html(tmp_path):
    """Should save HTML format."""
    path = save_report(
        "# Test\n\nHello",
        str(tmp_path / "report.html"),
        topic="test",
        fmt="html",
    )
    content = open(path).read()
    assert "<!DOCTYPE html>" in content
    assert "<h1>Test</h1>" in content


def test_save_report_pdf_fallback(tmp_path):
    """PDF export should work even without weasyprint (saves HTML fallback)."""
    path = save_report(
        "# PDF Test\n\nPDF content here.",
        str(tmp_path / "report.pdf"),
        topic="test",
        fmt="pdf",
    )
    # Either a real PDF or an HTML fallback should exist
    assert os.path.exists(path)


def test_save_report_text(tmp_path):
    """Should save plain text format."""
    path = save_report(
        "# Title\n\n**Bold** and *italic* text.",
        str(tmp_path / "report.txt"),
        topic="test",
        fmt="text",
    )
    content = open(path).read()
    assert "Title" in content
    assert "**" not in content  # markdown stripped


SAMPLE_REPORT = """# My Research

## Executive Summary

This is a summary.

## Key Findings

Finding 1 is important.

### Sub-Finding A

Details about finding A.

## Sources

- [Source 1](https://example.com/1)
- [Source 2](https://example.com/2)
"""


def test_extract_toc():
    toc = extract_toc(SAMPLE_REPORT)
    assert len(toc) == 5
    assert toc[0]["text"] == "My Research"
    assert toc[0]["level"] == 1
    assert toc[1]["text"] == "Executive Summary"
    assert toc[1]["level"] == 2
    assert toc[2]["text"] == "Key Findings"
    assert toc[3]["text"] == "Sub-Finding A"
    assert toc[3]["level"] == 3
    assert toc[4]["text"] == "Sources"


def test_generate_toc_markdown():
    toc_md = generate_toc_markdown(SAMPLE_REPORT)
    assert "Table of Contents" in toc_md
    assert "[My Research]" in toc_md
    assert "[Key Findings]" in toc_md


def test_inject_toc():
    result = inject_toc(SAMPLE_REPORT)
    assert "Table of Contents" in result
    # Original content should still be there
    assert "Executive Summary" in result
    assert "Key Findings" in result


def test_inject_toc_empty():
    result = inject_toc("No headings here.")
    assert result == "No headings here."


def test_report_stats():
    stats = report_stats(SAMPLE_REPORT)
    assert stats["word_count"] > 0
    assert stats["heading_count"] == 5
    assert stats["link_count"] == 2
    assert stats["reading_time_minutes"] >= 1


def test_extract_sections():
    sections = extract_sections(SAMPLE_REPORT)
    assert len(sections) >= 3
    headings = [s["heading"] for s in sections]
    assert "Executive Summary" in headings
    assert "Key Findings" in headings
    assert "Sources" in headings


def test_extract_sections_content():
    sections = extract_sections(SAMPLE_REPORT)
    summary = next(s for s in sections if s["heading"] == "Executive Summary")
    assert "summary" in summary["content"].lower()


def test_extract_links():
    report = """# Title

Check [this link](https://example.com/page) and https://bare.example.com/path.

Also see [reference](https://docs.example.org).
"""
    links = extract_links(report)
    assert len(links) == 3
    urls = [l["url"] for l in links]
    assert "https://example.com/page" in urls
    assert "https://bare.example.com/path" in urls


def test_extract_links_dedup():
    report = "See https://example.com and https://example.com again."
    links = extract_links(report)
    assert len(links) == 1


def test_report_summary():
    summary = report_summary(SAMPLE_REPORT, max_sentences=2)
    assert len(summary) > 10
    assert summary.count(". ") <= 2 or summary.endswith(".")
