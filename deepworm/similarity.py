"""Text similarity and plagiarism detection utilities.

Provides multiple similarity metrics for comparing text documents,
detecting near-duplicates, and finding common passages.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SimilarityResult:
    """Result of comparing two texts."""

    cosine: float = 0.0  # Cosine similarity (0-1)
    jaccard: float = 0.0  # Jaccard similarity (0-1)
    overlap: float = 0.0  # Overlap coefficient (0-1)
    common_terms: list[str] = field(default_factory=list)

    @property
    def average(self) -> float:
        """Average of all similarity scores."""
        return round((self.cosine + self.jaccard + self.overlap) / 3, 4)

    @property
    def is_similar(self) -> bool:
        """Whether texts are considered similar (> 0.6 average)."""
        return self.average > 0.6

    @property
    def is_duplicate(self) -> bool:
        """Whether texts are likely duplicates (> 0.85 average)."""
        return self.average > 0.85

    def to_dict(self) -> dict[str, Any]:
        return {
            "cosine": round(self.cosine, 4),
            "jaccard": round(self.jaccard, 4),
            "overlap": round(self.overlap, 4),
            "average": self.average,
            "is_similar": self.is_similar,
            "is_duplicate": self.is_duplicate,
            "common_terms_count": len(self.common_terms),
        }


@dataclass
class PlagiarismMatch:
    """A passage found in common between two texts."""

    text: str
    length: int


@dataclass
class PlagiarismResult:
    """Result of plagiarism detection."""

    similarity: float  # Overall similarity (0-1)
    matches: list[PlagiarismMatch] = field(default_factory=list)
    source_coverage: float = 0.0  # How much of source appears in target

    @property
    def is_plagiarized(self) -> bool:
        """Whether plagiarism is likely (> 0.4 coverage)."""
        return self.source_coverage > 0.4

    def to_dict(self) -> dict[str, Any]:
        return {
            "similarity": round(self.similarity, 4),
            "match_count": len(self.matches),
            "source_coverage": round(self.source_coverage, 4),
            "is_plagiarized": self.is_plagiarized,
        }


def compare_texts(text_a: str, text_b: str) -> SimilarityResult:
    """Compare two texts using multiple similarity metrics.

    Args:
        text_a: First text.
        text_b: Second text.

    Returns:
        SimilarityResult with cosine, jaccard, and overlap scores.
    """
    words_a = _tokenize(text_a)
    words_b = _tokenize(text_b)

    if not words_a or not words_b:
        return SimilarityResult()

    set_a = set(words_a)
    set_b = set(words_b)
    common = set_a & set_b

    return SimilarityResult(
        cosine=cosine_similarity(text_a, text_b),
        jaccard=jaccard_similarity(set_a, set_b),
        overlap=overlap_coefficient(set_a, set_b),
        common_terms=sorted(common)[:50],
    )


def cosine_similarity(text_a: str, text_b: str) -> float:
    """Compute cosine similarity between two texts.

    Uses term frequency vectors.

    Args:
        text_a: First text.
        text_b: Second text.

    Returns:
        Similarity score between 0 and 1.
    """
    words_a = _tokenize(text_a)
    words_b = _tokenize(text_b)

    if not words_a or not words_b:
        return 0.0

    freq_a = Counter(words_a)
    freq_b = Counter(words_b)
    all_words = set(freq_a) | set(freq_b)

    dot_product = sum(freq_a.get(w, 0) * freq_b.get(w, 0) for w in all_words)
    magnitude_a = sum(v ** 2 for v in freq_a.values()) ** 0.5
    magnitude_b = sum(v ** 2 for v in freq_b.values()) ** 0.5

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)


def jaccard_similarity(set_a: set, set_b: set) -> float:
    """Compute Jaccard similarity between two sets.

    Args:
        set_a: First set.
        set_b: Second set.

    Returns:
        Similarity score between 0 and 1.
    """
    if not set_a and not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def overlap_coefficient(set_a: set, set_b: set) -> float:
    """Compute overlap coefficient between two sets.

    Args:
        set_a: First set.
        set_b: Second set.

    Returns:
        Overlap coefficient between 0 and 1.
    """
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    min_size = min(len(set_a), len(set_b))
    return intersection / min_size if min_size > 0 else 0.0


def detect_plagiarism(
    source: str,
    target: str,
    min_match_length: int = 5,
) -> PlagiarismResult:
    """Detect potential plagiarism between source and target texts.

    Finds common n-gram sequences and calculates coverage.

    Args:
        source: Original source text.
        target: Text to check for plagiarism.
        min_match_length: Minimum matching word sequence length.

    Returns:
        PlagiarismResult with matches and coverage.
    """
    source_words = _tokenize(source)
    target_words = _tokenize(target)

    if not source_words or not target_words:
        return PlagiarismResult(similarity=0.0)

    matches = _find_common_sequences(source_words, target_words, min_match_length)

    matched_words = sum(m.length for m in matches)
    coverage = matched_words / len(source_words) if source_words else 0.0

    sim = cosine_similarity(source, target)

    return PlagiarismResult(
        similarity=sim,
        matches=matches,
        source_coverage=min(coverage, 1.0),
    )


def find_similar(
    text: str,
    corpus: list[str],
    threshold: float = 0.3,
) -> list[tuple[int, float]]:
    """Find similar texts in a corpus.

    Args:
        text: Text to compare against corpus.
        corpus: List of texts to search.
        threshold: Minimum cosine similarity to include.

    Returns:
        List of (index, similarity_score) tuples sorted by similarity.
    """
    results: list[tuple[int, float]] = []
    for i, doc in enumerate(corpus):
        sim = cosine_similarity(text, doc)
        if sim >= threshold:
            results.append((i, round(sim, 4)))
    results.sort(key=lambda x: x[1], reverse=True)
    return results


def text_fingerprint(text: str, n: int = 3) -> set[str]:
    """Generate a fingerprint (set of n-grams) for a text.

    Args:
        text: Input text.
        n: N-gram size.

    Returns:
        Set of n-gram strings.
    """
    words = _tokenize(text)
    if len(words) < n:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}


# ── Internal helpers ──


def _tokenize(text: str) -> list[str]:
    """Tokenize and normalize text for comparison."""
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`]+`", "", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = text.lower()
    return re.findall(r"[a-z]+", text)


def _find_common_sequences(
    source: list[str],
    target: list[str],
    min_len: int,
) -> list[PlagiarismMatch]:
    """Find common word sequences using dynamic programming."""
    matches: list[PlagiarismMatch] = []
    target_set = set()
    for i in range(len(target) - min_len + 1):
        seq = tuple(target[i : i + min_len])
        target_set.add(seq)

    used_positions: set[int] = set()

    for i in range(len(source) - min_len + 1):
        if i in used_positions:
            continue
        seq = tuple(source[i : i + min_len])
        if seq in target_set:
            # Extend match as far as possible
            end = i + min_len
            while end < len(source):
                extended = source[i : end + 1]
                extended_str = " ".join(extended)
                if extended_str.lower() in " ".join(target).lower():
                    end += 1
                else:
                    break
            matched = source[i:end]
            matches.append(
                PlagiarismMatch(
                    text=" ".join(matched),
                    length=len(matched),
                )
            )
            for j in range(i, end):
                used_positions.add(j)

    return matches
