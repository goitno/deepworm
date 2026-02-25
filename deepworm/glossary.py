"""Glossary extraction and management for research reports.

Automatically extracts technical terms, generates definitions,
and produces a formatted glossary section.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class GlossaryEntry:
    """A single glossary term with definition."""

    term: str
    definition: str
    abbreviation: str = ""
    first_occurrence: int = 0  # Line number of first use
    frequency: int = 1

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "term": self.term,
            "definition": self.definition,
            "frequency": self.frequency,
        }
        if self.abbreviation:
            d["abbreviation"] = self.abbreviation
        return d


@dataclass
class Glossary:
    """A collection of glossary entries."""

    entries: list[GlossaryEntry] = field(default_factory=list)
    title: str = "Glossary"

    @property
    def terms(self) -> list[str]:
        return [e.term for e in self.entries]

    def get(self, term: str) -> Optional[GlossaryEntry]:
        """Look up a term (case-insensitive)."""
        lower = term.lower()
        for entry in self.entries:
            if entry.term.lower() == lower:
                return entry
        return None

    def add(
        self,
        term: str,
        definition: str,
        abbreviation: str = "",
    ) -> GlossaryEntry:
        """Add or update a glossary entry."""
        existing = self.get(term)
        if existing:
            existing.definition = definition
            if abbreviation:
                existing.abbreviation = abbreviation
            return existing
        entry = GlossaryEntry(
            term=term,
            definition=definition,
            abbreviation=abbreviation,
        )
        self.entries.append(entry)
        return entry

    def remove(self, term: str) -> bool:
        """Remove a term. Returns True if found."""
        lower = term.lower()
        for i, entry in enumerate(self.entries):
            if entry.term.lower() == lower:
                self.entries.pop(i)
                return True
        return False

    def sort(self, by: str = "alpha") -> None:
        """Sort entries: 'alpha' (alphabetical), 'frequency', or 'occurrence'."""
        if by == "frequency":
            self.entries.sort(key=lambda e: e.frequency, reverse=True)
        elif by == "occurrence":
            self.entries.sort(key=lambda e: e.first_occurrence)
        else:  # alpha
            self.entries.sort(key=lambda e: e.term.lower())

    def to_markdown(self) -> str:
        """Render glossary as markdown."""
        if not self.entries:
            return ""
        lines = [f"## {self.title}", ""]
        for entry in self.entries:
            term = entry.term
            if entry.abbreviation:
                term = f"{entry.term} ({entry.abbreviation})"
            lines.append(f"**{term}**: {entry.definition}")
            lines.append("")
        return "\n".join(lines)

    def to_definition_list(self) -> str:
        """Render as HTML definition list."""
        if not self.entries:
            return ""
        lines = ["<dl>"]
        for entry in self.entries:
            term = entry.term
            if entry.abbreviation:
                term = f"{entry.term} (<abbr>{entry.abbreviation}</abbr>)"
            lines.append(f"  <dt>{term}</dt>")
            lines.append(f"  <dd>{entry.definition}</dd>")
        lines.append("</dl>")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "entries": [e.to_dict() for e in self.entries],
        }

    def merge(self, other: "Glossary") -> None:
        """Merge another glossary into this one."""
        for entry in other.entries:
            existing = self.get(entry.term)
            if existing:
                existing.frequency += entry.frequency
                if not existing.definition and entry.definition:
                    existing.definition = entry.definition
            else:
                self.entries.append(
                    GlossaryEntry(
                        term=entry.term,
                        definition=entry.definition,
                        abbreviation=entry.abbreviation,
                        first_occurrence=entry.first_occurrence,
                        frequency=entry.frequency,
                    )
                )


def extract_glossary(text: str, min_frequency: int = 1) -> Glossary:
    """Extract a glossary from text.

    Identifies technical terms via:
    - Explicit definitions (e.g. "X is defined as Y", "X refers to Y")
    - Abbreviation introductions (e.g. "Natural Language Processing (NLP)")
    - Capitalized compound terms used multiple times

    Args:
        text: Source text (markdown supported).
        min_frequency: Minimum occurrences for inclusion.

    Returns:
        Glossary with extracted entries.
    """
    glossary = Glossary()
    lines = text.split("\n")

    # Step 1: Find explicit definitions
    _extract_definitions(text, glossary)

    # Step 2: Find abbreviation introductions
    _extract_abbreviations(text, glossary)

    # Step 3: Find capitalized compound terms
    _extract_compound_terms(text, glossary, min_frequency)

    # Update first occurrence line numbers
    for entry in glossary.entries:
        for i, line in enumerate(lines, 1):
            if entry.term.lower() in line.lower():
                entry.first_occurrence = i
                break

    # Count frequencies
    lower_text = text.lower()
    for entry in glossary.entries:
        entry.frequency = _count_occurrences(lower_text, entry.term.lower())

    # Filter by minimum frequency
    if min_frequency > 1:
        glossary.entries = [e for e in glossary.entries if e.frequency >= min_frequency]

    glossary.sort("alpha")
    return glossary


def inject_glossary(text: str, glossary: Glossary) -> str:
    """Append a glossary section to the end of a report.

    Args:
        text: Report text.
        glossary: Glossary to inject.

    Returns:
        Text with glossary appended.
    """
    if not glossary.entries:
        return text

    md = glossary.to_markdown()
    return f"{text.rstrip()}\n\n---\n\n{md}"


# ── Internal helpers ──


# Patterns for explicit definitions
_DEFINITION_PATTERNS = [
    # "X is defined as Y"
    re.compile(r"([A-Z][A-Za-z\s]+?)\s+is\s+defined\s+as\s+(.+?)[.\n]", re.IGNORECASE),
    # "X refers to Y"
    re.compile(r"([A-Z][A-Za-z\s]+?)\s+refers\s+to\s+(.+?)[.\n]", re.IGNORECASE),
    # "X, which is Y"
    re.compile(r"([A-Z][A-Za-z\s]+?),\s+which\s+is\s+(.+?)[.\n]", re.IGNORECASE),
    # "X (i.e., Y)"
    re.compile(r"([A-Z][A-Za-z\s]+?)\s+\(i\.?e\.?,?\s*(.+?)\)"),
    # "X — Y" (em dash definition)
    re.compile(r"([A-Z][A-Za-z\s]+?)\s+[—–]\s+(.+?)[.\n]"),
]


def _extract_definitions(text: str, glossary: Glossary) -> None:
    """Extract terms with explicit definitions."""
    for pattern in _DEFINITION_PATTERNS:
        for m in pattern.finditer(text):
            term = m.group(1).strip()
            definition = m.group(2).strip()
            if len(term) >= 3 and len(definition) >= 5 and len(term.split()) <= 5:
                glossary.add(term, definition)


def _extract_abbreviations(text: str, glossary: Glossary) -> None:
    """Extract terms introduced with abbreviations."""
    # "Full Name (ABBR)" pattern
    pattern = re.compile(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s+\(([A-Z]{2,})\)")
    for m in pattern.finditer(text):
        full_name = m.group(1).strip()
        abbr = m.group(2).strip()
        existing = glossary.get(full_name)
        if existing:
            existing.abbreviation = abbr
        else:
            glossary.add(full_name, f"See {abbr}.", abbreviation=abbr)


def _extract_compound_terms(
    text: str,
    glossary: Glossary,
    min_freq: int,
) -> None:
    """Extract capitalized compound terms (2-3 words)."""
    # Find Capitalized Compound Terms (2-3 words, not at sentence start)
    pattern = re.compile(r"(?<=[.!?]\s|[,;:]\s)([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})")
    candidates: dict[str, int] = {}
    for m in pattern.finditer(text):
        term = m.group(1)
        candidates[term] = candidates.get(term, 0) + 1

    # Also find terms that appear in headings
    heading_terms: set[str] = set()
    for m in re.finditer(r"^#{1,6}\s+(.+)$", text, re.MULTILINE):
        heading = m.group(1).strip()
        # Extract multi-word capitalized terms from headings
        for sub_m in re.finditer(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", heading):
            heading_terms.add(sub_m.group(1))

    for term in heading_terms:
        lower = text.lower()
        count = _count_occurrences(lower, term.lower())
        if count >= min_freq:
            candidates[term] = count

    for term, count in candidates.items():
        if count >= min_freq and not glossary.get(term):
            glossary.add(term, "")  # No auto-definition


def _count_occurrences(text: str, term: str) -> int:
    """Count case-insensitive occurrences of a term."""
    try:
        escaped = re.escape(term)
        return len(re.findall(rf"\b{escaped}\b", text, re.IGNORECASE))
    except re.error:
        return text.count(term)
