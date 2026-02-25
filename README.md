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
deepworm "topic"               # research with auto-detected provider
deepworm "topic" -d 3          # 3 iterations (deeper research)
deepworm "topic" -b 6          # 6 queries per iteration (broader)
deepworm "topic" -m gpt-4o     # use specific model
deepworm "topic" -p ollama     # force Ollama provider
deepworm "topic" -o report.md  # save to file
deepworm "topic" -q            # quiet mode (no progress output)
deepworm "topic" --json        # output as JSON (for piping)
deepworm                       # interactive mode (prompts for topic)
```

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
```

## vs. gpt-researcher

| | deepworm | gpt-researcher |
|---|---|---|
| Install | `pip install deepworm` | Docker + multiple services |
| Setup | One env var (or zero for Ollama) | Multiple API keys + config files |
| Local models | Ollama out of the box | Limited |
| Dependencies | 3 packages | 30+ packages |
| Lines of code | ~500 | ~10,000+ |
| Web UI | No (CLI-first) | Yes |

deepworm is intentionally simple. If you need a web UI, multi-agent orchestration, or enterprise features, use gpt-researcher. If you want a research tool that just works, use deepworm.

## License

MIT
