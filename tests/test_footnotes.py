"""Tests for footnotes module."""

from deepworm.footnotes import (
    Footnote,
    FootnoteResult,
    add_footnotes,
    renumber_footnotes,
    strip_footnotes,
    merge_footnotes,
)


class TestFootnote:
    def test_to_dict_basic(self):
        fn = Footnote(number=1, text="Example source")
        d = fn.to_dict()
        assert d["number"] == 1
        assert d["text"] == "Example source"
        assert "source_url" not in d

    def test_to_dict_with_url(self):
        fn = Footnote(number=2, text="Link", source_url="https://example.com")
        d = fn.to_dict()
        assert d["source_url"] == "https://example.com"


class TestFootnoteResult:
    def test_render_markdown(self):
        result = FootnoteResult(
            body="Hello[^1] world[^2]",
            footnotes=[
                Footnote(1, "First note"),
                Footnote(2, "Second note", "https://example.com"),
            ],
        )
        md = result.render("markdown")
        assert "## Footnotes" in md
        assert "[^1]: First note" in md
        assert "[^2]: Second note (https://example.com)" in md
        assert "Hello[^1] world[^2]" in md

    def test_render_endnotes(self):
        result = FootnoteResult(
            body="Test[^1]",
            footnotes=[Footnote(1, "A note", "https://example.com")],
        )
        rendered = result.render("endnotes")
        assert "## Notes" in rendered
        assert "1. A note — https://example.com" in rendered

    def test_render_inline(self):
        result = FootnoteResult(
            body="Test[^1] and more[^2]",
            footnotes=[
                Footnote(1, "note one"),
                Footnote(2, "note two"),
            ],
        )
        rendered = result.render("inline")
        assert "(note one)" in rendered
        assert "(note two)" in rendered
        assert "[^" not in rendered

    def test_to_dict(self):
        result = FootnoteResult(
            body="Test",
            footnotes=[Footnote(1, "note")],
        )
        d = result.to_dict()
        assert d["body"] == "Test"
        assert len(d["footnotes"]) == 1


class TestAddFootnotes:
    def test_converts_links(self):
        text = "Check [Google](https://google.com) for more info."
        result = add_footnotes(text)
        assert "[^1]" in result.body
        assert "https://google.com" not in result.body
        assert len(result.footnotes) == 1
        assert result.footnotes[0].source_url == "https://google.com"

    def test_multiple_links(self):
        text = "Visit [A](https://a.com) and [B](https://b.com)."
        result = add_footnotes(text)
        assert "[^1]" in result.body
        assert "[^2]" in result.body
        assert len(result.footnotes) == 2

    def test_converts_citations(self):
        text = "As shown in prior work (Smith, 2023), the results..."
        result = add_footnotes(text)
        assert "[^" in result.body
        assert "(Smith, 2023)" not in result.body
        assert any("Smith, 2023" in fn.text for fn in result.footnotes)

    def test_citation_et_al(self):
        text = "Research (Johnson et al., 2022) shows improvement."
        result = add_footnotes(text)
        assert "[^" in result.body
        assert any("Johnson et al., 2022" in fn.text for fn in result.footnotes)

    def test_no_citations(self):
        text = "Plain text without any links or citations."
        result = add_footnotes(text)
        assert result.body == text
        assert result.footnotes == []

    def test_mixed_links_and_citations(self):
        text = "See [docs](https://docs.com) and (Brown, 2021) for details."
        result = add_footnotes(text)
        assert len(result.footnotes) == 2

    def test_preserves_non_http_links(self):
        text = "Check [section](#heading) for more."
        result = add_footnotes(text)
        # Non-http links should not be converted
        assert "[section](#heading)" in result.body
        assert len(result.footnotes) == 0


class TestRenumberFootnotes:
    def test_sequential(self):
        text = "A[^1] B[^3] C[^7]"
        result = renumber_footnotes(text)
        assert "[^1]" in result
        assert "[^2]" in result
        assert "[^3]" in result
        assert "[^7]" not in result

    def test_already_sequential(self):
        text = "A[^1] B[^2] C[^3]"
        result = renumber_footnotes(text)
        assert result == text

    def test_no_footnotes(self):
        text = "No footnotes here."
        assert renumber_footnotes(text) == text

    def test_renumbers_definitions_too(self):
        text = "Text[^5]\n\n[^5]: Note five"
        result = renumber_footnotes(text)
        assert "[^1]" in result
        assert "[^5]" not in result


class TestStripFootnotes:
    def test_removes_markers(self):
        text = "Hello[^1] world[^2]."
        result = strip_footnotes(text)
        assert result == "Hello world."

    def test_removes_definitions(self):
        text = "Text\n\n[^1]: Some note\n[^2]: Another note"
        result = strip_footnotes(text)
        assert "[^" not in result
        assert "Some note" not in result

    def test_removes_section(self):
        text = "Body text\n\n---\n## Footnotes\n\n[^1]: Note"
        result = strip_footnotes(text)
        assert "Footnotes" not in result
        assert "Body text" in result

    def test_plain_text(self):
        text = "No footnotes here"
        assert strip_footnotes(text) == text


class TestMergeFootnotes:
    def test_merge_two(self):
        r1 = FootnoteResult(
            body="Part A[^1]",
            footnotes=[Footnote(1, "Note A")],
        )
        r2 = FootnoteResult(
            body="Part B[^1]",
            footnotes=[Footnote(1, "Note B")],
        )
        merged = merge_footnotes(r1, r2)
        assert "[^1]" in merged.body
        assert "[^2]" in merged.body
        assert len(merged.footnotes) == 2
        assert merged.footnotes[0].number == 1
        assert merged.footnotes[1].number == 2

    def test_merge_empty(self):
        result = merge_footnotes()
        assert result.body == ""
        assert result.footnotes == []

    def test_merge_preserves_urls(self):
        r1 = FootnoteResult(
            body="Link[^1]",
            footnotes=[Footnote(1, "Example", "https://example.com")],
        )
        r2 = FootnoteResult(
            body="Other[^1]",
            footnotes=[Footnote(1, "Other", "https://other.com")],
        )
        merged = merge_footnotes(r1, r2)
        assert merged.footnotes[0].source_url == "https://example.com"
        assert merged.footnotes[1].source_url == "https://other.com"

    def test_merge_single(self):
        r1 = FootnoteResult(
            body="Solo[^1]",
            footnotes=[Footnote(1, "Only note")],
        )
        merged = merge_footnotes(r1)
        assert len(merged.footnotes) == 1
        assert merged.footnotes[0].number == 1
