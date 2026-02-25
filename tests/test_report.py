"""Tests for deepworm.report."""

import os
import tempfile

from deepworm.report import _slugify, markdown_to_html, save_report


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
