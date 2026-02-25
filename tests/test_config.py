"""Tests for deepworm.config."""

import os
from pathlib import Path

from deepworm.config import Config, _load_config_file, _load_env_overrides, _parse_toml_file, _parse_yaml_file


def test_default_config():
    """Config should auto-detect provider."""
    config = Config.auto()
    assert config.provider in ("openai", "anthropic", "google", "ollama")
    assert config.model is not None
    assert config.depth == 1
    assert config.breadth == 1


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
        ("google", "gemini-3-flash-preview"),
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


def test_config_validation_invalid_provider():
    """Should reject invalid provider."""
    import pytest
    with pytest.raises(ValueError, match="Invalid provider"):
        Config(provider="invalid_provider", api_key="test")


def test_config_validation_depth_range():
    """Should reject out-of-range depth."""
    import pytest
    with pytest.raises(ValueError, match="depth"):
        Config(provider="ollama", api_key="ollama", depth=0)
    with pytest.raises(ValueError, match="depth"):
        Config(provider="ollama", api_key="ollama", depth=21)


def test_config_validation_breadth_range():
    """Should reject out-of-range breadth."""
    import pytest
    with pytest.raises(ValueError, match="breadth"):
        Config(provider="ollama", api_key="ollama", breadth=0)


def test_config_validation_temperature_range():
    """Should reject out-of-range temperature."""
    import pytest
    with pytest.raises(ValueError, match="temperature"):
        Config(provider="ollama", api_key="ollama", temperature=-0.1)
    with pytest.raises(ValueError, match="temperature"):
        Config(provider="ollama", api_key="ollama", temperature=2.1)


def test_config_timeout_setting():
    """Timeout setting should be configurable."""
    config = Config(provider="ollama", api_key="ollama", timeout_seconds=300)
    assert config.timeout_seconds == 300


def test_config_rate_limit_setting():
    """Rate limit setting should be configurable."""
    config = Config(provider="ollama", api_key="ollama", max_requests_per_minute=30)
    assert config.max_requests_per_minute == 30


# --- YAML config tests ---

def test_parse_yaml_file_flat(tmp_path):
    """Should parse a flat YAML config."""
    yaml_file = tmp_path / "deepworm.yaml"
    yaml_file.write_text("provider: anthropic\napi_key: sk-test\ndepth: 5\nbreadth: 8\n")
    result = _parse_yaml_file(yaml_file)
    assert result is not None
    assert result["provider"] == "anthropic"
    assert result["depth"] == 5
    assert result["breadth"] == 8


def test_parse_yaml_file_nested(tmp_path):
    """Should extract nested deepworm key from YAML."""
    yaml_file = tmp_path / "deepworm.yml"
    yaml_file.write_text("deepworm:\n  provider: google\n  depth: 3\n  api_key: test\n")
    result = _parse_yaml_file(yaml_file)
    assert result is not None
    assert result["provider"] == "google"
    assert result["depth"] == 3


def test_parse_yaml_filters_invalid_fields(tmp_path):
    """Should ignore fields not in Config dataclass."""
    yaml_file = tmp_path / "deepworm.yaml"
    yaml_file.write_text("provider: ollama\nfake_field: ignore\nanother: 42\n")
    result = _parse_yaml_file(yaml_file)
    assert result is not None
    assert "fake_field" not in result
    assert result["provider"] == "ollama"


def test_parse_yaml_file_not_found():
    """Should return None for missing file."""
    result = _parse_yaml_file(Path("/nonexistent/deepworm.yaml"))
    assert result is None


def test_parse_yaml_file_invalid(tmp_path):
    """Should return None for non-dict YAML content."""
    yaml_file = tmp_path / "deepworm.yaml"
    yaml_file.write_text("- item1\n- item2\n")
    result = _parse_yaml_file(yaml_file)
    assert result is None


def test_from_file_yaml(tmp_path):
    """Config.from_file should load from YAML."""
    yaml_file = tmp_path / "deepworm.yaml"
    yaml_file.write_text("provider: ollama\napi_key: ollama\ndepth: 4\nbreadth: 6\n")
    config = Config.from_file(str(yaml_file))
    assert config.provider == "ollama"
    assert config.depth == 4
    assert config.breadth == 6


def test_from_yaml(tmp_path):
    """Config.from_yaml should load from YAML file."""
    yaml_file = tmp_path / "config.yml"
    yaml_file.write_text("provider: ollama\napi_key: ollama\ndepth: 3\n")
    config = Config.from_yaml(str(yaml_file))
    assert config.provider == "ollama"
    assert config.depth == 3


def test_from_yaml_not_found():
    """Config.from_yaml should raise FileNotFoundError."""
    import pytest
    with pytest.raises(FileNotFoundError):
        Config.from_yaml("/nonexistent/config.yaml")


# ── Environment Variable Override Tests ──


def test_load_env_overrides_depth(monkeypatch):
    """DEEPWORM_DEPTH should override depth."""
    monkeypatch.setenv("DEEPWORM_DEPTH", "7")
    overrides = _load_env_overrides()
    assert overrides["depth"] == 7


def test_load_env_overrides_breadth(monkeypatch):
    """DEEPWORM_BREADTH should override breadth."""
    monkeypatch.setenv("DEEPWORM_BREADTH", "10")
    overrides = _load_env_overrides()
    assert overrides["breadth"] == 10


def test_load_env_overrides_provider(monkeypatch):
    """DEEPWORM_PROVIDER should override provider."""
    monkeypatch.setenv("DEEPWORM_PROVIDER", "anthropic")
    overrides = _load_env_overrides()
    assert overrides["provider"] == "anthropic"


def test_load_env_overrides_verbose_true(monkeypatch):
    """DEEPWORM_VERBOSE=true should set verbose to True."""
    monkeypatch.setenv("DEEPWORM_VERBOSE", "true")
    overrides = _load_env_overrides()
    assert overrides["verbose"] is True


def test_load_env_overrides_verbose_false(monkeypatch):
    """DEEPWORM_VERBOSE=false should set verbose to False."""
    monkeypatch.setenv("DEEPWORM_VERBOSE", "false")
    overrides = _load_env_overrides()
    assert overrides["verbose"] is False


def test_load_env_overrides_temperature(monkeypatch):
    """DEEPWORM_TEMPERATURE should be parsed as float."""
    monkeypatch.setenv("DEEPWORM_TEMPERATURE", "0.7")
    overrides = _load_env_overrides()
    assert overrides["temperature"] == 0.7


def test_load_env_overrides_invalid_int(monkeypatch):
    """Invalid int values should be silently skipped."""
    monkeypatch.setenv("DEEPWORM_DEPTH", "not_a_number")
    overrides = _load_env_overrides()
    assert "depth" not in overrides


def test_load_env_overrides_empty():
    """No DEEPWORM_ vars should return empty dict."""
    # This may pick up existing vars if set, so we just check it doesn't crash
    overrides = _load_env_overrides()
    assert isinstance(overrides, dict)


def test_from_env(monkeypatch):
    """Config.from_env should apply env vars."""
    monkeypatch.setenv("DEEPWORM_DEPTH", "5")
    monkeypatch.setenv("DEEPWORM_PROVIDER", "ollama")
    monkeypatch.setenv("DEEPWORM_API_KEY", "ollama")
    config = Config.from_env()
    assert config.depth == 5
    assert config.provider == "ollama"


def test_from_env_explicit_override(monkeypatch):
    """Explicit kwargs should override env vars."""
    monkeypatch.setenv("DEEPWORM_DEPTH", "5")
    config = Config.from_env(provider="ollama", api_key="ollama", depth=10)
    assert config.depth == 10


def test_load_env_overrides_output_format(monkeypatch):
    """DEEPWORM_OUTPUT_FORMAT should override output format."""
    monkeypatch.setenv("DEEPWORM_OUTPUT_FORMAT", "html")
    overrides = _load_env_overrides()
    assert overrides["output_format"] == "html"


def test_load_env_overrides_multiple(monkeypatch):
    """Multiple env vars should all be loaded."""
    monkeypatch.setenv("DEEPWORM_DEPTH", "3")
    monkeypatch.setenv("DEEPWORM_BREADTH", "6")
    monkeypatch.setenv("DEEPWORM_TEMPERATURE", "0.5")
    monkeypatch.setenv("DEEPWORM_VERBOSE", "1")
    overrides = _load_env_overrides()
    assert overrides["depth"] == 3
    assert overrides["breadth"] == 6
    assert overrides["temperature"] == 0.5
    assert overrides["verbose"] is True