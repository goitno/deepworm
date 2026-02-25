"""CLI entry point for deepworm."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

from rich.console import Console

from . import __version__
from .config import Config
from .report import print_report, save_report
from .researcher import DeepResearcher

console = Console()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deepworm",
        description="AI-powered deep research agent. Like deep research, but open-source and free.",
    )
    parser.add_argument(
        "topic",
        nargs="?",
        help="Research topic or question",
    )
    parser.add_argument(
        "--compare",
        nargs="+",
        metavar="TOPIC",
        help="Compare multiple topics (e.g. --compare 'React' 'Vue' 'Svelte')",
    )
    parser.add_argument(
        "--depth", "-d",
        type=int,
        default=None,
        help="Number of research iterations (default: 2)",
    )
    parser.add_argument(
        "--breadth", "-b",
        type=int,
        default=None,
        help="Number of search queries per iteration (default: 4)",
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default=None,
        help="LLM model to use (default: auto-detect)",
    )
    parser.add_argument(
        "--provider", "-p",
        type=str,
        choices=["openai", "anthropic", "google", "ollama"],
        default=None,
        help="LLM provider (default: auto-detect from env)",
    )
    parser.add_argument(
        "--persona",
        type=str,
        default=None,
        help="Research perspective/persona (e.g. 'startup founder', 'PhD student')",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Save report to file (default: print to stdout)",
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["markdown", "html", "text", "json"],
        default=None,
        help="Output format when saving to file (auto-detected from extension)",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress progress output",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output report as JSON with metadata",
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"deepworm {__version__}",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable disk cache for search results and pages",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear the cache and exit",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Stream the report as it generates (real-time output)",
    )
    parser.add_argument(
        "--search-provider",
        type=str,
        choices=["duckduckgo", "brave", "searxng"],
        default=None,
        help="Search engine provider (default: duckduckgo)",
    )
    return parser


def main(args: list[str] | None = None) -> None:
    parser = build_parser()
    opts = parser.parse_args(args)

    if opts.debug:
        logging.basicConfig(level=logging.DEBUG, format="%(name)s %(levelname)s: %(message)s")

    # Handle cache operations
    from .cache import Cache, get_cache

    if opts.clear_cache:
        cache = get_cache()
        count = cache.clear()
        console.print(f"[green]Cleared {count} cached entries.[/green]")
        return

    cache = get_cache(enabled=not opts.no_cache)

    # Build config early (needed for both modes)
    config = Config.auto()

    if opts.provider:
        config.provider = opts.provider
        if opts.model is None:
            config.model = config._default_model(opts.provider)
    if opts.model:
        config.model = opts.model
    if opts.depth:
        config.depth = opts.depth
    if opts.breadth:
        config.breadth = opts.breadth
    if opts.search_provider:
        config.search_provider = opts.search_provider

    # Comparison mode
    if opts.compare:
        from .compare import compare
        try:
            report = compare(
                opts.compare,
                config=config,
                verbose=not opts.quiet,
                persona=opts.persona,
            )
        except KeyboardInterrupt:
            console.print("\n[yellow]Research interrupted.[/yellow]")
            return
        _output_report(report, opts)
        return

    if opts.topic is None:
        # Interactive mode
        console.print("[bold]deepworm[/bold] - AI deep research agent\n")
        try:
            topic = console.input("[bold cyan]What do you want to research?[/bold cyan] ")
        except (KeyboardInterrupt, EOFError):
            console.print("\nBye!")
            return
        if not topic.strip():
            console.print("[red]No topic provided.[/red]")
            return
        opts.topic = topic.strip()

    # Run research
    researcher = DeepResearcher(config=config, cache=cache)

    try:
        report = researcher.research(
            opts.topic,
            verbose=not opts.quiet,
            persona=opts.persona,
            stream=opts.stream,
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Research interrupted.[/yellow]")
        return

    _output_report(report, opts)


def _output_report(report: str, opts: argparse.Namespace) -> None:
    """Handle report output based on CLI options."""
    topic = opts.topic or "comparison"
    if opts.json_output:
        result = {
            "topic": topic,
            "report": report,
        }
        if opts.compare:
            result["topics"] = opts.compare
        print(json.dumps(result, indent=2))
    elif opts.output:
        # Auto-detect format from extension if not specified
        fmt = opts.format
        if fmt is None:
            ext_map = {".html": "html", ".htm": "html", ".txt": "text", ".json": "json"}
            ext = os.path.splitext(opts.output)[1].lower()
            fmt = ext_map.get(ext, "markdown")
        path = save_report(report, opts.output, topic=topic, fmt=fmt)
        console.print(f"\n[green]Report saved to {path}[/green]")
    else:
        print_report(report)


if __name__ == "__main__":
    main()
