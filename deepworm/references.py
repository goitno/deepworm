"""Reference and bibliography management for research reports.

Parse, store, format, and deduplicate academic and web references.
Supports multiple output styles and cross-referencing within reports.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Reference:
    """A single bibliographic reference."""

    title: str
    authors: List[str] = field(default_factory=list)
    year: Optional[str] = None
    url: Optional[str] = None
    journal: Optional[str] = None
    volume: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    publisher: Optional[str] = None
    ref_type: str = "web"  # web, article, book, report, thesis
    access_date: Optional[str] = None
    _id: Optional[int] = None

    @property
    def author_string(self) -> str:
        """Format authors as a string."""
        if not self.authors:
            return "Unknown"
        if len(self.authors) == 1:
            return self.authors[0]
        if len(self.authors) == 2:
            return f"{self.authors[0]} & {self.authors[1]}"
        return f"{self.authors[0]} et al."

    @property
    def citation_key(self) -> str:
        """Generate a short citation key (e.g., 'Smith2023')."""
        if self.authors:
            last = self.authors[0].split()[-1] if self.authors[0] else "Unknown"
        else:
            last = "Unknown"
        year = self.year or "n.d."
        return f"{last}{year}"

    def to_apa(self) -> str:
        """Format as APA style."""
        parts: List[str] = []

        # Authors
        if self.authors:
            formatted = []
            for author in self.authors:
                names = author.strip().split()
                if len(names) >= 2:
                    last = names[-1]
                    initials = ". ".join(n[0].upper() for n in names[:-1]) + "."
                    formatted.append(f"{last}, {initials}")
                else:
                    formatted.append(author)
            if len(formatted) <= 2:
                parts.append(" & ".join(formatted))
            else:
                parts.append(", ".join(formatted[:-1]) + ", & " + formatted[-1])
        else:
            parts.append("Unknown")

        # Year
        parts.append(f"({self.year or 'n.d.'})")

        # Title
        parts.append(f"{self.title}.")

        # Journal/publisher
        if self.journal:
            journal_str = f"*{self.journal}*"
            if self.volume:
                journal_str += f", *{self.volume}*"
            if self.pages:
                journal_str += f", {self.pages}"
            parts.append(journal_str + ".")
        elif self.publisher:
            parts.append(f"{self.publisher}.")

        # DOI or URL
        if self.doi:
            parts.append(f"https://doi.org/{self.doi}")
        elif self.url:
            parts.append(self.url)

        return " ".join(parts)

    def to_mla(self) -> str:
        """Format as MLA style."""
        parts: List[str] = []

        # Authors
        if self.authors:
            if len(self.authors) == 1:
                names = self.authors[0].split()
                if len(names) >= 2:
                    parts.append(f"{names[-1]}, {' '.join(names[:-1])}.")
                else:
                    parts.append(f"{self.authors[0]}.")
            elif len(self.authors) == 2:
                first = self.authors[0].split()
                parts.append(
                    f"{first[-1]}, {' '.join(first[:-1])}, "
                    f"and {self.authors[1]}."
                )
            else:
                first = self.authors[0].split()
                parts.append(f"{first[-1]}, {' '.join(first[:-1])}, et al.")
        else:
            parts.append("Unknown.")

        # Title
        if self.ref_type == "article":
            parts.append(f'"{self.title}."')
        else:
            parts.append(f"*{self.title}*.")

        # Journal
        if self.journal:
            journal_str = f"*{self.journal}*"
            if self.volume:
                journal_str += f", vol. {self.volume}"
            if self.pages:
                journal_str += f", pp. {self.pages}"
            if self.year:
                journal_str += f", {self.year}"
            parts.append(journal_str + ".")
        elif self.year:
            parts.append(f"{self.year}.")

        # URL
        if self.url:
            parts.append(self.url + ".")

        return " ".join(parts)

    def to_bibtex(self) -> str:
        """Format as BibTeX entry."""
        entry_type = {
            "article": "article",
            "book": "book",
            "report": "techreport",
            "thesis": "phdthesis",
            "web": "misc",
        }.get(self.ref_type, "misc")

        key = self.citation_key.lower()
        lines = [f"@{entry_type}{{{key},"]

        if self.authors:
            lines.append(f"  author = {{{' and '.join(self.authors)}}},")
        lines.append(f"  title = {{{self.title}}},")
        if self.year:
            lines.append(f"  year = {{{self.year}}},")
        if self.journal:
            lines.append(f"  journal = {{{self.journal}}},")
        if self.volume:
            lines.append(f"  volume = {{{self.volume}}},")
        if self.pages:
            lines.append(f"  pages = {{{self.pages}}},")
        if self.doi:
            lines.append(f"  doi = {{{self.doi}}},")
        if self.url:
            lines.append(f"  url = {{{self.url}}},")
        if self.publisher:
            lines.append(f"  publisher = {{{self.publisher}}},")

        lines.append("}")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result: Dict[str, Any] = {
            "title": self.title,
            "authors": self.authors,
            "type": self.ref_type,
        }
        if self.year:
            result["year"] = self.year
        if self.url:
            result["url"] = self.url
        if self.journal:
            result["journal"] = self.journal
        if self.doi:
            result["doi"] = self.doi
        return result


@dataclass
class Bibliography:
    """A collection of references."""

    title: str = "References"
    references: List[Reference] = field(default_factory=list)
    _next_id: int = 1

    def add(self, ref: Reference) -> Reference:
        """Add a reference to the bibliography."""
        ref._id = self._next_id
        self._next_id += 1
        self.references.append(ref)
        return ref

    def get(self, ref_id: int) -> Optional[Reference]:
        """Get a reference by ID."""
        for ref in self.references:
            if ref._id == ref_id:
                return ref
        return None

    def find_by_title(self, query: str) -> List[Reference]:
        """Find references by title substring."""
        query_lower = query.lower()
        return [
            r for r in self.references
            if query_lower in r.title.lower()
        ]

    def find_by_author(self, author: str) -> List[Reference]:
        """Find references by author name."""
        author_lower = author.lower()
        return [
            r for r in self.references
            if any(author_lower in a.lower() for a in r.authors)
        ]

    def find_by_year(self, year: str) -> List[Reference]:
        """Find references by year."""
        return [r for r in self.references if r.year == year]

    def sort(self, by: str = "author") -> None:
        """Sort references. Options: author, year, title."""
        if by == "author":
            self.references.sort(key=lambda r: r.author_string.lower())
        elif by == "year":
            self.references.sort(key=lambda r: r.year or "9999")
        elif by == "title":
            self.references.sort(key=lambda r: r.title.lower())

    def deduplicate(self) -> int:
        """Remove duplicate references. Returns count removed."""
        seen: set = set()
        unique: List[Reference] = []
        for ref in self.references:
            key = (ref.title.lower().strip(), ref.year or "")
            if key not in seen:
                seen.add(key)
                unique.append(ref)
        removed = len(self.references) - len(unique)
        self.references = unique
        return removed

    @property
    def by_type(self) -> Dict[str, List[Reference]]:
        """Group references by type."""
        groups: Dict[str, List[Reference]] = {}
        for ref in self.references:
            groups.setdefault(ref.ref_type, []).append(ref)
        return groups

    @property
    def years(self) -> List[str]:
        """Get unique years, sorted."""
        return sorted(set(r.year for r in self.references if r.year))

    def to_apa(self) -> str:
        """Format entire bibliography in APA style."""
        self.sort(by="author")
        lines = [f"## {self.title}\n"]
        for ref in self.references:
            lines.append(f"- {ref.to_apa()}")
        return "\n".join(lines) + "\n"

    def to_mla(self) -> str:
        """Format entire bibliography in MLA style."""
        self.sort(by="author")
        lines = [f"## {self.title}\n"]
        for ref in self.references:
            lines.append(f"- {ref.to_mla()}")
        return "\n".join(lines) + "\n"

    def to_bibtex(self) -> str:
        """Format entire bibliography as BibTeX."""
        entries = [ref.to_bibtex() for ref in self.references]
        return "\n\n".join(entries) + "\n"

    def to_numbered(self) -> str:
        """Format as a numbered reference list."""
        self.sort(by="author")
        lines = [f"## {self.title}\n"]
        for i, ref in enumerate(self.references, 1):
            lines.append(f"[{i}] {ref.to_apa()}")
        return "\n".join(lines) + "\n"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "count": len(self.references),
            "types": {k: len(v) for k, v in self.by_type.items()},
            "years": self.years,
            "references": [r.to_dict() for r in self.references],
        }


# --- Extraction ---

# Pattern: (Author, Year) or (Author et al., Year)
_INLINE_CITATION = re.compile(
    r"\(([A-Z][a-z]+(?:\s+(?:et\s+al\.|&\s+[A-Z][a-z]+))?),?\s+(\d{4})\)"
)

# Pattern: markdown links [title](url)
_MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")

# Pattern: bare URLs
_BARE_URL = re.compile(r"(?<!\()(https?://[^\s\)]+)")

# Pattern: "Author (Year)" in text
_AUTHOR_YEAR = re.compile(
    r"([A-Z][a-z]+(?:\s+(?:et\s+al\.|and\s+[A-Z][a-z]+))?)\s+\((\d{4})\)"
)

# Pattern: DOI
_DOI_PATTERN = re.compile(r"(?:doi:\s*|https?://doi\.org/)(10\.\d{4,}/[^\s]+)", re.IGNORECASE)


def extract_references(text: str) -> Bibliography:
    """Extract references from text.

    Detects inline citations, markdown links, bare URLs, and DOIs.

    Args:
        text: Input text to scan.

    Returns:
        Bibliography with extracted references.
    """
    bib = Bibliography()
    seen_urls: set = set()
    seen_citations: set = set()

    # Extract markdown links
    for match in _MARKDOWN_LINK.finditer(text):
        title = match.group(1).strip()
        url = match.group(2).strip()
        if url not in seen_urls:
            seen_urls.add(url)
            ref = Reference(title=title, url=url, ref_type="web")
            bib.add(ref)

    # Extract DOIs
    for match in _DOI_PATTERN.finditer(text):
        doi = match.group(1).strip()
        doi_url = f"https://doi.org/{doi}"
        if doi_url not in seen_urls:
            seen_urls.add(doi_url)
            ref = Reference(
                title=f"DOI: {doi}",
                doi=doi,
                ref_type="article",
            )
            bib.add(ref)

    # Extract inline citations (Author, Year)
    for match in _INLINE_CITATION.finditer(text):
        author = match.group(1).strip()
        year = match.group(2)
        key = (author.lower(), year)
        if key not in seen_citations:
            seen_citations.add(key)
            ref = Reference(
                title=f"{author} ({year})",
                authors=[author],
                year=year,
                ref_type="article",
            )
            bib.add(ref)

    # Extract Author (Year) patterns
    for match in _AUTHOR_YEAR.finditer(text):
        author = match.group(1).strip()
        year = match.group(2)
        key = (author.lower(), year)
        if key not in seen_citations:
            seen_citations.add(key)
            ref = Reference(
                title=f"{author} ({year})",
                authors=[author],
                year=year,
                ref_type="article",
            )
            bib.add(ref)

    # Extract bare URLs not already captured
    for match in _BARE_URL.finditer(text):
        url = match.group(0).strip().rstrip(".,;:")
        if url not in seen_urls:
            seen_urls.add(url)
            domain = _extract_domain(url)
            ref = Reference(title=domain, url=url, ref_type="web")
            bib.add(ref)

    return bib


def _extract_domain(url: str) -> str:
    """Extract domain name from URL."""
    match = re.match(r"https?://(?:www\.)?([^/]+)", url)
    if match:
        return match.group(1)
    return url


def create_reference(
    title: str,
    authors: Optional[List[str]] = None,
    year: Optional[str] = None,
    url: Optional[str] = None,
    journal: Optional[str] = None,
    doi: Optional[str] = None,
    ref_type: str = "web",
    **kwargs: Any,
) -> Reference:
    """Create a reference with the given fields.

    Convenience function for building Reference objects.
    """
    return Reference(
        title=title,
        authors=authors or [],
        year=year,
        url=url,
        journal=journal,
        doi=doi,
        ref_type=ref_type,
        volume=kwargs.get("volume"),
        pages=kwargs.get("pages"),
        publisher=kwargs.get("publisher"),
        access_date=kwargs.get("access_date"),
    )


def inject_bibliography(
    text: str,
    bib: Bibliography,
    style: str = "apa",
) -> str:
    """Append a formatted bibliography to text.

    Args:
        text: The report text.
        bib: Bibliography to append.
        style: Format style — 'apa', 'mla', 'bibtex', 'numbered'.

    Returns:
        Text with bibliography appended.
    """
    formatters = {
        "apa": bib.to_apa,
        "mla": bib.to_mla,
        "bibtex": bib.to_bibtex,
        "numbered": bib.to_numbered,
    }
    formatter = formatters.get(style, bib.to_apa)
    formatted = formatter()
    return f"{text.rstrip()}\n\n{formatted}"


def merge_bibliographies(*bibs: Bibliography) -> Bibliography:
    """Merge multiple bibliographies, deduplicating."""
    merged = Bibliography()
    for bib in bibs:
        for ref in bib.references:
            merged.add(ref)
    merged.deduplicate()
    return merged
