"""Tests for deepworm.transform – document text transformations."""

import pytest

from deepworm.transform import (
    TransformChain,
    TransformChainResult,
    TransformResult,
    TransformType,
    cleanup_transform,
    create_transform_chain,
    extract_section,
    find_replace,
    find_replace_batch,
    fix_indentation,
    normalize_headings,
    normalize_links,
    normalize_whitespace,
    remove_section,
    reorder_sections,
    strip_comments,
    strip_html,
    to_sentence_case,
    to_title_case,
    wrap_text,
)


# ---------------------------------------------------------------------------
# TransformResult
# ---------------------------------------------------------------------------

class TestTransformResult:
    def test_changed(self):
        r = TransformResult(original="abc", transformed="xyz", changes_made=1)
        assert r.changed is True

    def test_not_changed(self):
        r = TransformResult(original="abc", transformed="abc")
        assert r.changed is False

    def test_diff_ratio(self):
        r = TransformResult(original="abc", transformed="abcdef")
        assert r.diff_ratio == pytest.approx(1.0)

    def test_diff_ratio_empty(self):
        r = TransformResult(original="", transformed="")
        assert r.diff_ratio == 0.0


# ---------------------------------------------------------------------------
# Case transforms
# ---------------------------------------------------------------------------

class TestTitleCase:
    def test_basic(self):
        text = "# hello world\n## this is a test"
        result = to_title_case(text)
        assert "# Hello World" in result.transformed
        assert result.transform_type == TransformType.CASE

    def test_small_words(self):
        text = "# the art of war"
        result = to_title_case(text)
        # First word always capitalized
        assert result.transformed == "# The Art of War"

    def test_no_headings(self):
        text = "Just a paragraph."
        result = to_title_case(text)
        assert result.changed is False


class TestSentenceCase:
    def test_basic(self):
        text = "# Hello World Test"
        result = to_sentence_case(text)
        assert result.transformed == "# Hello world test"

    def test_preserves_non_headings(self):
        text = "Regular text.\n# A Heading"
        result = to_sentence_case(text)
        assert "Regular text." in result.transformed


# ---------------------------------------------------------------------------
# Whitespace transforms
# ---------------------------------------------------------------------------

class TestNormalizeWhitespace:
    def test_trailing_spaces(self):
        text = "hello   \nworld  "
        result = normalize_whitespace(text)
        assert "   " not in result.transformed
        assert result.changes_made >= 2

    def test_collapse_blank_lines(self):
        text = "a\n\n\n\n\nb"
        result = normalize_whitespace(text)
        # Max 2 consecutive blank lines
        assert "\n\n\n" not in result.transformed

    def test_trailing_newline(self):
        text = "hello"
        result = normalize_whitespace(text)
        assert result.transformed.endswith("\n")


class TestFixIndentation:
    def test_normalizes_indent(self):
        text = "```\n   code\n      nested\n```"
        result = fix_indentation(text)
        assert result.transform_type == TransformType.WHITESPACE


# ---------------------------------------------------------------------------
# Markdown transforms
# ---------------------------------------------------------------------------

class TestNormalizeHeadings:
    def test_offset_levels(self):
        text = "## Sub\n### Subsub"
        result = normalize_headings(text)
        assert result.transformed.startswith("# Sub")
        assert "## Subsub" in result.transformed

    def test_no_headings(self):
        text = "No headings here."
        result = normalize_headings(text)
        assert result.changed is False


class TestStripHtml:
    def test_removes_tags(self):
        text = "<b>bold</b> and <i>italic</i>"
        result = strip_html(text)
        assert result.transformed == "bold and italic"
        assert result.changes_made == 4

    def test_no_html(self):
        text = "plain text"
        result = strip_html(text)
        assert result.changed is False


class TestNormalizeLinks:
    def test_fix_spaces(self):
        text = "[ link text ]( https://example.com )"
        result = normalize_links(text)
        assert "[link text](https://example.com)" in result.transformed

    def test_no_change_needed(self):
        text = "[text](url)"
        result = normalize_links(text)
        assert result.changes_made == 0


class TestStripComments:
    def test_removes_comments(self):
        text = "Hello <!-- hidden --> world"
        result = strip_comments(text)
        assert "hidden" not in result.transformed
        assert result.changes_made == 1

    def test_multiline_comment(self):
        text = "Before\n<!-- multi\nline\ncomment -->\nAfter"
        result = strip_comments(text)
        assert "multi" not in result.transformed


# ---------------------------------------------------------------------------
# Find-and-replace
# ---------------------------------------------------------------------------

class TestFindReplace:
    def test_simple(self):
        result = find_replace("hello world", "world", "earth")
        assert result.transformed == "hello earth"
        assert result.changes_made == 1

    def test_regex(self):
        result = find_replace("item1 item2 item3", r"item\d", "X", regex=True)
        assert result.transformed == "X X X"
        assert result.changes_made == 3

    def test_case_insensitive(self):
        result = find_replace("Hello HELLO hello", "hello", "hi", case_sensitive=False)
        assert result.transformed == "hi hi hi"
        assert result.changes_made == 3

    def test_no_match(self):
        result = find_replace("hello", "xyz", "abc")
        assert result.changed is False


class TestFindReplaceBatch:
    def test_multiple(self):
        result = find_replace_batch("foo bar baz", [("foo", "x"), ("bar", "y")])
        assert result.transformed == "x y baz"
        assert result.changes_made == 2


# ---------------------------------------------------------------------------
# Structure transforms
# ---------------------------------------------------------------------------

class TestWrapText:
    def test_wraps_long_lines(self):
        long = "word " * 30
        result = wrap_text(long, width=40)
        for line in result.transformed.splitlines():
            assert len(line) <= 45  # small margin for word boundaries

    def test_preserves_headings(self):
        text = "# " + "a " * 50
        result = wrap_text(text, width=20)
        assert result.transformed.startswith("# ")

    def test_preserves_code_blocks(self):
        text = "```\n" + "x " * 50 + "\n```"
        result = wrap_text(text, width=20)
        # Code block should not be wrapped
        assert "```" in result.transformed


class TestExtractSection:
    def test_extracts(self):
        text = "# Intro\nHello\n## Methods\nDid stuff\n## Results\nGot stuff"
        result = extract_section(text, "Methods")
        assert "Did stuff" in result.transformed
        assert "Got stuff" not in result.transformed

    def test_not_found(self):
        result = extract_section("# A\nText", "Missing")
        assert result.transformed == ""


class TestRemoveSection:
    def test_removes(self):
        text = "# Intro\nHello\n## Bad\nRemove me\n## Good\nKeep me"
        result = remove_section(text, "Bad")
        assert "Remove me" not in result.transformed
        assert "Keep me" in result.transformed

    def test_not_found(self):
        text = "# A\nText"
        result = remove_section(text, "Missing")
        assert result.changes_made == 0


class TestReorderSections:
    def test_reorder(self):
        text = "# A\nFirst\n# B\nSecond\n# C\nThird"
        result = reorder_sections(text, ["C", "A", "B"])
        lines = result.transformed.splitlines()
        c_idx = next(i for i, l in enumerate(lines) if "# C" in l)
        a_idx = next(i for i, l in enumerate(lines) if "# A" in l)
        assert c_idx < a_idx


# ---------------------------------------------------------------------------
# TransformChain
# ---------------------------------------------------------------------------

class TestTransformChain:
    def test_chain(self):
        chain = TransformChain()
        chain.add("html", strip_html)
        chain.add("comments", strip_comments)
        result = chain.execute("<b>bold</b> <!-- hidden -->")
        assert "bold" in result.final
        assert "<b>" not in result.final
        assert "hidden" not in result.final
        assert len(result.steps) == 2

    def test_to_dict(self):
        chain = TransformChain()
        result = chain.execute("text")
        d = result.to_dict()
        assert "changed" in d

    def test_count(self):
        chain = TransformChain()
        chain.add("a", strip_html)
        chain.add("b", strip_comments)
        assert chain.count == 2


class TestCreateTransformChain:
    def test_with_transforms(self):
        chain = create_transform_chain([("html", strip_html)])
        assert chain.count == 1

    def test_empty(self):
        chain = create_transform_chain()
        assert chain.count == 0


class TestCleanupTransform:
    def test_prebuilt(self):
        chain = cleanup_transform()
        assert chain.count == 3
        text = "hello   \n[ link ]( url ) <!-- comment -->"
        result = chain.execute(text)
        assert "comment" not in result.final
