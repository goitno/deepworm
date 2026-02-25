"""Report summarization and abstract generation.

Generate concise summaries and abstracts from research reports:
- Executive summaries with key findings
- Academic-style abstracts
- Bullet-point key takeaways
- Configurable summary length
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Summary:
    """A generated summary of a research report."""

    text: str
    style: str  # "executive", "abstract", "bullets", "tldr"
    word_count: int = 0
    key_findings: list[str] = field(default_factory=list)
    topics_covered: list[str] = field(default_factory=list)
    source_word_count: int = 0

    @property
    def compression_ratio(self) -> float:
        """How much the text was compressed (0.0-1.0)."""
        if self.source_word_count <= 0:
            return 0.0
        return 1.0 - (self.word_count / self.source_word_count)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "style": self.style,
            "word_count": self.word_count,
            "key_findings": self.key_findings,
            "topics_covered": self.topics_covered,
            "source_word_count": self.source_word_count,
            "compression_ratio": round(self.compression_ratio, 2),
        }


def summarize(
    report: str,
    style: str = "executive",
    max_words: int | None = None,
) -> Summary:
    """Generate a summary from a research report.

    Args:
        report: Full markdown report text.
        style: Summary style — "executive", "abstract", "bullets", or "tldr".
        max_words: Maximum word count for the summary.

    Returns:
        Summary with text and metadata.
    """
    style = style if style in ("executive", "abstract", "bullets", "tldr") else "executive"

    source_words = len(report.split())

    if style == "executive":
        return _executive_summary(report, source_words, max_words)
    elif style == "abstract":
        return _academic_abstract(report, source_words, max_words)
    elif style == "bullets":
        return _bullet_summary(report, source_words, max_words)
    else:
        return _tldr_summary(report, source_words, max_words)


def extract_key_findings(report: str, max_findings: int = 5) -> list[str]:
    """Extract key findings from a report.

    Heuristically identifies the most important statements.

    Args:
        report: Markdown report text.
        max_findings: Maximum number of findings to extract.

    Returns:
        List of key finding strings.
    """
    findings: list[str] = []

    # Look for explicit findings/conclusions sections
    sections = _split_sections(report)
    priority_sections = []
    other_sections = []

    for title, content in sections:
        title_lower = title.lower()
        if any(k in title_lower for k in [
            "finding", "conclusion", "result", "key", "summary",
            "takeaway", "highlight", "insight",
        ]):
            priority_sections.append((title, content))
        else:
            other_sections.append((title, content))

    # Extract from priority sections first
    for _, content in priority_sections:
        findings.extend(_extract_important_sentences(content))
        if len(findings) >= max_findings:
            break

    # Then from other sections
    if len(findings) < max_findings:
        for _, content in other_sections:
            findings.extend(_extract_important_sentences(content))
            if len(findings) >= max_findings:
                break

    return findings[:max_findings]


def extract_topics(report: str) -> list[str]:
    """Extract main topics covered in the report.

    Args:
        report: Markdown report text.

    Returns:
        List of topic strings from headings.
    """
    topics = []
    for match in re.finditer(r"^#{2,3}\s+(.+)", report, re.MULTILINE):
        topic = match.group(1).strip()
        # Skip generic headings
        if topic.lower() not in {
            "introduction", "conclusion", "references", "sources",
            "table of contents", "abstract", "summary",
        }:
            topics.append(topic)
    return topics


# ── Internal helpers ──


def _split_sections(report: str) -> list[tuple[str, str]]:
    """Split report into (heading, content) pairs."""
    sections: list[tuple[str, str]] = []
    current_title = ""
    current_lines: list[str] = []

    for line in report.split("\n"):
        heading_match = re.match(r"^#{1,3}\s+(.+)", line)
        if heading_match:
            if current_title or current_lines:
                sections.append((current_title, "\n".join(current_lines)))
            current_title = heading_match.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_title or current_lines:
        sections.append((current_title, "\n".join(current_lines)))

    return sections


def _extract_important_sentences(text: str) -> list[str]:
    """Extract sentences that are likely key findings."""
    # Split into sentences
    sentences = re.split(r"(?<=[.!?])\s+", text)
    important = []

    importance_signals = [
        r"\b(significant|significantly|notably|importantly)\b",
        r"\b(found|discovered|revealed|showed|demonstrated)\b",
        r"\b(increase|decrease|growth|decline|change)\b",
        r"\b(\d+%|\d+\.\d+%)",  # percentages
        r"\b(key|critical|essential|primary|main)\b",
        r"\b(according to|research shows|studies indicate)\b",
        r"\b(million|billion|trillion)\b",
        r"\b(first|largest|most|best|worst|highest|lowest)\b",
    ]

    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 20 or len(sentence) > 300:
            continue
        # Skip bullets, headings, links
        if sentence.startswith(("-", "*", "#", "[", "|")):
            continue

        score = sum(
            1 for pattern in importance_signals
            if re.search(pattern, sentence, re.I)
        )
        if score >= 1:
            # Clean up the sentence
            clean = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", sentence)  # Remove links
            clean = re.sub(r"\*\*(.+?)\*\*", r"\1", clean)  # Remove bold
            clean = clean.strip()
            if clean and clean not in important:
                important.append(clean)

    return important


def _get_first_paragraph(report: str) -> str:
    """Get the first substantial paragraph after the title."""
    lines = report.split("\n")
    paragraph_lines: list[str] = []
    in_paragraph = False

    for line in lines:
        stripped = line.strip()
        # Skip headings, empty, bullets, code
        if stripped.startswith("#") or stripped.startswith("```"):
            if in_paragraph:
                break
            continue
        if not stripped:
            if in_paragraph:
                break
            continue
        if stripped.startswith(("-", "*", "|", ">")):
            if in_paragraph:
                break
            continue

        in_paragraph = True
        paragraph_lines.append(stripped)

    return " ".join(paragraph_lines)


def _executive_summary(
    report: str, source_words: int, max_words: int | None,
) -> Summary:
    """Generate an executive summary."""
    max_w = max_words or max(50, source_words // 8)

    sections = _split_sections(report)
    topics = extract_topics(report)
    findings = extract_key_findings(report)

    # Build summary from first paragraph + findings
    parts: list[str] = []

    first_para = _get_first_paragraph(report)
    if first_para:
        parts.append(first_para)

    if findings:
        parts.append("\nKey findings:")
        for f in findings[:3]:
            parts.append(f"- {f}")

    if topics:
        parts.append(f"\nTopics covered: {', '.join(topics[:5])}.")

    text = "\n".join(parts)

    # Truncate to max_words
    words = text.split()
    if len(words) > max_w:
        text = " ".join(words[:max_w]) + "..."

    return Summary(
        text=text,
        style="executive",
        word_count=len(text.split()),
        key_findings=findings,
        topics_covered=topics,
        source_word_count=source_words,
    )


def _academic_abstract(
    report: str, source_words: int, max_words: int | None,
) -> Summary:
    """Generate an academic-style abstract."""
    max_w = max_words or min(250, max(100, source_words // 10))

    topics = extract_topics(report)
    findings = extract_key_findings(report)

    # Extract title
    title_match = re.match(r"^#\s+(.+)", report)
    title = title_match.group(1).strip() if title_match else "this research"

    parts: list[str] = []

    # Context/background
    first_para = _get_first_paragraph(report)
    if first_para:
        # Take first sentence as context
        first_sentence = re.split(r"(?<=[.!?])\s+", first_para)[0]
        parts.append(first_sentence)

    # Method (implied)
    parts.append(
        f"This report examines {title.lower()} through analysis of "
        f"multiple sources and research findings."
    )

    # Key results
    if findings:
        parts.append(f"Key findings include: {findings[0].lower()}")
        if len(findings) > 1:
            parts.append(f"Additionally, {findings[1].lower()}")

    # Scope
    if topics:
        parts.append(
            f"The analysis covers {', '.join(topics[:3]).lower()}"
            f"{' and more' if len(topics) > 3 else ''}."
        )

    text = " ".join(parts)

    words = text.split()
    if len(words) > max_w:
        text = " ".join(words[:max_w]) + "..."

    return Summary(
        text=text,
        style="abstract",
        word_count=len(text.split()),
        key_findings=findings,
        topics_covered=topics,
        source_word_count=source_words,
    )


def _bullet_summary(
    report: str, source_words: int, max_words: int | None,
) -> Summary:
    """Generate a bullet-point summary."""
    topics = extract_topics(report)
    findings = extract_key_findings(report, max_findings=7)

    lines: list[str] = []
    if findings:
        for f in findings:
            lines.append(f"• {f}")
    else:
        # Fallback: use section headings as summary
        for topic in topics[:7]:
            lines.append(f"• {topic}")

    text = "\n".join(lines)

    if max_words:
        words = text.split()
        if len(words) > max_words:
            text = " ".join(words[:max_words]) + "..."

    return Summary(
        text=text,
        style="bullets",
        word_count=len(text.split()),
        key_findings=findings,
        topics_covered=topics,
        source_word_count=source_words,
    )


def _tldr_summary(
    report: str, source_words: int, max_words: int | None,
) -> Summary:
    """Generate a TL;DR one-liner."""
    max_w = max_words or 50
    topics = extract_topics(report)
    findings = extract_key_findings(report, max_findings=2)

    title_match = re.match(r"^#\s+(.+)", report)
    title = title_match.group(1).strip() if title_match else "the topic"

    if findings:
        text = f"TL;DR: {findings[0]}"
    elif topics:
        text = f"TL;DR: Report covers {', '.join(topics[:3]).lower()}."
    else:
        text = f"TL;DR: Research report on {title.lower()}."

    words = text.split()
    if len(words) > max_w:
        text = " ".join(words[:max_w]) + "..."

    return Summary(
        text=text,
        style="tldr",
        word_count=len(text.split()),
        key_findings=findings,
        topics_covered=topics,
        source_word_count=source_words,
    )
