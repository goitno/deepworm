# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- TOML config file support (`deepworm.toml`, `.deepworm.toml`, `pyproject.toml [tool.deepworm]`)
- Cache layer for search results and LLM responses

## [0.1.0] - 2025-01-20

### Added
- Initial release
- Core research engine with iterative deep search loop
- Multi-provider LLM support (OpenAI, Anthropic, Google, Ollama)
- Web search via DuckDuckGo (with HTML fallback)
- Concurrent page fetching with ThreadPoolExecutor
- CLI with interactive mode
- Python API (`research()`, `DeepResearcher`)
- Comparison mode (`--compare`) for multi-topic research
- Persona mode (`--persona`) for research perspective tuning
- JSON output (`--json`) for programmatic usage
- Debug logging (`--debug`)
- Report export to Markdown, plain text, or JSON
- Retry logic with exponential backoff for LLM calls
- Source relevance tracking
- Per-iteration and total timing display
- 36 tests with CI across Python 3.9–3.13
- CONTRIBUTING.md

[Unreleased]: https://github.com/bysiber/deepworm/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/bysiber/deepworm/releases/tag/v0.1.0
