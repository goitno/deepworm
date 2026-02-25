"""Named configuration profiles.

Save and load named configurations for different research scenarios.
Profiles are stored as JSON in ~/.deepworm/profiles/.

Usage:
    deepworm --save-profile myconfig
    deepworm "topic" --profile myconfig
    deepworm --list-profiles
    deepworm --delete-profile myconfig
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

from .config import Config

PROFILES_DIR = Path.home() / ".deepworm" / "profiles"


def _ensure_dir() -> None:
    """Ensure profiles directory exists."""
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)


def _profile_path(name: str) -> Path:
    """Get path for a named profile."""
    # Sanitize name
    safe = "".join(c for c in name if c.isalnum() or c in "-_").strip()
    if not safe:
        raise ValueError(f"Invalid profile name: {name}")
    return PROFILES_DIR / f"{safe}.json"


def save_profile(name: str, config: Config) -> Path:
    """Save a configuration as a named profile.

    Args:
        name: Profile name (alphanumeric, hyphens, underscores).
        config: Config to save.

    Returns:
        Path to the saved profile file.
    """
    _ensure_dir()
    path = _profile_path(name)

    # Convert config to serializable dict, excluding secrets
    data = asdict(config)
    data.pop("api_key", None)  # Never store API keys in profiles
    # Remove None values
    data = {k: v for k, v in data.items() if v is not None}

    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    return path


def load_profile(name: str) -> Optional[Config]:
    """Load a named profile.

    Args:
        name: Profile name.

    Returns:
        Config from the profile, or None if not found.
    """
    path = _profile_path(name)
    if not path.exists():
        return None

    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    # Filter to valid Config fields
    valid_fields = {f.name for f in Config.__dataclass_fields__.values()}
    filtered = {k: v for k, v in data.items() if k in valid_fields}

    # Create config bypassing __post_init__ auto-detection by providing
    # provider explicitly. The profile values override auto-detected ones.
    config = Config.__new__(Config)
    # Set defaults from dataclass
    defaults = {f.name: f.default for f in Config.__dataclass_fields__.values()
                if f.default is not dataclasses.MISSING}
    for k, v in defaults.items():
        setattr(config, k, v)
    # Apply profile overrides
    for k, v in filtered.items():
        setattr(config, k, v)
    return config


def list_profiles() -> list[dict[str, Any]]:
    """List all saved profiles.

    Returns:
        List of dicts with 'name', 'provider', 'model', 'depth', 'breadth' keys.
    """
    _ensure_dir()
    profiles = []
    for path in sorted(PROFILES_DIR.glob("*.json")):
        try:
            with open(path) as f:
                data = json.load(f)
            profiles.append({
                "name": path.stem,
                "provider": data.get("provider", "?"),
                "model": data.get("model", "?"),
                "depth": data.get("depth", 2),
                "breadth": data.get("breadth", 4),
            })
        except (json.JSONDecodeError, OSError):
            continue
    return profiles


def delete_profile(name: str) -> bool:
    """Delete a named profile.

    Returns:
        True if deleted, False if not found.
    """
    path = _profile_path(name)
    if path.exists():
        path.unlink()
        return True
    return False
