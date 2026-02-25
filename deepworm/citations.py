"""Citation formatting for research reports.

Generates formatted citations in APA, MLA, Chicago, and BibTeX styles.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse


@dataclass
class Citation:
    """A single citation/reference."""

    url: str
    title: str
    author: str = ""
    publisher: str = ""
    date_accessed: str = ""
    date_published: str = ""

    def __post_init__(self) -> None:
        if not self.date_accessed:
            self.date_accessed = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if not self.publisher:
            self.publisher = self._extract_publisher()

    def _extract_publisher(self) -> str:
        """Extract publisher name from URL domain."""
        try:
            domain = urlparse(self.url).netloc
            # Remove www. prefix
            domain = re.sub(r'^www\.', '', domain)
            # Map known domains
            known = {
                "arxiv.org": "arXiv",
                "github.com": "GitHub",
                "stackoverflow.com": "Stack Overflow",
                "en.wikipedia.org": "Wikipedia",
                "medium.com": "Medium",
                "nytimes.com": "The New York Times",
                "bbc.com": "BBC",
                "reuters.com": "Reuters",
                "nature.com": "Nature",
                "science.org": "Science",
            }
            if domain in known:
                return known[domain]
            # Capitalize domain parts
            parts = domain.replace('.com', '').replace('.org', '').replace('.io', '').split('.')
            return ' '.join(p.capitalize() for p in parts)
        except Exception:
            return ""


def format_apa(citation: Citation) -> str:
    """Format citation in APA 7th edition style.

    Example: Author. (Year). *Title*. Publisher. URL
    """
    parts = []

    # Author
    author = citation.author or citation.publisher or "Unknown Author"
    parts.append(f"{author}.")

    # Date
    if citation.date_published:
        parts.append(f"({citation.date_published}).")
    else:
        parts.append("(n.d.).")

    # Title (italicized in real APA, we use markdown)
    parts.append(f"*{citation.title}*.")

    # Publisher (if different from author)
    if citation.publisher and citation.publisher != author:
        parts.append(f"{citation.publisher}.")

    # URL
    parts.append(citation.url)

    return " ".join(parts)


def format_mla(citation: Citation) -> str:
    """Format citation in MLA 9th edition style.

    Example: Author. "Title." *Publisher*, Date. URL.
    """
    parts = []

    author = citation.author or "Unknown Author"
    parts.append(f'{author}.')

    parts.append(f'"{citation.title}."')

    if citation.publisher:
        parts.append(f"*{citation.publisher}*,")

    if citation.date_published:
        parts.append(f"{citation.date_published}.")
    else:
        parts.append(f"Accessed {citation.date_accessed}.")

    parts.append(citation.url + ".")

    return " ".join(parts)


def format_chicago(citation: Citation) -> str:
    """Format citation in Chicago Manual of Style (Notes-Bibliography).

    Example: Author. "Title." Publisher. Accessed Date. URL.
    """
    parts = []

    author = citation.author or citation.publisher or "Unknown Author"
    parts.append(f"{author}.")

    parts.append(f'"{citation.title}."')

    if citation.publisher and citation.publisher != author:
        parts.append(f"{citation.publisher}.")

    if citation.date_published:
        parts.append(f"{citation.date_published}.")

    parts.append(f"Accessed {citation.date_accessed}.")
    parts.append(citation.url + ".")

    return " ".join(parts)


def format_bibtex(citation: Citation, key: str = "") -> str:
    """Format citation as BibTeX entry.

    Example:
        @online{key,
          title  = {Title},
          author = {Author},
          url    = {URL},
          ...
        }
    """
    if not key:
        # Generate key from title
        words = re.sub(r'[^\w\s]', '', citation.title.lower()).split()[:3]
        year = citation.date_published[:4] if citation.date_published else "nd"
        key = "_".join(words) + f"_{year}"

    lines = [f"@online{{{key},"]
    lines.append(f"  title     = {{{citation.title}}},")

    if citation.author:
        lines.append(f"  author    = {{{citation.author}}},")

    lines.append(f"  url       = {{{citation.url}}},")

    if citation.publisher:
        lines.append(f"  publisher = {{{citation.publisher}}},")

    if citation.date_published:
        lines.append(f"  year      = {{{citation.date_published[:4]}}},")

    lines.append(f"  urldate   = {{{citation.date_accessed}}},")
    lines.append("}")

    return "\n".join(lines)


# ── Batch formatting ────────────────────────────────────────────


FORMATTERS = {
    "apa": format_apa,
    "mla": format_mla,
    "chicago": format_chicago,
    "bibtex": format_bibtex,
}


def format_citations(
    citations: list[Citation],
    style: str = "apa",
) -> str:
    """Format multiple citations in the given style.

    Args:
        citations: List of Citation objects.
        style: One of 'apa', 'mla', 'chicago', 'bibtex'.

    Returns:
        Formatted citations as a single string.
    """
    formatter = FORMATTERS.get(style.lower())
    if formatter is None:
        raise ValueError(f"Unknown citation style: {style}. Supported: {', '.join(FORMATTERS)}")

    parts = []
    for i, cite in enumerate(citations, 1):
        if style.lower() == "bibtex":
            parts.append(formatter(cite))
        else:
            parts.append(f"[{i}] {formatter(cite)}")

    separator = "\n\n" if style.lower() == "bibtex" else "\n"
    return separator.join(parts)


def citations_from_sources(
    sources: list[dict[str, Any]],
) -> list[Citation]:
    """Create Citation objects from research source dicts.

    Expected dict keys: 'url', 'title' (required), 'author', 'publisher', etc.
    """
    citations = []
    for src in sources:
        citations.append(Citation(
            url=src.get("url", ""),
            title=src.get("title", "Untitled"),
            author=src.get("author", ""),
            publisher=src.get("publisher", ""),
            date_published=src.get("date_published", ""),
        ))
    return citations
