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
deepworm "topic" -f html                            # force HTML format
deepworm "topic" -q                                 # quiet mode
deepworm "topic" --json                             # JSON output for piping
deepworm "topic" --stream                           # stream report as it generates
deepworm "topic" --persona "startup founder"        # research perspective
deepworm "topic" --no-cache                         # skip disk cache
deepworm "topic" --search-provider brave            # use Brave Search
deepworm --compare "React" "Vue" "Svelte"           # compare topics
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
| Search providers | 3 (DDG, Brave, SearXNG) | 5+ |
| Dependencies | 3 packages | 30+ packages |
| Lines of code | ~1,500 | ~10,000+ |
| Web UI | No (CLI-first) | Yes |

deepworm is intentionally simple. If you need a web UI, multi-agent orchestration, or enterprise features, use gpt-researcher. If you want a research tool that just works, use deepworm.

## Features

- **Iterative deep research** — search → analyze → identify gaps → dig deeper
- **Multi-provider** — OpenAI, Anthropic, Google, or free with Ollama
- **Plugin system** — 6 hook types for full pipeline customization
- **Event system** — 13 event types for progress tracking and UI integration
- **Async API** — `AsyncResearcher` for web frameworks (FastAPI, etc.)
- **Citation formatting** — APA, MLA, Chicago, and BibTeX styles
- **Research history** — persistent log with search, stats, and CLI integration
- **HTML export** — responsive reports with automatic dark mode
- **Multiple search engines** — DuckDuckGo, Brave Search, SearXNG
- **Disk cache** — 24h cached search results and pages (`--no-cache` to skip)
- **Streaming** — watch the report generate in real-time (`--stream`)
- **Comparison mode** — research and compare multiple topics side by side
- **Persona mode** — adjust perspective (e.g. "PhD student", "startup founder")
- **Session save/resume** — auto-saves state after each iteration
- **Config file** — `deepworm.toml` or `pyproject.toml [tool.deepworm]`
- **Source scoring** — quality heuristics prioritize better sources
- **Custom exceptions** — user-friendly error messages with hints
- **Retry logic** — exponential backoff for transient failures
- **Concurrent fetching** — parallel page downloads for speed
- **JSON output** — pipe results to other tools (`--json`)
- **Typed** — full `py.typed` marker for IDE support

## License

MIT
