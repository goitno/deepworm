"""Research session save/resume.

Allows saving research state mid-session and resuming later.
Sessions are stored as JSON files.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class SessionMeta:
    """Session metadata."""
    topic: str
    created_at: float
    updated_at: float
    iterations_done: int
    total_sources: int
    status: str  # "in_progress", "completed", "interrupted"


def save_session(
    topic: str,
    state_data: dict[str, Any],
    path: str | Path | None = None,
    status: str = "in_progress",
) -> Path:
    """Save research session to a JSON file.

    Args:
        topic: Research topic.
        state_data: Serializable research state.
        path: Output path. Auto-generated if None.
        status: Session status.

    Returns:
        Path to saved session file.
    """
    if path is None:
        slug = _slugify(topic)[:50]
        path = Path(f".deepworm-session-{slug}.json")
    else:
        path = Path(path)

    now = time.time()
    session = {
        "meta": {
            "topic": topic,
            "created_at": state_data.get("created_at", now),
            "updated_at": now,
            "iterations_done": state_data.get("iterations_done", 0),
            "total_sources": len(state_data.get("sources", [])),
            "status": status,
        },
        "state": state_data,
    }

    path.write_text(json.dumps(session, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_session(path: str | Path) -> dict[str, Any]:
    """Load a research session from file.

    Returns:
        Dict with 'meta' and 'state' keys.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Session file not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))

    if "meta" not in data or "state" not in data:
        raise ValueError(f"Invalid session file format: {path}")

    return data


def list_sessions(directory: Path | None = None) -> list[SessionMeta]:
    """List available session files in a directory.

    Args:
        directory: Directory to search. Defaults to CWD.

    Returns:
        List of SessionMeta objects.
    """
    if directory is None:
        directory = Path.cwd()

    sessions = []
    for f in sorted(directory.glob(".deepworm-session-*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            meta = data.get("meta", {})
            sessions.append(SessionMeta(
                topic=meta.get("topic", "unknown"),
                created_at=meta.get("created_at", 0),
                updated_at=meta.get("updated_at", 0),
                iterations_done=meta.get("iterations_done", 0),
                total_sources=meta.get("total_sources", 0),
                status=meta.get("status", "unknown"),
            ))
        except (json.JSONDecodeError, KeyError):
            continue

    return sessions


def _slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    import re
    slug = text.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug
