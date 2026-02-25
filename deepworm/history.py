"""Persistent research history.

Stores a log of all completed research with metadata, searchable and
exportable.  History entries are appended to a single JSON-Lines file
(``~/.deepworm/history.jsonl`` by default).
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional


DEFAULT_HISTORY_DIR = Path.home() / ".deepworm"
DEFAULT_HISTORY_FILE = DEFAULT_HISTORY_DIR / "history.jsonl"


@dataclass
class HistoryEntry:
    """A single research history record."""

    topic: str
    created_at: float
    elapsed_seconds: float
    model: str
    provider: str
    depth: int
    breadth: int
    total_sources: int
    report_length: int
    persona: str | None = None
    output_file: str | None = None
    tags: list[str] = field(default_factory=list)
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = _make_id(self.topic, self.created_at)

    @property
    def created_iso(self) -> str:
        """ISO-8601 formatted creation time."""
        import datetime as _dt

        return _dt.datetime.fromtimestamp(self.created_at, tz=_dt.timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HistoryEntry":
        # Filter out unknown fields for forward compatibility
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


def _make_id(topic: str, ts: float) -> str:
    """Deterministic short ID from topic + timestamp."""
    import hashlib

    raw = f"{topic}:{ts}".encode()
    return hashlib.sha256(raw).hexdigest()[:12]


# ── Public API ─────────────────────────────────────────────────


def add_entry(
    topic: str,
    elapsed: float,
    model: str,
    provider: str,
    depth: int,
    breadth: int,
    total_sources: int,
    report_length: int,
    persona: str | None = None,
    output_file: str | None = None,
    tags: list[str] | None = None,
    history_file: Path | None = None,
) -> HistoryEntry:
    """Append a research record to the history file.

    Returns the newly created :class:`HistoryEntry`.
    """
    entry = HistoryEntry(
        topic=topic,
        created_at=time.time(),
        elapsed_seconds=elapsed,
        model=model,
        provider=provider,
        depth=depth,
        breadth=breadth,
        total_sources=total_sources,
        report_length=report_length,
        persona=persona,
        output_file=output_file,
        tags=tags or [],
    )

    path = history_file or DEFAULT_HISTORY_FILE
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")

    return entry


def list_entries(
    history_file: Path | None = None,
    limit: int | None = None,
) -> list[HistoryEntry]:
    """Return all history entries, newest first.

    Args:
        history_file: Path to history JSONL file.
        limit: Maximum entries to return (``None`` = all).
    """
    path = history_file or DEFAULT_HISTORY_FILE
    if not path.exists():
        return []

    entries: list[HistoryEntry] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(HistoryEntry.from_dict(json.loads(line)))
        except (json.JSONDecodeError, TypeError):
            continue

    entries.sort(key=lambda e: e.created_at, reverse=True)

    if limit is not None:
        entries = entries[:limit]

    return entries


def search_history(
    query: str,
    history_file: Path | None = None,
) -> list[HistoryEntry]:
    """Search history entries by topic text (case-insensitive substring)."""
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    return [
        e
        for e in list_entries(history_file=history_file)
        if pattern.search(e.topic)
    ]


def get_entry(entry_id: str, history_file: Path | None = None) -> HistoryEntry | None:
    """Retrieve a single entry by its ID prefix."""
    for entry in list_entries(history_file=history_file):
        if entry.id.startswith(entry_id):
            return entry
    return None


def delete_entry(entry_id: str, history_file: Path | None = None) -> bool:
    """Delete a single entry by ID. Returns True if found and deleted."""
    path = history_file or DEFAULT_HISTORY_FILE
    if not path.exists():
        return False

    lines = path.read_text(encoding="utf-8").splitlines()
    new_lines: list[str] = []
    found = False

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            eid = data.get("id", "")
            if eid.startswith(entry_id):
                found = True
                continue  # skip this line
        except json.JSONDecodeError:
            pass
        new_lines.append(line)

    if found:
        path.write_text("\n".join(new_lines) + ("\n" if new_lines else ""), encoding="utf-8")

    return found


def clear_history(history_file: Path | None = None) -> int:
    """Remove all history entries. Returns count of deleted entries."""
    path = history_file or DEFAULT_HISTORY_FILE
    if not path.exists():
        return 0
    count = len(list_entries(history_file=path))
    path.unlink()
    return count


def stats(history_file: Path | None = None) -> dict[str, Any]:
    """Aggregate statistics over all history entries."""
    entries = list_entries(history_file=history_file)
    if not entries:
        return {
            "total_researches": 0,
            "total_sources": 0,
            "total_time_seconds": 0.0,
            "avg_time_seconds": 0.0,
            "avg_sources": 0.0,
            "models_used": [],
            "providers_used": [],
        }

    total_time = sum(e.elapsed_seconds for e in entries)
    total_sources = sum(e.total_sources for e in entries)
    models = sorted({e.model for e in entries})
    providers = sorted({e.provider for e in entries})

    return {
        "total_researches": len(entries),
        "total_sources": total_sources,
        "total_time_seconds": round(total_time, 1),
        "avg_time_seconds": round(total_time / len(entries), 1),
        "avg_sources": round(total_sources / len(entries), 1),
        "models_used": models,
        "providers_used": providers,
    }
