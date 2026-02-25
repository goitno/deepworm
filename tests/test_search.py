"""Tests for deepworm.search."""

import re

from deepworm.search import (
    SearchResult,
    _extract_ddg_url,
    _extract_text_from_html,
    search_web,
)


def test_search_result_dataclass():
    r = SearchResult(title="Test", url="https://example.com", snippet="Hello")
    assert r.title == "Test"
    assert r.body is None


def test_extract_text_from_html():
    html = "<html><head><title>T</title></head><body><p>Hello World</p></body></html>"
    text = _extract_text_from_html(html)
    assert "Hello World" in text
    assert "<p>" not in text


def test_extract_text_removes_scripts():
    html = '<script>alert("xss")</script><p>Content</p>'
    text = _extract_text_from_html(html)
    assert "alert" not in text
    assert "Content" in text


def test_extract_text_removes_style():
    html = "<style>body{color:red}</style><p>Visible</p>"
    text = _extract_text_from_html(html)
    assert "color" not in text
    assert "Visible" in text


def test_extract_text_decodes_entities():
    html = "<p>A &amp; B &lt; C &gt; D</p>"
    text = _extract_text_from_html(html)
    assert "A & B < C > D" in text


def test_extract_ddg_url():
    redirect = "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fpage&rut=abc"
    assert _extract_ddg_url(redirect) == "https://example.com/page"


def test_extract_ddg_url_passthrough():
    """Non-DDG URLs should pass through unchanged."""
    url = "https://example.com/page"
    assert _extract_ddg_url(url) == url


def test_search_web_returns_results():
    """Integration test: search should return results (requires network)."""
    results = search_web("python programming language", max_results=3)
    # We can't guarantee results in CI, but the function should not crash
    assert isinstance(results, list)
    for r in results:
        assert isinstance(r, SearchResult)
