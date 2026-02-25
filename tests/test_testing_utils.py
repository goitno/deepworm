"""Tests for deepworm.testing_utils module."""

import json
import time

import pytest

from deepworm.testing_utils import (
    AssertionMode,
    MockCall,
    MockFunction,
    MockSequence,
    Snapshot,
    SnapshotStore,
    TestFixture,
    TimingResult,
    assert_contains_all,
    assert_fast,
    assert_json_valid,
    assert_markdown_valid,
    assert_no_duplicates,
    assert_word_count_range,
    create_fixture,
    create_mock,
    create_sequence,
    create_snapshot_store,
    sample_config,
    sample_markdown,
    sample_research_data,
    time_execution,
)


# ---------------------------------------------------------------------------
# AssertionMode enum
# ---------------------------------------------------------------------------


class TestAssertionMode:
    def test_values(self):
        assert AssertionMode.EXACT.value == "exact"
        assert AssertionMode.CONTAINS.value == "contains"
        assert AssertionMode.STARTS_WITH.value == "starts_with"
        assert AssertionMode.REGEX.value == "regex"
        assert AssertionMode.APPROXIMATE.value == "approximate"

    def test_all_modes(self):
        assert len(AssertionMode) == 6


# ---------------------------------------------------------------------------
# TestFixture
# ---------------------------------------------------------------------------


class TestTestFixture:
    def test_create_empty_fixture(self):
        f = create_fixture("test")
        assert f.name == "test"
        assert f.data == {}

    def test_create_with_data(self):
        f = create_fixture("test", data={"key": "value"})
        assert f.data["key"] == "value"

    def test_setup_teardown(self):
        setup_called = []
        teardown_called = []

        def setup(data):
            data["initialized"] = True
            setup_called.append(True)

        def teardown(data):
            teardown_called.append(True)

        f = create_fixture("test", setup=setup, teardown=teardown)
        f.setup()
        assert f.data["initialized"] is True
        assert len(setup_called) == 1

        f.teardown()
        assert len(teardown_called) == 1

    def test_context_manager(self):
        events = []

        def setup(data):
            events.append("setup")

        def teardown(data):
            events.append("teardown")

        f = create_fixture("test", setup=setup, teardown=teardown)
        with f:
            events.append("body")

        assert events == ["setup", "body", "teardown"]

    def test_setup_only_runs_once(self):
        count = []

        def setup(data):
            count.append(1)

        f = create_fixture("test", setup=setup)
        f.setup()
        f.setup()  # should not run again
        assert len(count) == 1

    def test_teardown_without_setup(self):
        called = []

        def teardown(data):
            called.append(1)

        f = create_fixture("test", teardown=teardown)
        f.teardown()  # should not call since not setup
        assert len(called) == 0


# ---------------------------------------------------------------------------
# MockFunction
# ---------------------------------------------------------------------------


class TestMockFunction:
    def test_basic_return(self):
        m = create_mock(return_value=42)
        assert m() == 42

    def test_call_count(self):
        m = create_mock()
        m()
        m()
        m()
        assert m.call_count == 3
        assert m.called is True

    def test_not_called(self):
        m = create_mock()
        assert m.called is False
        assert m.call_count == 0
        assert m.last_call is None

    def test_call_args(self):
        m = create_mock(return_value="ok")
        m(1, 2, key="val")
        assert m.last_call is not None
        assert m.last_call.args == (1, 2)
        assert m.last_call.kwargs == {"key": "val"}

    def test_called_with(self):
        m = create_mock()
        m(1, x=2)
        m(3, y=4)
        assert m.called_with(1, x=2) is True
        assert m.called_with(3, y=4) is True
        assert m.called_with(5) is False

    def test_side_effect(self):
        def effect(x):
            return x * 2

        m = create_mock(side_effect=effect)
        assert m(5) == 10
        assert m(3) == 6

    def test_reset(self):
        m = create_mock(return_value=1)
        m()
        m()
        m.reset()
        assert m.call_count == 0
        assert m.called is False

    def test_set_return(self):
        m = create_mock(return_value=1)
        assert m() == 1
        m.set_return(2)
        assert m() == 2

    def test_set_side_effect(self):
        m = create_mock(return_value=1)
        assert m() == 1
        m.set_side_effect(lambda: 99)
        assert m() == 99

    def test_calls_list(self):
        m = create_mock()
        m("a")
        m("b")
        calls = m.calls
        assert len(calls) == 2
        assert calls[0].args == ("a",)
        assert calls[1].args == ("b",)

    def test_mock_name(self):
        m = create_mock(name="test_fn")
        assert m.name == "test_fn"


# ---------------------------------------------------------------------------
# MockSequence
# ---------------------------------------------------------------------------


class TestMockSequence:
    def test_sequential_returns(self):
        seq = create_sequence([1, 2, 3])
        assert seq() == 1
        assert seq() == 2
        assert seq() == 3

    def test_exhausted_returns_last(self):
        seq = create_sequence([10, 20])
        seq()
        seq()
        assert seq() == 20  # repeats last
        assert seq() == 20

    def test_call_count(self):
        seq = create_sequence(["a", "b"])
        seq()
        seq()
        assert seq.call_count == 2

    def test_reset(self):
        seq = create_sequence([1, 2, 3])
        seq()
        seq()
        seq.reset()
        assert seq() == 1
        assert seq.call_count == 1

    def test_empty_sequence(self):
        seq = create_sequence([])
        assert seq() is None


# ---------------------------------------------------------------------------
# Sample data generators
# ---------------------------------------------------------------------------


class TestSampleData:
    def test_sample_markdown_default(self):
        md = sample_markdown()
        assert "# Test Report" in md
        assert "## Section 1" in md
        assert "## Section 2" in md
        assert "## Section 3" in md

    def test_sample_markdown_custom(self):
        md = sample_markdown(title="Custom", sections=2, paragraphs_per_section=1)
        assert "# Custom" in md
        assert "## Section 2" in md
        assert "## Section 3" not in md

    def test_sample_research_data(self):
        data = sample_research_data(topic="AI", sources=5)
        assert data["topic"] == "AI"
        assert len(data["sources"]) == 5
        assert "AI" in data["summary"]
        assert "timestamp" in data

    def test_sample_research_source_fields(self):
        data = sample_research_data()
        s = data["sources"][0]
        assert "title" in s
        assert "url" in s
        assert "snippet" in s
        assert "credibility" in s

    def test_sample_config(self):
        cfg = sample_config()
        assert cfg["provider"] == "openai"
        assert cfg["model"] == "gpt-4"
        assert "max_tokens" in cfg

    def test_sample_config_custom(self):
        cfg = sample_config(provider="anthropic", model="claude-3")
        assert cfg["provider"] == "anthropic"
        assert cfg["model"] == "claude-3"


# ---------------------------------------------------------------------------
# Assertion helpers
# ---------------------------------------------------------------------------


class TestAssertionHelpers:
    def test_markdown_valid(self):
        md = "# Title\n\n## Section\n\nParagraph."
        issues = assert_markdown_valid(md)
        assert issues == []

    def test_markdown_no_title(self):
        issues = assert_markdown_valid("Some text without heading")
        assert any("No top-level heading" in i for i in issues)

    def test_markdown_empty(self):
        issues = assert_markdown_valid("")
        assert any("empty" in i.lower() for i in issues)

    def test_markdown_heading_jump(self):
        md = "# Title\n\n### Level 3"
        issues = assert_markdown_valid(md)
        assert any("jump" in i.lower() for i in issues)

    def test_markdown_unclosed_fence(self):
        md = "# Title\n\n```python\ncode"
        issues = assert_markdown_valid(md)
        assert any("fence" in i.lower() for i in issues)

    def test_contains_all_pass(self):
        missing = assert_contains_all("hello world", ["hello", "world"])
        assert missing == []

    def test_contains_all_missing(self):
        missing = assert_contains_all("hello", ["hello", "world"])
        assert missing == ["world"]

    def test_json_valid(self):
        assert assert_json_valid('{"key": "value"}') is True
        assert assert_json_valid("not json") is False

    def test_word_count_range(self):
        text = "one two three four five"
        assert assert_word_count_range(text, 3, 10) is True
        assert assert_word_count_range(text, 10, 20) is False

    def test_no_duplicates(self):
        assert assert_no_duplicates([1, 2, 3]) == []
        dups = assert_no_duplicates([1, 2, 2, 3, 3])
        assert 2 in dups
        assert 3 in dups


# ---------------------------------------------------------------------------
# Snapshot testing
# ---------------------------------------------------------------------------


class TestSnapshotStore:
    def test_save_and_get(self):
        store = create_snapshot_store()
        store.save("test1", "hello world")
        snap = store.get("test1")
        assert snap is not None
        assert snap.content == "hello world"

    def test_get_missing(self):
        store = create_snapshot_store()
        assert store.get("nonexistent") is None

    def test_compare_match(self):
        store = create_snapshot_store()
        store.save("snap", "content A")
        diffs = store.compare("snap", "content A")
        assert diffs == []

    def test_compare_mismatch(self):
        store = create_snapshot_store()
        store.save("snap", "line1\nline2")
        diffs = store.compare("snap", "line1\nchanged")
        assert diffs is not None
        assert len(diffs) > 0

    def test_compare_no_snapshot(self):
        store = create_snapshot_store()
        assert store.compare("missing", "data") is None

    def test_update(self):
        store = create_snapshot_store()
        store.save("snap", "old")
        store.update("snap", "new")
        assert store.get("snap").content == "new"

    def test_names(self):
        store = create_snapshot_store()
        store.save("a", "1")
        store.save("b", "2")
        assert set(store.names) == {"a", "b"}

    def test_clear(self):
        store = create_snapshot_store()
        store.save("a", "1")
        store.clear()
        assert store.names == []

    def test_snapshot_hash(self):
        snap = Snapshot(name="test", content="hello")
        assert len(snap.content_hash) == 16


# ---------------------------------------------------------------------------
# Timing helpers
# ---------------------------------------------------------------------------


class TestTiming:
    def test_time_execution(self):
        def add(a, b):
            return a + b

        result = time_execution(add, 1, 2)
        assert result.result == 3
        assert result.elapsed_ms >= 0

    def test_assert_fast_pass(self):
        result = assert_fast(lambda: 42, max_ms=1000)
        assert result.result == 42

    def test_assert_fast_fail(self):
        def slow():
            time.sleep(0.05)
            return "done"

        with pytest.raises(AssertionError, match="expected"):
            assert_fast(slow, max_ms=1)

    def test_timing_result_fields(self):
        r = TimingResult(elapsed_ms=5.0, result="ok")
        assert r.elapsed_ms == 5.0
        assert r.result == "ok"
