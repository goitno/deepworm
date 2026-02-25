"""Word frequency analysis and word cloud data generation.

Analyze word frequencies in reports and generate structured data
suitable for word cloud visualization. Supports stop word filtering,
stemming approximation, and category-based grouping.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


# Common English stop words
_STOP_WORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "also", "am",
    "an", "and", "any", "are", "aren't", "as", "at", "be", "because", "been",
    "before", "being", "below", "between", "both", "but", "by", "can", "can't",
    "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing",
    "don't", "down", "during", "each", "few", "for", "from", "further", "get",
    "got", "had", "hadn't", "has", "hasn't", "have", "haven't", "having",
    "he", "her", "here", "hers", "herself", "him", "himself", "his", "how",
    "i", "if", "in", "into", "is", "isn't", "it", "its", "itself", "just",
    "let", "like", "ll", "me", "might", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "now", "of", "off", "on", "once", "only",
    "or", "other", "our", "ours", "ourselves", "out", "over", "own", "re",
    "s", "same", "she", "should", "shouldn't", "so", "some", "still", "such",
    "t", "than", "that", "the", "their", "theirs", "them", "themselves",
    "then", "there", "these", "they", "this", "those", "through", "to",
    "too", "under", "until", "up", "us", "ve", "very", "was", "wasn't",
    "we", "were", "weren't", "what", "when", "where", "which", "while",
    "who", "whom", "why", "will", "with", "won't", "would", "wouldn't",
    "you", "your", "yours", "yourself", "yourselves",
    "one", "two", "three", "use", "used", "using", "may", "new", "well",
    "also", "however", "many", "much", "make", "made", "see", "way",
    "first", "second", "even", "back", "go", "going", "take", "since",
    "need", "come", "know", "say", "said", "part", "based", "different",
}


@dataclass
class WordFrequency:
    """A word with its frequency metrics."""

    word: str
    count: int
    frequency: float  # relative frequency (0-1)
    rank: int = 0
    tfidf: float = 0.0  # TF-IDF score if multiple docs
    weight: float = 0.0  # normalized weight for visualization (0-1)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "word": self.word,
            "count": self.count,
            "frequency": round(self.frequency, 4),
            "rank": self.rank,
            "weight": round(self.weight, 3),
        }


@dataclass
class WordCloudData:
    """Word cloud data ready for visualization."""

    words: List[WordFrequency] = field(default_factory=list)
    total_words: int = 0
    unique_words: int = 0
    source_title: str = ""

    @property
    def top(self) -> List[WordFrequency]:
        """Get top 10 words by weight."""
        return sorted(self.words, key=lambda w: w.weight, reverse=True)[:10]

    def filter_by_min_count(self, min_count: int) -> List[WordFrequency]:
        """Filter words with at least min_count occurrences."""
        return [w for w in self.words if w.count >= min_count]

    def to_size_map(
        self, min_size: int = 12, max_size: int = 72
    ) -> List[Dict[str, Any]]:
        """Convert to size-mapped format for visualization.

        Returns list of {word, size, count} dicts.
        """
        if not self.words:
            return []

        result = []
        for wf in self.words:
            size = min_size + (max_size - min_size) * wf.weight
            result.append({
                "word": wf.word,
                "size": round(size),
                "count": wf.count,
            })
        return result

    def to_markdown(self) -> str:
        """Render as markdown table."""
        lines = ["## Word Frequencies\n"]
        if self.source_title:
            lines.append(f"*Source: {self.source_title}*\n")

        lines.append(f"Total words: {self.total_words} | "
                      f"Unique: {self.unique_words}\n")

        lines.append("| Rank | Word | Count | Frequency |")
        lines.append("|------|------|-------|-----------|")

        for wf in sorted(self.words, key=lambda w: w.rank)[:50]:
            lines.append(
                f"| {wf.rank} | {wf.word} | {wf.count} | "
                f"{wf.frequency:.2%} |"
            )

        return "\n".join(lines) + "\n"

    def to_html_cloud(self) -> str:
        """Generate inline HTML word cloud."""
        if not self.words:
            return "<p>No words to display.</p>"

        parts = ['<div style="text-align:center;line-height:2.5;">']

        for item in self.to_size_map():
            opacity = 0.5 + 0.5 * (item["size"] / 72)
            parts.append(
                f'<span style="font-size:{item["size"]}px;'
                f'opacity:{opacity:.2f};'
                f'margin:0 8px;display:inline-block;" '
                f'title="{item["count"]} occurrences">'
                f'{item["word"]}</span>'
            )

        parts.append("</div>")
        return "\n".join(parts)

    def to_csv(self) -> str:
        """Export as CSV."""
        lines = ["word,count,frequency,rank,weight"]
        for wf in sorted(self.words, key=lambda w: w.rank):
            lines.append(
                f"{wf.word},{wf.count},{wf.frequency:.4f},"
                f"{wf.rank},{wf.weight:.3f}"
            )
        return "\n".join(lines) + "\n"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_words": self.total_words,
            "unique_words": self.unique_words,
            "source_title": self.source_title,
            "words": [w.to_dict() for w in sorted(
                self.words, key=lambda w: w.rank
            )],
        }


def generate_word_cloud(
    text: str,
    max_words: int = 100,
    min_length: int = 3,
    min_count: int = 2,
    custom_stop_words: Optional[Set[str]] = None,
    title: str = "",
) -> WordCloudData:
    """Generate word cloud data from text.

    Args:
        text: Input text to analyze.
        max_words: Maximum number of words in the cloud.
        min_length: Minimum word length to include.
        min_count: Minimum frequency to include.
        custom_stop_words: Additional stop words to filter.
        title: Source title for the data.

    Returns:
        WordCloudData ready for visualization.
    """
    words = _tokenize(text)
    total = len(words)

    if total == 0:
        return WordCloudData(source_title=title)

    # Build stop word set
    stop_words = _STOP_WORDS.copy()
    if custom_stop_words:
        stop_words |= custom_stop_words

    # Count frequencies
    counts: Dict[str, int] = {}
    for word in words:
        if (
            len(word) >= min_length
            and word not in stop_words
            and not word.isdigit()
        ):
            counts[word] = counts.get(word, 0) + 1

    # Filter by minimum count
    counts = {w: c for w, c in counts.items() if c >= min_count}

    if not counts:
        return WordCloudData(
            total_words=total,
            unique_words=len(set(words)),
            source_title=title,
        )

    # Sort by count
    sorted_words = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    sorted_words = sorted_words[:max_words]

    # Calculate weights
    max_count = sorted_words[0][1] if sorted_words else 1
    min_count_val = sorted_words[-1][1] if sorted_words else 1
    count_range = max(max_count - min_count_val, 1)

    word_freqs: List[WordFrequency] = []
    for rank, (word, count) in enumerate(sorted_words, 1):
        frequency = count / total
        weight = (count - min_count_val) / count_range
        word_freqs.append(WordFrequency(
            word=word,
            count=count,
            frequency=frequency,
            rank=rank,
            weight=weight,
        ))

    return WordCloudData(
        words=word_freqs,
        total_words=total,
        unique_words=len(set(words)),
        source_title=title,
    )


def compare_word_clouds(
    cloud_a: WordCloudData,
    cloud_b: WordCloudData,
) -> Dict[str, Any]:
    """Compare two word clouds.

    Returns shared words, unique words, and differences.
    """
    words_a = {w.word: w for w in cloud_a.words}
    words_b = {w.word: w for w in cloud_b.words}

    shared = set(words_a.keys()) & set(words_b.keys())
    only_a = set(words_a.keys()) - set(words_b.keys())
    only_b = set(words_b.keys()) - set(words_a.keys())

    # Biggest differences in shared words
    diffs: List[Dict[str, Any]] = []
    for word in shared:
        diff = abs(words_a[word].frequency - words_b[word].frequency)
        diffs.append({
            "word": word,
            "freq_a": round(words_a[word].frequency, 4),
            "freq_b": round(words_b[word].frequency, 4),
            "diff": round(diff, 4),
        })
    diffs.sort(key=lambda d: d["diff"], reverse=True)

    return {
        "shared_count": len(shared),
        "unique_to_a": len(only_a),
        "unique_to_b": len(only_b),
        "overlap_ratio": len(shared) / max(
            len(words_a) + len(words_b) - len(shared), 1
        ),
        "top_shared": [d["word"] for d in diffs[:10]],
        "top_only_a": sorted(only_a, key=lambda w: words_a[w].count, reverse=True)[:10],
        "top_only_b": sorted(only_b, key=lambda w: words_b[w].count, reverse=True)[:10],
        "biggest_diffs": diffs[:10],
    }


def tfidf_cloud(
    texts: List[str],
    max_words: int = 50,
    min_length: int = 3,
) -> List[WordCloudData]:
    """Generate TF-IDF word clouds for multiple documents.

    Uses TF-IDF scoring instead of raw frequency to highlight
    words that are distinctive to each document.

    Args:
        texts: List of document texts.
        max_words: Maximum words per cloud.
        min_length: Minimum word length.

    Returns:
        List of WordCloudData, one per document.
    """
    if not texts:
        return []

    n_docs = len(texts)

    # Tokenize all docs
    all_tokens: List[List[str]] = []
    doc_freqs: Dict[str, int] = {}  # document frequency

    for text in texts:
        tokens = _tokenize(text)
        filtered = [
            w for w in tokens
            if len(w) >= min_length
            and w not in _STOP_WORDS
            and not w.isdigit()
        ]
        all_tokens.append(filtered)

        unique_in_doc = set(filtered)
        for word in unique_in_doc:
            doc_freqs[word] = doc_freqs.get(word, 0) + 1

    # Calculate TF-IDF for each document
    results: List[WordCloudData] = []
    for doc_idx, tokens in enumerate(all_tokens):
        if not tokens:
            results.append(WordCloudData())
            continue

        # Term frequency
        tf: Dict[str, int] = {}
        for word in tokens:
            tf[word] = tf.get(word, 0) + 1

        # TF-IDF scores
        scores: Dict[str, float] = {}
        for word, count in tf.items():
            tf_val = count / len(tokens)
            idf = math.log(n_docs / max(doc_freqs.get(word, 1), 1))
            scores[word] = tf_val * idf

        # Sort and take top
        sorted_scores = sorted(
            scores.items(), key=lambda x: x[1], reverse=True
        )
        sorted_scores = sorted_scores[:max_words]

        if not sorted_scores:
            results.append(WordCloudData(total_words=len(tokens)))
            continue

        max_score = sorted_scores[0][1] if sorted_scores else 1
        min_score = sorted_scores[-1][1] if sorted_scores else 0
        score_range = max(max_score - min_score, 0.0001)

        word_freqs: List[WordFrequency] = []
        total = len(tokens)
        for rank, (word, score) in enumerate(sorted_scores, 1):
            weight = (score - min_score) / score_range
            word_freqs.append(WordFrequency(
                word=word,
                count=tf.get(word, 0),
                frequency=tf.get(word, 0) / total,
                rank=rank,
                tfidf=round(score, 6),
                weight=weight,
            ))

        results.append(WordCloudData(
            words=word_freqs,
            total_words=total,
            unique_words=len(set(tokens)),
        ))

    return results


def _tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase words, stripping markdown."""
    # Remove code blocks
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`]+`", "", text)
    # Remove images and links (keeping link text)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]+\)", r"\1", text)
    # Remove headings markers
    text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)
    # Remove bold/italic
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    # Remove URLs
    text = re.sub(r"https?://\S+", "", text)
    # Extract words
    return re.findall(r"[a-z]+", text.lower())
