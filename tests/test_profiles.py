"""Tests for deepworm.profiles."""

import json

import pytest

from deepworm.config import Config
from deepworm.profiles import (
    _profile_path,
    delete_profile,
    list_profiles,
    load_profile,
    save_profile,
)


@pytest.fixture(autouse=True)
def tmp_profiles_dir(tmp_path, monkeypatch):
    """Use a temporary directory for profiles in all tests."""
    import deepworm.profiles as profiles_mod
    monkeypatch.setattr(profiles_mod, "PROFILES_DIR", tmp_path)
    return tmp_path


def test_save_and_load_profile():
    """Can save and load a profile."""
    config = Config(provider="openai", model="gpt-4o", depth=3, breadth=6, api_key="test-key")
    # Manually set provider since auto-detect may override
    config.provider = "openai"
    config.model = "gpt-4o"
    save_profile("test1", config)
    loaded = load_profile("test1")
    assert loaded is not None
    assert loaded.provider == "openai"
    assert loaded.model == "gpt-4o"
    assert loaded.depth == 3
    assert loaded.breadth == 6


def test_save_profile_excludes_api_key():
    """API keys are never stored in profiles."""
    config = Config(provider="openai", model="gpt-4o", api_key="sk-secret")
    path = save_profile("secret-test", config)
    with open(path) as f:
        data = json.load(f)
    assert "api_key" not in data
    # Loading should use auto-detected key, not stored one
    loaded = load_profile("secret-test")
    assert loaded is not None


def test_list_profiles_empty():
    """Returns empty list when no profiles exist."""
    profiles = list_profiles()
    assert profiles == []


def test_list_profiles_with_entries():
    """List returns all saved profiles."""
    save_profile("p1", Config(provider="openai", model="gpt-4o", depth=2))
    save_profile("p2", Config(provider="anthropic", model="claude-3-5-haiku-latest", depth=4))
    profiles = list_profiles()
    assert len(profiles) == 2
    names = [p["name"] for p in profiles]
    assert "p1" in names
    assert "p2" in names


def test_delete_profile():
    """Can delete a saved profile."""
    save_profile("to-delete", Config())
    assert delete_profile("to-delete") is True
    assert load_profile("to-delete") is None


def test_delete_nonexistent_profile():
    """Delete returns False for missing profile."""
    assert delete_profile("nonexistent") is False


def test_load_nonexistent_profile():
    """Load returns None for missing profile."""
    assert load_profile("nonexistent") is None


def test_save_profile_overwrites():
    """Saving with same name overwrites."""
    save_profile("overwrite", Config(depth=2))
    save_profile("overwrite", Config(depth=5))
    loaded = load_profile("overwrite")
    assert loaded is not None
    assert loaded.depth == 5


def test_profile_name_sanitization():
    """Profile names are sanitized."""
    path = _profile_path("my-profile_1")
    assert path.name == "my-profile_1.json"
