"""Tests for deepworm.config."""

from deepworm.config import Config


def test_default_config():
    """Config should auto-detect provider."""
    config = Config.auto()
    assert config.provider in ("openai", "anthropic", "google", "ollama")
    assert config.model is not None
    assert config.depth == 2
    assert config.breadth == 4


def test_ollama_config():
    """Ollama config should work without API key."""
    config = Config(provider="ollama", api_key="ollama")
    assert config.model == "llama3.2"
    assert config.ollama_base_url == "http://localhost:11434/v1"


def test_custom_depth_breadth():
    config = Config(provider="ollama", api_key="ollama", depth=5, breadth=8)
    assert config.depth == 5
    assert config.breadth == 8


def test_default_models():
    """Each provider should have a sensible default model."""
    for provider, expected in [
        ("openai", "gpt-4o-mini"),
        ("anthropic", "claude-3-5-haiku-latest"),
        ("google", "gemini-2.0-flash"),
        ("ollama", "llama3.2"),
    ]:
        config = Config(provider=provider, api_key="test")
        assert config.model == expected, f"{provider}: got {config.model}"
