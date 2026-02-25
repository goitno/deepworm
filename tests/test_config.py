"""Tests for deepworm.config."""

import os
from pathlib import Path

from deepworm.config import Config, _load_config_file, _parse_toml_file


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


def test_parse_toml_file_deepworm(tmp_path):
    """Should parse a deepworm.toml config file."""
    toml_file = tmp_path / "deepworm.toml"
    toml_file.write_text(
        'provider = "anthropic"\napi_key = "sk-test"\ndepth = 5\nbreadth = 8\n'
    )
    result = _parse_toml_file(toml_file)
    assert result is not None
    assert result["provider"] == "anthropic"
    assert result["depth"] == 5
    assert result["breadth"] == 8


def test_parse_toml_file_pyproject(tmp_path):
    """Should extract [tool.deepworm] from pyproject.toml."""
    toml_file = tmp_path / "pyproject.toml"
    toml_file.write_text(
        '[project]\nname = "myproject"\n\n'
        '[tool.deepworm]\nprovider = "google"\ndepth = 3\n'
    )
    result = _parse_toml_file(toml_file)
    assert result is not None
    assert result["provider"] == "google"
    assert result["depth"] == 3


def test_parse_toml_file_pyproject_no_section(tmp_path):
    """Should return None if pyproject.toml has no [tool.deepworm]."""
    toml_file = tmp_path / "pyproject.toml"
    toml_file.write_text('[project]\nname = "myproject"\n')
    result = _parse_toml_file(toml_file)
    assert result is None


def test_parse_toml_filters_invalid_fields(tmp_path):
    """Should ignore fields not in Config dataclass."""
    toml_file = tmp_path / "deepworm.toml"
    toml_file.write_text(
        'provider = "ollama"\nfake_field = "ignore"\nanother = 42\n'
    )
    result = _parse_toml_file(toml_file)
    assert result is not None
    assert "fake_field" not in result
    assert "another" not in result
    assert result["provider"] == "ollama"


def test_from_file(tmp_path):
    """Config.from_file should load from a specific path."""
    toml_file = tmp_path / "deepworm.toml"
    toml_file.write_text(
        'provider = "ollama"\napi_key = "ollama"\ndepth = 4\nbreadth = 6\n'
    )
    config = Config.from_file(str(toml_file))
    assert config.provider == "ollama"
    assert config.depth == 4
    assert config.breadth == 6


def test_from_file_not_found():
    """Config.from_file should raise FileNotFoundError."""
    try:
        Config.from_file("/nonexistent/path/config.toml")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass


def test_config_temperature():
    """Temperature setting should be configurable."""
    config = Config(provider="ollama", api_key="ollama", temperature=0.7)
    assert config.temperature == 0.7


def test_config_search_settings():
    """Search settings should be configurable."""
    config = Config(
        provider="ollama",
        api_key="ollama",
        search_region="us-en",
        search_max_results=15,
    )
    assert config.search_region == "us-en"
    assert config.search_max_results == 15
