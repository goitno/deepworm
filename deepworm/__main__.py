"""CLI entry point for deepworm."""

from __future__ import annotations

import argparse
import json
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
    return parser


def main(args: list[str] | None = None) -> None:
    parser = build_parser()
    opts = parser.parse_args(args)

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

    # Build config
    config = Config.auto()

    if opts.provider:
        config.provider = opts.provider
        # Reset model to default for new provider if not explicitly set
        if opts.model is None:
            config.model = config._default_model(opts.provider)

    if opts.model:
        config.model = opts.model
    if opts.depth:
        config.depth = opts.depth
    if opts.breadth:
        config.breadth = opts.breadth

    # Run research
    researcher = DeepResearcher(config=config)

    try:
        report = researcher.research(
            opts.topic,
            verbose=not opts.quiet,
            persona=opts.persona,
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Research interrupted.[/yellow]")
        return

    # Output
    if opts.json_output:
        import time
        result = {
            "topic": opts.topic,
            "provider": config.provider,
            "model": config.model,
            "depth": config.depth,
            "breadth": config.breadth,
            "report": report,
        }
        print(json.dumps(result, indent=2))
    elif opts.output:
        path = save_report(report, opts.output, topic=opts.topic)
        console.print(f"\n[green]Report saved to {path}[/green]")
    else:
        print_report(report)


if __name__ == "__main__":
    main()
