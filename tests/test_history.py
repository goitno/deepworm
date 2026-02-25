"""Tests for deepworm.history module."""

import json
import time
from pathlib import Path

import pytest

from deepworm.history import (
    HistoryEntry,
    add_entry,
    clear_history,
    delete_entry,
    get_entry,
    list_entries,
    search_history,
    stats,
)


@pytest.fixture
def history_file(tmp_path):
    return tmp_path / "test_history.jsonl"


def _add(history_file, topic="Test topic", **kwargs):
    defaults = dict(
        elapsed=10.5,
        model="gpt-4o",
        provider="openai",
        depth=2,
        breadth=4,
        total_sources=12,
        report_length=3000,
    )
    defaults.update(kwargs)
    return add_entry(topic=topic, history_file=history_file, **defaults)


class TestHistoryEntry:
    def test_auto_id(self):
        entry = HistoryEntry(
            topic="test", created_at=100.0, elapsed_seconds=5.0,
            model="m", provider="p", depth=1, breadth=1,
            total_sources=1, report_length=100,
        )
        assert len(entry.id) == 12

    def test_created_iso(self):
        entry = HistoryEntry(
            topic="test", created_at=0.0, elapsed_seconds=0.0,
            model="m", provider="p", depth=1, breadth=1,
            total_sources=1, report_length=100,
        )
        assert entry.created_iso.startswith("1970-01-01")

    def test_roundtrip(self):
        entry = HistoryEntry(
            topic="roundtrip", created_at=time.time(), elapsed_seconds=5.0,
            model="gpt-4o", provider="openai", depth=2, breadth=4,
            total_sources=10, report_length=2000, persona="dev",
            tags=["ai", "test"],
        )
        data = entry.to_dict()
        restored = HistoryEntry.from_dict(data)
        assert restored.topic == entry.topic
        assert restored.tags == entry.tags
        assert restored.persona == entry.persona


class TestAddAndList:
    def test_add_creates_file(self, history_file):
        entry = _add(history_file)
        assert history_file.exists()
        assert entry.topic == "Test topic"
        assert len(entry.id) == 12

    def test_list_entries(self, history_file):
        _add(history_file, topic="First")
        _add(history_file, topic="Second")
        entries = list_entries(history_file=history_file)
        assert len(entries) == 2
        # newest first
        assert entries[0].topic == "Second"

    def test_list_entries_empty(self, history_file):
        assert list_entries(history_file=history_file) == []

    def test_list_entries_limit(self, history_file):
        for i in range(5):
            _add(history_file, topic=f"Topic {i}")
        entries = list_entries(history_file=history_file, limit=3)
        assert len(entries) == 3


class TestSearch:
    def test_search_finds_match(self, history_file):
        _add(history_file, topic="Quantum computing trends")
        _add(history_file, topic="Machine learning basics")
        results = search_history("quantum", history_file=history_file)
        assert len(results) == 1
        assert results[0].topic == "Quantum computing trends"

    def test_search_case_insensitive(self, history_file):
        _add(history_file, topic="Python Best Practices")
        results = search_history("python", history_file=history_file)
        assert len(results) == 1

    def test_search_no_match(self, history_file):
        _add(history_file, topic="Something else")
        assert search_history("nonexistent", history_file=history_file) == []


class TestGetAndDelete:
    def test_get_entry(self, history_file):
        entry = _add(history_file, topic="Find me")
        found = get_entry(entry.id, history_file=history_file)
        assert found is not None
        assert found.topic == "Find me"

    def test_get_entry_prefix(self, history_file):
        entry = _add(history_file, topic="Prefix test")
        found = get_entry(entry.id[:6], history_file=history_file)
        assert found is not None

    def test_get_entry_not_found(self, history_file):
        assert get_entry("nonexistent", history_file=history_file) is None

    def test_delete_entry(self, history_file):
        e1 = _add(history_file, topic="Keep me")
        e2 = _add(history_file, topic="Delete me")
        assert delete_entry(e2.id, history_file=history_file)
        entries = list_entries(history_file=history_file)
        assert len(entries) == 1
        assert entries[0].topic == "Keep me"

    def test_delete_not_found(self, history_file):
        assert not delete_entry("nonexistent", history_file=history_file)


class TestClearAndStats:
    def test_clear(self, history_file):
        _add(history_file, topic="A")
        _add(history_file, topic="B")
        count = clear_history(history_file=history_file)
        assert count == 2
        assert list_entries(history_file=history_file) == []

    def test_clear_empty(self, history_file):
        assert clear_history(history_file=history_file) == 0

    def test_stats(self, history_file):
        _add(history_file, topic="A", elapsed=10.0, total_sources=5, model="gpt-4o", provider="openai")
        _add(history_file, topic="B", elapsed=20.0, total_sources=15, model="claude-3", provider="anthropic")
        s = stats(history_file=history_file)
        assert s["total_researches"] == 2
        assert s["total_sources"] == 20
        assert s["avg_time_seconds"] == 15.0
        assert "gpt-4o" in s["models_used"]
        assert "anthropic" in s["providers_used"]

    def test_stats_empty(self, history_file):
        s = stats(history_file=history_file)
        assert s["total_researches"] == 0
