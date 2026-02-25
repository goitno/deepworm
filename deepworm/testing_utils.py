"""Testing utilities for deepworm.

Provides test fixtures, mock builders, assertion helpers, and snapshot testing
to make writing tests for deepworm-based applications easier.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class AssertionMode(Enum):
    """Assertion comparison mode."""

    EXACT = "exact"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"
    APPROXIMATE = "approximate"


@dataclass
class TestFixture:
    """Test fixture with setup/teardown lifecycle."""

    name: str
    data: Dict[str, Any] = field(default_factory=dict)
    _setup_fn: Optional[Callable] = field(default=None, repr=False)
    _teardown_fn: Optional[Callable] = field(default=None, repr=False)
    _is_setup: bool = False

    def setup(self) -> None:
        if self._setup_fn and not self._is_setup:
            self._setup_fn(self.data)
            self._is_setup = True

    def teardown(self) -> None:
        if self._teardown_fn and self._is_setup:
            self._teardown_fn(self.data)
            self._is_setup = False

    def __enter__(self) -> "TestFixture":
        self.setup()
        return self

    def __exit__(self, *args: Any) -> None:
        self.teardown()


def create_fixture(
    name: str,
    data: Optional[Dict[str, Any]] = None,
    setup: Optional[Callable] = None,
    teardown: Optional[Callable] = None,
) -> TestFixture:
    """Create a test fixture with optional setup/teardown."""
    return TestFixture(
        name=name,
        data=data or {},
        _setup_fn=setup,
        _teardown_fn=teardown,
    )


# ---------------------------------------------------------------------------
# Mock builders
# ---------------------------------------------------------------------------


@dataclass
class MockCall:
    """Record of a mock function call."""

    args: tuple
    kwargs: dict
    timestamp: float = field(default_factory=time.time)
    return_value: Any = None


class MockFunction:
    """A mock function that records calls and returns configurable values."""

    def __init__(
        self,
        return_value: Any = None,
        side_effect: Optional[Callable] = None,
        name: str = "mock",
    ) -> None:
        self._return_value = return_value
        self._side_effect = side_effect
        self._calls: List[MockCall] = []
        self.name = name

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if self._side_effect:
            result = self._side_effect(*args, **kwargs)
        else:
            result = self._return_value

        call = MockCall(args=args, kwargs=kwargs, return_value=result)
        self._calls.append(call)
        return result

    @property
    def calls(self) -> List[MockCall]:
        return list(self._calls)

    @property
    def call_count(self) -> int:
        return len(self._calls)

    @property
    def called(self) -> bool:
        return len(self._calls) > 0

    @property
    def last_call(self) -> Optional[MockCall]:
        return self._calls[-1] if self._calls else None

    def called_with(self, *args: Any, **kwargs: Any) -> bool:
        """Check if mock was ever called with specific args."""
        for call in self._calls:
            if call.args == args and call.kwargs == kwargs:
                return True
        return False

    def reset(self) -> None:
        self._calls.clear()

    def set_return(self, value: Any) -> None:
        self._return_value = value

    def set_side_effect(self, fn: Callable) -> None:
        self._side_effect = fn


class MockSequence:
    """Returns different values on successive calls."""

    def __init__(self, values: List[Any]) -> None:
        self._values = list(values)
        self._index = 0
        self._calls: List[MockCall] = []

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if self._index < len(self._values):
            result = self._values[self._index]
            self._index += 1
        else:
            result = self._values[-1] if self._values else None

        self._calls.append(MockCall(args=args, kwargs=kwargs, return_value=result))
        return result

    @property
    def call_count(self) -> int:
        return len(self._calls)

    def reset(self) -> None:
        self._index = 0
        self._calls.clear()


def create_mock(
    return_value: Any = None,
    side_effect: Optional[Callable] = None,
    name: str = "mock",
) -> MockFunction:
    """Create a mock function."""
    return MockFunction(return_value=return_value, side_effect=side_effect, name=name)


def create_sequence(values: List[Any]) -> MockSequence:
    """Create a mock that returns values sequentially."""
    return MockSequence(values)


# ---------------------------------------------------------------------------
# Sample data generators
# ---------------------------------------------------------------------------


def sample_markdown(
    *,
    title: str = "Test Report",
    sections: int = 3,
    paragraphs_per_section: int = 2,
) -> str:
    """Generate sample markdown for testing."""
    lines = [f"# {title}", ""]

    for i in range(1, sections + 1):
        lines.append(f"## Section {i}")
        lines.append("")
        for j in range(paragraphs_per_section):
            lines.append(
                f"This is paragraph {j + 1} of section {i}. "
                f"It contains sample text for testing purposes. "
                f"The content is generated automatically."
            )
            lines.append("")

    return "\n".join(lines)


def sample_research_data(
    *,
    topic: str = "Test Topic",
    sources: int = 3,
) -> Dict[str, Any]:
    """Generate sample research data for testing."""
    source_list = []
    for i in range(sources):
        source_list.append({
            "title": f"Source {i + 1}: {topic}",
            "url": f"https://example.com/source-{i + 1}",
            "snippet": f"This is a snippet about {topic} from source {i + 1}.",
            "credibility": 0.8 - (i * 0.1),
        })

    return {
        "topic": topic,
        "sources": source_list,
        "summary": f"Research summary for {topic}.",
        "timestamp": time.time(),
    }


def sample_config(
    *,
    provider: str = "openai",
    model: str = "gpt-4",
) -> Dict[str, Any]:
    """Generate sample config for testing."""
    return {
        "provider": provider,
        "model": model,
        "max_tokens": 4096,
        "temperature": 0.7,
        "search_engine": "duckduckgo",
        "max_search_results": 10,
        "language": "en",
        "output_format": "markdown",
    }


# ---------------------------------------------------------------------------
# Assertion helpers
# ---------------------------------------------------------------------------


def assert_markdown_valid(text: str) -> List[str]:
    """Validate markdown structure and return list of issues."""
    issues = []
    lines = text.split("\n")

    if not text.strip():
        issues.append("Document is empty")
        return issues

    # Check for title
    has_title = any(l.startswith("# ") for l in lines)
    if not has_title:
        issues.append("No top-level heading (# ) found")

    # Check heading hierarchy
    levels = []
    for line in lines:
        if line.startswith("#"):
            level = len(line.split()[0]) if line.split() else 0
            if levels and level > levels[-1] + 1:
                issues.append(f"Heading level jump: h{levels[-1]} to h{level}")
            levels.append(level)

    # Check for unclosed code fences
    fence_count = sum(1 for l in lines if l.strip().startswith("```"))
    if fence_count % 2 != 0:
        issues.append("Unclosed code fence")

    return issues


def assert_contains_all(text: str, substrings: List[str]) -> List[str]:
    """Check that text contains all substrings. Returns missing ones."""
    return [s for s in substrings if s not in text]


def assert_json_valid(text: str) -> bool:
    """Check if text is valid JSON."""
    try:
        json.loads(text)
        return True
    except (json.JSONDecodeError, TypeError):
        return False


def assert_word_count_range(
    text: str,
    min_words: int = 0,
    max_words: int = 100000,
) -> bool:
    """Check if word count is within range."""
    count = len(text.split())
    return min_words <= count <= max_words


def assert_no_duplicates(items: List[Any]) -> List[Any]:
    """Check for duplicates. Returns list of duplicated items."""
    seen = set()
    duplicates = []
    for item in items:
        key = str(item)
        if key in seen:
            duplicates.append(item)
        seen.add(key)
    return duplicates


# ---------------------------------------------------------------------------
# Snapshot testing
# ---------------------------------------------------------------------------


@dataclass
class Snapshot:
    """A snapshot for comparison testing."""

    name: str
    content: str
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = hashlib.sha256(
                self.content.encode("utf-8"),
            ).hexdigest()[:16]


class SnapshotStore:
    """In-memory snapshot store for comparison testing."""

    def __init__(self) -> None:
        self._snapshots: Dict[str, Snapshot] = {}

    def save(self, name: str, content: str) -> Snapshot:
        snap = Snapshot(name=name, content=content)
        self._snapshots[name] = snap
        return snap

    def get(self, name: str) -> Optional[Snapshot]:
        return self._snapshots.get(name)

    def compare(self, name: str, content: str) -> Optional[List[str]]:
        """Compare content against stored snapshot.

        Returns None if no snapshot exists, empty list if match,
        or list of differences if changed.
        """
        snap = self._snapshots.get(name)
        if snap is None:
            return None

        if snap.content == content:
            return []

        # Simple diff
        old_lines = snap.content.split("\n")
        new_lines = content.split("\n")
        diffs = []

        max_lines = max(len(old_lines), len(new_lines))
        for i in range(max_lines):
            old = old_lines[i] if i < len(old_lines) else "<missing>"
            new = new_lines[i] if i < len(new_lines) else "<missing>"
            if old != new:
                diffs.append(f"Line {i + 1}: '{old}' -> '{new}'")

        return diffs

    def update(self, name: str, content: str) -> Snapshot:
        """Update or create a snapshot."""
        return self.save(name, content)

    @property
    def names(self) -> List[str]:
        return list(self._snapshots.keys())

    def clear(self) -> None:
        self._snapshots.clear()


def create_snapshot_store() -> SnapshotStore:
    """Create a new snapshot store."""
    return SnapshotStore()


# ---------------------------------------------------------------------------
# Timing helpers
# ---------------------------------------------------------------------------


@dataclass
class TimingResult:
    """Result of a timed execution."""

    elapsed_ms: float
    result: Any = None


def time_execution(func: Callable, *args: Any, **kwargs: Any) -> TimingResult:
    """Time a function execution."""
    start = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = (time.perf_counter() - start) * 1000
    return TimingResult(elapsed_ms=elapsed, result=result)


def assert_fast(
    func: Callable,
    *args: Any,
    max_ms: float = 100,
    **kwargs: Any,
) -> TimingResult:
    """Assert that a function executes within a time limit."""
    timing = time_execution(func, *args, **kwargs)
    if timing.elapsed_ms > max_ms:
        raise AssertionError(
            f"Function took {timing.elapsed_ms:.2f}ms, "
            f"expected < {max_ms}ms"
        )
    return timing
