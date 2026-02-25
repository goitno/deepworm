"""Timeline extraction and visualization from research reports.

Extract dates, events, and temporal references from text to build
chronological timelines. Supports multiple date formats, relative
dates, and markdown/text output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class TimelineEvent:
    """A single event on the timeline."""

    date: str
    description: str
    category: str = "general"
    source: Optional[str] = None
    sort_key: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result: Dict[str, Any] = {
            "date": self.date,
            "description": self.description,
            "category": self.category,
        }
        if self.source:
            result["source"] = self.source
        return result


@dataclass
class Timeline:
    """A chronological timeline of events."""

    title: str = "Timeline"
    events: List[TimelineEvent] = field(default_factory=list)

    def add(
        self,
        date: str,
        description: str,
        category: str = "general",
        source: Optional[str] = None,
    ) -> TimelineEvent:
        """Add an event to the timeline."""
        sort_key = _date_to_sort_key(date)
        event = TimelineEvent(
            date=date,
            description=description,
            category=category,
            source=source,
            sort_key=sort_key,
        )
        self.events.append(event)
        return event

    def sort(self) -> None:
        """Sort events chronologically."""
        self.events.sort(key=lambda e: e.sort_key)

    def filter_by_category(self, category: str) -> List[TimelineEvent]:
        """Get events matching a category."""
        return [e for e in self.events if e.category == category]

    def filter_by_range(
        self, start: str, end: str
    ) -> List[TimelineEvent]:
        """Get events within a date range."""
        start_key = _date_to_sort_key(start)
        end_key = _date_to_sort_key(end)
        return [
            e for e in self.events
            if start_key <= e.sort_key <= end_key
        ]

    @property
    def categories(self) -> List[str]:
        """Get unique categories."""
        seen: List[str] = []
        for e in self.events:
            if e.category not in seen:
                seen.append(e.category)
        return seen

    @property
    def date_range(self) -> Optional[Tuple[str, str]]:
        """Get the earliest and latest dates."""
        if not self.events:
            return None
        sorted_events = sorted(self.events, key=lambda e: e.sort_key)
        return sorted_events[0].date, sorted_events[-1].date

    def merge(self, other: "Timeline") -> "Timeline":
        """Merge another timeline into this one."""
        merged = Timeline(title=self.title)
        merged.events = list(self.events) + list(other.events)
        merged.sort()
        return merged

    def deduplicate(self) -> None:
        """Remove duplicate events (same date + description)."""
        seen: set = set()
        unique: List[TimelineEvent] = []
        for event in self.events:
            key = (event.date, event.description.lower().strip())
            if key not in seen:
                seen.add(key)
                unique.append(event)
        self.events = unique

    def to_markdown(self) -> str:
        """Render timeline as markdown."""
        if not self.events:
            return f"## {self.title}\n\n*No events found.*\n"

        self.sort()
        lines = [f"## {self.title}\n"]

        for event in self.events:
            line = f"- **{event.date}** — {event.description}"
            if event.source:
                line += f" *({event.source})*"
            lines.append(line)

        return "\n".join(lines) + "\n"

    def to_table(self) -> str:
        """Render timeline as a markdown table."""
        if not self.events:
            return f"## {self.title}\n\n*No events found.*\n"

        self.sort()
        lines = [
            f"## {self.title}\n",
            "| Date | Event | Category |",
            "|------|-------|----------|",
        ]

        for event in self.events:
            desc = event.description.replace("|", "\\|")
            lines.append(f"| {event.date} | {desc} | {event.category} |")

        return "\n".join(lines) + "\n"

    def to_dict(self) -> Dict[str, Any]:
        """Convert timeline to dictionary."""
        self.sort()
        return {
            "title": self.title,
            "event_count": len(self.events),
            "date_range": self.date_range,
            "categories": self.categories,
            "events": [e.to_dict() for e in self.events],
        }


# Date patterns for extraction
_MONTH_NAMES = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9,
    "oct": 10, "nov": 11, "dec": 12,
}

# Patterns: "January 2023", "Jan 2023"
_MONTH_YEAR_PATTERN = re.compile(
    r"\b("
    + "|".join(_MONTH_NAMES.keys())
    + r")\s+(\d{4})\b",
    re.IGNORECASE,
)

# Patterns: "January 15, 2023", "Jan 15 2023"
_FULL_DATE_PATTERN = re.compile(
    r"\b("
    + "|".join(_MONTH_NAMES.keys())
    + r")\s+(\d{1,2}),?\s+(\d{4})\b",
    re.IGNORECASE,
)

# Pattern: "2023-01-15", "2023/01/15"
_ISO_DATE_PATTERN = re.compile(
    r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b"
)

# Pattern: just a year "in 2023", "since 1990"
_YEAR_PATTERN = re.compile(
    r"\b(?:in|since|from|by|around|circa|during|until|after|before)\s+(\d{4})\b",
    re.IGNORECASE,
)

# Pattern: decades "the 1990s", "2000s"
_DECADE_PATTERN = re.compile(
    r"\b(?:the\s+)?(\d{4})s\b",
    re.IGNORECASE,
)

# Pattern: "Q1 2023", "Q3 2024"
_QUARTER_PATTERN = re.compile(
    r"\b(Q[1-4])\s+(\d{4})\b",
    re.IGNORECASE,
)

# Century pattern: "21st century", "19th century"
_CENTURY_PATTERN = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)\s+century\b",
    re.IGNORECASE,
)


def _date_to_sort_key(date: str) -> int:
    """Convert a date string to an integer for sorting.

    Returns YYYYMMDD as integer, with missing parts zeroed.
    """
    date_lower = date.lower().strip()

    # Try ISO format: 2023-01-15
    iso_match = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$", date_lower)
    if iso_match:
        y, m, d = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
        return y * 10000 + m * 100 + d

    # Try "Month Day, Year"
    full_match = re.match(
        r"^([a-z]+)\s+(\d{1,2}),?\s+(\d{4})$", date_lower
    )
    if full_match:
        month_name = full_match.group(1)
        m = _MONTH_NAMES.get(month_name, 0)
        d = int(full_match.group(2))
        y = int(full_match.group(3))
        return y * 10000 + m * 100 + d

    # Try "Month Year"
    month_year_match = re.match(r"^([a-z]+)\s+(\d{4})$", date_lower)
    if month_year_match:
        month_name = month_year_match.group(1)
        m = _MONTH_NAMES.get(month_name, 0)
        y = int(month_year_match.group(2))
        return y * 10000 + m * 100

    # Quarter: "Q1 2023"
    q_match = re.match(r"^q([1-4])\s+(\d{4})$", date_lower)
    if q_match:
        q = int(q_match.group(1))
        y = int(q_match.group(2))
        month = (q - 1) * 3 + 1
        return y * 10000 + month * 100

    # Decade: "1990s"
    decade_match = re.match(r"^(?:the\s+)?(\d{4})s$", date_lower)
    if decade_match:
        y = int(decade_match.group(1))
        return y * 10000

    # Century: "21st century"
    century_match = re.match(
        r"^(\d{1,2})(?:st|nd|rd|th)\s+century$", date_lower
    )
    if century_match:
        c = int(century_match.group(1))
        y = (c - 1) * 100 + 1
        return y * 10000

    # Plain year
    year_match = re.match(r"^(\d{4})$", date_lower)
    if year_match:
        return int(year_match.group(1)) * 10000

    return 0


def extract_timeline(
    text: str,
    title: str = "Timeline",
    include_context: bool = True,
) -> Timeline:
    """Extract a timeline from text.

    Scans text for dates and temporal references, extracting
    surrounding context as event descriptions.

    Args:
        text: Input text to scan.
        title: Title for the timeline.
        include_context: Include surrounding sentence context.

    Returns:
        Timeline with extracted events.
    """
    timeline = Timeline(title=title)
    sentences = _split_sentences(text)
    seen: set = set()

    for sentence in sentences:
        clean = sentence.strip()
        if not clean or len(clean) < 10:
            continue

        events = _extract_from_sentence(clean, include_context)
        for date, description in events:
            key = (date, description.lower().strip())
            if key not in seen:
                seen.add(key)
                category = _categorize_event(description)
                timeline.add(date, description, category=category)

    timeline.sort()
    return timeline


def _split_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    # Remove markdown headings but keep text
    text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)
    # Split on sentence boundaries
    parts = re.split(r"(?<=[.!?])\s+", text)
    result: List[str] = []
    for part in parts:
        # Also split on newlines for list items
        for sub in part.split("\n"):
            sub = sub.strip(" -•*>")
            if sub:
                result.append(sub)
    return result


def _extract_from_sentence(
    sentence: str, include_context: bool
) -> List[Tuple[str, str]]:
    """Extract date-description pairs from a sentence."""
    results: List[Tuple[str, str]] = []

    # Full dates: "January 15, 2023"
    for match in _FULL_DATE_PATTERN.finditer(sentence):
        month_name = match.group(1).capitalize()
        day = match.group(2)
        year = match.group(3)
        date = f"{month_name} {day}, {year}"
        desc = _get_context(sentence, match, include_context)
        if desc:
            results.append((date, desc))

    # Month-Year: "January 2023" (skip if already captured as full date)
    full_date_spans = {m.span() for m in _FULL_DATE_PATTERN.finditer(sentence)}
    for match in _MONTH_YEAR_PATTERN.finditer(sentence):
        # Skip if this month-year is part of a full date
        overlaps = False
        for start, end in full_date_spans:
            if start <= match.start() < end:
                overlaps = True
                break
        if overlaps:
            continue

        month_name = match.group(1).capitalize()
        if month_name.lower() == "may":
            # "may" can be a verb — check context
            before = sentence[:match.start()].strip().lower()
            if before.endswith(("it", "you", "we", "they", "this", "that", "which")):
                continue
        year = match.group(2)
        date = f"{month_name} {year}"
        desc = _get_context(sentence, match, include_context)
        if desc:
            results.append((date, desc))

    # ISO dates: "2023-01-15"
    for match in _ISO_DATE_PATTERN.finditer(sentence):
        year = match.group(1)
        month = match.group(2).zfill(2)
        day = match.group(3).zfill(2)
        date = f"{year}-{month}-{day}"
        desc = _get_context(sentence, match, include_context)
        if desc:
            results.append((date, desc))

    # Quarters: "Q1 2023"
    for match in _QUARTER_PATTERN.finditer(sentence):
        quarter = match.group(1).upper()
        year = match.group(2)
        date = f"{quarter} {year}"
        desc = _get_context(sentence, match, include_context)
        if desc:
            results.append((date, desc))

    # Decades: "the 1990s"
    for match in _DECADE_PATTERN.finditer(sentence):
        decade = match.group(1)
        date = f"{decade}s"
        desc = _get_context(sentence, match, include_context)
        if desc:
            results.append((date, desc))

    # Century: "21st century"
    for match in _CENTURY_PATTERN.finditer(sentence):
        num = match.group(1)
        suffix = _ordinal_suffix(int(num))
        date = f"{num}{suffix} century"
        desc = _get_context(sentence, match, include_context)
        if desc:
            results.append((date, desc))

    # Year references: "in 2023", "since 1990"
    if not results:
        for match in _YEAR_PATTERN.finditer(sentence):
            year = match.group(1)
            desc = _get_context(sentence, match, include_context)
            if desc:
                results.append((year, desc))

    return results


def _get_context(
    sentence: str, match: re.Match, include_context: bool
) -> str:
    """Get the event description from context around a date match."""
    if not include_context:
        # Just return the date portion
        return sentence.strip()

    # Use the full sentence as context, cleaning up
    desc = sentence.strip()
    # Remove leading list markers
    desc = re.sub(r"^[-•*]\s+", "", desc)
    # Remove markdown bold/italic
    desc = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", desc)
    # Truncate very long descriptions
    if len(desc) > 200:
        desc = desc[:197] + "..."
    return desc


def _categorize_event(description: str) -> str:
    """Auto-categorize an event based on keywords."""
    desc_lower = description.lower()

    categories = {
        "technology": [
            "launched", "released", "software", "app", "platform",
            "technology", "digital", "computer", "internet", "api",
            "version", "update", "patent", "invented",
        ],
        "business": [
            "company", "founded", "acquired", "merger", "ipo",
            "revenue", "profit", "startup", "investment", "market",
            "billion", "million", "valuation", "funding",
        ],
        "science": [
            "discovered", "research", "study", "published", "journal",
            "experiment", "theory", "scientist", "laboratory",
            "breakthrough",
        ],
        "policy": [
            "law", "regulation", "act", "policy", "government",
            "legislation", "passed", "signed", "enacted", "banned",
            "approved", "treaty",
        ],
        "milestone": [
            "first", "record", "achievement", "milestone", "historic",
            "landmark", "breakthrough", "pioneered",
        ],
    }

    for category, keywords in categories.items():
        if any(kw in desc_lower for kw in keywords):
            return category

    return "general"


def _ordinal_suffix(n: int) -> str:
    """Get the ordinal suffix for a number."""
    if 11 <= n % 100 <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def create_timeline(
    events: List[Dict[str, str]],
    title: str = "Timeline",
) -> Timeline:
    """Create a timeline from a list of event dicts.

    Args:
        events: List of dicts with 'date' and 'description' keys.
            Optional 'category' and 'source' keys.
        title: Title for the timeline.

    Returns:
        Timeline with the provided events.
    """
    timeline = Timeline(title=title)
    for event_data in events:
        date = event_data.get("date", "")
        desc = event_data.get("description", "")
        if not date or not desc:
            continue
        category = event_data.get("category", "general")
        source = event_data.get("source")
        timeline.add(date, desc, category=category, source=source)
    timeline.sort()
    return timeline


def compare_timelines(
    timeline_a: Timeline,
    timeline_b: Timeline,
) -> Dict[str, Any]:
    """Compare two timelines.

    Returns a dict with overlap analysis, unique events,
    and coverage comparison.
    """
    dates_a = {e.date for e in timeline_a.events}
    dates_b = {e.date for e in timeline_b.events}

    shared_dates = dates_a & dates_b
    only_a = dates_a - dates_b
    only_b = dates_b - dates_a

    # Events on shared dates
    shared_events: List[Dict[str, Any]] = []
    for date in sorted(shared_dates, key=lambda d: _date_to_sort_key(d)):
        events_a = [e for e in timeline_a.events if e.date == date]
        events_b = [e for e in timeline_b.events if e.date == date]
        shared_events.append({
            "date": date,
            "timeline_a": [e.description for e in events_a],
            "timeline_b": [e.description for e in events_b],
        })

    return {
        "total_a": len(timeline_a.events),
        "total_b": len(timeline_b.events),
        "shared_dates": len(shared_dates),
        "unique_to_a": len(only_a),
        "unique_to_b": len(only_b),
        "overlap_ratio": (
            len(shared_dates) / max(len(dates_a | dates_b), 1)
        ),
        "shared_events": shared_events,
    }
