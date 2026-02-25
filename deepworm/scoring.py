"""Report quality scoring.

Evaluates research report quality across multiple dimensions:
- Structure (headings, sections, organization)
- Content depth (word count, detail, data density)
- Source coverage (citation count, diversity)
- Readability (sentence length, paragraph structure)
- Completeness (required sections, executive summary, conclusions)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class QualityScore:
    """Detailed quality assessment of a research report."""

    structure: float = 0.0       # 0-1: heading hierarchy, section balance
    depth: float = 0.0           # 0-1: content depth, data density
    sources: float = 0.0         # 0-1: source citation coverage
    readability: float = 0.0     # 0-1: sentence/paragraph quality
    completeness: float = 0.0    # 0-1: required sections present

    @property
    def overall(self) -> float:
        """Weighted overall score (0-1)."""
        weights = {
            "structure": 0.15,
            "depth": 0.30,
            "sources": 0.20,
            "readability": 0.15,
            "completeness": 0.20,
        }
        return round(
            self.structure * weights["structure"]
            + self.depth * weights["depth"]
            + self.sources * weights["sources"]
            + self.readability * weights["readability"]
            + self.completeness * weights["completeness"],
            3,
        )

    @property
    def grade(self) -> str:
        """Letter grade based on overall score."""
        score = self.overall
        if score >= 0.9:
            return "A+"
        elif score >= 0.85:
            return "A"
        elif score >= 0.80:
            return "A-"
        elif score >= 0.75:
            return "B+"
        elif score >= 0.70:
            return "B"
        elif score >= 0.65:
            return "B-"
        elif score >= 0.60:
            return "C+"
        elif score >= 0.55:
            return "C"
        elif score >= 0.50:
            return "C-"
        elif score >= 0.40:
            return "D"
        else:
            return "F"

    def to_dict(self) -> dict:
        return {
            "structure": self.structure,
            "depth": self.depth,
            "sources": self.sources,
            "readability": self.readability,
            "completeness": self.completeness,
            "overall": self.overall,
            "grade": self.grade,
        }

    @property
    def suggestions(self) -> list[str]:
        """Generate improvement suggestions based on weak areas."""
        tips: list[str] = []
        if self.structure < 0.6:
            tips.append("Add more section headings to improve organization")
        if self.depth < 0.6:
            tips.append("Include more specific data, statistics, and examples")
        if self.sources < 0.6:
            tips.append("Cite more sources and include diverse references")
        if self.readability < 0.6:
            tips.append("Shorten long sentences and break up large paragraphs")
        if self.completeness < 0.6:
            tips.append("Add an executive summary and key takeaways section")
        return tips


def score_report(report: str) -> QualityScore:
    """Score a research report's quality across multiple dimensions.

    Args:
        report: The markdown report text.

    Returns:
        QualityScore with dimension scores and overall grade.
    """
    score = QualityScore()
    score.structure = _score_structure(report)
    score.depth = _score_depth(report)
    score.sources = _score_sources(report)
    score.readability = _score_readability(report)
    score.completeness = _score_completeness(report)
    return score


def _score_structure(report: str) -> float:
    """Score heading structure and organization."""
    lines = report.split("\n")
    headings = [l for l in lines if l.startswith("#")]

    if not headings:
        return 0.1

    score = 0.0

    # Has a title (h1)
    h1_count = sum(1 for h in headings if h.startswith("# ") and not h.startswith("## "))
    if h1_count == 1:
        score += 0.25
    elif h1_count > 0:
        score += 0.15

    # Has section headings (h2)
    h2_count = sum(1 for h in headings if h.startswith("## ") and not h.startswith("### "))
    if h2_count >= 3:
        score += 0.30
    elif h2_count >= 2:
        score += 0.20
    elif h2_count >= 1:
        score += 0.10

    # Has sub-sections (h3)
    h3_count = sum(1 for h in headings if h.startswith("### "))
    if h3_count >= 2:
        score += 0.20
    elif h3_count >= 1:
        score += 0.10

    # Balance: sections are roughly similar length
    sections = re.split(r'^#{1,3}\s', report, flags=re.MULTILINE)
    sections = [s for s in sections if len(s.strip()) > 50]
    if len(sections) >= 2:
        lengths = [len(s) for s in sections]
        avg = sum(lengths) / len(lengths)
        if avg > 0:
            variance = sum((l - avg) ** 2 for l in lengths) / len(lengths)
            cv = (variance ** 0.5) / avg  # coefficient of variation
            if cv < 0.5:
                score += 0.25
            elif cv < 1.0:
                score += 0.15
            else:
                score += 0.05

    return min(1.0, score)


def _score_depth(report: str) -> float:
    """Score content depth and data density."""
    words = report.split()
    word_count = len(words)

    score = 0.0

    # Word count (more words generally means more depth)
    if word_count >= 2000:
        score += 0.25
    elif word_count >= 1000:
        score += 0.20
    elif word_count >= 500:
        score += 0.15
    elif word_count >= 200:
        score += 0.10

    # Data density: numbers, statistics, percentages
    number_pattern = r'\b\d+[\d,.]*%?\b'
    numbers = re.findall(number_pattern, report)
    number_density = len(numbers) / max(1, word_count) * 100
    if number_density > 2.0:
        score += 0.25
    elif number_density > 1.0:
        score += 0.15
    elif number_density > 0.5:
        score += 0.10

    # Bullet points / lists (shows detail)
    bullet_lines = len(re.findall(r'^[\s]*[-*•]\s', report, re.MULTILINE))
    if bullet_lines >= 10:
        score += 0.20
    elif bullet_lines >= 5:
        score += 0.15
    elif bullet_lines >= 2:
        score += 0.10

    # Technical specificity (quoted text, bold emphasis)
    bold_items = len(re.findall(r'\*\*[^*]+\*\*', report))
    if bold_items >= 5:
        score += 0.15
    elif bold_items >= 2:
        score += 0.10

    # Comparative language (shows analysis)
    comparison_words = ['however', 'although', 'whereas', 'compared', 'unlike',
                        'similar', 'in contrast', 'on the other hand', 'alternatively']
    comparison_count = sum(1 for w in comparison_words if w.lower() in report.lower())
    if comparison_count >= 3:
        score += 0.15
    elif comparison_count >= 1:
        score += 0.08

    return min(1.0, score)


def _score_sources(report: str) -> float:
    """Score source citation coverage."""
    score = 0.0

    # Count URLs
    urls = re.findall(r'https?://[^\s\)>\]]+', report)
    unique_urls = set(urls)

    if len(unique_urls) >= 10:
        score += 0.40
    elif len(unique_urls) >= 5:
        score += 0.30
    elif len(unique_urls) >= 3:
        score += 0.20
    elif len(unique_urls) >= 1:
        score += 0.10

    # Domain diversity
    domains = set()
    for url in unique_urls:
        match = re.search(r'https?://([^/]+)', url)
        if match:
            domains.add(match.group(1).split(".")[-2] if "." in match.group(1) else match.group(1))
    if len(domains) >= 5:
        score += 0.30
    elif len(domains) >= 3:
        score += 0.20
    elif len(domains) >= 1:
        score += 0.10

    # Has a sources/references section
    if re.search(r'^#{1,3}\s*(Sources|References|Bibliography|Citations)', report, re.MULTILINE | re.IGNORECASE):
        score += 0.30

    return min(1.0, score)


def _score_readability(report: str) -> float:
    """Score readability and formatting."""
    score = 0.0

    # Sentence length analysis
    sentences = re.split(r'[.!?]+\s+', report)
    sentences = [s for s in sentences if len(s.split()) >= 3]

    if sentences:
        avg_words = sum(len(s.split()) for s in sentences) / len(sentences)
        if 10 <= avg_words <= 25:
            score += 0.30  # Good sentence length
        elif 8 <= avg_words <= 35:
            score += 0.20
        else:
            score += 0.10

    # Paragraph structure
    paragraphs = [p for p in report.split("\n\n") if len(p.strip()) > 0 and not p.strip().startswith("#")]
    if len(paragraphs) >= 5:
        avg_para_len = sum(len(p.split()) for p in paragraphs) / len(paragraphs)
        if 30 <= avg_para_len <= 150:
            score += 0.25
        elif 15 <= avg_para_len <= 250:
            score += 0.15
        else:
            score += 0.05
    elif len(paragraphs) >= 2:
        score += 0.10

    # Uses formatting (bold, italic, code)
    has_bold = bool(re.search(r'\*\*[^*]+\*\*', report))
    has_lists = bool(re.search(r'^[\s]*[-*•]\s', report, re.MULTILINE))
    has_code = bool(re.search(r'`[^`]+`', report))
    formatting_count = sum([has_bold, has_lists, has_code])
    if formatting_count >= 3:
        score += 0.25
    elif formatting_count >= 2:
        score += 0.15
    elif formatting_count >= 1:
        score += 0.10

    # No excessive whitespace
    double_blank = len(re.findall(r'\n{4,}', report))
    if double_blank == 0:
        score += 0.20
    elif double_blank <= 2:
        score += 0.10

    return min(1.0, score)


def _score_completeness(report: str) -> float:
    """Score presence of required report sections."""
    score = 0.0
    report_lower = report.lower()

    # Executive summary / overview
    summary_patterns = ['executive summary', 'summary', 'overview', 'introduction', 'abstract']
    if any(p in report_lower for p in summary_patterns):
        score += 0.25

    # Main content sections (at least 2)
    h2_sections = re.findall(r'^##\s+(.+)$', report, re.MULTILINE)
    if len(h2_sections) >= 3:
        score += 0.25
    elif len(h2_sections) >= 2:
        score += 0.15

    # Key takeaways / conclusions
    conclusion_patterns = ['key takeaway', 'takeaway', 'conclusion', 'key finding', 'key insight']
    if any(p in report_lower for p in conclusion_patterns):
        score += 0.25

    # Sources section
    source_patterns = ['sources', 'references', 'bibliography', 'citations']
    if any(p in report_lower for p in source_patterns):
        score += 0.15

    # Follow-up / next steps
    followup_patterns = ['follow-up', 'follow up', 'next steps', 'future', 'further research']
    if any(p in report_lower for p in followup_patterns):
        score += 0.10

    return min(1.0, score)
