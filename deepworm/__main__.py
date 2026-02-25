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
        choices=["markdown", "html", "text", "json", "pdf"],
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
    parser.add_argument(
        "--history",
        nargs="?",
        const=10,
        type=int,
        metavar="N",
        help="Show last N research entries (default: 10) and exit",
    )
    parser.add_argument(
        "--history-search",
        type=str,
        metavar="QUERY",
        help="Search research history by topic keyword and exit",
    )
    parser.add_argument(
        "--history-stats",
        action="store_true",
        help="Show aggregate research statistics and exit",
    )
    parser.add_argument(
        "--history-clear",
        action="store_true",
        help="Clear all research history and exit",
    )
    parser.add_argument(
        "--serve",
        nargs="?",
        const=8888,
        type=int,
        metavar="PORT",
        help="Start web UI server (default port: 8888)",
    )
    parser.add_argument(
        "--template", "-t",
        type=str,
        metavar="NAME",
        help="Use a research template (e.g. quick, deep, academic, market, technical)",
    )
    parser.add_argument(
        "--list-templates",
        action="store_true",
        help="List available research templates and exit",
    )
    return parser


def main(args: list[str] | None = None) -> None:
    parser = build_parser()
    opts = parser.parse_args(args)

    if opts.debug:
        logging.basicConfig(level=logging.DEBUG, format="%(name)s %(levelname)s: %(message)s")

    # Handle history operations
    from .history import clear_history, list_entries, search_history, stats as history_stats

    if opts.history is not None:
        entries = list_entries(limit=opts.history)
        if not entries:
            console.print("[dim]No research history yet.[/dim]")
            return
        console.print(f"[bold]Last {len(entries)} research entries:[/bold]\n")
        for e in entries:
            console.print(
                f"  [cyan]{e.created_iso[:19]}[/cyan]  "
                f"[bold]{e.topic[:60]}[/bold]  "
                f"[dim]{e.provider}/{e.model} · {e.total_sources} sources · {e.elapsed_seconds:.0f}s[/dim]"
            )
        return

    if opts.history_search:
        entries = search_history(opts.history_search)
        if not entries:
            console.print(f"[dim]No history entries matching '{opts.history_search}'.[/dim]")
            return
        console.print(f"[bold]Found {len(entries)} entries matching '{opts.history_search}':[/bold]\n")
        for e in entries:
            console.print(
                f"  [cyan]{e.created_iso[:19]}[/cyan]  "
                f"[bold]{e.topic[:60]}[/bold]  "
                f"[dim]{e.total_sources} sources · {e.elapsed_seconds:.0f}s[/dim]"
            )
        return

    if opts.history_stats:
        s = history_stats()
        if s["total_researches"] == 0:
            console.print("[dim]No research history yet.[/dim]")
            return
        console.print("[bold]Research Statistics[/bold]\n")
        console.print(f"  Total researches:  {s['total_researches']}")
        console.print(f"  Total sources:     {s['total_sources']}")
        console.print(f"  Total time:        {s['total_time_seconds']:.0f}s")
        console.print(f"  Avg time/research: {s['avg_time_seconds']:.1f}s")
        console.print(f"  Avg sources:       {s['avg_sources']:.1f}")
        console.print(f"  Models used:       {', '.join(s['models_used'])}")
        console.print(f"  Providers used:    {', '.join(s['providers_used'])}")
        return

    if opts.history_clear:
        count = clear_history()
        console.print(f"[green]Cleared {count} history entries.[/green]")
        return

    # Handle web UI
    if opts.serve is not None:
        from .web import serve
        serve(port=opts.serve)
        return

    # Handle templates
    from .templates import get_template, list_templates

    if opts.list_templates:
        templates = list_templates()
        console.print("[bold]Available research templates:[/bold]\n")
        for t in templates:
            console.print(f"  [cyan]{t.name:<14}[/cyan] {t.description}")
            if t.persona:
                console.print(f"  [dim]{'':14} Persona: {t.persona}[/dim]")
        return

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

    # Apply template if specified
    template = None
    if opts.template:
        template = get_template(opts.template)
        if template is None:
            console.print(f"[red]Unknown template: {opts.template}[/red]")
            console.print("[dim]Run deepworm --list-templates to see available templates[/dim]")
            sys.exit(1)
        template.apply_to_config(config)
        if template.persona and not opts.persona:
            opts.persona = template.persona

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
    except Exception as e:
        # Import our custom exceptions
        from .exceptions import DeepWormError
        if isinstance(e, DeepWormError):
            console.print(f"\n[red bold]Error:[/red bold] {e}")
            if e.hint:
                console.print(f"[dim]  Hint: {e.hint}[/dim]")
        else:
            console.print(f"\n[red bold]Unexpected error:[/red bold] {e}")
            if opts.debug:
                import traceback
                traceback.print_exc()
            else:
                console.print("[dim]  Run with --debug for full traceback[/dim]")
        sys.exit(1)

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
            ext_map = {".html": "html", ".htm": "html", ".txt": "text", ".json": "json", ".pdf": "pdf"}
            ext = os.path.splitext(opts.output)[1].lower()
            fmt = ext_map.get(ext, "markdown")
        path = save_report(report, opts.output, topic=topic, fmt=fmt)
        console.print(f"\n[green]Report saved to {path}[/green]")
    else:
        print_report(report)


if __name__ == "__main__":
    main()
