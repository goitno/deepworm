"""Source credibility scoring.

Scores web sources based on domain authority signals, content quality,
and structural indicators to help assess research reliability.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urlparse


# Domain authority tiers
_TIER1_DOMAINS: set[str] = {
    # Academic / Research
    "nature.com", "science.org", "sciencedirect.com", "springer.com",
    "ieee.org", "acm.org", "arxiv.org", "pubmed.ncbi.nlm.nih.gov",
    "scholar.google.com", "jstor.org", "researchgate.net",
    "ncbi.nlm.nih.gov", "nih.gov", "who.int",
    # Government
    "gov", "edu", "ac.uk", "gov.uk", "europa.eu",
    # Major news
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk",
    "nytimes.com", "washingtonpost.com", "theguardian.com",
    # Tech authority
    "github.com", "stackoverflow.com", "docs.python.org",
    "developer.mozilla.org", "w3.org",
}

_TIER2_DOMAINS: set[str] = {
    # Quality publications
    "medium.com", "dev.to", "hackernews.com", "arstechnica.com",
    "wired.com", "techcrunch.com", "theverge.com", "engadget.com",
    "cnn.com", "forbes.com", "bloomberg.com", "economist.com",
    "ft.com", "wsj.com", "nationalgeographic.com",
    # Reference
    "wikipedia.org", "wikimedia.org", "britannica.com",
    # Tech docs
    "readthedocs.io", "docs.rs", "cppreference.com",
    "learn.microsoft.com", "cloud.google.com", "aws.amazon.com",
}

_LOW_CREDIBILITY_DOMAINS: set[str] = {
    "reddit.com", "quora.com", "yahoo.com", "answers.yahoo.com",
    "buzzfeed.com", "dailymail.co.uk", "infowars.com",
    "breitbart.com", "naturalcures.com",
}

# TLD authority signals
_AUTHORITY_TLDS = {".edu", ".gov", ".ac.uk", ".gov.uk", ".mil"}


@dataclass
class CredibilityScore:
    """Credibility assessment for a source."""

    url: str
    domain: str
    overall_score: float  # 0.0 - 1.0
    domain_score: float  # Based on domain authority
    content_score: float  # Based on content quality signals
    freshness_score: float  # Based on publication date
    signals: list[str] = field(default_factory=list)  # Positive signals
    warnings: list[str] = field(default_factory=list)  # Negative signals
    tier: str = "unknown"  # "tier1", "tier2", "standard", "low"

    @property
    def label(self) -> str:
        """Human-readable credibility label."""
        if self.overall_score >= 0.8:
            return "High"
        elif self.overall_score >= 0.5:
            return "Medium"
        elif self.overall_score >= 0.3:
            return "Low"
        return "Very Low"

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "domain": self.domain,
            "overall_score": round(self.overall_score, 2),
            "domain_score": round(self.domain_score, 2),
            "content_score": round(self.content_score, 2),
            "freshness_score": round(self.freshness_score, 2),
            "label": self.label,
            "tier": self.tier,
            "signals": self.signals,
            "warnings": self.warnings,
        }


@dataclass
class CredibilityReport:
    """Aggregated credibility report for multiple sources."""

    scores: list[CredibilityScore] = field(default_factory=list)

    @property
    def average_score(self) -> float:
        if not self.scores:
            return 0.0
        return sum(s.overall_score for s in self.scores) / len(self.scores)

    @property
    def high_credibility_count(self) -> int:
        return sum(1 for s in self.scores if s.overall_score >= 0.8)

    @property
    def low_credibility_count(self) -> int:
        return sum(1 for s in self.scores if s.overall_score < 0.3)

    def to_markdown(self) -> str:
        """Render credibility report as markdown table."""
        lines = [
            "## Source Credibility Report",
            "",
            f"**Average Score:** {self.average_score:.0%} | "
            f"**High:** {self.high_credibility_count} | "
            f"**Low:** {self.low_credibility_count} | "
            f"**Total:** {len(self.scores)}",
            "",
            "| Source | Score | Label | Tier |",
            "|--------|-------|-------|------|",
        ]
        for s in sorted(self.scores, key=lambda x: x.overall_score, reverse=True):
            domain = s.domain[:30]
            lines.append(
                f"| {domain} | {s.overall_score:.0%} | {s.label} | {s.tier} |"
            )
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "average_score": round(self.average_score, 2),
            "high_credibility_count": self.high_credibility_count,
            "low_credibility_count": self.low_credibility_count,
            "total": len(self.scores),
            "scores": [s.to_dict() for s in self.scores],
        }


def score_source(
    url: str,
    content: str = "",
    published_date: Optional[str] = None,
) -> CredibilityScore:
    """Score the credibility of a single source.

    Args:
        url: Source URL.
        content: Optional page content for quality analysis.
        published_date: Optional publication date string (ISO format).

    Returns:
        CredibilityScore with detailed breakdown.
    """
    parsed = urlparse(url)
    domain = parsed.netloc.lower().lstrip("www.")

    signals: list[str] = []
    warnings: list[str] = []

    # Domain scoring
    domain_score, tier = _score_domain(domain, signals, warnings)

    # Content scoring
    content_score = _score_content(content, signals, warnings) if content else 0.5

    # Freshness scoring
    freshness_score = _score_freshness(published_date, signals, warnings)

    # URL structure signals
    _check_url_signals(url, parsed, signals, warnings)

    # Weighted overall score
    overall = (
        domain_score * 0.45
        + content_score * 0.35
        + freshness_score * 0.20
    )
    overall = max(0.0, min(1.0, overall))

    return CredibilityScore(
        url=url,
        domain=domain,
        overall_score=overall,
        domain_score=domain_score,
        content_score=content_score,
        freshness_score=freshness_score,
        signals=signals,
        warnings=warnings,
        tier=tier,
    )


def score_sources(
    urls: list[str],
    contents: Optional[dict[str, str]] = None,
) -> CredibilityReport:
    """Score credibility for multiple sources.

    Args:
        urls: List of source URLs.
        contents: Optional mapping of URL → page content.

    Returns:
        CredibilityReport with all scores.
    """
    contents = contents or {}
    scores = [
        score_source(url, content=contents.get(url, ""))
        for url in urls
    ]
    return CredibilityReport(scores=scores)


def _score_domain(
    domain: str,
    signals: list[str],
    warnings: list[str],
) -> tuple[float, str]:
    """Score domain authority. Returns (score, tier)."""
    # Check exact domain match
    if domain in _TIER1_DOMAINS:
        signals.append(f"Tier 1 domain: {domain}")
        return 0.95, "tier1"

    if domain in _TIER2_DOMAINS:
        signals.append(f"Tier 2 domain: {domain}")
        return 0.75, "tier2"

    if domain in _LOW_CREDIBILITY_DOMAINS:
        warnings.append(f"Low credibility domain: {domain}")
        return 0.2, "low"

    # Check TLD-based authority
    for tld in _AUTHORITY_TLDS:
        if domain.endswith(tld):
            signals.append(f"Authority TLD: {tld}")
            return 0.9, "tier1"

    # Check subdomain matches (e.g., docs.python.org matches python.org)
    parts = domain.split(".")
    if len(parts) >= 2:
        base = ".".join(parts[-2:])
        if base in _TIER1_DOMAINS:
            signals.append(f"Subdomain of tier 1: {base}")
            return 0.85, "tier1"
        if base in _TIER2_DOMAINS:
            signals.append(f"Subdomain of tier 2: {base}")
            return 0.7, "tier2"

    # HTTPS bonus
    return 0.5, "standard"


def _score_content(
    content: str,
    signals: list[str],
    warnings: list[str],
) -> float:
    """Score content quality. Returns 0.0-1.0."""
    if not content:
        return 0.5

    score = 0.5
    words = content.split()
    word_count = len(words)

    # Length signals
    if word_count >= 1000:
        score += 0.15
        signals.append("Substantial content (1000+ words)")
    elif word_count >= 500:
        score += 0.1
        signals.append("Moderate content length")
    elif word_count < 100:
        score -= 0.1
        warnings.append("Very short content")

    # Structural signals
    if re.search(r"references|bibliography|sources|citations", content, re.I):
        score += 0.1
        signals.append("Contains references section")

    if re.search(r"\b(study|research|data|analysis|findings)\b", content, re.I):
        score += 0.05
        signals.append("Contains research language")

    # Numbers and data
    numbers = re.findall(r"\d+\.?\d*%|\$\d+|\d{4}", content)
    if len(numbers) >= 5:
        score += 0.05
        signals.append("Contains quantitative data")

    # Paragraph structure
    paragraphs = [p for p in content.split("\n\n") if len(p.strip()) > 50]
    if len(paragraphs) >= 5:
        score += 0.05
        signals.append("Well-structured paragraphs")

    # Warning signals
    if re.search(r"click here|buy now|limited time|act now", content, re.I):
        score -= 0.2
        warnings.append("Contains promotional language")

    if re.search(r"!!!|\$\$\$|FREE|GUARANTEED", content):
        score -= 0.15
        warnings.append("Contains spam-like patterns")

    return max(0.0, min(1.0, score))


def _score_freshness(
    date_str: Optional[str],
    signals: list[str],
    warnings: list[str],
) -> float:
    """Score publication freshness. Returns 0.0-1.0."""
    if not date_str:
        return 0.5  # Unknown date, neutral score

    try:
        # Try to parse year from date string
        year_match = re.search(r"(20\d{2})", date_str)
        if not year_match:
            return 0.5

        import datetime

        year = int(year_match.group(1))
        current_year = datetime.datetime.now().year
        age = current_year - year

        if age <= 1:
            signals.append("Recently published")
            return 0.95
        elif age <= 3:
            signals.append("Published within 3 years")
            return 0.8
        elif age <= 5:
            return 0.6
        elif age <= 10:
            warnings.append(f"Published {age} years ago")
            return 0.4
        else:
            warnings.append(f"Published {age} years ago (potentially outdated)")
            return 0.2
    except (ValueError, TypeError):
        return 0.5


def _check_url_signals(
    url: str,
    parsed: Any,
    signals: list[str],
    warnings: list[str],
) -> None:
    """Check URL structure for quality signals."""
    # HTTPS
    if parsed.scheme == "https":
        signals.append("Uses HTTPS")
    elif parsed.scheme == "http":
        warnings.append("Uses HTTP (not HTTPS)")

    # Path depth (very deep paths may be low-quality)
    path_depth = len([p for p in parsed.path.split("/") if p])
    if path_depth > 6:
        warnings.append("Very deep URL path")

    # Query parameters (lots of params may indicate tracking)
    if parsed.query and parsed.query.count("&") > 5:
        warnings.append("Many query parameters (possible tracking)")

    # Known quality paths
    path_lower = parsed.path.lower()
    if any(p in path_lower for p in ["/research/", "/paper/", "/article/", "/study/"]):
        signals.append("Research-oriented URL path")
    if any(p in path_lower for p in ["/blog/", "/post/"]):
        # Blogs are lower authority than formal pages
        pass  # Neutral, don't penalize
    if any(p in path_lower for p in ["/ad/", "/sponsored/", "/promo/"]):
        warnings.append("URL suggests sponsored content")
