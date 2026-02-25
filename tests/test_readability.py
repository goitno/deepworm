"""Tests for deepworm.readability."""

import pytest

from deepworm.readability import (
    ReadabilityResult,
    _strip_markdown,
    analyze_readability,
    count_syllables,
)

SIMPLE_TEXT = """
The cat sat on the mat. The dog ran in the park.
The sun was bright. The bird sang a song.
It was a nice day. The kids played outside.
"""

COMPLEX_TEXT = """
The implementation of sophisticated quantum computational algorithms
necessitates a comprehensive understanding of superposition and entanglement
phenomena. Furthermore, the extrapolation of experimental observations
regarding decoherence mechanisms contributes significantly to the
characterization of environmental interference patterns. Additionally,
the development of error-correcting methodologies demonstrates considerable
promise in achieving fault-tolerant quantum computation architectures.
"""


class TestAnalyzeReadability:
    def test_simple_text(self):
        result = analyze_readability(SIMPLE_TEXT)
        assert result.flesch_reading_ease > 70  # Should be easy
        assert result.total_words > 0
        assert result.total_sentences > 0

    def test_complex_text(self):
        result = analyze_readability(COMPLEX_TEXT)
        assert result.flesch_reading_ease < 50  # Should be difficult
        assert result.flesch_kincaid_grade > 10  # College level

    def test_empty_text(self):
        result = analyze_readability("")
        assert result.total_words == 0
        assert result.flesch_reading_ease == 0.0

    def test_markdown_stripped(self):
        md = "# Title\n\n**Bold text** and *italic text*.\n\n```python\ncode\n```\n\nPlain paragraph here."
        result = analyze_readability(md)
        assert result.total_words > 0
        # Code block content should be stripped

    def test_vocabulary_richness(self):
        # Repetitive text should have low richness
        repetitive = "the the the the the. the the the the the."
        result = analyze_readability(repetitive)
        assert result.vocabulary_richness < 0.5

    def test_diverse_vocabulary(self):
        diverse = "Alpha beta gamma delta epsilon. Zeta eta theta iota kappa."
        result = analyze_readability(diverse)
        assert result.vocabulary_richness > 0.5


class TestReadabilityResult:
    def test_reading_level_easy(self):
        result = analyze_readability(SIMPLE_TEXT)
        assert result.reading_level in ("Very Easy", "Easy", "Fairly Easy")

    def test_reading_level_difficult(self):
        result = analyze_readability(COMPLEX_TEXT)
        assert result.reading_level in ("Difficult", "Very Difficult", "Fairly Difficult")

    def test_grade_level(self):
        result = analyze_readability(COMPLEX_TEXT)
        assert result.grade_level in ("College", "Graduate", "High School")

    def test_to_dict(self):
        result = analyze_readability(SIMPLE_TEXT)
        d = result.to_dict()
        assert "flesch_reading_ease" in d
        assert "reading_level" in d
        assert "grade_level" in d
        assert "vocabulary_richness" in d
        assert isinstance(d["total_words"], int)

    def test_to_markdown(self):
        result = analyze_readability(SIMPLE_TEXT)
        md = result.to_markdown()
        assert "Readability Analysis" in md
        assert "Flesch Reading Ease" in md
        assert "Vocabulary" in md


class TestCountSyllables:
    def test_monosyllabic(self):
        assert count_syllables("cat") == 1
        assert count_syllables("dog") == 1
        assert count_syllables("the") == 1

    def test_disyllabic(self):
        assert count_syllables("water") == 2
        assert count_syllables("happy") == 2

    def test_polysyllabic(self):
        assert count_syllables("understanding") >= 3
        assert count_syllables("implementation") >= 4

    def test_empty(self):
        assert count_syllables("") == 0

    def test_single_vowel(self):
        assert count_syllables("a") == 1


class TestStripMarkdown:
    def test_removes_headings(self):
        result = _strip_markdown("# Title\n## Subtitle")
        assert "#" not in result
        assert "Title" in result

    def test_removes_bold_italic(self):
        result = _strip_markdown("**bold** and *italic*")
        assert "**" not in result
        assert "*" not in result
        assert "bold" in result

    def test_removes_links(self):
        result = _strip_markdown("[text](https://example.com)")
        assert "text" in result
        assert "https" not in result

    def test_removes_code_blocks(self):
        result = _strip_markdown("text\n```python\ncode\n```\nmore text")
        assert "code" not in result
        assert "text" in result

    def test_removes_list_markers(self):
        result = _strip_markdown("- item 1\n- item 2\n1. item 3")
        assert "-" not in result.strip()
        assert "item 1" in result
