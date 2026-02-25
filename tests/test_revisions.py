"""Tests for document revision tracking and version history."""

import pytest
from datetime import datetime
from deepworm.revisions import (
    Revision,
    Change,
    RevisionDiff,
    RevisionHistory,
    compute_diff,
    create_revision,
    create_history,
    track_changes,
    merge_revisions,
)


# --- Revision ---

class TestRevision:
    def test_basic(self):
        rev = Revision(content="Hello world", version="v1")
        assert rev.content == "Hello world"
        assert rev.version == "v1"

    def test_hash(self):
        rev = Revision(content="Hello world")
        assert len(rev.hash) == 12

    def test_short_hash(self):
        rev = Revision(content="Hello world")
        assert len(rev.short_hash) == 7
        assert rev.hash.startswith(rev.short_hash)

    def test_same_content_same_hash(self):
        a = Revision(content="Hello")
        b = Revision(content="Hello")
        assert a.hash == b.hash

    def test_different_content_different_hash(self):
        a = Revision(content="Hello")
        b = Revision(content="World")
        assert a.hash != b.hash

    def test_word_count(self):
        rev = Revision(content="one two three four five")
        assert rev.word_count == 5

    def test_line_count(self):
        rev = Revision(content="line 1\nline 2\nline 3")
        assert rev.line_count == 3

    def test_empty_content(self):
        rev = Revision(content="")
        assert rev.word_count == 0
        assert rev.line_count == 0

    def test_timestamp_auto(self):
        rev = Revision(content="test")
        assert rev.timestamp is not None

    def test_to_dict(self):
        rev = Revision(content="test", version="v1", author="Alice")
        d = rev.to_dict()
        assert d["version"] == "v1"
        assert d["author"] == "Alice"
        assert "hash" in d

    def test_metadata(self):
        rev = Revision(content="test", metadata={"source": "api"})
        assert rev.metadata["source"] == "api"


# --- Change ---

class TestChange:
    def test_add(self):
        ch = Change(type="add", line_number=5, new_text="new line")
        assert ch.type == "add"
        assert ch.new_text == "new line"

    def test_delete(self):
        ch = Change(type="delete", line_number=3, old_text="old line")
        assert ch.type == "delete"

    def test_modify(self):
        ch = Change(type="modify", line_number=2, old_text="old", new_text="new")
        assert ch.type == "modify"

    def test_to_dict(self):
        ch = Change(type="add", line_number=1, new_text="hello")
        d = ch.to_dict()
        assert d["type"] == "add"
        assert d["line_number"] == 1


# --- RevisionDiff ---

class TestRevisionDiff:
    def test_total_changes(self):
        diff = RevisionDiff(
            from_version="v1", to_version="v2",
            additions=3, deletions=2, modifications=1,
        )
        assert diff.total_changes == 6

    def test_summary(self):
        diff = RevisionDiff(
            from_version="v1", to_version="v2",
            additions=2, deletions=1,
        )
        assert "+2 added" in diff.summary
        assert "-1 deleted" in diff.summary

    def test_no_changes(self):
        diff = RevisionDiff(from_version="v1", to_version="v2")
        assert diff.summary == "no changes"

    def test_to_markdown(self):
        diff = RevisionDiff(
            from_version="v1", to_version="v2",
            additions=1,
            changes=[Change(type="add", line_number=3, new_text="new line")],
        )
        md = diff.to_markdown()
        assert "v1 → v2" in md
        assert "added" in md

    def test_to_unified_diff(self):
        diff = RevisionDiff(
            from_version="v1", to_version="v2",
            changes=[
                Change(type="delete", line_number=1, old_text="old"),
                Change(type="add", line_number=1, new_text="new"),
            ],
        )
        ud = diff.to_unified_diff()
        assert "--- v1" in ud
        assert "+++ v2" in ud

    def test_to_dict(self):
        diff = RevisionDiff(from_version="v1", to_version="v2", additions=1)
        d = diff.to_dict()
        assert d["additions"] == 1
        assert d["from_version"] == "v1"


# --- RevisionHistory ---

class TestRevisionHistory:
    def test_empty(self):
        history = RevisionHistory()
        assert history.version_count == 0
        assert history.current is None

    def test_add_revision(self):
        history = RevisionHistory(title="Test")
        history.add(Revision(content="first", message="Initial"))
        assert history.version_count == 1
        assert history.current.content == "first"

    def test_auto_version(self):
        history = RevisionHistory()
        history.add(Revision(content="first"))
        history.add(Revision(content="second"))
        assert history.revisions[0].version == "v1"
        assert history.revisions[1].version == "v2"

    def test_get_by_version(self):
        history = RevisionHistory()
        history.add(Revision(content="first", version="v1"))
        assert history.get("v1").content == "first"
        assert history.get("v999") is None

    def test_get_by_hash(self):
        history = RevisionHistory()
        rev = Revision(content="unique content here")
        history.add(rev)
        found = history.get_by_hash(rev.short_hash)
        assert found is not None
        assert found.content == "unique content here"

    def test_diff(self):
        history = RevisionHistory()
        history.add(Revision(content="line 1\nline 2", version="v1"))
        history.add(Revision(content="line 1\nline 2\nline 3", version="v2"))
        diff = history.diff("v1", "v2")
        assert diff.additions > 0

    def test_changelog(self):
        history = RevisionHistory(title="Report")
        history.add(Revision(content="a", message="Initial draft", author="Alice"))
        history.add(Revision(content="b", message="Edits", author="Bob"))
        log = history.changelog()
        assert "Changelog: Report" in log
        assert "Initial draft" in log
        assert "Alice" in log

    def test_statistics(self):
        history = RevisionHistory()
        history.add(Revision(content="one two", author="Alice"))
        history.add(Revision(content="one two three", author="Bob"))
        stats = history.statistics()
        assert stats["version_count"] == 2
        assert stats["total_authors"] == 2
        assert len(stats["word_count_trend"]) == 2

    def test_statistics_empty(self):
        stats = RevisionHistory().statistics()
        assert stats["version_count"] == 0

    def test_rollback(self):
        history = RevisionHistory()
        history.add(Revision(content="original", version="v1"))
        history.add(Revision(content="changed", version="v2"))
        rolled = history.rollback("v1")
        assert rolled is not None
        assert rolled.content == "original"
        assert "Rollback" in rolled.message
        assert history.version_count == 3

    def test_rollback_nonexistent(self):
        history = RevisionHistory()
        assert history.rollback("v999") is None

    def test_to_dict(self):
        history = RevisionHistory(title="Test")
        history.add(Revision(content="a"))
        d = history.to_dict()
        assert d["title"] == "Test"
        assert d["version_count"] == 1


# --- compute_diff ---

class TestComputeDiff:
    def test_identical(self):
        a = Revision(content="same text", version="v1")
        b = Revision(content="same text", version="v2")
        diff = compute_diff(a, b)
        assert diff.total_changes == 0

    def test_addition(self):
        a = Revision(content="line 1", version="v1")
        b = Revision(content="line 1\nline 2", version="v2")
        diff = compute_diff(a, b)
        assert diff.additions >= 1

    def test_deletion(self):
        a = Revision(content="line 1\nline 2", version="v1")
        b = Revision(content="line 1", version="v2")
        diff = compute_diff(a, b)
        assert diff.deletions >= 1

    def test_modification(self):
        a = Revision(content="hello world", version="v1")
        b = Revision(content="hello universe", version="v2")
        diff = compute_diff(a, b)
        assert diff.modifications >= 1

    def test_complex_diff(self):
        a = Revision(content="line 1\nline 2\nline 3\nline 4", version="v1")
        b = Revision(content="line 1\nmodified 2\nline 3\nline 5\nline 6", version="v2")
        diff = compute_diff(a, b)
        assert diff.total_changes > 0


# --- create_revision ---

class TestCreateRevision:
    def test_basic(self):
        rev = create_revision("hello", version="v1", author="Alice")
        assert rev.content == "hello"
        assert rev.version == "v1"
        assert rev.author == "Alice"

    def test_with_metadata(self):
        rev = create_revision("test", metadata={"key": "val"})
        assert rev.metadata["key"] == "val"


# --- create_history ---

class TestCreateHistory:
    def test_from_dicts(self):
        data = [
            {"content": "first", "message": "Init", "author": "Alice"},
            {"content": "second", "message": "Update", "author": "Bob"},
        ]
        history = create_history(title="Test", revisions=data)
        assert history.version_count == 2
        assert history.title == "Test"

    def test_empty(self):
        history = create_history()
        assert history.version_count == 0


# --- track_changes ---

class TestTrackChanges:
    def test_basic(self):
        diff = track_changes("hello\nworld", "hello\nuniverse")
        assert diff.from_version == "v1"
        assert diff.to_version == "v2"
        assert diff.total_changes > 0

    def test_no_changes(self):
        diff = track_changes("same", "same")
        assert diff.total_changes == 0


# --- merge_revisions ---

class TestMergeRevisions:
    def test_merge(self):
        h1 = RevisionHistory(title="Branch A")
        h1.add(Revision(content="a1", version="a-v1", author="Alice"))
        h2 = RevisionHistory(title="Branch B")
        h2.add(Revision(content="b1", version="b-v1", author="Bob"))
        merged = merge_revisions(h1, h2)
        assert merged.version_count == 2
        assert "Branch A" in merged.title

    def test_merge_dedup(self):
        h1 = RevisionHistory()
        h1.add(Revision(content="same", version="v1"))
        h2 = RevisionHistory()
        h2.add(Revision(content="same", version="v1-copy"))
        merged = merge_revisions(h1, h2)
        # Same content hash → deduplicated
        assert merged.version_count == 1
