"""Tests for deepworm.citations module."""

import pytest

from deepworm.citations import (
    Citation,
    citations_from_sources,
    format_apa,
    format_bibtex,
    format_chicago,
    format_citations,
    format_mla,
)


@pytest.fixture
def sample_citation():
    return Citation(
        url="https://arxiv.org/abs/2401.12345",
        title="Deep Learning for Research Automation",
        author="Smith, J.",
        publisher="arXiv",
        date_published="2024-01-15",
        date_accessed="2024-06-01",
    )


@pytest.fixture
def minimal_citation():
    return Citation(
        url="https://example.com/article",
        title="Test Article",
    )


class TestCitation:
    def test_auto_publisher(self, minimal_citation):
        assert minimal_citation.publisher == "Example"

    def test_known_publisher(self):
        c = Citation(url="https://github.com/repo", title="Repo")
        assert c.publisher == "GitHub"

    def test_auto_date_accessed(self, minimal_citation):
        # Should be today's date
        assert len(minimal_citation.date_accessed) == 10  # YYYY-MM-DD


class TestAPA:
    def test_full(self, sample_citation):
        result = format_apa(sample_citation)
        assert "Smith, J." in result
        assert "(2024-01-15)" in result
        assert "*Deep Learning for Research Automation*" in result
        assert "arxiv.org" in result

    def test_no_date(self, minimal_citation):
        result = format_apa(minimal_citation)
        assert "(n.d.)" in result

    def test_no_author(self, minimal_citation):
        result = format_apa(minimal_citation)
        assert "Example." in result  # publisher used as author


class TestMLA:
    def test_full(self, sample_citation):
        result = format_mla(sample_citation)
        assert "Smith, J." in result
        assert '"Deep Learning for Research Automation."' in result
        assert "*arXiv*" in result

    def test_no_date(self, minimal_citation):
        result = format_mla(minimal_citation)
        assert "Accessed" in result


class TestChicago:
    def test_full(self, sample_citation):
        result = format_chicago(sample_citation)
        assert "Smith, J." in result
        assert '"Deep Learning for Research Automation."' in result
        assert "Accessed" in result


class TestBibTeX:
    def test_full(self, sample_citation):
        result = format_bibtex(sample_citation)
        assert "@online{" in result
        assert "title" in result
        assert "author    = {Smith, J.}" in result
        assert "year      = {2024}" in result
        assert result.strip().endswith("}")

    def test_custom_key(self, sample_citation):
        result = format_bibtex(sample_citation, key="smith2024deep")
        assert "@online{smith2024deep," in result


class TestBatchFormatting:
    def test_format_citations_apa(self, sample_citation, minimal_citation):
        result = format_citations([sample_citation, minimal_citation], style="apa")
        assert "[1]" in result
        assert "[2]" in result

    def test_format_citations_bibtex(self, sample_citation):
        result = format_citations([sample_citation], style="bibtex")
        assert "@online{" in result
        assert "[1]" not in result  # bibtex doesn't number

    def test_unknown_style(self, sample_citation):
        with pytest.raises(ValueError, match="Unknown citation style"):
            format_citations([sample_citation], style="ieee")


class TestFromSources:
    def test_basic(self):
        sources = [
            {"url": "https://example.com", "title": "Example"},
            {"url": "https://test.org", "title": "Test", "author": "Doe"},
        ]
        citations = citations_from_sources(sources)
        assert len(citations) == 2
        assert citations[1].author == "Doe"
