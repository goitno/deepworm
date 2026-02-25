"""Keyword and keyphrase extraction from research reports.

Extracts important terms and phrases using TF-IDF-like scoring
and statistical analysis — no external NLP dependencies required.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any


# Common English stop words to filter out
_STOP_WORDS: frozenset[str] = frozenset({
    "a", "about", "above", "after", "again", "against", "all", "am", "an",
    "and", "any", "are", "aren't", "as", "at", "be", "because", "been",
    "before", "being", "below", "between", "both", "but", "by", "can",
    "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does",
    "doesn't", "doing", "don't", "down", "during", "each", "few", "for",
    "from", "further", "get", "got", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "her", "here", "hers", "herself",
    "him", "himself", "his", "how", "i", "if", "in", "into", "is",
    "isn't", "it", "its", "itself", "just", "let", "like", "ll", "may",
    "me", "might", "more", "most", "must", "mustn't", "my", "myself",
    "need", "no", "nor", "not", "now", "of", "off", "on", "once",
    "only", "or", "other", "our", "ours", "ourselves", "out", "over",
    "own", "re", "s", "same", "shall", "shan't", "she", "should",
    "shouldn't", "so", "some", "such", "t", "than", "that", "the",
    "their", "theirs", "them", "themselves", "then", "there", "these",
    "they", "this", "those", "through", "to", "too", "under", "until",
    "up", "us", "ve", "very", "was", "wasn't", "we", "were", "weren't",
    "what", "when", "where", "which", "while", "who", "whom", "why",
    "will", "with", "won't", "would", "wouldn't", "you", "your", "yours",
    "yourself", "yourselves", "also", "been", "being", "well", "much",
    "still", "even", "back", "make", "made", "many", "way", "new",
    "used", "using", "one", "two", "first", "however", "since",
})


@dataclass
class Keyword:
    """An extracted keyword or keyphrase."""

    term: str
    score: float  # Importance score (higher = more important)
    frequency: int  # Raw occurrence count
    is_phrase: bool = False  # True if multi-word phrase

    def to_dict(self) -> dict[str, Any]:
        return {
            "term": self.term,
            "score": round(self.score, 3),
            "frequency": self.frequency,
            "is_phrase": self.is_phrase,
        }


@dataclass
class KeywordResult:
    """Result of keyword extraction."""

    keywords: list[Keyword] = field(default_factory=list)
    total_words: int = 0
    unique_words: int = 0

    @property
    def top_terms(self) -> list[str]:
        """Top keyword strings only."""
        return [k.term for k in self.keywords]

    def to_dict(self) -> dict[str, Any]:
        return {
            "keywords": [k.to_dict() for k in self.keywords],
            "total_words": self.total_words,
            "unique_words": self.unique_words,
        }

    def to_markdown(self) -> str:
        """Render keywords as markdown."""
        lines = [
            "## Keywords",
            "",
            "| Keyword | Score | Frequency |",
            "|---------|-------|-----------|",
        ]
        for kw in self.keywords:
            lines.append(f"| {kw.term} | {kw.score:.3f} | {kw.frequency} |")
        return "\n".join(lines)


def extract_keywords(
    text: str,
    max_keywords: int = 15,
    include_phrases: bool = True,
    min_frequency: int = 2,
) -> KeywordResult:
    """Extract keywords from text using TF-based scoring.

    Args:
        text: Text to extract keywords from.
        max_keywords: Maximum number of keywords to return.
        include_phrases: Include multi-word phrases (bigrams/trigrams).
        min_frequency: Minimum occurrence count for inclusion.

    Returns:
        KeywordResult with ranked keywords.
    """
    clean = _strip_markdown(text)
    words = _tokenize(clean)

    if not words:
        return KeywordResult()

    total_words = len(words)

    # Filter stop words
    content_words = [w for w in words if w.lower() not in _STOP_WORDS and len(w) > 2]

    # Unigram scoring
    word_freq = Counter(w.lower() for w in content_words)
    keywords: list[Keyword] = []

    for word, freq in word_freq.items():
        if freq < min_frequency:
            continue
        score = _score_term(word, freq, total_words)
        keywords.append(Keyword(term=word, score=score, frequency=freq))

    # Phrase extraction (bigrams and trigrams)
    if include_phrases:
        phrases = _extract_phrases(content_words, min_frequency)
        keywords.extend(phrases)

    # Sort by score descending
    keywords.sort(key=lambda k: k.score, reverse=True)

    # Deduplicate (remove words that are part of higher-scoring phrases)
    keywords = _deduplicate(keywords)

    return KeywordResult(
        keywords=keywords[:max_keywords],
        total_words=total_words,
        unique_words=len(set(w.lower() for w in words)),
    )


def extract_tags(text: str, max_tags: int = 8) -> list[str]:
    """Extract short tags suitable for tagging/categorization.

    Args:
        text: Text to extract tags from.
        max_tags: Maximum number of tags.

    Returns:
        List of tag strings.
    """
    result = extract_keywords(text, max_keywords=max_tags * 2, min_frequency=1)
    tags = []
    for kw in result.keywords:
        tag = kw.term.lower().replace(" ", "-")
        if len(tag) <= 30 and tag not in tags:
            tags.append(tag)
        if len(tags) >= max_tags:
            break
    return tags


# ── Internal helpers ──


def _score_term(word: str, frequency: int, total_words: int) -> float:
    """Score a term based on TF and heuristics."""
    # Term frequency (log-normalized)
    tf = 1 + math.log(frequency) if frequency > 0 else 0

    # Length bonus (longer words tend to be more specific)
    length_bonus = min(1.0, len(word) / 10)

    # Capitalization bonus (proper nouns, acronyms)
    cap_bonus = 0.0
    if word[0].isupper():
        cap_bonus = 0.2
    if word.isupper() and len(word) >= 2:
        cap_bonus = 0.5

    # Rarity bonus (less common = more distinctive)
    rarity = 1.0 - (frequency / total_words) if total_words > 0 else 0

    score = tf * (1 + length_bonus) * (1 + cap_bonus) * (0.5 + rarity * 0.5)
    return score


def _extract_phrases(words: list[str], min_freq: int) -> list[Keyword]:
    """Extract significant bigrams and trigrams."""
    phrases: list[Keyword] = []
    lower_words = [w.lower() for w in words]

    # Bigrams
    bigram_freq: Counter[str] = Counter()
    for i in range(len(lower_words) - 1):
        w1, w2 = lower_words[i], lower_words[i + 1]
        if w1 not in _STOP_WORDS and w2 not in _STOP_WORDS:
            bigram_freq[f"{w1} {w2}"] += 1

    for phrase, freq in bigram_freq.items():
        if freq >= min_freq:
            score = _score_term(phrase, freq, len(words)) * 1.5  # Phrase bonus
            phrases.append(Keyword(term=phrase, score=score, frequency=freq, is_phrase=True))

    # Trigrams
    trigram_freq: Counter[str] = Counter()
    for i in range(len(lower_words) - 2):
        w1, w2, w3 = lower_words[i], lower_words[i + 1], lower_words[i + 2]
        # Allow one stop word in middle
        if w1 not in _STOP_WORDS and w3 not in _STOP_WORDS:
            trigram_freq[f"{w1} {w2} {w3}"] += 1

    for phrase, freq in trigram_freq.items():
        if freq >= min_freq:
            score = _score_term(phrase, freq, len(words)) * 2.0  # Higher phrase bonus
            phrases.append(Keyword(term=phrase, score=score, frequency=freq, is_phrase=True))

    return phrases


def _deduplicate(keywords: list[Keyword]) -> list[Keyword]:
    """Remove single words that are substrings of higher-scoring phrases."""
    result: list[Keyword] = []
    phrase_terms = {k.term for k in keywords if k.is_phrase}

    for kw in keywords:
        if not kw.is_phrase:
            # Check if this word is part of any phrase
            if any(kw.term in phrase for phrase in phrase_terms):
                continue
        result.append(kw)

    return result


def _tokenize(text: str) -> list[str]:
    """Tokenize text into words."""
    return re.findall(r"[A-Za-z][A-Za-z']*[A-Za-z]|[A-Za-z]", text)


def _strip_markdown(text: str) -> str:
    """Remove markdown formatting."""
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`]+`", "", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"^\|.*\|$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)
    return text
