"""Readability analysis for research reports.

Calculates readability metrics to assess how accessible a report is:
- Flesch Reading Ease
- Flesch-Kincaid Grade Level
- Gunning Fog Index
- Coleman-Liau Index
- Average sentence/word length
- Vocabulary richness
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class ReadabilityResult:
    """Readability analysis results."""

    flesch_reading_ease: float  # 0-100, higher = easier
    flesch_kincaid_grade: float  # US grade level
    gunning_fog: float  # Years of education needed
    coleman_liau: float  # US grade level
    avg_sentence_length: float  # Words per sentence
    avg_word_length: float  # Characters per word
    avg_syllables_per_word: float
    total_words: int
    total_sentences: int
    total_syllables: int
    vocabulary_size: int  # Unique words
    vocabulary_richness: float  # Type-token ratio (0.0-1.0)

    @property
    def reading_level(self) -> str:
        """Human-readable reading level based on Flesch Reading Ease."""
        score = self.flesch_reading_ease
        if score >= 90:
            return "Very Easy"
        elif score >= 80:
            return "Easy"
        elif score >= 70:
            return "Fairly Easy"
        elif score >= 60:
            return "Standard"
        elif score >= 50:
            return "Fairly Difficult"
        elif score >= 30:
            return "Difficult"
        return "Very Difficult"

    @property
    def grade_level(self) -> str:
        """Consensus grade level from multiple formulas."""
        avg = (self.flesch_kincaid_grade + self.coleman_liau) / 2
        if avg <= 6:
            return "Elementary"
        elif avg <= 8:
            return "Middle School"
        elif avg <= 12:
            return "High School"
        elif avg <= 16:
            return "College"
        return "Graduate"

    def to_dict(self) -> dict[str, Any]:
        return {
            "flesch_reading_ease": round(self.flesch_reading_ease, 1),
            "flesch_kincaid_grade": round(self.flesch_kincaid_grade, 1),
            "gunning_fog": round(self.gunning_fog, 1),
            "coleman_liau": round(self.coleman_liau, 1),
            "avg_sentence_length": round(self.avg_sentence_length, 1),
            "avg_word_length": round(self.avg_word_length, 1),
            "avg_syllables_per_word": round(self.avg_syllables_per_word, 2),
            "total_words": self.total_words,
            "total_sentences": self.total_sentences,
            "total_syllables": self.total_syllables,
            "vocabulary_size": self.vocabulary_size,
            "vocabulary_richness": round(self.vocabulary_richness, 2),
            "reading_level": self.reading_level,
            "grade_level": self.grade_level,
        }

    def to_markdown(self) -> str:
        """Render readability results as markdown."""
        lines = [
            "## Readability Analysis",
            "",
            f"**Reading Level:** {self.reading_level} | "
            f"**Grade Level:** {self.grade_level}",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Flesch Reading Ease | {self.flesch_reading_ease:.1f}/100 |",
            f"| Flesch-Kincaid Grade | {self.flesch_kincaid_grade:.1f} |",
            f"| Gunning Fog Index | {self.gunning_fog:.1f} |",
            f"| Coleman-Liau Index | {self.coleman_liau:.1f} |",
            f"| Avg. Sentence Length | {self.avg_sentence_length:.1f} words |",
            f"| Avg. Word Length | {self.avg_word_length:.1f} chars |",
            f"| Avg. Syllables/Word | {self.avg_syllables_per_word:.2f} |",
            f"| Total Words | {self.total_words} |",
            f"| Total Sentences | {self.total_sentences} |",
            f"| Vocabulary Size | {self.vocabulary_size} unique |",
            f"| Vocabulary Richness | {self.vocabulary_richness:.0%} |",
        ]
        return "\n".join(lines)


def analyze_readability(text: str) -> ReadabilityResult:
    """Analyze readability of text.

    Strips markdown formatting before analysis.

    Args:
        text: Text or markdown to analyze.

    Returns:
        ReadabilityResult with all metrics.
    """
    # Strip markdown formatting
    clean = _strip_markdown(text)

    words = _get_words(clean)
    sentences = _get_sentences(clean)
    syllables_list = [count_syllables(w) for w in words]

    total_words = len(words)
    total_sentences = max(len(sentences), 1)
    total_syllables = sum(syllables_list)

    avg_sentence_length = total_words / total_sentences
    avg_word_length = (
        sum(len(w) for w in words) / total_words if total_words > 0 else 0.0
    )
    avg_syllables = total_syllables / total_words if total_words > 0 else 0.0

    # Unique words
    unique_words = set(w.lower() for w in words)
    vocabulary_size = len(unique_words)
    vocabulary_richness = vocabulary_size / total_words if total_words > 0 else 0.0

    # Complex words (3+ syllables)
    complex_words = sum(1 for s in syllables_list if s >= 3)

    # Character counts for Coleman-Liau
    total_chars = sum(len(w) for w in words)

    # Calculate metrics
    flesch = _flesch_reading_ease(total_words, total_sentences, total_syllables)
    fk_grade = _flesch_kincaid_grade(total_words, total_sentences, total_syllables)
    fog = _gunning_fog(total_words, total_sentences, complex_words)
    cl = _coleman_liau(total_chars, total_words, total_sentences)

    return ReadabilityResult(
        flesch_reading_ease=flesch,
        flesch_kincaid_grade=fk_grade,
        gunning_fog=fog,
        coleman_liau=cl,
        avg_sentence_length=avg_sentence_length,
        avg_word_length=avg_word_length,
        avg_syllables_per_word=avg_syllables,
        total_words=total_words,
        total_sentences=total_sentences,
        total_syllables=total_syllables,
        vocabulary_size=vocabulary_size,
        vocabulary_richness=vocabulary_richness,
    )


def count_syllables(word: str) -> int:
    """Count syllables in a word using heuristic rules.

    Args:
        word: Single word to analyze.

    Returns:
        Estimated syllable count (minimum 1).
    """
    word = word.lower().strip()
    if not word:
        return 0

    # Remove trailing e (silent e)
    if word.endswith("e") and len(word) > 2:
        word = word[:-1]

    # Count vowel groups
    count = len(re.findall(r"[aeiouy]+", word))

    # Special endings
    if word.endswith(("le", "les")) and len(word) > 2:
        count += 1

    return max(1, count)


# ── Readability formulas ──


def _flesch_reading_ease(
    total_words: int, total_sentences: int, total_syllables: int,
) -> float:
    """Flesch Reading Ease: 0-100 scale, higher = easier."""
    if total_words == 0 or total_sentences == 0:
        return 0.0
    asl = total_words / total_sentences
    asw = total_syllables / total_words
    score = 206.835 - (1.015 * asl) - (84.6 * asw)
    return max(0.0, min(100.0, score))


def _flesch_kincaid_grade(
    total_words: int, total_sentences: int, total_syllables: int,
) -> float:
    """Flesch-Kincaid Grade Level: US grade level."""
    if total_words == 0 or total_sentences == 0:
        return 0.0
    asl = total_words / total_sentences
    asw = total_syllables / total_words
    grade = (0.39 * asl) + (11.8 * asw) - 15.59
    return max(0.0, grade)


def _gunning_fog(
    total_words: int, total_sentences: int, complex_words: int,
) -> float:
    """Gunning Fog Index: years of education needed."""
    if total_words == 0 or total_sentences == 0:
        return 0.0
    asl = total_words / total_sentences
    pcw = (complex_words / total_words) * 100
    fog = 0.4 * (asl + pcw)
    return max(0.0, fog)


def _coleman_liau(
    total_chars: int, total_words: int, total_sentences: int,
) -> float:
    """Coleman-Liau Index: US grade level."""
    if total_words == 0 or total_sentences == 0:
        return 0.0
    l = (total_chars / total_words) * 100  # Avg letters per 100 words
    s = (total_sentences / total_words) * 100  # Avg sentences per 100 words
    cli = (0.0588 * l) - (0.296 * s) - 15.8
    return max(0.0, cli)


# ── Text preprocessing ──


def _strip_markdown(text: str) -> str:
    """Remove markdown formatting from text."""
    # Remove code blocks
    text = re.sub(r"```[\s\S]*?```", "", text)
    # Remove inline code
    text = re.sub(r"`[^`]+`", "", text)
    # Remove headings markers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove bold/italic
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    # Remove links
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove images
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", "", text)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Remove table separators
    text = re.sub(r"^\|[-:|]+\|$", "", text, flags=re.MULTILINE)
    # Remove list markers
    text = re.sub(r"^[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\d+\.\s+", "", text, flags=re.MULTILINE)
    # Remove blockquote markers
    text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)
    # Remove horizontal rules
    text = re.sub(r"^---+\s*$", "", text, flags=re.MULTILINE)
    return text


def _get_words(text: str) -> list[str]:
    """Extract words from text."""
    return re.findall(r"[a-zA-Z']+", text)


def _get_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    sentences = re.split(r"[.!?]+\s+", text)
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]
