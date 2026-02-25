# DeepWorm 🐁

[![PyPI](https://img.shields.io/pypi/v/deepworm)](https://pypi.org/project/deepworm/)
[![Python](https://img.shields.io/pypi/pyversions/deepworm)](https://pypi.org/project/deepworm/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

AI deep research tool that searches the web, reads sources, and synthesizes findings into comprehensive reports.

<p align="center">
  <video src="https://github.com/bysiber/deepworm/raw/main/demo.mp4" width="800" autoplay loop muted playsinline></video>
</p>

<p align="center">
  <a href="https://github.com/bysiber/deepworm/raw/main/demo.mp4">▶️ Watch demo video</a>
</p>

**Works 100% free** with Ollama (local LLM) + DuckDuckGo (no API key needed for search). Also supports OpenAI, Google Gemini, Anthropic Claude, and [OpenRouter](https://openrouter.ai/) (200+ models).

No Langchain dependency. No paid search APIs required. Just `pip install deepworm` and go.

## Quick Start

```bash
pip install deepworm
```

### Set up an API key (choose one)

```bash
# Option 1: Google Gemini (recommended, free tier available)
export GOOGLE_API_KEY="AIza..."

# Option 2: OpenRouter (200+ models, free & paid)
export OPENROUTER_API_KEY="sk-or-..."

# Option 3: OpenAI
export OPENAI_API_KEY="sk-..."

# Option 4: Anthropic Claude
export ANTHROPIC_API_KEY="sk-ant..."

# Option 5: Ollama (fully local, no key needed)
# Just install Ollama and pull a model
```

### Run a research

```bash
deepworm "what are the latest advances in quantum computing?"
```

That's it. DeepWorm will:
1. Search the web for relevant sources
2. Read and analyze each source
3. Generate followup questions
4. Go deeper recursively
5. Produce a final report with citations

## Command Line Options

```bash
# Control research depth and breadth
deepworm "topic" --depth 2 --breadth 3

# Verbose mode (see searches, pages, analysis in real-time)
deepworm "topic" -v

# Save report to file
deepworm "topic" --output report.md

# Auto-polish analysis (readability, quality score, compliance)
deepworm "topic" --polish

# Knowledge graph extraction
deepworm "topic" --graph              # Mermaid diagram
deepworm "topic" --graph stats        # Top connected concepts table

# Full pipeline
deepworm "topic" -v --polish --graph stats

# Choose provider
deepworm "topic" --provider google
deepworm "topic" --provider openrouter --model google/gemini-2.0-flash-001

# Compare topics
deepworm compare "Python" "Rust"

# See all options
deepworm --help
```

## Interactive Mode (TUI)

```bash
deepworm interactive
```

Features:
- **Arrow-key menu navigation** — navigate commands without typing
- **`/keys`** — manage API keys interactively (saved to `~/.deepworm_keys`)
- **`/models`** — browse and switch models with arrow keys
- **`/set`** — change depth, breadth, model inline
- **`/last`** — view last research report
- **`/graph`** — extract knowledge graph from last report
- **`/polish`** — run quality analysis on last report
- **Command history** — arrow up/down to recall previous queries
- **Auto-save** — all reports saved to `~/.deepworm/reports/`

## Python API

```python
from deepworm import Researcher

researcher = Researcher(provider="openai")
result = researcher.research("your topic")
print(result.report)
```

## Supported Providers

| Provider | Env Variable | Default Model | Notes |
|---|---|---|---|
| Google | `GOOGLE_API_KEY` | gemini-2.5-flash-lite | Free tier available |
| OpenRouter | `OPENROUTER_API_KEY` | gemini-2.0-flash-001 | 200+ models, free & paid |
| OpenAI | `OPENAI_API_KEY` | gpt-4o-mini | |
| Anthropic | `ANTHROPIC_API_KEY` | claude-3-5-haiku-latest | |
| Ollama | (none, local) | llama3.2 | Fully offline |

## Configuration

Create `deepworm.yaml` in your project root:

```yaml
provider: google
model: gemini-pro
depth: 3
breadth: 5
output_dir: ./reports
```

## Key Features

- **Multi-provider LLM support** — OpenAI, Google Gemini, Anthropic, OpenRouter (200+ models), Ollama
- **Recursive deep research** with configurable depth and breadth
- **Interactive TUI** with arrow-key navigation, command menu, and auto-save
- **Knowledge graph extraction** — Mermaid, DOT, stats, JSON formats
- **Polish pipeline** — readability scoring, compliance checks, quality grades (A-F)
- **Auto-save reports** to `~/.deepworm/reports/` (both CLI and interactive)
- **API key management** — `/keys` command saves keys securely to `~/.deepworm_keys`
- Markdown reports with citations and source links
- Comparison mode for side-by-side analysis
- Research chains for multi-step investigations
- Built-in retry and rate limiting
- DuckDuckGo search (no API key needed for search)
- Rich terminal output with emoji progress tracking
- Token usage tracking per research
- Extensible plugin system

## License

MIT
