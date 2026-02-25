"""Configuration for DeepWorm."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


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

    # Ollama settings
    @property
    def ollama_base_url(self) -> str:
        return self.base_url or "http://localhost:11434/v1"

    @classmethod
    def auto(cls) -> "Config":
        """Create a Config with auto-detected settings."""
        return cls()
