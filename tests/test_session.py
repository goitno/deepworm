"""Tests for deepworm.session."""

import json
import time

from deepworm.session import list_sessions, load_session, save_session


def test_save_and_load(tmp_path):
    """Should save and load a session."""
    state = {
        "topic": "test research",
        "queries": ["q1", "q2"],
        "sources": [{"url": "https://example.com", "title": "Example", "findings": "f"}],
        "findings": ["finding 1"],
        "iterations_done": 1,
    }
    path = save_session("test research", state, path=tmp_path / "session.json")
    loaded = load_session(path)
    assert loaded["meta"]["topic"] == "test research"
    assert loaded["meta"]["status"] == "in_progress"
    assert loaded["state"]["queries"] == ["q1", "q2"]
    assert len(loaded["state"]["sources"]) == 1


def test_save_auto_path(tmp_path, monkeypatch):
    """Should auto-generate filename from topic."""
    monkeypatch.chdir(tmp_path)
    state = {"topic": "Python Web Scraping", "iterations_done": 2, "sources": []}
    path = save_session("Python Web Scraping", state)
    assert path.name.startswith(".deepworm-session-")
    assert path.exists()


def test_load_not_found():
    """Should raise FileNotFoundError."""
    try:
        load_session("/nonexistent/session.json")
        assert False, "Should have raised"
    except FileNotFoundError:
        pass


def test_list_sessions(tmp_path):
    """Should list session files."""
    for i in range(3):
        state = {"topic": f"topic {i}", "iterations_done": i, "sources": [{"a": 1}] * i}
        save_session(f"topic {i}", state, path=tmp_path / f".deepworm-session-topic-{i}.json")

    sessions = list_sessions(tmp_path)
    assert len(sessions) == 3
    assert sessions[0].topic == "topic 0"
    assert sessions[2].total_sources == 2


def test_session_status_update(tmp_path):
    """Should update status on re-save."""
    state = {"topic": "test", "iterations_done": 1, "sources": []}
    path = tmp_path / "session.json"
    save_session("test", state, path=path, status="in_progress")
    save_session("test", state, path=path, status="completed")
    loaded = load_session(path)
    assert loaded["meta"]["status"] == "completed"
