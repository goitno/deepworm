# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2025-02-25

### Added

- **Content Compliance** (`compliance.py`): Style guide enforcement and content quality checking. `Severity` enum (error/warning/info/suggestion). `IssueCategory` enum (formatting/style/consistency/content/accessibility/structure). `ComplianceReport` with score (0-100), category/severity grouping, markdown output. `StyleGuide` with configurable rules (sentence/paragraph length, banned/preferred words, require intro/conclusion). 13 built-in checks: sentence length, paragraph length, heading hierarchy, alt text, banned words, preferred words, passive voice, weasel words, clichés, redundant phrases, formatting, consecutive headings, structure. `academic_style_guide()` and `technical_style_guide()` presets.
- **Internationalization** (`i18n.py`): Multi-language support and translation management. `TranslationEntry` with locale-aware fallback. `TranslationCatalog` with PO and JSON export, coverage statistics. `LanguageDetection` with confidence scoring and script identification. `detect_language()` for 12 languages (en, tr, de, fr, es, pt, it, ja, zh, ko, ar, ru). 8 script types (Latin, CJK, Hiragana, Katakana, Hangul, Arabic, Cyrillic, Devanagari). `extract_translatable()` for markdown. `create_catalog()` and `merge_catalogs()`.
- **Document Schema Validation** (`schema.py`): Structured data validation and document schema enforcement. `FieldType` enum (string, integer, float, boolean, list, dict, date, url, email, markdown). `SchemaField` with constraint-based validation (min/max length, pattern, choices, value range). `SectionRule` for heading presence and word count constraints. `DocumentSchema` with `validate_data()`, `validate_document()`, `to_json_schema()` export. `report_schema()` and `article_schema()` presets. `create_schema()` dict-based construction helper.
- **Pipeline Hooks & Middleware** (`hooks.py`): Lifecycle hooks for document processing pipelines. `HookStage` enum with 10 stages (pre/post research, analysis, generation, export, error, complete). `HookContext` with data store and cancellation. `HookRegistry` with register/unregister, enable/disable, priority ordering. `Pipeline` with composable multi-step processing and automatic hook integration. `PipelineResult` with timing and error aggregation. `create_middleware()` before/after wrapper. `@hook` decorator for global registry.
- **New Exports**: 35 new public API exports. Total public API: 171 exports.

## [1.0.0] - 2025-02-25

### Added

- **Word Cloud & Frequency Analysis** (`wordcloud.py`): Generate word frequency data and cloud visualizations. `WordFrequency` dataclass with count, frequency, rank, TF-IDF, weight. `WordCloudData` with multiple output formats (markdown table, inline HTML cloud, CSV, size map). `generate_word_cloud()` with 130+ built-in stop words, configurable max_words, min_length, min_count, custom stop words. `compare_word_clouds()` for frequency distribution comparison. `tfidf_cloud()` for multi-document TF-IDF analysis. Markdown stripping and code block/URL removal in tokenizer.
- **Document Revision Tracking** (`revisions.py`): Track changes between document versions with full history management. `Revision` with SHA-256 content hashing, word/line counts. `RevisionDiff` with LCS-based diff algorithm, unified diff output, markdown format. `RevisionHistory` with add/get/rollback/changelog/statistics. `compute_diff()` with modification detection (adjacent delete+add merging). `track_changes()` for quick two-version comparison. `merge_revisions()` with chronological ordering and deduplication.
- **Comprehensive Statistics** (`statistics.py`): 25+ document metrics with markdown awareness. `TextStatistics` covering characters, words, sentences, paragraphs, vocabulary richness, hapax legomena, reading/speaking time (238/150 WPM). `compare_statistics()` for side-by-side document comparison with diff. `vocabulary_analysis()` with frequency distribution, rare words, type-token ratio. `section_statistics()` for per-heading breakdown. `reading_level()` with Flesch-Kincaid Grade Level and Automated Readability Index.
- **Table of Contents** (`toc.py`): Generate, customize, and inject table of contents from markdown headings. `TocEntry` with auto-anchor slugification, depth tracking. `TableOfContents` with flat view, level filtering, max_depth. Multiple output formats: markdown, numbered markdown (hierarchical 1, 1.1, 1.2), HTML. `extract_toc()` with duplicate anchor handling. `inject_toc()` with marker-based or auto-placement insertion. `merge_tocs()` for combining multiple ToCs.
- **New Exports**: 27 new public API exports. Total public API: 136 exports.

## [0.9.0] - 2025-02-25

### Added

- **Timeline Extraction** (`timeline.py`): Extract dates and events from reports to build chronological timelines. 7 date pattern types (ISO, full date, month-year, quarter, decade, century, year references). Auto-categorization (technology, business, science, policy, milestone). `Timeline` with sort, filter, merge, deduplicate. `compare_timelines()` for overlap analysis. Markdown list, table, and dict output.
- **Bibliography Management** (`references.py`): Structured reference management with APA, MLA, and BibTeX formatting. `Reference` with citation_key, author_string. `Bibliography` with add/find/sort/deduplicate, group by type. `extract_references()` detects inline citations, markdown links, bare URLs, DOIs, Author (Year) patterns. `inject_bibliography()` and `merge_bibliographies()`.
- **Sentiment Analysis** (`sentiment.py`): Lexicon-based sentiment analysis with negation handling and intensifier detection. `SentimentScore` with positive/negative/compound scores. `ToneAnalysis` with formality, objectivity, 6 bias patterns. `analyze_report_sentiment()` with section and sentence breakdowns. `sentiment_diff()` for comparing text sentiment.
- **Cross-Referencing** (`crossref.py`): Detect, create, and validate internal cross-references. `CrossRefIndex` with targets (section, figure, table) and links. `build_crossref_index()` scans `{#label}` and `{@label}` syntax. `inject_crossrefs()` replaces references with formatted display. `generate_list_of_figures()` and `generate_list_of_tables()`. Validation for unresolved references and duplicate labels.
- **New Exports**: 25 new public API exports including `Timeline`, `TimelineEvent`, `extract_timeline`, `create_timeline`, `compare_timelines`, `Reference`, `Bibliography`, `extract_references`, `create_reference`, `inject_bibliography`, `merge_bibliographies`, `SentimentScore`, `SentimentReport`, `ToneAnalysis`, `analyze_sentiment`, `analyze_tone`, `analyze_report_sentiment`, `sentiment_diff`, `CrossRefIndex`, `CrossRefTarget`, `build_crossref_index`, `inject_crossrefs`, `generate_list_of_figures`, `generate_list_of_tables`. Total public API: 109 exports.

## [0.8.0] - 2025-02-25

### Added

- **Glossary Extraction** (`glossary.py`): Automatic glossary generation from research reports. 5 definition patterns ("defined as", "refers to", "which is", "i.e.", em-dash), abbreviation detection (e.g., "Natural Language Processing (NLP)"), compound term extraction from headings. `Glossary` with add/get/remove/sort (alphabetical, frequency, occurrence). `inject_glossary()` appends formatted glossary section. Markdown table and definition list output.
- **Text Similarity Analysis** (`similarity.py`): Three similarity metrics — cosine similarity (TF vectors), Jaccard similarity (set overlap), overlap coefficient. `compare_texts()` combines all metrics with `is_similar` (>0.6) and `is_duplicate` (>0.85) thresholds. `detect_plagiarism()` via common n-gram sequences. `find_similar()` corpus search. `text_fingerprint()` for document fingerprinting.
- **Report Annotations** (`annotations.py`): 6 annotation types — comment, highlight, question, todo, warning, fact_check. `AnnotationSet` with add/resolve/filter/summary. `annotate_report()` with inline HTML comments or append styles. `extract_annotations()` parses HTML comment and CriticMarkup (`{>> <<}`) formats. `auto_annotate()` detects vague language, unsupported statistics, and TODO markers.
- **Batch Research** (`batch.py`): Run multiple research tasks sequentially with `create_batch()` and `run_batch()`. `BatchConfig` with stop_on_error, retry_failed (configurable max_retries), delay_between tasks. `BatchResult` with success_rate, `combine_reports()`, markdown summary. `batch_from_file()` loads topics from text files.
- **New Exports**: 20 new public API exports including `AnnotationSet`, `AnnotationType`, `annotate_report`, `auto_annotate`, `extract_annotations`, `BatchConfig`, `BatchResult`, `BatchStatus`, `BatchTask`, `create_batch`, `run_batch`, `Glossary`, `GlossaryEntry`, `extract_glossary`, `inject_glossary`, `SimilarityResult`, `compare_texts`, `cosine_similarity`, `detect_plagiarism`, `find_similar`. Total public API: 85 exports.

## [0.7.0] - 2025-02-25

### Added

- **Keyword Extraction** (`keywords.py`): TF-based keyword and keyphrase extraction from reports. Bigram/trigram phrase detection, stop word filtering, deduplication of subsumed terms, `extract_tags()` for short tag generation. `KeywordResult` with markdown table output.
- **Footnote Management** (`footnotes.py`): Convert inline citations and markdown links to numbered footnotes. Three render styles (markdown, endnotes, inline). `renumber_footnotes()` fixes gaps, `strip_footnotes()` removes all markers, `merge_footnotes()` combines multiple results.
- **Unified Export Hub** (`export.py`): Single interface for multi-format report export — Markdown (with ToC), HTML (responsive CSS), JSON (structured sections), plain text (word-wrapped), Notion (block API), CSV. `batch_export()` for exporting to multiple formats at once.
- **Summary & Abstract Generator** (`summary.py`): 4 summarization styles — executive, abstract, bullets, TLDR. `extract_key_findings()` with importance scoring (8 signal patterns). `extract_topics()` from report headings.
- **Readability Analysis** (`readability.py`): 4 readability formulas — Flesch Reading Ease, Flesch-Kincaid Grade, Gunning Fog, Coleman-Liau. Vocabulary richness, reading level classification, markdown stripping.
- **Progress Tracking** (`progress.py`): Real-time research progress with 10 stages, callback support, ETA estimation, progress bar formatting.
- **New Exports**: 25 new public API exports including `Keyword`, `KeywordResult`, `extract_keywords`, `extract_tags`, `FootnoteResult`, `add_footnotes`, `merge_footnotes`, `renumber_footnotes`, `strip_footnotes`, `ExportFormat`, `ExportOptions`, `ExportResult`, `export_report`, `batch_export`, `Summary`, `summarize`, `extract_key_findings`, `extract_topics`, `ReadabilityResult`, `analyze_readability`, `ProgressTracker`, `ProgressSnapshot`, `ResearchStage`. Total public API: 65 exports.

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
