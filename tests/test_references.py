"""Tests for references and bibliography management."""

import pytest
from deepworm.references import (
    Reference,
    Bibliography,
    extract_references,
    create_reference,
    inject_bibliography,
    merge_bibliographies,
    _extract_domain,
)


# --- Reference ---

class TestReference:
    def test_basic_reference(self):
        ref = Reference(title="Test Article")
        assert ref.title == "Test Article"
        assert ref.authors == []
        assert ref.ref_type == "web"

    def test_author_string_single(self):
        ref = Reference(title="T", authors=["John Smith"])
        assert ref.author_string == "John Smith"

    def test_author_string_two(self):
        ref = Reference(title="T", authors=["John Smith", "Jane Doe"])
        assert ref.author_string == "John Smith & Jane Doe"

    def test_author_string_many(self):
        ref = Reference(title="T", authors=["A", "B", "C"])
        assert ref.author_string == "A et al."

    def test_author_string_none(self):
        ref = Reference(title="T")
        assert ref.author_string == "Unknown"

    def test_citation_key(self):
        ref = Reference(title="T", authors=["John Smith"], year="2023")
        assert ref.citation_key == "Smith2023"

    def test_citation_key_no_author(self):
        ref = Reference(title="T", year="2023")
        assert ref.citation_key == "Unknown2023"

    def test_citation_key_no_year(self):
        ref = Reference(title="T", authors=["Jane Doe"])
        assert ref.citation_key == "Doen.d."

    def test_to_apa(self):
        ref = Reference(
            title="Machine Learning Basics",
            authors=["John Smith", "Jane Doe"],
            year="2023",
            journal="AI Journal",
            volume="10",
            pages="1-25",
        )
        apa = ref.to_apa()
        assert "Smith, J." in apa
        assert "Doe, J." in apa
        assert "(2023)" in apa
        assert "*AI Journal*" in apa

    def test_to_apa_with_doi(self):
        ref = Reference(title="T", year="2023", doi="10.1234/test")
        apa = ref.to_apa()
        assert "https://doi.org/10.1234/test" in apa

    def test_to_mla_article(self):
        ref = Reference(
            title="Deep Learning",
            authors=["John Smith"],
            year="2023",
            journal="AI Review",
            ref_type="article",
        )
        mla = ref.to_mla()
        assert "Smith, John." in mla
        assert '"Deep Learning."' in mla
        assert "*AI Review*" in mla

    def test_to_mla_book(self):
        ref = Reference(
            title="Python Handbook",
            authors=["Jane Doe"],
            year="2023",
            ref_type="book",
        )
        mla = ref.to_mla()
        assert "*Python Handbook*" in mla

    def test_to_bibtex_article(self):
        ref = Reference(
            title="Test Article",
            authors=["John Smith"],
            year="2023",
            journal="Test Journal",
            doi="10.1234/test",
            ref_type="article",
        )
        bib = ref.to_bibtex()
        assert "@article{" in bib
        assert "author = {John Smith}" in bib
        assert "title = {Test Article}" in bib
        assert "doi = {10.1234/test}" in bib

    def test_to_bibtex_web(self):
        ref = Reference(title="Web Page", url="https://example.com")
        bib = ref.to_bibtex()
        assert "@misc{" in bib

    def test_to_dict(self):
        ref = Reference(
            title="Test", authors=["Author"], year="2023",
            url="https://example.com", doi="10.1234/test",
        )
        d = ref.to_dict()
        assert d["title"] == "Test"
        assert d["authors"] == ["Author"]
        assert d["year"] == "2023"
        assert d["url"] == "https://example.com"
        assert d["doi"] == "10.1234/test"


# --- Bibliography ---

class TestBibliography:
    def test_empty(self):
        bib = Bibliography()
        assert len(bib.references) == 0

    def test_add_reference(self):
        bib = Bibliography()
        ref = Reference(title="Test")
        bib.add(ref)
        assert len(bib.references) == 1
        assert ref._id == 1

    def test_get_by_id(self):
        bib = Bibliography()
        ref = Reference(title="Test")
        bib.add(ref)
        found = bib.get(1)
        assert found is ref

    def test_get_missing(self):
        bib = Bibliography()
        assert bib.get(99) is None

    def test_find_by_title(self):
        bib = Bibliography()
        bib.add(Reference(title="Machine Learning Guide"))
        bib.add(Reference(title="Python Tutorial"))
        results = bib.find_by_title("machine")
        assert len(results) == 1

    def test_find_by_author(self):
        bib = Bibliography()
        bib.add(Reference(title="A", authors=["John Smith"]))
        bib.add(Reference(title="B", authors=["Jane Doe"]))
        results = bib.find_by_author("smith")
        assert len(results) == 1

    def test_find_by_year(self):
        bib = Bibliography()
        bib.add(Reference(title="A", year="2023"))
        bib.add(Reference(title="B", year="2024"))
        results = bib.find_by_year("2023")
        assert len(results) == 1

    def test_sort_by_author(self):
        bib = Bibliography()
        bib.add(Reference(title="T", authors=["Zoe"]))
        bib.add(Reference(title="T", authors=["Alice"]))
        bib.sort(by="author")
        assert bib.references[0].authors[0] == "Alice"

    def test_sort_by_year(self):
        bib = Bibliography()
        bib.add(Reference(title="T", year="2025"))
        bib.add(Reference(title="T", year="2020"))
        bib.sort(by="year")
        assert bib.references[0].year == "2020"

    def test_sort_by_title(self):
        bib = Bibliography()
        bib.add(Reference(title="Zebra"))
        bib.add(Reference(title="Apple"))
        bib.sort(by="title")
        assert bib.references[0].title == "Apple"

    def test_deduplicate(self):
        bib = Bibliography()
        bib.add(Reference(title="Same Title", year="2023"))
        bib.add(Reference(title="Same Title", year="2023"))
        bib.add(Reference(title="Different", year="2023"))
        removed = bib.deduplicate()
        assert removed == 1
        assert len(bib.references) == 2

    def test_by_type(self):
        bib = Bibliography()
        bib.add(Reference(title="A", ref_type="web"))
        bib.add(Reference(title="B", ref_type="article"))
        bib.add(Reference(title="C", ref_type="web"))
        groups = bib.by_type
        assert len(groups["web"]) == 2
        assert len(groups["article"]) == 1

    def test_years(self):
        bib = Bibliography()
        bib.add(Reference(title="A", year="2023"))
        bib.add(Reference(title="B", year="2020"))
        bib.add(Reference(title="C", year="2023"))
        assert bib.years == ["2020", "2023"]

    def test_to_apa(self):
        bib = Bibliography()
        bib.add(Reference(title="Test", authors=["John Smith"], year="2023"))
        apa = bib.to_apa()
        assert "## References" in apa
        assert "Smith" in apa

    def test_to_mla(self):
        bib = Bibliography()
        bib.add(Reference(title="Test", authors=["John Smith"], year="2023"))
        mla = bib.to_mla()
        assert "## References" in mla

    def test_to_bibtex(self):
        bib = Bibliography()
        bib.add(Reference(title="Test", authors=["John Smith"], year="2023"))
        bibtex = bib.to_bibtex()
        assert "@misc{" in bibtex

    def test_to_numbered(self):
        bib = Bibliography()
        bib.add(Reference(title="First", authors=["A"]))
        bib.add(Reference(title="Second", authors=["B"]))
        numbered = bib.to_numbered()
        assert "[1]" in numbered
        assert "[2]" in numbered

    def test_to_dict(self):
        bib = Bibliography()
        bib.add(Reference(title="T", year="2023", ref_type="web"))
        d = bib.to_dict()
        assert d["count"] == 1
        assert d["types"]["web"] == 1
        assert d["years"] == ["2023"]


# --- Extract References ---

SAMPLE_TEXT = """
# Research Report

According to Smith (2023), machine learning has evolved significantly.
This is supported by (Johnson & Lee, 2022) and other researchers.

For more details, see [TensorFlow Documentation](https://tensorflow.org/docs)
and [PyTorch Guide](https://pytorch.org/tutorials).

The original paper (doi: 10.1038/nature12373) presented groundbreaking results.

Additional resources: https://arxiv.org/papers
"""


class TestExtractReferences:
    def test_extracts_markdown_links(self):
        bib = extract_references(SAMPLE_TEXT)
        urls = [r.url for r in bib.references if r.url]
        assert any("tensorflow.org" in u for u in urls)
        assert any("pytorch.org" in u for u in urls)

    def test_extracts_inline_citations(self):
        bib = extract_references(SAMPLE_TEXT)
        authors = []
        for ref in bib.references:
            authors.extend(ref.authors)
        assert any("Johnson" in a for a in authors)

    def test_extracts_author_year(self):
        bib = extract_references(SAMPLE_TEXT)
        authors = []
        for ref in bib.references:
            authors.extend(ref.authors)
        assert any("Smith" in a for a in authors)

    def test_extracts_dois(self):
        bib = extract_references(SAMPLE_TEXT)
        dois = [r.doi for r in bib.references if r.doi]
        assert any("10.1038" in d for d in dois)

    def test_extracts_bare_urls(self):
        bib = extract_references(SAMPLE_TEXT)
        urls = [r.url for r in bib.references if r.url]
        assert any("arxiv.org" in u for u in urls)

    def test_no_duplicate_urls(self):
        text = "[Link](https://example.com) and https://example.com again"
        bib = extract_references(text)
        urls = [r.url for r in bib.references if r.url]
        assert urls.count("https://example.com") == 1

    def test_empty_text(self):
        bib = extract_references("")
        assert len(bib.references) == 0

    def test_no_references(self):
        bib = extract_references("Just a plain paragraph with no references.")
        assert len(bib.references) == 0


# --- Create Reference ---

class TestCreateReference:
    def test_basic(self):
        ref = create_reference("Test Article", authors=["John"], year="2023")
        assert ref.title == "Test Article"
        assert ref.authors == ["John"]
        assert ref.year == "2023"

    def test_with_kwargs(self):
        ref = create_reference(
            "T", volume="10", pages="1-25", publisher="Springer",
        )
        assert ref.volume == "10"
        assert ref.pages == "1-25"
        assert ref.publisher == "Springer"


# --- Inject Bibliography ---

class TestInjectBibliography:
    def test_inject_apa(self):
        bib = Bibliography()
        bib.add(Reference(title="Test", authors=["Author"], year="2023"))
        result = inject_bibliography("Report text here.", bib, style="apa")
        assert "Report text here." in result
        assert "## References" in result

    def test_inject_numbered(self):
        bib = Bibliography()
        bib.add(Reference(title="Test", authors=["Author"]))
        result = inject_bibliography("Report.", bib, style="numbered")
        assert "[1]" in result

    def test_inject_bibtex(self):
        bib = Bibliography()
        bib.add(Reference(title="Test", authors=["Author"], year="2023"))
        result = inject_bibliography("Report.", bib, style="bibtex")
        assert "@misc{" in result


# --- Merge Bibliographies ---

class TestMergeBibliographies:
    def test_merge_two(self):
        bib_a = Bibliography()
        bib_a.add(Reference(title="Article A", year="2023"))
        bib_b = Bibliography()
        bib_b.add(Reference(title="Article B", year="2024"))
        merged = merge_bibliographies(bib_a, bib_b)
        assert len(merged.references) == 2

    def test_merge_deduplicates(self):
        bib_a = Bibliography()
        bib_a.add(Reference(title="Same", year="2023"))
        bib_b = Bibliography()
        bib_b.add(Reference(title="Same", year="2023"))
        merged = merge_bibliographies(bib_a, bib_b)
        assert len(merged.references) == 1

    def test_merge_empty(self):
        merged = merge_bibliographies(Bibliography(), Bibliography())
        assert len(merged.references) == 0


# --- Helpers ---

class TestHelpers:
    def test_extract_domain(self):
        assert _extract_domain("https://www.example.com/path") == "example.com"
        assert _extract_domain("https://docs.python.org/3/") == "docs.python.org"
        assert _extract_domain("http://localhost:8000") == "localhost:8000"
