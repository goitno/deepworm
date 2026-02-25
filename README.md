# deepworm

[![CI](https://github.com/bysiber/deepworm/actions/workflows/ci.yml/badge.svg)](https://github.com/bysiber/deepworm/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

Open-source deep research agent. Like OpenAI's Deep Research, but free and local.

Give it a topic, it searches the web, reads sources, identifies gaps, digs deeper, and writes a comprehensive research report. Works with OpenAI, Anthropic, Google, or **completely free with Ollama** (local models).

## Install

```bash
pip install deepworm
```

## Quick Start

```bash
# With OpenAI
export OPENAI_API_KEY=sk-...
deepworm "impact of sleep deprivation on cognitive performance"

# With Ollama (free, local, no API key needed)
# Just have Ollama running: https://ollama.com
deepworm "impact of sleep deprivation on cognitive performance" --provider ollama

# Save to file
deepworm "quantum computing 2024" --output report.md
```

Or use it as a library:

```python
from deepworm import research

report = research("impact of sleep deprivation on cognitive performance")
print(report)
```

## How It Works

```
Topic
  │
  ├─ Generate search queries (multiple angles)
  │
  ├─ Search the web (DuckDuckGo, free)
  │
  ├─ Fetch & read sources
  │
  ├─ Analyze each source with LLM
  │
  ├─ Identify knowledge gaps
  │
  ├─ Generate follow-up queries ──┐
  │                                │
  │  (repeat for N iterations) ◄───┘
  │
  └─ Synthesize final report (Markdown)
```

Each iteration digs deeper. The LLM identifies what's missing and generates targeted follow-up searches. Default is 2 iterations with 4 queries each.

## Example Output

```
$ deepworm "solid-state batteries 2024 breakthroughs"

╭──────────────────────── deepworm research ─────────────────────────╮
│ solid-state batteries 2024 breakthroughs                          │
│                                                                   │
│ Provider: openai | Model: gpt-4o-mini                             │
│ Depth: 2 | Breadth: 4                                             │
╰───────────────────────────────────────────────────────────────────╯

--- Iteration 1/2 ---
 Generated 4 search queries
  • solid state battery breakthroughs 2024
  • solid state battery companies production 2024
  • solid state battery vs lithium ion comparison
  • solid state battery challenges manufacturing scalability
 Fetched 12 sources
 Analyzing sources...

--- Iteration 2/2 ---
 Generated 4 search queries
  • Toyota solid state battery timeline
  • QuantumScape Samsung SDI solid state 2024
  • solid state battery energy density improvements
  • sulfide oxide electrolyte comparison
 Fetched 9 sources
 Analyzing sources...

Synthesizing report...
Done!
```

The output is a full Markdown report with sections, citations, and source URLs.

## Providers

deepworm auto-detects your provider from environment variables:

| Provider | Env Variable | Default Model | Free? |
|----------|-------------|---------------|-------|
| Ollama | *(none needed)* | llama3.2 | Yes |
| OpenAI | `OPENAI_API_KEY` | gpt-4o-mini | No |
| Anthropic | `ANTHROPIC_API_KEY` | claude-3-5-haiku-latest | No |
| Google | `GOOGLE_API_KEY` | gemini-2.0-flash | Free tier |

### Using Ollama (recommended for free usage)

1. Install [Ollama](https://ollama.com)
2. Pull a model: `ollama pull llama3.2`
3. Run deepworm: `deepworm "your topic" --provider ollama`

## CLI Options

```
deepworm "topic"                                    # research a topic
deepworm "topic" -d 3                               # 3 iterations (deeper)
deepworm "topic" -b 6                               # 6 queries per iteration (broader)
deepworm "topic" -m gpt-4o                          # use specific model
deepworm "topic" -p ollama                          # force Ollama provider
deepworm "topic" -o report.md                       # save to file
deepworm "topic" -o report.html                     # save as HTML (dark mode)
deepworm "topic" -o report.pdf                      # save as PDF
deepworm "topic" -f html                            # force HTML format
deepworm "topic" -q                                 # quiet mode
deepworm "topic" --json                             # JSON output for piping
deepworm "topic" --stream                           # stream report as it generates
deepworm "topic" --persona "startup founder"        # research perspective
deepworm "topic" --no-cache                         # skip disk cache
deepworm "topic" --search-provider brave            # use Brave Search
deepworm "topic" -t academic                        # use template preset
deepworm "topic" --lang tr                          # output in Turkish
deepworm "topic" --lang ja                          # output in Japanese
deepworm "topic" -i                                 # interactive Q&A after research
deepworm "topic" --copy                             # copy report to clipboard
deepworm "topic" --chain 3                          # 3-step progressive deep dive
deepworm "topic" --no-followup                      # don't generate follow-up questions
deepworm "topic" --export-sources sources.json      # export sources as JSON
deepworm "topic" --export-sources sources.csv       # export sources as CSV
deepworm "topic" --export-sources refs.bib          # export sources as BibTeX
deepworm "topic" --profile myconfig                 # use saved config profile
deepworm "topic" --toc                              # insert table of contents
deepworm "topic" --stats                            # show report statistics
deepworm "topic" --score                            # show report quality score
deepworm "topic" --metrics                          # show detailed research metrics
deepworm "topic" --sections "Summary|Findings"      # filter to matching sections
deepworm "topic" --timeout 300                      # 5-minute time budget
deepworm "topic" --resume                           # resume latest session
deepworm "topic" --plan                             # show research plan before executing
deepworm "topic" --plan-only                        # generate plan without researching
deepworm "topic" --config myconfig.yaml             # load config from custom file
deepworm "topic" --log-file research.log            # log to file
deepworm "topic" --log-level debug                  # set log level
deepworm --compare "React" "Vue" "Svelte"           # compare topics
deepworm --diff old.md new.md                       # diff two report files
deepworm --save-profile myconfig                    # save current config as profile
deepworm --list-profiles                            # show saved profiles
deepworm --delete-profile myconfig                  # remove a profile
deepworm --list-templates                           # show research templates
deepworm --list-languages                           # show supported languages
deepworm --serve                                    # start web UI (port 8888)
deepworm --serve 3000                               # start web UI on port 3000
deepworm --clear-cache                              # clear cached data
deepworm --history                                  # show last 10 researches
deepworm --history 20                               # show last 20 researches
deepworm --history-search "quantum"                 # search history
deepworm --history-stats                            # aggregate stats
deepworm --history-clear                            # clear all history
deepworm                                            # interactive mode
```

## Comparison Mode

Compare multiple topics side by side:

```bash
deepworm --compare "PostgreSQL" "MySQL" "SQLite" -o comparison.md
```

This researches each topic individually, then generates a structured comparison with tables and analysis.

## Search Providers

| Provider | Setup | Free? |
|----------|-------|-------|
| DuckDuckGo | None (default) | Yes |
| Brave Search | `BRAVE_API_KEY` env var | Free tier (2k queries/mo) |
| SearXNG | `SEARXNG_URL` env var (self-hosted) | Yes |

```bash
# Use Brave Search
export BRAVE_API_KEY=BSA...
deepworm "topic" --search-provider brave

# Use self-hosted SearXNG
export SEARXNG_URL=http://localhost:8888
deepworm "topic" --search-provider searxng
```

## Config File

Instead of CLI flags, you can use a config file. deepworm searches from the current directory up to the root for:

1. `deepworm.toml`
2. `.deepworm.toml`
3. `pyproject.toml` (under `[tool.deepworm]`)

**deepworm.toml:**

```toml
provider = "ollama"
model = "llama3.2"
depth = 3
breadth = 6
temperature = 0.2
search_region = "us-en"
search_max_results = 10
```

**pyproject.toml:**

```toml
[tool.deepworm]
provider = "openai"
model = "gpt-4o"
depth = 3
```

All settings are optional. CLI flags override config file values.

### Environment Variables

Override any config setting with `DEEPWORM_*` environment variables:

```bash
export DEEPWORM_DEPTH=3
export DEEPWORM_BREADTH=6
export DEEPWORM_PROVIDER=anthropic
export DEEPWORM_VERBOSE=true
export DEEPWORM_OUTPUT_FORMAT=html
```

Priority: CLI flags > env vars > config file > defaults.

## Python API

```python
from deepworm import research, DeepResearcher
from deepworm.config import Config

# Simple
report = research("your topic")

# With options
config = Config(provider="ollama", depth=3, breadth=6)
researcher = DeepResearcher(config=config)
report = researcher.research("your topic")

# Comparison
from deepworm.compare import compare
report = compare(["React", "Vue", "Svelte"])
```

### Async API

```python
import asyncio
from deepworm import AsyncResearcher, async_research

async def main():
    # Simple
    report = await async_research("your topic")

    # Concurrent research
    tasks = [async_research(t) for t in ["topic A", "topic B", "topic C"]]
    reports = await asyncio.gather(*tasks)
```

### Events

```python
from deepworm import DeepResearcher, EventEmitter, EventType

emitter = EventEmitter()

@emitter.on(EventType.ITERATION_END)
def on_iteration(event):
    print(f"Iteration {event.data['iteration']} done in {event.data['elapsed']:.1f}s")

researcher = DeepResearcher(events=emitter)
report = researcher.research("your topic")
```

### Plugins

```python
from deepworm import DeepResearcher
from deepworm.plugins import PluginManager

pm = PluginManager()

@pm.hook("filter_source")
def block_domains(url, title):
    return "pinterest.com" not in url

@pm.hook("post_report")
def add_disclaimer(report):
    return report + "\n\n*AI-generated content — verify from primary sources.*"

researcher = DeepResearcher(plugins=pm)
report = researcher.research("your topic")
```

### Citations

```python
from deepworm.citations import Citation, format_citations

citations = [
    Citation(url="https://arxiv.org/abs/2401.12345", title="Deep Learning Paper", author="Smith, J."),
    Citation(url="https://nature.com/article", title="Nature Study"),
]

print(format_citations(citations, style="apa"))    # APA format
print(format_citations(citations, style="bibtex")) # BibTeX format
```

### Research History

```python
from deepworm.history import list_entries, search_history, stats

# List recent research
for entry in list_entries(limit=10):
    print(f"{entry.created_iso} - {entry.topic}")

# Search history
results = search_history("quantum")

# Aggregate stats
print(stats())  # total researches, avg time, models used, etc.
```

### Research Chaining

```python
from deepworm import research_chain

# 3-step progressive deep dive
report = research_chain("AI in healthcare", steps=3)
```

### Multi-Language

```python
from deepworm import DeepResearcher

researcher = DeepResearcher()
report = researcher.research("quantum computing", lang="tr")  # Turkish output
```

### Source Export

```python
from deepworm.sources import export_sources, import_sources

# Export after research
sources = [{"url": "https://...", "title": "...", "findings": "...", "relevance": 0.9}]
export_sources(sources, "refs.bib")  # BibTeX
export_sources(sources, "sources.csv")  # CSV

# Re-import
sources = import_sources("sources.json")
```

### Report Quality Scoring

```python
from deepworm import score_report

score = score_report(report)
print(f"Grade: {score.grade} ({score.overall:.0%})")
print(f"Structure: {score.structure:.0%}")
print(f"Depth: {score.depth:.0%}")
for tip in score.suggestions:
    print(f"  • {tip}")
```

### Report Diffing

```python
from deepworm.diff import diff_reports, diff_summary

# Compare two reports
diff_text = diff_reports(old_report, new_report)
summary = diff_summary(old_report, new_report)
print(f"Added: {summary['added_lines']} | Removed: {summary['removed_lines']}")
print(f"Similarity: {summary['similarity_ratio']:.0%}")
```

### Source Credibility

```python
from deepworm import score_source, score_sources

# Single source
score = score_source("https://arxiv.org/abs/2401.12345")
print(f"Credibility: {score.label} ({score.overall_score:.0%})")
print(f"Tier: {score.tier}")

# Batch scoring
report = score_sources(["https://arxiv.org/abs/123", "https://medium.com/article"])
print(report.to_markdown())
```

### Notion Export

```python
from deepworm import markdown_to_notion, export_notion_json

# Convert report to Notion blocks
page = markdown_to_notion(report)
print(f"Title: {page.title}")
print(f"Blocks: {page.block_count}")

# Get ready-to-use Notion API payload
payload = export_notion_json(report)
# Use with Notion API client
```

### Report Outlines

```python
from deepworm import generate_outline, outline_from_report

# Generate outline before research
outline = generate_outline("quantum computing", style="academic")
print(outline.to_markdown())

# Extract outline from existing report
outline = outline_from_report(report)
print(f"Sections: {outline.section_count}")
```

### Progress Tracking

```python
from deepworm.progress import ProgressTracker, ResearchStage

tracker = ProgressTracker()
tracker.on_progress(lambda snap: print(f"{snap.overall_percent:.0f}% - {snap.message}"))
tracker.start()
tracker.enter_stage(ResearchStage.SEARCHING, total_items=10)
# ... research loop ...
tracker.complete()
```

## vs. gpt-researcher

| | deepworm | gpt-researcher |
|---|---|---|
| Install | `pip install deepworm` | Docker + multiple services |
| Setup | One env var (or zero for Ollama) | Multiple API keys + config files |
| Local models | Ollama out of the box | Limited |
| Streaming | Built-in `--stream` | Requires WebSocket |
| Caching | Disk cache (24h TTL) | No built-in cache |
| Session resume | Auto-save after each iteration | No |
| Plugin system | 6 hook types | No |
| Event system | 13 event types | Custom callbacks |
| Async API | Built-in `AsyncResearcher` | Async by default |
| Citations | APA, MLA, Chicago, BibTeX | No |
| Research history | Persistent JSONL log | No |
| Multi-language | 17 languages (`--lang`) | No |
| Interactive Q&A | Post-research follow-up (`-i`) | No |
| Research chaining | Progressive deep-dive (`--chain`) | No |
| Config profiles | Save/load configs (`--profile`) | No |
| Source export | JSON, CSV, BibTeX | No |
| Report scoring | Quality grades A+ to F (`--score`) | No |
| Metrics | Detailed research instrumentation (`--metrics`) | No |
| Report diffing | Compare report versions (`--diff`) | No |
| Section filtering | Regex section filter (`--sections`) | No |
| Time budget | Research timeout (`--timeout`) | No |
| Research planner | Topic analysis & sub-questions (`--plan`) | No |
| YAML config | `deepworm.yaml` + `--config` flag | No |
| Topic validation | Auto-validates topics with suggestions | No |
| Content extraction | Metadata, headings, quality scoring | Limited |
| Table generation | Markdown tables from data/CSV | No |
| Source credibility | 3-tier domain scoring + content analysis | No |
| Notion export | Notion API block format + roundtrip | No |
| Progress tracking | Stage-based progress with ETA | Limited |
| Env var config | `DEEPWORM_*` env var overrides | No |
| Report outlines | 3 outline styles + reverse-engineering | No |
| Retry strategies | 4 backoff strategies + circuit breaker | No |
| Link checking | Extract & validate markdown links | No |
| Config validation | Validates all settings on creation | No |
| Templates | 10 built-in presets | No |
| Web UI | Built-in (`--serve`) | Yes |
| Search providers | 3 (DDG, Brave, SearXNG) | 5+ |
| Dependencies | 3 packages | 30+ packages |
| Keyword extraction | TF-based keywords + phrase detection | No |
| Footnote management | Auto-convert citations to footnotes | No |
| Multi-format export | MD/HTML/JSON/Text/Notion/CSV hub | Limited |
| Summarization | 4 styles (executive, abstract, bullets, TLDR) | No |
| Readability analysis | 4 formulas (Flesch, Fog, Coleman-Liau) | No |
| Glossary extraction | Auto-detect definitions + abbreviations | No |
| Similarity analysis | Cosine, Jaccard, plagiarism detection | No |
| Annotations | 6 types + auto-detect + CriticMarkup | No |
| Batch research | Multi-topic with retry + config | No |
| Timeline extraction | Date parsing + chronological ordering | No |
| Bibliography mgmt | APA/MLA/BibTeX + auto-extraction | No |
| Sentiment analysis | Lexicon-based + bias detection | No |
| Cross-referencing | Sections/figures/tables + validation | No |
| Word cloud | TF-IDF, frequency analysis, HTML output | No |
| Revision tracking | LCS diff, rollback, changelog | No |
| Document statistics | 25+ metrics, reading level, vocabulary | No |
| Table of contents | Auto-generate, inject, numbered, HTML | No |
| Content compliance | Style guides, 13 checks, presets | No |
| Internationalization | 12 languages, PO/JSON export, catalogs | No |
| Document schemas | Field validation, JSON Schema export | No |
| Pipeline hooks | 10 lifecycle stages, middleware, pipelines | No |
| Lines of code | ~22,000 | ~10,000+ |

deepworm is intentionally simple. If you need a web UI, multi-agent orchestration, or enterprise features, use gpt-researcher. If you want a research tool that just works, use deepworm.

## Features

- **Iterative deep research** — search → analyze → identify gaps → dig deeper
- **Multi-provider** — OpenAI, Anthropic, Google, or free with Ollama
- **Multi-language** — generate reports in 17 languages (`--lang tr`, `--lang ja`, etc.)
- **Interactive Q&A** — ask follow-up questions after research (`--interactive`)
- **Research chaining** — progressive deep dives building on each other (`--chain`)
- **Follow-up questions** — auto-generated questions for further exploration
- **Plugin system** — 6 hook types for full pipeline customization
- **Event system** — 13 event types for progress tracking and UI integration
- **Async API** — `AsyncResearcher` for web frameworks (FastAPI, etc.)
- **Citation formatting** — APA, MLA, Chicago, and BibTeX styles
- **Source export** — export to JSON, CSV, or BibTeX (`--export-sources`)
- **Research history** — persistent log with search, stats, and CLI integration
- **Config profiles** — save and reuse research configurations (`--profile`)
- **Research templates** — 10 built-in presets (quick, deep, academic, etc.)
- **Web UI** — built-in dark-themed web interface (`--serve`)
- **HTML/PDF export** — responsive reports with automatic dark mode
- **Multiple search engines** — DuckDuckGo, Brave Search, SearXNG
- **Clipboard** — copy report to clipboard (`--copy`)
- **Disk cache** — 24h cached search results and pages (`--no-cache` to skip)
- **Streaming** — watch the report generate in real-time (`--stream`)
- **Comparison mode** — research and compare multiple topics side by side
- **Persona mode** — adjust perspective (e.g. "PhD student", "startup founder")
- **Session save/resume** — auto-saves state after each iteration
- **Config file** — `deepworm.toml`, `deepworm.yaml`, or `pyproject.toml [tool.deepworm]`
- **Research planner** — pre-research topic analysis with sub-questions
- **Topic validation** — validates and sanitizes topics before research
- **Content extraction** — structured metadata, headings, code blocks from web pages
- **Table generation** — markdown tables from data, CSV import/export
- **Source scoring** — quality heuristics prioritize better sources
- **Content deduplication** — shingle-based near-duplicate detection
- **Report quality scoring** — grades A+ to F with improvement suggestions
- **Research metrics** — timing, API calls, fetch rates, error tracking
- **Report diffing** — compare two report versions with unified diff
- **Section filtering** — extract specific sections by regex pattern
- **Table of contents** — auto-generated from headings
- **Report statistics** — word count, reading time, links, headings
- **Config validation** — validates all settings with clear error messages
- **Time budget** — set research timeout in seconds
- **Rate limiting** — configurable API call rate limits
- **Structured logging** — file output with configurable levels
- **Custom exceptions** — user-friendly error messages with hints
- **Retry logic** — exponential backoff for transient failures
- **Concurrent fetching** — parallel page downloads and searches
- **JSON output** — pipe results to other tools (`--json`)
- **Typed** — full `py.typed` marker for IDE support
- **Source credibility** — 3-tier domain authority scoring with content analysis
- **Notion export** — convert reports to Notion API-ready block format
- **Report outlines** — 3 outline styles (comprehensive, brief, academic)
- **Progress tracking** — real-time stage-based progress with ETA estimation
- **Env var config** — `DEEPWORM_*` environment variable overrides
- **Circuit breaker** — prevent cascading failures with auto-recovery
- **Link checking** — extract and validate links from markdown reports
- **Keyword extraction** — TF-based keywords and keyphrase detection with tagging
- **Footnote management** — auto-convert citations and links to numbered footnotes
- **Multi-format export** — unified export to MD, HTML, JSON, text, Notion, CSV
- **Summarization** — 4 styles: executive, abstract, bullets, TLDR
- **Readability analysis** — Flesch, Flesch-Kincaid, Gunning Fog, Coleman-Liau
- **Glossary extraction** — auto-detect definitions, abbreviations, compound terms
- **Text similarity** — cosine, Jaccard, overlap; plagiarism detection and fingerprinting
- **Report annotations** — 6 annotation types, auto-detect vague language, CriticMarkup
- **Batch research** — run multiple topics with retry, stop-on-error, and callbacks
- **Timeline extraction** — extract dates and events, build chronological timelines
- **Bibliography management** — APA, MLA, BibTeX formatting with auto-extraction
- **Sentiment analysis** — lexicon-based sentiment, tone, and bias detection
- **Cross-referencing** — internal section/figure/table references with validation
- **Word cloud** — word frequency analysis, TF-IDF, HTML cloud, CSV export
- **Revision tracking** — LCS-based diff, rollback, changelog, merge histories
- **Document statistics** — 25+ metrics, Flesch-Kincaid/ARI reading level, vocabulary analysis
- **Table of contents** — auto-generate from headings, inject with markers, numbered, HTML
- **Content compliance** — 13 style checks, academic/technical presets, scoring
- **Internationalization** — detect 12 languages, translation catalogs, PO/JSON export
- **Document schemas** — field validation, section rules, JSON Schema export
- **Pipeline hooks** — 10 lifecycle stages, priority ordering, middleware, pipelines

## License

MIT
