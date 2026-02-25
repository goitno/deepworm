# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.6.0] - 2025-02-25

### Added

- **Report Outline Generation**: Structured outline creation with 3 styles — comprehensive (6 sections), brief (3 sections), academic (8 sections with Abstract, Literature Review, Methodology). Comparison-aware section generation for "vs" topics. Reverse-engineering outlines from existing reports via `outline_from_report()`.
- **Source Credibility Scoring**: Multi-factor credibility assessment for web sources. 3-tier domain authority system, content quality analysis (research language, references, spam detection), freshness scoring, URL structure signals. `CredibilityReport` with markdown table output.
- **Notion Export**: Convert markdown reports to Notion API block format. Supports headings, paragraphs, code blocks, quotes, lists, tables, dividers. Rich text parsing with bold, italic, inline code, and links. Roundtrip support via `notion_to_markdown()`.
- **Progress Tracking**: Real-time research progress tracking with 10 research stages, callback support, ETA estimation, and progress bar utilities. `ProgressTracker` with `ProgressSnapshot` for serializable progress state.
- **Environment Variable Config Overrides**: `DEEPWORM_*` environment variables (e.g., `DEEPWORM_DEPTH=5`, `DEEPWORM_PROVIDER=anthropic`) override config file settings. `Config.from_env()` classmethod for explicit env-based configuration.
- **Retry Strategies**: Advanced retry decorator with 4 backoff strategies (exponential, linear, constant, exponential_jitter). Circuit breaker pattern with closed/open/half-open states and auto-recovery.
- **Markdown Link Checker**: Extract and validate links from markdown reports. `LinkReport` with health scoring, broken link detection, and markdown output.
- **New Exports**: `CredibilityScore`, `CredibilityReport`, `score_source`, `score_sources`, `NotionBlock`, `NotionPage`, `export_notion_json`, `markdown_to_notion`, `OutlineSection`, `ReportOutline`, `generate_outline`, `outline_from_report` added to public API.

## [0.5.0] - 2025-02-25

### Added

- **Research Planner** (`--plan`, `--plan-only`): Pre-research topic analysis that generates a structured research plan with sub-questions, key aspects, complexity estimation, and suggested depth/breadth settings. Uses LLM for intelligent analysis with heuristic fallback.
- **YAML Config Support**: Load configuration from `deepworm.yaml`, `deepworm.yml`, `.deepworm.yaml`, or `.deepworm.yml` files. Supports both flat and nested (`deepworm:` key) formats.
- **Config File Flag** (`--config FILE`): Load configuration from a specific TOML or YAML file.
- **Topic Validator**: Automatic topic validation before research — catches empty/too-short/too-long topics, detects vague or overly broad topics, normalizes whitespace, provides improvement suggestions.
- **Markdown Table Generation**: Utility module for creating well-formatted markdown tables from lists of dicts, key-value pairs, or CSV data. Supports column alignment, transposition, and CSV import/export.
- **Content Extraction**: Advanced HTML content extraction with metadata (title, author, date, description), heading/link/code block extraction, reading time estimation, and content quality scoring.
- **New Exports**: `ResearchPlan`, `generate_plan`, `estimate_complexity`, `ValidationResult`, `validate_topic` added to public API.
- PyYAML added as optional dependency (`pip install deepworm[yaml]`).

## [0.4.0] - 2025-02-25

### Added

- **Config Validation**: All configuration values are now validated on creation. Invalid provider, depth, breadth, temperature, or search settings raise clear `ValueError` messages.
- **Report Quality Scoring** (`--score`): Automated report quality assessment across 5 dimensions — structure, depth, sources, readability, completeness — with letter grades (A+ to F) and improvement suggestions.
- **Research Metrics** (`--metrics`): Detailed instrumentation tracking: timing breakdown (search/analysis/synthesis), API call counts, fetch success rates, duplicate detection stats, retry counts, and error tracking.
- **Rate Limiting**: Built-in rate limiter for LLM API calls (`max_requests_per_minute` config option) prevents hitting provider limits.
- **Research Timeout** (`--timeout SECONDS`): Set a time budget for research; automatically proceeds to synthesis when budget expires.
- **Section Filtering** (`--sections PATTERN`): Filter report output to only sections matching a regex pattern.
- **Parallel Search**: Search queries now execute concurrently (up to 4 workers), significantly speeding up the research phase.
- **Report Diffing** (`--diff OLD NEW`): Compare two report files side-by-side with unified diff, added/removed line counts, and similarity ratio.
- **Report Analysis**: Table of contents generation (`--toc`), report statistics (`--stats`), link extraction, and report summaries.
- **Research Resume** (`--resume [FILE]`): Resume interrupted research from saved session files. Use `--resume auto` to find and resume the latest in-progress session.
- **Logging Module** (`--log-file`, `--log-level`): Structured logging with configurable levels and optional file output for debugging.
- **Link Extraction**: Extract all links from reports (inline markdown, bare URLs) with deduplication.
- **Report Summary**: Auto-extract a brief summary from the report's first content paragraph.
- New modules: `scoring.py`, `metrics.py`, `diff.py`, `log.py`
- 258 tests (up from 203)

## [0.3.0] - 2025-02-25

### Added

- **Follow-up Questions**: Auto-generated follow-up questions appended to research reports. Disable with `--no-followup`.
- **Interactive Mode** (`--interactive` / `-i`): Post-research Q&A loop that lets you ask follow-up questions about the report using the same LLM.
- **Clipboard Export** (`--copy`): Copy the research report directly to your system clipboard (macOS, Linux, Windows).
- **Multi-Language Support** (`--lang CODE`): Generate reports in 17 languages including English, Turkish, German, French, Spanish, Portuguese, Italian, Russian, Chinese, Japanese, Korean, Arabic, Hindi, Dutch, Polish, Swedish, and Ukrainian. Use `--list-languages` to see all options.
- **Research Chaining** (`--chain N`): Run progressive deep-dive research that builds on previous findings. Each step identifies the most important sub-topic to explore next.
- **Configuration Profiles**: Save and reuse research configurations with `--save-profile`, `--profile`, `--list-profiles`, `--delete-profile`.
- **Source Export** (`--export-sources FILE`): Export discovered sources as JSON, CSV, or BibTeX for external citation management.
- **Source Import**: Programmatic API to import previously exported sources.
- New modules: `languages.py`, `chain.py`, `profiles.py`, `sources.py`
- 203 tests (up from 154)

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
