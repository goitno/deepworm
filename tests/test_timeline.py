"""Tests for timeline extraction and management."""

import pytest
from deepworm.timeline import (
    Timeline,
    TimelineEvent,
    extract_timeline,
    create_timeline,
    compare_timelines,
    _date_to_sort_key,
    _categorize_event,
    _ordinal_suffix,
)


# --- TimelineEvent ---

class TestTimelineEvent:
    def test_basic_event(self):
        event = TimelineEvent(date="2023", description="Something happened")
        assert event.date == "2023"
        assert event.description == "Something happened"
        assert event.category == "general"
        assert event.source is None

    def test_to_dict_minimal(self):
        event = TimelineEvent(date="2023", description="Event")
        d = event.to_dict()
        assert d["date"] == "2023"
        assert d["description"] == "Event"
        assert "source" not in d

    def test_to_dict_with_source(self):
        event = TimelineEvent(date="2023", description="Event", source="Wikipedia")
        d = event.to_dict()
        assert d["source"] == "Wikipedia"


# --- Timeline ---

class TestTimeline:
    def test_empty_timeline(self):
        tl = Timeline()
        assert tl.title == "Timeline"
        assert len(tl.events) == 0

    def test_add_event(self):
        tl = Timeline()
        event = tl.add("2023", "Something happened")
        assert len(tl.events) == 1
        assert event.date == "2023"
        assert event.sort_key > 0

    def test_add_with_category(self):
        tl = Timeline()
        tl.add("2023", "Python released", category="technology")
        assert tl.events[0].category == "technology"

    def test_add_with_source(self):
        tl = Timeline()
        tl.add("2023", "Discovery", source="Nature")
        assert tl.events[0].source == "Nature"

    def test_sort_chronological(self):
        tl = Timeline()
        tl.add("2025", "Third")
        tl.add("2020", "First")
        tl.add("2023", "Second")
        tl.sort()
        assert tl.events[0].description == "First"
        assert tl.events[1].description == "Second"
        assert tl.events[2].description == "Third"

    def test_sort_with_months(self):
        tl = Timeline()
        tl.add("March 2023", "Later")
        tl.add("January 2023", "Earlier")
        tl.sort()
        assert tl.events[0].description == "Earlier"

    def test_filter_by_category(self):
        tl = Timeline()
        tl.add("2020", "Tech event", category="technology")
        tl.add("2021", "Biz event", category="business")
        tl.add("2022", "Another tech", category="technology")
        tech = tl.filter_by_category("technology")
        assert len(tech) == 2

    def test_filter_by_range(self):
        tl = Timeline()
        tl.add("2018", "Before")
        tl.add("2020", "In range")
        tl.add("2023", "In range 2")
        tl.add("2026", "After")
        result = tl.filter_by_range("2019", "2024")
        assert len(result) == 2

    def test_categories(self):
        tl = Timeline()
        tl.add("2020", "A", category="tech")
        tl.add("2021", "B", category="biz")
        tl.add("2022", "C", category="tech")
        cats = tl.categories
        assert cats == ["tech", "biz"]

    def test_date_range_empty(self):
        tl = Timeline()
        assert tl.date_range is None

    def test_date_range(self):
        tl = Timeline()
        tl.add("2020", "First")
        tl.add("2025", "Last")
        tl.add("2023", "Middle")
        rng = tl.date_range
        assert rng == ("2020", "2025")

    def test_merge(self):
        tl_a = Timeline(title="A")
        tl_a.add("2020", "Event A")
        tl_b = Timeline(title="B")
        tl_b.add("2023", "Event B")
        merged = tl_a.merge(tl_b)
        assert len(merged.events) == 2
        assert merged.events[0].description == "Event A"

    def test_deduplicate(self):
        tl = Timeline()
        tl.add("2023", "Same event")
        tl.add("2023", "Same Event")  # same after lowercase
        tl.add("2023", "Different event")
        tl.deduplicate()
        assert len(tl.events) == 2

    def test_to_markdown_empty(self):
        tl = Timeline(title="Test")
        md = tl.to_markdown()
        assert "No events found" in md

    def test_to_markdown(self):
        tl = Timeline(title="History")
        tl.add("2020", "Started project")
        tl.add("2023", "Released v1.0", source="GitHub")
        md = tl.to_markdown()
        assert "## History" in md
        assert "**2020**" in md
        assert "**2023**" in md
        assert "*(GitHub)*" in md

    def test_to_table(self):
        tl = Timeline(title="Events")
        tl.add("2020", "First event", category="tech")
        table = tl.to_table()
        assert "| Date | Event | Category |" in table
        assert "| 2020 | First event | tech |" in table

    def test_to_table_empty(self):
        tl = Timeline()
        table = tl.to_table()
        assert "No events found" in table

    def test_to_dict(self):
        tl = Timeline(title="Test")
        tl.add("2023", "An event", category="tech")
        d = tl.to_dict()
        assert d["title"] == "Test"
        assert d["event_count"] == 1
        assert d["categories"] == ["tech"]
        assert len(d["events"]) == 1

    def test_to_table_escapes_pipe(self):
        tl = Timeline()
        tl.add("2023", "A | B comparison")
        table = tl.to_table()
        assert "A \\| B comparison" in table


# --- Date Sort Key ---

class TestDateSortKey:
    def test_plain_year(self):
        assert _date_to_sort_key("2023") == 20230000

    def test_iso_date(self):
        assert _date_to_sort_key("2023-01-15") == 20230115

    def test_iso_date_slash(self):
        assert _date_to_sort_key("2023/03/20") == 20230320

    def test_month_year(self):
        assert _date_to_sort_key("January 2023") == 20230100

    def test_full_date(self):
        assert _date_to_sort_key("March 15, 2023") == 20230315

    def test_quarter(self):
        assert _date_to_sort_key("Q1 2023") == 20230100
        assert _date_to_sort_key("Q3 2023") == 20230700

    def test_decade(self):
        assert _date_to_sort_key("1990s") == 19900000

    def test_century(self):
        assert _date_to_sort_key("21st century") == 20010000
        assert _date_to_sort_key("19th century") == 18010000

    def test_unknown(self):
        assert _date_to_sort_key("sometime") == 0

    def test_abbreviated_month(self):
        assert _date_to_sort_key("Jan 2023") == 20230100


# --- Extract Timeline ---

SAMPLE_TEXT = """
# History of Python

Python was created by Guido van Rossum. The first version was released in February 1991.

In January 2000, Python 2.0 was released with list comprehensions.

Python 3.0 was released on December 3, 2008, breaking backward compatibility.

Python 3.6, released in December 2016, introduced f-strings.

In October 2020, Python 3.9 was released with dictionary merge operators.

The Python Software Foundation was founded in March 2001.
"""


class TestExtractTimeline:
    def test_extracts_events(self):
        tl = extract_timeline(SAMPLE_TEXT)
        assert len(tl.events) >= 4

    def test_chronological_order(self):
        tl = extract_timeline(SAMPLE_TEXT)
        sort_keys = [e.sort_key for e in tl.events]
        assert sort_keys == sorted(sort_keys)

    def test_finds_month_year(self):
        tl = extract_timeline(SAMPLE_TEXT)
        dates = [e.date for e in tl.events]
        assert any("2000" in d for d in dates)

    def test_finds_full_date(self):
        tl = extract_timeline(SAMPLE_TEXT)
        dates = [e.date for e in tl.events]
        assert any("December" in d and "2008" in d for d in dates)

    def test_custom_title(self):
        tl = extract_timeline(SAMPLE_TEXT, title="Python History")
        assert tl.title == "Python History"

    def test_empty_text(self):
        tl = extract_timeline("")
        assert len(tl.events) == 0

    def test_no_dates_text(self):
        tl = extract_timeline("This text has no dates whatsoever and is just plain words.")
        assert len(tl.events) == 0

    def test_iso_dates(self):
        text = "Version 1.0 was released on 2023-06-15. The beta was on 2023-01-10."
        tl = extract_timeline(text)
        assert len(tl.events) >= 2

    def test_quarters(self):
        text = "Revenue grew in Q1 2023. Expansion planned for Q3 2024."
        tl = extract_timeline(text)
        dates = [e.date for e in tl.events]
        assert any("Q1 2023" in d for d in dates)

    def test_decades(self):
        text = "The internet boom of the 1990s changed everything. AI surged in the 2020s."
        tl = extract_timeline(text)
        assert len(tl.events) >= 2

    def test_century(self):
        text = "This practice dates back to the 19th century."
        tl = extract_timeline(text)
        assert len(tl.events) >= 1
        assert any("century" in e.date for e in tl.events)

    def test_deduplication(self):
        text = "Python was released in February 1991. Python was released in February 1991."
        tl = extract_timeline(text)
        # Should deduplicate identical date+description
        dates_1991 = [e for e in tl.events if "1991" in e.date]
        assert len(dates_1991) == 1

    def test_year_references(self):
        text = "The company was established since 1995 and has grown consistently."
        tl = extract_timeline(text)
        assert len(tl.events) >= 1

    def test_categorization(self):
        text = "The company was founded in January 2020. The software was released in March 2021."
        tl = extract_timeline(text)
        categories = [e.category for e in tl.events]
        assert "business" in categories or "technology" in categories


# --- Create Timeline ---

class TestCreateTimeline:
    def test_from_dicts(self):
        events = [
            {"date": "2020", "description": "Started"},
            {"date": "2023", "description": "Released"},
        ]
        tl = create_timeline(events)
        assert len(tl.events) == 2

    def test_with_category_and_source(self):
        events = [
            {"date": "2023", "description": "Launch", "category": "tech", "source": "Blog"},
        ]
        tl = create_timeline(events, title="Launches")
        assert tl.events[0].category == "tech"
        assert tl.events[0].source == "Blog"
        assert tl.title == "Launches"

    def test_skips_empty(self):
        events = [
            {"date": "", "description": "No date"},
            {"date": "2023", "description": ""},
            {"date": "2023", "description": "Valid"},
        ]
        tl = create_timeline(events)
        assert len(tl.events) == 1

    def test_sorted_output(self):
        events = [
            {"date": "2025", "description": "Later"},
            {"date": "2020", "description": "Earlier"},
        ]
        tl = create_timeline(events)
        assert tl.events[0].description == "Earlier"


# --- Compare Timelines ---

class TestCompareTimelines:
    def test_compare_overlapping(self):
        tl_a = Timeline(title="A")
        tl_a.add("2020", "Event 1")
        tl_a.add("2023", "Event 2")

        tl_b = Timeline(title="B")
        tl_b.add("2023", "Different event")
        tl_b.add("2025", "Event 3")

        result = compare_timelines(tl_a, tl_b)
        assert result["total_a"] == 2
        assert result["total_b"] == 2
        assert result["shared_dates"] == 1
        assert result["unique_to_a"] == 1
        assert result["unique_to_b"] == 1
        assert 0 < result["overlap_ratio"] < 1

    def test_compare_no_overlap(self):
        tl_a = Timeline()
        tl_a.add("2020", "A")
        tl_b = Timeline()
        tl_b.add("2025", "B")
        result = compare_timelines(tl_a, tl_b)
        assert result["shared_dates"] == 0
        assert result["overlap_ratio"] == 0

    def test_compare_full_overlap(self):
        tl_a = Timeline()
        tl_a.add("2023", "Event A")
        tl_b = Timeline()
        tl_b.add("2023", "Event B")
        result = compare_timelines(tl_a, tl_b)
        assert result["shared_dates"] == 1
        assert result["overlap_ratio"] == 1.0

    def test_shared_events_content(self):
        tl_a = Timeline()
        tl_a.add("2023", "Version A released")
        tl_b = Timeline()
        tl_b.add("2023", "Version B released")
        result = compare_timelines(tl_a, tl_b)
        shared = result["shared_events"]
        assert len(shared) == 1
        assert "Version A released" in shared[0]["timeline_a"]
        assert "Version B released" in shared[0]["timeline_b"]


# --- Categorization ---

class TestCategorization:
    def test_technology(self):
        assert _categorize_event("The new software was released") == "technology"

    def test_business(self):
        assert _categorize_event("The company was founded in 2020") == "business"

    def test_science(self):
        assert _categorize_event("Scientists discovered a new element") == "science"

    def test_policy(self):
        assert _categorize_event("The government passed a new law") == "policy"

    def test_milestone(self):
        assert _categorize_event("This was the first achievement of its kind") == "milestone"

    def test_general(self):
        assert _categorize_event("The weather was nice today") == "general"


# --- Helpers ---

class TestHelpers:
    def test_ordinal_suffix(self):
        assert _ordinal_suffix(1) == "st"
        assert _ordinal_suffix(2) == "nd"
        assert _ordinal_suffix(3) == "rd"
        assert _ordinal_suffix(4) == "th"
        assert _ordinal_suffix(11) == "th"
        assert _ordinal_suffix(21) == "st"
