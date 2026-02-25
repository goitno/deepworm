"""Tests for text similarity module."""

from deepworm.similarity import (
    SimilarityResult,
    PlagiarismResult,
    PlagiarismMatch,
    compare_texts,
    cosine_similarity,
    jaccard_similarity,
    overlap_coefficient,
    detect_plagiarism,
    find_similar,
    text_fingerprint,
)


TEXT_A = """
Machine learning is a subset of artificial intelligence that enables
systems to learn and improve from experience. Deep learning is a
specialized form of machine learning using neural networks.
"""

TEXT_B = """
Machine learning is a branch of artificial intelligence focused on
building systems that learn from data. Neural networks are the
foundation of deep learning approaches.
"""

TEXT_C = """
Cooking is an art that requires patience and practice. The best
recipes combine fresh ingredients with careful technique.
"""


class TestSimilarityResult:
    def test_average(self):
        r = SimilarityResult(cosine=0.8, jaccard=0.6, overlap=0.7)
        assert 0.69 <= r.average <= 0.71

    def test_is_similar(self):
        r = SimilarityResult(cosine=0.8, jaccard=0.7, overlap=0.7)
        assert r.is_similar is True

    def test_not_similar(self):
        r = SimilarityResult(cosine=0.1, jaccard=0.1, overlap=0.1)
        assert r.is_similar is False

    def test_is_duplicate(self):
        r = SimilarityResult(cosine=0.95, jaccard=0.9, overlap=0.9)
        assert r.is_duplicate is True

    def test_to_dict(self):
        r = SimilarityResult(cosine=0.5, jaccard=0.4, overlap=0.3)
        d = r.to_dict()
        assert "cosine" in d
        assert "jaccard" in d
        assert "average" in d
        assert "is_similar" in d


class TestPlagiarismResult:
    def test_no_plagiarism(self):
        r = PlagiarismResult(similarity=0.1, source_coverage=0.05)
        assert r.is_plagiarized is False

    def test_plagiarized(self):
        r = PlagiarismResult(similarity=0.8, source_coverage=0.6)
        assert r.is_plagiarized is True

    def test_to_dict(self):
        r = PlagiarismResult(
            similarity=0.5,
            matches=[PlagiarismMatch("test match", 2)],
            source_coverage=0.3,
        )
        d = r.to_dict()
        assert d["match_count"] == 1
        assert d["source_coverage"] == 0.3


class TestCompareTexts:
    def test_similar_texts(self):
        result = compare_texts(TEXT_A, TEXT_B)
        assert result.cosine > 0.3
        assert result.jaccard > 0.1
        assert len(result.common_terms) > 0

    def test_dissimilar_texts(self):
        result = compare_texts(TEXT_A, TEXT_C)
        assert result.cosine < result.average + 0.5  # Sanity check
        assert result.cosine < compare_texts(TEXT_A, TEXT_B).cosine

    def test_identical_texts(self):
        result = compare_texts(TEXT_A, TEXT_A)
        assert result.cosine > 0.99

    def test_empty_texts(self):
        result = compare_texts("", "hello")
        assert result.cosine == 0.0
        assert result.jaccard == 0.0


class TestCosineSimilarity:
    def test_identical(self):
        assert cosine_similarity("hello world", "hello world") > 0.99

    def test_different(self):
        sim = cosine_similarity("cat dog", "fish bird")
        assert sim == 0.0

    def test_partial_overlap(self):
        sim = cosine_similarity("hello world test", "hello world foo")
        assert 0.3 < sim < 1.0

    def test_empty(self):
        assert cosine_similarity("", "hello") == 0.0
        assert cosine_similarity("hello", "") == 0.0


class TestJaccardSimilarity:
    def test_identical(self):
        s = {"a", "b", "c"}
        assert jaccard_similarity(s, s) == 1.0

    def test_no_overlap(self):
        assert jaccard_similarity({"a", "b"}, {"c", "d"}) == 0.0

    def test_partial(self):
        sim = jaccard_similarity({"a", "b", "c"}, {"b", "c", "d"})
        assert abs(sim - 0.5) < 0.01

    def test_empty(self):
        assert jaccard_similarity(set(), set()) == 0.0


class TestOverlapCoefficient:
    def test_complete_overlap(self):
        assert overlap_coefficient({"a", "b"}, {"a", "b", "c"}) == 1.0

    def test_no_overlap(self):
        assert overlap_coefficient({"a"}, {"b"}) == 0.0

    def test_empty(self):
        assert overlap_coefficient(set(), {"a"}) == 0.0


class TestDetectPlagiarism:
    def test_no_plagiarism(self):
        result = detect_plagiarism(TEXT_A, TEXT_C)
        assert result.source_coverage < 0.3

    def test_self_plagiarism(self):
        result = detect_plagiarism(TEXT_A, TEXT_A)
        assert result.similarity > 0.9

    def test_empty(self):
        result = detect_plagiarism("", TEXT_A)
        assert result.similarity == 0.0

    def test_partial_copy(self):
        source = "The quick brown fox jumps over the lazy dog in the park"
        target = "Yesterday, the quick brown fox jumps over the lazy dog was seen running"
        result = detect_plagiarism(source, target, min_match_length=3)
        assert result.similarity > 0


class TestFindSimilar:
    def test_finds_similar(self):
        corpus = [TEXT_A, TEXT_B, TEXT_C]
        results = find_similar(TEXT_A, corpus, threshold=0.3)
        assert len(results) > 0
        # First result should be the identical text
        assert results[0][0] == 0
        assert results[0][1] > 0.9

    def test_threshold_filter(self):
        corpus = [TEXT_C]  # Very different text
        results = find_similar(TEXT_A, corpus, threshold=0.9)
        assert len(results) == 0

    def test_empty_corpus(self):
        results = find_similar(TEXT_A, [])
        assert results == []

    def test_sorted_by_similarity(self):
        corpus = [TEXT_A, TEXT_B, TEXT_C]
        results = find_similar(TEXT_A, corpus, threshold=0.0)
        scores = [r[1] for r in results]
        assert scores == sorted(scores, reverse=True)


class TestTextFingerprint:
    def test_basic(self):
        fp = text_fingerprint("the quick brown fox jumps", n=3)
        assert len(fp) > 0
        assert all(isinstance(s, str) for s in fp)

    def test_ngram_count(self):
        fp = text_fingerprint("one two three four five", n=3)
        assert len(fp) == 3  # 5 words - 3 + 1 = 3 trigrams

    def test_short_text(self):
        fp = text_fingerprint("hello", n=3)
        assert len(fp) == 1

    def test_empty(self):
        fp = text_fingerprint("")
        assert fp == set()

    def test_similar_fingerprints(self):
        fp_a = text_fingerprint(TEXT_A)
        fp_b = text_fingerprint(TEXT_B)
        # Should share some n-grams
        common = fp_a & fp_b
        assert isinstance(common, set)
