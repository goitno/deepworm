# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2025-01-20

### Added
- **Research history**: Persistent JSONL log of all completed research (`--history`, `--history-search`, `--history-stats`, `--history-clear`)
- **Custom exceptions**: `DeepWormError` hierarchy with user-friendly messages and hints (`APIKeyError`, `RateLimitError`, `ProviderError`, `ConfigError`, etc.)
- **Citation formatting**: APA, MLA, Chicago, and BibTeX citation styles with auto-publisher detection (`deepworm.citations`)
- **Plugin/hook system**: 6 hook types for pipeline customization (`transform_queries`, `filter_source`, `post_analysis`, `post_report`, `pre_search`, `post_search`)
- **Structured event system**: `EventEmitter` with 13 event types for progress tracking
- **Async research API**: `AsyncResearcher` and `async_research()` for web framework integration
- **HTML export**: Responsive reports with dark mode CSS (`--format html` or `.html` extension)
- **Multiple search providers**: Brave Search API and SearXNG in addition to DuckDuckGo (`--search-provider`)
- **TOML config file support**: `deepworm.toml`, `.deepworm.toml`, `pyproject.toml [tool.deepworm]`
- **Disk cache**: Cached search results and page content with 24h TTL (`--no-cache`, `--clear-cache`)
- **Streaming output**: Real-time report generation (`--stream`)
- **Session save/resume**: Auto-save after each iteration
- **Source quality scoring**: Domain authority heuristics and keyword overlap ranking
- **Retry decorator**: `@retry()` with exponential backoff, exception filtering, and callbacks
- **Text utilities**: `chunk_text()` for splitting long documents, `sanitize_filename()`
- **Thread-safe rate limiter**
- 5 new example scripts: FastAPI server, plugin usage, event monitoring, async research, HTML export
- 132 tests (up from 36 in v0.1.0)

### Changed
- Improved CLI error handling with friendly messages and `--debug` traceback
- LLM client validates API keys at initialization with clear error messages
- Research engine records all completed research to persistent history

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

[Unreleased]: https://github.com/bysiber/deepworm/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/bysiber/deepworm/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/bysiber/deepworm/releases/tag/v0.1.0
