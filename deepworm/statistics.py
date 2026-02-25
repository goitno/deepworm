"""Comprehensive document and report statistics.

Compute detailed statistics about text documents including word counts,
reading time, paragraph analysis, vocabulary richness, and more.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class TextStatistics:
    """Comprehensive statistics for a text document."""

    # Basic counts
    character_count: int = 0
    character_count_no_spaces: int = 0
    word_count: int = 0
    sentence_count: int = 0
    paragraph_count: int = 0
    line_count: int = 0

    # Vocabulary
    unique_words: int = 0
    vocabulary_richness: float = 0.0  # unique / total
    hapax_legomena: int = 0  # words appearing only once
    top_words: List[Tuple[str, int]] = field(default_factory=list)

    # Averages
    avg_word_length: float = 0.0
    avg_sentence_length: float = 0.0
    avg_paragraph_length: float = 0.0

    # Reading metrics
    reading_time_minutes: float = 0.0
    speaking_time_minutes: float = 0.0

    # Structure
    heading_count: int = 0
    link_count: int = 0
    image_count: int = 0
    code_block_count: int = 0
    list_item_count: int = 0
    table_count: int = 0

    # Advanced
    longest_word: str = ""
    longest_sentence: str = ""
    shortest_sentence: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "character_count": self.character_count,
            "character_count_no_spaces": self.character_count_no_spaces,
            "word_count": self.word_count,
            "sentence_count": self.sentence_count,
            "paragraph_count": self.paragraph_count,
            "line_count": self.line_count,
            "unique_words": self.unique_words,
            "vocabulary_richness": round(self.vocabulary_richness, 4),
            "hapax_legomena": self.hapax_legomena,
            "top_words": self.top_words,
            "avg_word_length": round(self.avg_word_length, 2),
            "avg_sentence_length": round(self.avg_sentence_length, 2),
            "avg_paragraph_length": round(self.avg_paragraph_length, 2),
            "reading_time_minutes": round(self.reading_time_minutes, 1),
            "speaking_time_minutes": round(self.speaking_time_minutes, 1),
            "heading_count": self.heading_count,
            "link_count": self.link_count,
            "image_count": self.image_count,
            "code_block_count": self.code_block_count,
            "list_item_count": self.list_item_count,
            "table_count": self.table_count,
            "longest_word": self.longest_word,
            "longest_sentence": self.longest_sentence,
            "shortest_sentence": self.shortest_sentence,
        }

    def to_markdown(self) -> str:
        """Generate a markdown summary of statistics."""
        lines = [
            "## Document Statistics",
            "",
            "### Basic Counts",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Characters | {self.character_count:,} |",
            f"| Characters (no spaces) | {self.character_count_no_spaces:,} |",
            f"| Words | {self.word_count:,} |",
            f"| Sentences | {self.sentence_count:,} |",
            f"| Paragraphs | {self.paragraph_count:,} |",
            f"| Lines | {self.line_count:,} |",
            "",
            "### Vocabulary",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Unique words | {self.unique_words:,} |",
            f"| Vocabulary richness | {self.vocabulary_richness:.2%} |",
            f"| Hapax legomena | {self.hapax_legomena:,} |",
            "",
            "### Averages",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Avg word length | {self.avg_word_length:.1f} chars |",
            f"| Avg sentence length | {self.avg_sentence_length:.1f} words |",
            f"| Avg paragraph length | {self.avg_paragraph_length:.1f} words |",
            "",
            "### Reading Time",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Reading time | {self.reading_time_minutes:.1f} min |",
            f"| Speaking time | {self.speaking_time_minutes:.1f} min |",
            "",
        ]
        if any([self.heading_count, self.link_count, self.image_count,
                self.code_block_count, self.list_item_count, self.table_count]):
            lines.extend([
                "### Structure",
                f"| Element | Count |",
                f"|---------|-------|",
                f"| Headings | {self.heading_count} |",
                f"| Links | {self.link_count} |",
                f"| Images | {self.image_count} |",
                f"| Code blocks | {self.code_block_count} |",
                f"| List items | {self.list_item_count} |",
                f"| Tables | {self.table_count} |",
                "",
            ])
        if self.top_words:
            lines.extend([
                "### Top Words",
                "| Word | Count |",
                "|------|-------|",
            ])
            for word, count in self.top_words[:10]:
                lines.append(f"| {word} | {count} |")
            lines.append("")
        return "\n".join(lines)


@dataclass
class ComparisonResult:
    """Result of comparing statistics between two documents."""

    stats_a: TextStatistics
    stats_b: TextStatistics
    label_a: str = "Document A"
    label_b: str = "Document B"

    @property
    def word_count_diff(self) -> int:
        return self.stats_b.word_count - self.stats_a.word_count

    @property
    def vocabulary_diff(self) -> float:
        return self.stats_b.vocabulary_richness - self.stats_a.vocabulary_richness

    def to_markdown(self) -> str:
        lines = [
            "## Statistics Comparison",
            "",
            f"| Metric | {self.label_a} | {self.label_b} | Diff |",
            f"|--------|{'------|' * 3}",
        ]
        metrics = [
            ("Words", self.stats_a.word_count, self.stats_b.word_count),
            ("Sentences", self.stats_a.sentence_count, self.stats_b.sentence_count),
            ("Paragraphs", self.stats_a.paragraph_count, self.stats_b.paragraph_count),
            ("Unique words", self.stats_a.unique_words, self.stats_b.unique_words),
            ("Avg word length", round(self.stats_a.avg_word_length, 1),
             round(self.stats_b.avg_word_length, 1)),
            ("Avg sentence length", round(self.stats_a.avg_sentence_length, 1),
             round(self.stats_b.avg_sentence_length, 1)),
            ("Reading time (min)", round(self.stats_a.reading_time_minutes, 1),
             round(self.stats_b.reading_time_minutes, 1)),
        ]
        for name, a, b in metrics:
            if isinstance(a, int):
                diff = b - a
                sign = "+" if diff > 0 else ""
                lines.append(f"| {name} | {a:,} | {b:,} | {sign}{diff:,} |")
            else:
                diff = b - a
                sign = "+" if diff > 0 else ""
                lines.append(f"| {name} | {a} | {b} | {sign}{diff:.1f} |")
        lines.append("")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label_a": self.label_a,
            "label_b": self.label_b,
            "stats_a": self.stats_a.to_dict(),
            "stats_b": self.stats_b.to_dict(),
            "word_count_diff": self.word_count_diff,
            "vocabulary_diff": round(self.vocabulary_diff, 4),
        }


# Stop words for vocabulary analysis
_STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "shall", "should", "may", "might", "can", "could", "must", "it", "its",
    "this", "that", "these", "those", "i", "you", "he", "she", "we", "they",
    "me", "him", "her", "us", "them", "my", "your", "his", "our", "their",
    "not", "no", "nor", "if", "then", "than", "when", "where", "what",
    "which", "who", "whom", "how", "as", "so", "up", "out", "about",
}


def _split_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    # Remove code blocks before sentence splitting
    cleaned = re.sub(r"```[\s\S]*?```", "", text)
    # Split on sentence-ending punctuation
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 1]


def _extract_words(text: str) -> List[str]:
    """Extract words from text, stripping markdown."""
    # Remove code blocks
    text = re.sub(r"```[\s\S]*?```", "", text)
    # Remove inline code
    text = re.sub(r"`[^`]+`", "", text)
    # Remove URLs
    text = re.sub(r"https?://\S+", "", text)
    # Remove markdown syntax
    text = re.sub(r"[#*_\[\]()!>|]", " ", text)
    # Extract words
    words = re.findall(r"[a-zA-Z]+(?:'[a-zA-Z]+)?", text.lower())
    return words


def compute_statistics(text: str) -> TextStatistics:
    """Compute comprehensive statistics for a text document.

    Args:
        text: The document text (supports markdown).

    Returns:
        TextStatistics with all computed metrics.
    """
    stats = TextStatistics()

    if not text or not text.strip():
        return stats

    # Basic counts
    stats.character_count = len(text)
    stats.character_count_no_spaces = len(text.replace(" ", "").replace("\t", ""))
    stats.line_count = len(text.splitlines())

    # Paragraphs (blocks separated by blank lines)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    stats.paragraph_count = len(paragraphs)

    # Words
    words = _extract_words(text)
    stats.word_count = len(words)

    if not words:
        return stats

    # Vocabulary
    word_counts = Counter(words)
    content_words = {w: c for w, c in word_counts.items() if w not in _STOP_WORDS}
    stats.unique_words = len(word_counts)
    stats.vocabulary_richness = len(word_counts) / len(words) if words else 0
    stats.hapax_legomena = sum(1 for c in word_counts.values() if c == 1)
    stats.top_words = sorted(content_words.items(), key=lambda x: x[1], reverse=True)[:10]

    # Averages
    stats.avg_word_length = sum(len(w) for w in words) / len(words)

    # Sentences
    sentences = _split_sentences(text)
    stats.sentence_count = len(sentences) if sentences else 1
    sentence_word_counts = [len(s.split()) for s in sentences] if sentences else [len(words)]
    stats.avg_sentence_length = (
        sum(sentence_word_counts) / len(sentence_word_counts) if sentence_word_counts else 0
    )

    if sentences:
        longest_idx = max(range(len(sentences)), key=lambda i: len(sentences[i].split()))
        shortest_idx = min(range(len(sentences)), key=lambda i: len(sentences[i].split()))
        stats.longest_sentence = sentences[longest_idx][:200]
        stats.shortest_sentence = sentences[shortest_idx][:200]

    # Paragraph averages
    para_word_counts = [len(p.split()) for p in paragraphs]
    stats.avg_paragraph_length = (
        sum(para_word_counts) / len(para_word_counts) if para_word_counts else 0
    )

    # Reading time (238 WPM average reading speed)
    stats.reading_time_minutes = stats.word_count / 238.0
    # Speaking time (150 WPM average speaking speed)
    stats.speaking_time_minutes = stats.word_count / 150.0

    # Longest word
    if words:
        stats.longest_word = max(words, key=len)

    # Markdown structure
    stats.heading_count = len(re.findall(r"^#{1,6}\s", text, re.MULTILINE))
    stats.link_count = len(re.findall(r"\[([^\]]+)\]\(([^)]+)\)", text))
    stats.image_count = len(re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", text))
    stats.code_block_count = len(re.findall(r"```", text)) // 2
    stats.list_item_count = len(re.findall(r"^[\s]*[-*+]\s", text, re.MULTILINE))
    stats.list_item_count += len(re.findall(r"^[\s]*\d+\.\s", text, re.MULTILINE))
    stats.table_count = _count_tables(text)

    return stats


def _count_tables(text: str) -> int:
    """Count markdown tables in text."""
    count = 0
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            if not in_table:
                in_table = True
                count += 1
        else:
            in_table = False
    return count


def compare_statistics(
    text_a: str,
    text_b: str,
    label_a: str = "Document A",
    label_b: str = "Document B",
) -> ComparisonResult:
    """Compare statistics between two documents.

    Args:
        text_a: First document text.
        text_b: Second document text.
        label_a: Label for first document.
        label_b: Label for second document.

    Returns:
        ComparisonResult with side-by-side statistics.
    """
    return ComparisonResult(
        stats_a=compute_statistics(text_a),
        stats_b=compute_statistics(text_b),
        label_a=label_a,
        label_b=label_b,
    )


def vocabulary_analysis(text: str) -> Dict[str, Any]:
    """Detailed vocabulary analysis.

    Returns word frequency distribution, rare words,
    vocabulary density, and lexical diversity metrics.
    """
    words = _extract_words(text)
    if not words:
        return {
            "total_words": 0,
            "unique_words": 0,
            "vocabulary_richness": 0,
            "type_token_ratio": 0,
            "hapax_legomena": 0,
            "hapax_ratio": 0,
            "frequency_distribution": {},
            "rare_words": [],
            "common_words": [],
        }

    word_counts = Counter(words)
    unique = len(word_counts)
    total = len(words)
    hapax = [w for w, c in word_counts.items() if c == 1]

    # Frequency distribution buckets
    freq_dist: Dict[str, int] = {
        "1 occurrence": 0,
        "2-3 occurrences": 0,
        "4-10 occurrences": 0,
        "11+ occurrences": 0,
    }
    for count in word_counts.values():
        if count == 1:
            freq_dist["1 occurrence"] += 1
        elif count <= 3:
            freq_dist["2-3 occurrences"] += 1
        elif count <= 10:
            freq_dist["4-10 occurrences"] += 1
        else:
            freq_dist["11+ occurrences"] += 1

    # Content words (excluding stop words)
    content_words = {w: c for w, c in word_counts.items() if w not in _STOP_WORDS}

    return {
        "total_words": total,
        "unique_words": unique,
        "vocabulary_richness": round(unique / total, 4) if total else 0,
        "type_token_ratio": round(unique / total, 4) if total else 0,
        "hapax_legomena": len(hapax),
        "hapax_ratio": round(len(hapax) / unique, 4) if unique else 0,
        "frequency_distribution": freq_dist,
        "rare_words": sorted(hapax)[:20],
        "common_words": sorted(content_words.items(), key=lambda x: x[1], reverse=True)[:10],
    }


def section_statistics(text: str) -> List[Dict[str, Any]]:
    """Compute statistics per section (split by headings).

    Args:
        text: Markdown text with headings.

    Returns:
        List of dicts with section title, level, and statistics.
    """
    sections: List[Dict[str, Any]] = []
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    matches = list(heading_pattern.finditer(text))

    if not matches:
        # No headings, treat entire text as one section
        stats = compute_statistics(text)
        return [{
            "title": "(untitled)",
            "level": 0,
            "word_count": stats.word_count,
            "sentence_count": stats.sentence_count,
            "paragraph_count": stats.paragraph_count,
            "reading_time_minutes": round(stats.reading_time_minutes, 1),
        }]

    for i, match in enumerate(matches):
        level = len(match.group(1))
        title = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section_text = text[start:end].strip()

        stats = compute_statistics(section_text)
        sections.append({
            "title": title,
            "level": level,
            "word_count": stats.word_count,
            "sentence_count": stats.sentence_count,
            "paragraph_count": stats.paragraph_count,
            "reading_time_minutes": round(stats.reading_time_minutes, 1),
        })

    return sections


def reading_level(text: str) -> Dict[str, Any]:
    """Estimate reading level using multiple formulas.

    Computes Flesch-Kincaid Grade Level and Automated Readability Index.
    """
    words = _extract_words(text)
    if not words:
        return {"flesch_kincaid_grade": 0, "ari": 0, "level": "N/A"}

    sentences = _split_sentences(text)
    sentence_count = max(len(sentences), 1)
    word_count = len(words)
    char_count = sum(len(w) for w in words)

    # Count syllables (approximation)
    total_syllables = sum(_count_syllables(w) for w in words)

    # Flesch-Kincaid Grade Level
    fk_grade = (
        0.39 * (word_count / sentence_count)
        + 11.8 * (total_syllables / word_count)
        - 15.59
    )

    # Automated Readability Index
    ari = (
        4.71 * (char_count / word_count)
        + 0.5 * (word_count / sentence_count)
        - 21.43
    )

    fk_grade = max(0, round(fk_grade, 1))
    ari = max(0, round(ari, 1))

    # Determine level
    avg_grade = (fk_grade + ari) / 2
    if avg_grade <= 5:
        level = "Elementary"
    elif avg_grade <= 8:
        level = "Middle School"
    elif avg_grade <= 12:
        level = "High School"
    elif avg_grade <= 16:
        level = "College"
    else:
        level = "Graduate"

    return {
        "flesch_kincaid_grade": fk_grade,
        "ari": ari,
        "level": level,
        "avg_grade": round(avg_grade, 1),
        "word_count": word_count,
        "sentence_count": sentence_count,
        "syllable_count": total_syllables,
    }


def _count_syllables(word: str) -> int:
    """Approximate syllable count for a word."""
    word = word.lower().strip()
    if len(word) <= 2:
        return 1
    # Remove trailing 'e'
    if word.endswith("e") and not word.endswith("le"):
        word = word[:-1]
    # Count vowel groups
    count = len(re.findall(r"[aeiouy]+", word))
    return max(1, count)
