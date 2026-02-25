"""Configuration for DeepWorm."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# Config file names to search for (in order of priority)
CONFIG_FILES = [
    "deepworm.toml",
    ".deepworm.toml",
    "pyproject.toml",  # [tool.deepworm] section
]


@dataclass
class Config:
    """Research configuration."""

    # LLM settings
    provider: str = "openai"
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.1

    # Research settings
    depth: int = 2
    breadth: int = 4
    max_sources: int = 10

    # Output settings
    output_format: str = "markdown"
    output_file: Optional[str] = None
    verbose: bool = False

    # Search settings
    search_region: str = "wt-wt"
    search_max_results: int = 8

    def __post_init__(self):
        if self.api_key is None:
            self._detect_provider()

        if self.model is None:
            self.model = self._default_model()

    def _detect_provider(self):
        """Auto-detect provider from environment variables."""
        if os.getenv("OPENAI_API_KEY"):
            self.provider = "openai"
            self.api_key = os.getenv("OPENAI_API_KEY")
        elif os.getenv("ANTHROPIC_API_KEY"):
            self.provider = "anthropic"
            self.api_key = os.getenv("ANTHROPIC_API_KEY")
        elif os.getenv("GOOGLE_API_KEY"):
            self.provider = "google"
            self.api_key = os.getenv("GOOGLE_API_KEY")
        else:
            # Default to Ollama (local, no API key needed)
            self.provider = "ollama"
            self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
            self.api_key = "ollama"

    def _default_model(self, provider: str | None = None) -> str:
        """Return default model for the provider."""
        defaults = {
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-5-haiku-latest",
            "google": "gemini-2.0-flash",
            "ollama": "llama3.2",
        }
        return defaults.get(provider or self.provider, "gpt-4o-mini")

    @property
    def ollama_base_url(self) -> str:
        return self.base_url or "http://localhost:11434/v1"

    @classmethod
    def auto(cls) -> "Config":
        """Create a Config with auto-detected settings, loading from config file if available."""
        file_config = _load_config_file()
        if file_config:
            return cls(**file_config)
        return cls()

    @classmethod
    def from_file(cls, path: str) -> "Config":
        """Load config from a specific TOML file."""
        data = _parse_toml_file(Path(path))
        if data is None:
            raise FileNotFoundError(f"Config file not found: {path}")
        return cls(**data)


def _load_config_file() -> dict[str, Any] | None:
    """Search for and load a config file from CWD up to root."""
    cwd = Path.cwd()

    for directory in [cwd, *cwd.parents]:
        for filename in CONFIG_FILES:
            filepath = directory / filename
            if filepath.exists():
                return _parse_toml_file(filepath)
    return None


def _parse_toml_file(path: Path) -> dict[str, Any] | None:
    """Parse a TOML config file and extract deepworm settings."""
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            # Python < 3.11 without tomli installed
            return None

    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        return None

    # Check for [tool.deepworm] in pyproject.toml
    if path.name == "pyproject.toml":
        data = data.get("tool", {}).get("deepworm", {})
        if not data:
            return None

    # Filter to only valid Config fields
    valid_fields = {f.name for f in Config.__dataclass_fields__.values()}
    return {k: v for k, v in data.items() if k in valid_fields} or None
