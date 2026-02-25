"""Tests for document statistics module."""

import pytest
from deepworm.statistics import (
    TextStatistics,
    ComparisonResult,
    compute_statistics,
    compare_statistics,
    vocabulary_analysis,
    section_statistics,
    reading_level,
    _count_syllables,
    _split_sentences,
    _extract_words,
)


SAMPLE_DOC = """# Introduction

This is a sample document for testing. It has multiple paragraphs
and various markdown elements. The document covers several topics.

## Methods

We used Python for data analysis. The methodology includes:

- Data collection
- Data cleaning
- Statistical analysis
- Visualization

### Tools

We used pandas, numpy, and matplotlib for our analysis.
The code was written in Python 3.9.

## Results

The results show a significant improvement. Performance increased
by 25% compared to the baseline. The accuracy was measured at 95%.

| Metric | Value |
|--------|-------|
| Accuracy | 95% |
| Precision | 92% |

## Conclusion

In conclusion, our approach works well. Future work should
explore additional optimization techniques.
"""


# --- TextStatistics ---

class TestTextStatistics:
    def test_defaults(self):
        stats = TextStatistics()
        assert stats.word_count == 0
        assert stats.character_count == 0

    def test_to_dict(self):
        stats = TextStatistics(word_count=100, sentence_count=5)
        d = stats.to_dict()
        assert d["word_count"] == 100
        assert d["sentence_count"] == 5

    def test_to_markdown(self):
        stats = TextStatistics(
            word_count=100, sentence_count=5, paragraph_count=3,
            heading_count=2, vocabulary_richness=0.75,
        )
        md = stats.to_markdown()
        assert "Document Statistics" in md
        assert "100" in md
        assert "Headings" in md


# --- compute_statistics ---

class TestComputeStatistics:
    def test_basic(self):
        stats = compute_statistics(SAMPLE_DOC)
        assert stats.word_count > 0
        assert stats.sentence_count > 0
        assert stats.paragraph_count > 0

    def test_character_count(self):
        stats = compute_statistics("Hello World")
        assert stats.character_count == 11
        assert stats.character_count_no_spaces == 10

    def test_word_count(self):
        stats = compute_statistics("one two three four five")
        assert stats.word_count == 5

    def test_line_count(self):
        stats = compute_statistics("a\nb\nc")
        assert stats.line_count == 3

    def test_headings(self):
        stats = compute_statistics(SAMPLE_DOC)
        assert stats.heading_count >= 4  # Introduction, Methods, Tools, Results, Conclusion

    def test_list_items(self):
        stats = compute_statistics(SAMPLE_DOC)
        assert stats.list_item_count >= 4

    def test_tables(self):
        stats = compute_statistics(SAMPLE_DOC)
        assert stats.table_count >= 1

    def test_links(self):
        stats = compute_statistics("Click [here](https://example.com) for info")
        assert stats.link_count == 1

    def test_images(self):
        stats = compute_statistics("![alt](image.png)")
        assert stats.image_count == 1

    def test_code_blocks(self):
        stats = compute_statistics("text\n```python\ncode\n```\nmore text")
        assert stats.code_block_count == 1

    def test_reading_time(self):
        # 238 words should be ~1 minute
        text = " ".join(["word"] * 238)
        stats = compute_statistics(text)
        assert 0.9 < stats.reading_time_minutes < 1.1

    def test_speaking_time(self):
        # 150 words should be ~1 minute
        text = " ".join(["word"] * 150)
        stats = compute_statistics(text)
        assert 0.9 < stats.speaking_time_minutes < 1.1

    def test_vocabulary_richness(self):
        stats = compute_statistics("cat dog bird cat dog bird cat")
        assert 0 < stats.vocabulary_richness < 1

    def test_hapax(self):
        stats = compute_statistics("cat cat dog dog bird")
        assert stats.hapax_legomena == 1  # "bird"

    def test_avg_word_length(self):
        stats = compute_statistics("hi hello")
        assert stats.avg_word_length > 0

    def test_longest_word(self):
        stats = compute_statistics("short extraordinarily brief")
        assert stats.longest_word == "extraordinarily"

    def test_empty_text(self):
        stats = compute_statistics("")
        assert stats.word_count == 0

    def test_whitespace_only(self):
        stats = compute_statistics("   \n\n  ")
        assert stats.word_count == 0

    def test_top_words_exclude_stop_words(self):
        stats = compute_statistics("the the the python python java")
        top_word_list = [w for w, c in stats.top_words]
        assert "the" not in top_word_list
        assert "python" in top_word_list

    def test_paragraph_count(self):
        stats = compute_statistics("Para one.\n\nPara two.\n\nPara three.")
        assert stats.paragraph_count == 3


# --- compare_statistics ---

class TestCompareStatistics:
    def test_basic(self):
        result = compare_statistics(
            "Short doc.", "A much longer document with many words.",
            label_a="Short", label_b="Long",
        )
        assert result.word_count_diff > 0
        assert result.label_a == "Short"

    def test_to_markdown(self):
        result = compare_statistics("First.", "Second text here.")
        md = result.to_markdown()
        assert "Statistics Comparison" in md
        assert "Words" in md

    def test_to_dict(self):
        result = compare_statistics("A.", "B.")
        d = result.to_dict()
        assert "stats_a" in d
        assert "stats_b" in d
        assert "word_count_diff" in d


# --- vocabulary_analysis ---

class TestVocabularyAnalysis:
    def test_basic(self):
        result = vocabulary_analysis(
            "Python programming is fun. Python is versatile."
        )
        assert result["total_words"] > 0
        assert result["unique_words"] > 0
        assert result["vocabulary_richness"] > 0

    def test_frequency_distribution(self):
        result = vocabulary_analysis("alpha beta gamma alpha beta alpha")
        dist = result["frequency_distribution"]
        assert dist["1 occurrence"] >= 1  # gamma
        assert "rare_words" in result

    def test_empty(self):
        result = vocabulary_analysis("")
        assert result["total_words"] == 0

    def test_hapax_ratio(self):
        result = vocabulary_analysis("unique words that never repeat")
        assert result["hapax_ratio"] > 0

    def test_common_words(self):
        result = vocabulary_analysis(
            "python python python java java ruby"
        )
        common = result["common_words"]
        assert common[0][0] == "python"


# --- section_statistics ---

class TestSectionStatistics:
    def test_with_headings(self):
        sections = section_statistics(SAMPLE_DOC)
        assert len(sections) >= 4
        assert sections[0]["title"] == "Introduction"

    def test_without_headings(self):
        sections = section_statistics("Just plain text without any headings.")
        assert len(sections) == 1
        assert sections[0]["title"] == "(untitled)"

    def test_word_counts(self):
        sections = section_statistics("# A\n\nShort.\n\n# B\n\nLonger section with more words here.")
        assert sections[0]["word_count"] < sections[1]["word_count"]

    def test_levels(self):
        sections = section_statistics("# H1\n\nText\n\n## H2\n\nText\n\n### H3\n\nText")
        assert sections[0]["level"] == 1
        assert sections[1]["level"] == 2
        assert sections[2]["level"] == 3


# --- reading_level ---

class TestReadingLevel:
    def test_simple_text(self):
        result = reading_level(
            "The cat sat on the mat. The dog ran fast. It was fun."
        )
        assert result["level"] in ["Elementary", "Middle School", "High School",
                                     "College", "Graduate"]
        assert result["flesch_kincaid_grade"] >= 0

    def test_complex_text(self):
        result = reading_level(
            "The implementation of sophisticated algorithmic methodologies "
            "necessitates comprehensive understanding of computational "
            "complexity theory and mathematical optimization principles."
        )
        assert result["flesch_kincaid_grade"] > 5

    def test_empty(self):
        result = reading_level("")
        assert result["level"] == "N/A"

    def test_has_all_fields(self):
        result = reading_level("This is a test sentence.")
        assert "flesch_kincaid_grade" in result
        assert "ari" in result
        assert "avg_grade" in result
        assert "syllable_count" in result


# --- Helpers ---

class TestHelpers:
    def test_count_syllables(self):
        assert _count_syllables("cat") == 1
        assert _count_syllables("hello") == 2
        assert _count_syllables("beautiful") >= 3

    def test_split_sentences(self):
        sentences = _split_sentences("Hello. World! How are you?")
        assert len(sentences) == 3

    def test_extract_words(self):
        words = _extract_words("Hello **world** and `code`")
        assert "hello" in words
        assert "world" in words

    def test_extract_words_strips_urls(self):
        words = _extract_words("Visit https://example.com today")
        word_list = [w for w in words]
        assert "example" not in word_list
        assert "visit" in word_list
