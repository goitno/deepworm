# DeepWorm 🐁

[![PyPI](https://img.shields.io/pypi/v/deepworm)](https://pypi.org/project/deepworm/)
[![Python](https://img.shields.io/pypi/pyversions/deepworm)](https://pypi.org/project/deepworm/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

AI deep research tool that searches the web, reads sources, and synthesizes findings into comprehensive reports.

**Works 100% free** with Ollama (local LLM) + DuckDuckGo (no API key needed for search). Also supports OpenAI, Google Gemini, and Anthropic Claude.

No Langchain dependency. No paid search APIs required. Just `pip install deepworm` and go.

## Quick Start

```bash
pip install deepworm
```

### Set up an API key (choose one)

```bash
# Option 1: OpenAI
export OPENAI_API_KEY="sk-..."

# Option 2: Google Gemini
export GOOGLE_API_KEY="AIza..."

# Option 3: Anthropic Claude
export ANTHROPIC_API_KEY="sk-ant..."
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
# Control research depth
deepworm "topic" --depth 3 --breadth 5

# Save report to file
deepworm "topic" --output report.md

# Choose provider
deepworm "topic" --provider google

# Compare topics
deepworm compare "Python" "Rust"

# Interactive mode
deepworm interactive

# See all options
deepworm --help
```

## Python API

```python
from deepworm import Researcher

researcher = Researcher(provider="openai")
result = researcher.research("your topic")
print(result.report)
```

## Supported Providers

| Provider | Env Variable | Models |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | gpt-4o, gpt-4o-mini |
| Google | `GOOGLE_API_KEY` | gemini-pro, gemini-flash |
| Anthropic | `ANTHROPIC_API_KEY` | claude-3.5, claude-3 haiku |
| Ollama | (none, local) | llama3, mistral |

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

- Multi-provider LLM support (OpenAI, Google, Anthropic, Ollama)
- Recursive deep research with configurable depth and breadth
- Markdown reports with citations and source links
- Comparison mode for side-by-side analysis
- Research chains for multi-step investigations
- Built-in retry and rate limiting
- DuckDuckGo search (no API key needed for search)
- Interactive mode for exploratory research
- Research history and caching
- Template system for repeatable research
- Rich terminal output with progress tracking
- Extensible plugin system

## License

MIT
