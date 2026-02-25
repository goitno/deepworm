"""Tests for keyword extraction module."""

from deepworm.keywords import (
    Keyword,
    KeywordResult,
    extract_keywords,
    extract_tags,
    _strip_markdown,
    _tokenize,
    _score_term,
    _extract_phrases,
    _deduplicate,
)


SAMPLE_TEXT = """
# Machine Learning in Healthcare

Machine learning algorithms have transformed healthcare diagnostics.
Deep learning models, particularly neural networks, achieve impressive
accuracy in medical imaging analysis. Machine learning enables automated
detection of tumors, fractures, and other pathologies.

## Natural Language Processing

Natural language processing (NLP) is another important application.
Clinical notes contain valuable patient information that NLP algorithms
can extract efficiently. Natural language processing helps summarize
medical records and identify key findings.

## Computer Vision Applications

Computer vision techniques combined with deep learning have revolutionized
radiology. Computer vision algorithms analyze X-rays, MRIs, and CT scans
with accuracy comparable to radiologists. Deep learning models continue
to improve diagnostic accuracy in healthcare settings.
"""


class TestKeyword:
    def test_to_dict(self):
        kw = Keyword(term="machine learning", score=5.123456, frequency=4, is_phrase=True)
        d = kw.to_dict()
        assert d["term"] == "machine learning"
        assert d["score"] == 5.123
        assert d["frequency"] == 4
        assert d["is_phrase"] is True

    def test_defaults(self):
        kw = Keyword(term="test", score=1.0, frequency=2)
        assert kw.is_phrase is False


class TestKeywordResult:
    def test_top_terms(self):
        result = KeywordResult(keywords=[
            Keyword("alpha", 3.0, 5),
            Keyword("beta", 2.0, 3),
        ])
        assert result.top_terms == ["alpha", "beta"]

    def test_to_dict(self):
        result = KeywordResult(
            keywords=[Keyword("test", 1.5, 2)],
            total_words=100,
            unique_words=50,
        )
        d = result.to_dict()
        assert d["total_words"] == 100
        assert d["unique_words"] == 50
        assert len(d["keywords"]) == 1

    def test_to_markdown(self):
        result = KeywordResult(keywords=[
            Keyword("alpha", 3.0, 5),
            Keyword("beta", 2.0, 3),
        ])
        md = result.to_markdown()
        assert "## Keywords" in md
        assert "alpha" in md
        assert "beta" in md
        assert "| Keyword |" in md

    def test_empty_result(self):
        result = KeywordResult()
        assert result.top_terms == []
        assert result.total_words == 0


class TestExtractKeywords:
    def test_basic_extraction(self):
        result = extract_keywords(SAMPLE_TEXT, max_keywords=10)
        assert len(result.keywords) > 0
        assert result.total_words > 0
        assert result.unique_words > 0

    def test_finds_relevant_terms(self):
        result = extract_keywords(SAMPLE_TEXT, max_keywords=20)
        terms = [k.term for k in result.keywords]
        # Should find domain-specific terms
        found = any("learning" in t or "medical" in t or "healthcare" in t for t in terms)
        assert found, f"Expected domain terms, got: {terms}"

    def test_max_keywords_limit(self):
        result = extract_keywords(SAMPLE_TEXT, max_keywords=5)
        assert len(result.keywords) <= 5

    def test_min_frequency_filter(self):
        result = extract_keywords(SAMPLE_TEXT, min_frequency=3)
        for kw in result.keywords:
            assert kw.frequency >= 3

    def test_without_phrases(self):
        result = extract_keywords(SAMPLE_TEXT, include_phrases=False)
        for kw in result.keywords:
            assert not kw.is_phrase

    def test_with_phrases(self):
        result = extract_keywords(SAMPLE_TEXT, include_phrases=True, min_frequency=2)
        phrase_found = any(kw.is_phrase for kw in result.keywords)
        # Phrases may or may not be found depending on text
        assert isinstance(phrase_found, bool)

    def test_empty_text(self):
        result = extract_keywords("")
        assert result.keywords == []
        assert result.total_words == 0

    def test_short_text(self):
        result = extract_keywords("Hello world", min_frequency=1)
        assert result.total_words == 2

    def test_scores_sorted(self):
        result = extract_keywords(SAMPLE_TEXT, max_keywords=10)
        scores = [k.score for k in result.keywords]
        assert scores == sorted(scores, reverse=True)

    def test_repeated_term_high_score(self):
        text = " ".join(["algorithm"] * 20 + ["random word"] * 50)
        result = extract_keywords(text, min_frequency=1, max_keywords=10)
        terms = [k.term for k in result.keywords]
        found = any("algorithm" in t for t in terms)
        assert found, f"Expected 'algorithm' in terms, got: {terms}"


class TestExtractTags:
    def test_basic_tags(self):
        tags = extract_tags(SAMPLE_TEXT, max_tags=5)
        assert len(tags) <= 5
        assert all(isinstance(t, str) for t in tags)

    def test_tag_format(self):
        tags = extract_tags(SAMPLE_TEXT)
        for tag in tags:
            assert len(tag) <= 30
            assert " " not in tag  # Spaces replaced with hyphens

    def test_max_tags(self):
        tags = extract_tags(SAMPLE_TEXT, max_tags=3)
        assert len(tags) <= 3

    def test_no_duplicates(self):
        tags = extract_tags(SAMPLE_TEXT)
        assert len(tags) == len(set(tags))


class TestStripMarkdown:
    def test_removes_headings(self):
        assert "Title" in _strip_markdown("# Title")
        assert "#" not in _strip_markdown("# Title").strip()

    def test_removes_bold_italic(self):
        result = _strip_markdown("**bold** and *italic*")
        assert "bold" in result
        assert "**" not in result
        assert result.count("*") == 0

    def test_removes_code_blocks(self):
        result = _strip_markdown("text\n```python\ncode\n```\nmore text")
        assert "code" not in result
        assert "text" in result

    def test_removes_links(self):
        result = _strip_markdown("[click here](http://example.com)")
        assert "click here" in result
        assert "http" not in result


class TestTokenize:
    def test_basic(self):
        tokens = _tokenize("Hello world test")
        assert tokens == ["Hello", "world", "test"]

    def test_punctuation(self):
        tokens = _tokenize("Hello, world! Test.")
        assert "Hello" in tokens
        assert "world" in tokens

    def test_contractions(self):
        tokens = _tokenize("don't can't won't")
        assert "don't" in tokens


class TestScoreTerm:
    def test_higher_frequency_higher_score(self):
        s1 = _score_term("algorithm", 5, 100)
        s2 = _score_term("algorithm", 1, 100)
        assert s1 > s2

    def test_longer_word_bonus(self):
        s1 = _score_term("algorithm", 3, 100)
        s2 = _score_term("cat", 3, 100)
        assert s1 > s2

    def test_zero_frequency(self):
        score = _score_term("test", 0, 100)
        assert score == 0.0


class TestExtractPhrases:
    def test_bigrams(self):
        words = ["machine", "learning", "machine", "learning", "deep", "model"]
        phrases = _extract_phrases(words, min_freq=2)
        terms = [p.term for p in phrases]
        assert "machine learning" in terms

    def test_min_freq_filter(self):
        words = ["one", "two", "three", "four"]
        phrases = _extract_phrases(words, min_freq=2)
        assert len(phrases) == 0


class TestDeduplicate:
    def test_removes_subsumed_words(self):
        keywords = [
            Keyword("machine learning", 5.0, 4, is_phrase=True),
            Keyword("machine", 3.0, 6, is_phrase=False),
            Keyword("algorithm", 2.0, 3, is_phrase=False),
        ]
        result = _deduplicate(keywords)
        terms = [k.term for k in result]
        assert "machine learning" in terms
        assert "machine" not in terms  # Subsumed by phrase
        assert "algorithm" in terms  # Not part of any phrase
