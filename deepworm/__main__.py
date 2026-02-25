"""CLI entry point for deepworm."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

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
        "--config",
        type=str,
        default=None,
        metavar="FILE",
        help="Load config from a specific file (TOML or YAML)",
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
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Enter interactive Q&A mode after research completes",
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help="Copy the report to clipboard after completion",
    )
    parser.add_argument(
        "--no-followup",
        action="store_true",
        help="Disable follow-up question generation",
    )
    parser.add_argument(
        "--lang",
        type=str,
        metavar="CODE",
        help="Output language code (e.g. en, tr, de, fr, es, zh, ja, ko)",
    )
    parser.add_argument(
        "--list-languages",
        action="store_true",
        help="List supported output languages and exit",
    )
    parser.add_argument(
        "--chain",
        type=int,
        metavar="STEPS",
        nargs="?",
        const=3,
        help="Run a chain of N research steps, each diving deeper (default: 3)",
    )
    parser.add_argument(
        "--profile",
        type=str,
        metavar="NAME",
        help="Load a saved configuration profile",
    )
    parser.add_argument(
        "--save-profile",
        type=str,
        metavar="NAME",
        help="Save current configuration as a named profile and exit",
    )
    parser.add_argument(
        "--list-profiles",
        action="store_true",
        help="List saved configuration profiles and exit",
    )
    parser.add_argument(
        "--delete-profile",
        type=str,
        metavar="NAME",
        help="Delete a saved profile and exit",
    )
    parser.add_argument(
        "--export-sources",
        type=str,
        metavar="FILE",
        help="Export discovered sources to file (json/csv/bib)",
    )
    parser.add_argument(
        "--toc",
        action="store_true",
        help="Insert a table of contents into the report",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show report statistics (word count, reading time, etc.)",
    )
    parser.add_argument(
        "--diff",
        nargs=2,
        metavar=("OLD", "NEW"),
        help="Show diff between two report files and exit",
    )
    parser.add_argument(
        "--score",
        action="store_true",
        help="Show report quality score after research",
    )
    parser.add_argument(
        "--sections",
        type=str,
        metavar="PATTERN",
        help="Filter report to sections matching pattern (regex)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        metavar="SECONDS",
        default=None,
        help="Maximum research time in seconds (0 = unlimited)",
    )
    parser.add_argument(
        "--resume",
        type=str,
        metavar="FILE",
        nargs="?",
        const="auto",
        help="Resume research from a saved session file (or 'auto' to find latest)",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        metavar="PATH",
        help="Log to a file in addition to stderr",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["debug", "info", "warning", "error"],
        default=None,
        help="Set logging level",
    )
    parser.add_argument(
        "--metrics",
        action="store_true",
        help="Show detailed research metrics after completion",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="Show research plan before executing (topic analysis & sub-questions)",
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Generate and show research plan without executing research",
    )
    parser.add_argument(
        "--polish",
        action="store_true",
        help="Auto-polish report: run readability, compliance, scoring, and annotation analysis",
    )
    parser.add_argument(
        "--graph",
        nargs="?",
        const="mermaid",
        choices=["mermaid", "dot", "stats", "json"],
        metavar="FORMAT",
        help="Extract knowledge graph from report (mermaid/dot/stats/json, default: mermaid)",
    )
    return parser


def main(args: list[str] | None = None) -> None:
    parser = build_parser()
    opts = parser.parse_args(args)

    if opts.debug:
        logging.basicConfig(level=logging.DEBUG, format="%(name)s %(levelname)s: %(message)s")

    # Setup structured logging
    if opts.log_file or opts.log_level:
        from .log import setup_logging
        level = opts.log_level.upper() if opts.log_level else ("DEBUG" if opts.debug else "WARNING")
        setup_logging(level=level, log_file=opts.log_file)

    # Handle diff mode
    if opts.diff:
        from .diff import diff_reports, diff_summary
        old_path, new_path = opts.diff
        try:
            old_content = open(old_path, encoding="utf-8").read()
            new_content = open(new_path, encoding="utf-8").read()
        except FileNotFoundError as e:
            console.print(f"[red]File not found: {e.filename}[/red]")
            sys.exit(1)
        diff = diff_reports(old_content, new_content, old_label=old_path, new_label=new_path)
        if not diff:
            console.print("[green]Reports are identical.[/green]")
        else:
            summary = diff_summary(old_content, new_content)
            console.print(f"[bold]Diff: {old_path} → {new_path}[/bold]")
            console.print(
                f"  [green]+{summary['added_lines']} lines[/green]  "
                f"[red]-{summary['removed_lines']} lines[/red]  "
                f"[dim]similarity: {summary['similarity_ratio']:.1%}[/dim]\n"
            )
            print(diff)
        return

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

    # Handle languages
    from .languages import get_language, list_languages

    if opts.list_languages:
        langs = list_languages()
        console.print("[bold]Supported output languages:[/bold]\n")
        for lang in langs:
            console.print(f"  [cyan]{lang.code:<4}[/cyan] {lang.name} ({lang.native_name})")
        return

    if opts.lang:
        lang_obj = get_language(opts.lang)
        if lang_obj is None:
            console.print(f"[red]Unknown language code: {opts.lang}[/red]")
            console.print("[dim]Run deepworm --list-languages to see available languages[/dim]")
            sys.exit(1)

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

    # Handle profiles
    from .profiles import delete_profile, list_profiles, load_profile, save_profile

    if opts.list_profiles:
        profiles = list_profiles()
        if not profiles:
            console.print("[dim]No saved profiles. Use --save-profile NAME to create one.[/dim]")
            return
        console.print("[bold]Saved configuration profiles:[/bold]\n")
        for p in profiles:
            console.print(
                f"  [cyan]{p['name']:<16}[/cyan] "
                f"{p['provider']}/{p['model']}  depth={p['depth']} breadth={p['breadth']}"
            )
        return

    if opts.delete_profile:
        if delete_profile(opts.delete_profile):
            console.print(f"[green]Profile '{opts.delete_profile}' deleted.[/green]")
        else:
            console.print(f"[red]Profile '{opts.delete_profile}' not found.[/red]")
        return

    # Build config - from profile or auto-detected
    if opts.profile:
        config = load_profile(opts.profile)
        if config is None:
            console.print(f"[red]Profile '{opts.profile}' not found.[/red]")
            console.print("[dim]Run deepworm --list-profiles to see available profiles[/dim]")
            sys.exit(1)
    else:
        if getattr(opts, "config", None):
            try:
                config = Config.from_file(opts.config)
            except FileNotFoundError:
                console.print(f"[red]Config file not found: {opts.config}[/red]")
                sys.exit(1)
        else:
            config = Config.auto()

    # Save profile if requested (after config is built)
    if opts.save_profile:
        path = save_profile(opts.save_profile, config)
        console.print(f"[green]Profile '{opts.save_profile}' saved.[/green]")
        return

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
    if opts.timeout is not None:
        config.timeout_seconds = opts.timeout

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

    # Chain mode
    if opts.chain is not None:
        if opts.topic is None:
            console.print("[red]Chain mode requires a topic.[/red]")
            sys.exit(1)
        from .chain import research_chain
        try:
            report = research_chain(
                opts.topic,
                steps=opts.chain,
                config=config,
                verbose=not opts.quiet,
                persona=opts.persona,
                lang=getattr(opts, "lang", None),
            )
        except KeyboardInterrupt:
            console.print("\n[yellow]Research chain interrupted.[/yellow]")
            return
        _output_report(report, opts)
        if opts.copy:
            _copy_to_clipboard(report)
        return

    # Resume mode
    if opts.resume:
        from pathlib import Path
        from .session import list_sessions, load_session

        if opts.resume == "auto":
            # Find the latest in-progress session
            sessions = list_sessions()
            in_progress = [s for s in sessions if s.status == "in_progress"]
            if not in_progress:
                console.print("[yellow]No in-progress sessions found to resume.[/yellow]")
                sys.exit(1)
            latest = max(in_progress, key=lambda s: s.updated_at)
            slug = latest.topic.lower().strip()
            import re as _re
            slug = _re.sub(r'[^\w\s-]', '', slug)
            slug = _re.sub(r'[-\s]+', '-', slug)[:50]
            session_path = Path(f".deepworm-session-{slug}.json")
        else:
            session_path = Path(opts.resume)

        try:
            session_data = load_session(session_path)
            meta = session_data["meta"]
            console.print(
                f"[bold cyan]Resuming:[/bold cyan] {meta['topic']}\n"
                f"  Iterations done: {meta['iterations_done']} | Sources: {meta['total_sources']}"
            )
            opts.topic = meta["topic"]
        except FileNotFoundError:
            console.print(f"[red]Session file not found: {session_path}[/red]")
            sys.exit(1)
        except ValueError as e:
            console.print(f"[red]Invalid session file: {e}[/red]")
            sys.exit(1)

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

    # Validate topic
    from .validator import validate_topic
    validation = validate_topic(opts.topic)
    if not validation.is_valid:
        console.print(f"[red bold]Invalid topic:[/red bold] {validation.error}")
        return
    opts.topic = validation.topic
    if validation.has_warnings:
        for w in validation.warnings:
            console.print(f"[yellow]⚠ {w}[/yellow]")
    if validation.has_suggestions:
        for s in validation.suggestions:
            console.print(f"[dim]💡 {s}[/dim]")

    # Research planning
    if getattr(opts, "plan", False) or getattr(opts, "plan_only", False):
        from .planner import generate_plan, estimate_complexity

        console.print("[bold cyan]Analyzing topic...[/bold cyan]")
        try:
            from .llm import get_client
            llm = get_client(config)
            plan = generate_plan(opts.topic, llm)
        except Exception:
            from .planner import _fallback_plan
            plan = _fallback_plan(opts.topic)

        from rich.panel import Panel
        from rich.markdown import Markdown
        console.print(Panel(
            Markdown(plan.to_markdown()),
            title="[bold]Research Plan[/bold]",
            border_style="cyan",
        ))

        if opts.plan_only:
            return

        # Apply suggested settings if user hasn't overridden
        if config.depth == 2 and plan.suggested_depth != 2:
            config = Config(**{**config.__dict__, "depth": plan.suggested_depth})
            console.print(f"[dim]Adjusted depth to {plan.suggested_depth} based on plan[/dim]")
        if config.breadth == 4 and plan.suggested_breadth != 4:
            config = Config(**{**config.__dict__, "breadth": plan.suggested_breadth})
            console.print(f"[dim]Adjusted breadth to {plan.suggested_breadth} based on plan[/dim]")

    # Run research
    researcher = DeepResearcher(config=config, cache=cache)

    try:
        report = researcher.research(
            opts.topic,
            verbose=not opts.quiet,
            persona=opts.persona,
            stream=opts.stream,
            followup=not opts.no_followup,
            lang=getattr(opts, "lang", None),
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

    # Insert TOC if requested
    if opts.toc:
        from .report import inject_toc
        report = inject_toc(report)

    # Filter sections if requested
    if opts.sections:
        import re as _re
        from .report import extract_sections
        sections = extract_sections(report)
        filtered = [s for s in sections if _re.search(opts.sections, s["heading"], _re.IGNORECASE)]
        if filtered:
            parts = []
            for s in filtered:
                level = s["level"]
                parts.append(f"{'#' * level} {s['heading']}\n\n{s['content'].strip()}")
            report = "\n\n".join(parts)
        else:
            console.print(f"[yellow]No sections matched pattern '{opts.sections}'[/yellow]")

    _output_report(report, opts)

    # Show report stats if requested
    if opts.stats:
        from .report import report_stats
        s = report_stats(report)
        console.print("\n[bold]Report Statistics[/bold]")
        console.print(f"  Words:       {s['word_count']:,}")
        console.print(f"  Sentences:   {s['sentence_count']}")
        console.print(f"  Paragraphs:  {s['paragraph_count']}")
        console.print(f"  Headings:    {s['heading_count']}")
        console.print(f"  Links:       {s['link_count']}")
        console.print(f"  Reading:     ~{s['reading_time_minutes']} min")

    # Show report quality score if requested
    if opts.score:
        from .scoring import score_report
        qs = score_report(report)
        console.print(f"\n[bold]Report Quality: {qs.grade} ({qs.overall:.0%})[/bold]")
        console.print(f"  Structure:    {qs.structure:.0%}")
        console.print(f"  Depth:        {qs.depth:.0%}")
        console.print(f"  Sources:      {qs.sources:.0%}")
        console.print(f"  Readability:  {qs.readability:.0%}")
        console.print(f"  Completeness: {qs.completeness:.0%}")
        if qs.suggestions:
            console.print("\n[dim]Suggestions:[/dim]")
            for tip in qs.suggestions:
                console.print(f"  [dim]• {tip}[/dim]")

    # Polish mode: full post-processing pipeline
    if getattr(opts, "polish", False):
        from .readability import analyze_readability
        from .compliance import check_compliance
        from .scoring import score_report as _score_polish
        from .annotations import auto_annotate, annotate_report

        console.print()
        console.print(Panel("[bold]Polish Pipeline[/bold]", border_style="cyan", expand=False))
        console.print()

        # Step 1: Readability
        ra = analyze_readability(report)
        r_color = "green" if ra.flesch_reading_ease >= 60 else ("yellow" if ra.flesch_reading_ease >= 30 else "red")
        console.print(f"  [bold]1.[/bold] Readability   [{r_color}]{ra.reading_level}[/{r_color}] (Flesch {ra.flesch_reading_ease:.0f})")
        console.print(
            f"     Grade: {ra.grade_level} │ "
            f"Fog: {ra.gunning_fog:.1f} │ "
            f"Words: {ra.total_words:,} │ "
            f"Vocab: {ra.vocabulary_richness:.0%}"
        )

        # Step 2: Compliance
        cr = check_compliance(report)
        status = "[green]✓ PASS[/green]" if cr.is_compliant else "[red]✗ FAIL[/red]"
        console.print(f"\n  [bold]2.[/bold] Compliance   {status} ({cr.score:.0f}/100)")
        if cr.issues:
            errors = cr.error_count
            warnings = cr.warning_count
            info = len(cr.issues) - errors - warnings
            console.print(
                f"     [red]{errors} errors[/red] │ "
                f"[yellow]{warnings} warnings[/yellow] │ "
                f"[dim]{info} info[/dim]"
            )
            for issue in cr.issues[:5]:
                sev_color = {"error": "red", "warning": "yellow", "info": "dim", "suggestion": "cyan"}
                color = sev_color.get(issue.severity.value, "dim")
                console.print(f"     [{color}]• {issue.message}[/{color}]")
            if len(cr.issues) > 5:
                console.print(f"     [dim]… +{len(cr.issues) - 5} more[/dim]")

        # Step 3: Quality Score
        qs_polish = _score_polish(report)
        grade_color = "green" if qs_polish.overall >= 0.8 else ("yellow" if qs_polish.overall >= 0.6 else "red")
        console.print(f"\n  [bold]3.[/bold] Quality      [{grade_color}]{qs_polish.grade}[/{grade_color}] ({qs_polish.overall:.0%})")

        # Quality dimensions as a mini bar chart
        dims = [
            ("Structure", qs_polish.structure),
            ("Depth", qs_polish.depth),
            ("Sources", qs_polish.sources),
            ("Readability", qs_polish.readability),
            ("Complete", qs_polish.completeness),
        ]
        for name, val in dims:
            bar_len = int(val * 20)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            bar_color = "green" if val >= 0.8 else ("yellow" if val >= 0.6 else "red")
            console.print(f"     {name:<12} [{bar_color}]{bar}[/{bar_color}] {val:.0%}")

        # Step 4: Auto-annotations
        anns = auto_annotate(report)
        ann_count = len(anns.annotations)
        if ann_count > 0:
            console.print(f"\n  [bold]4.[/bold] Annotations  [yellow]{ann_count} findings[/yellow]")
            from collections import Counter
            type_counts = Counter(a.annotation_type.value for a in anns.annotations)
            parts = [f"{v} {k}" for k, v in type_counts.most_common()]
            console.print(f"     {' │ '.join(parts)}")
            for a in anns.annotations[:5]:
                type_color = {
                    "fact_check": "red", "warning": "yellow",
                    "question": "cyan", "todo": "magenta",
                }
                color = type_color.get(a.annotation_type.value, "dim")
                target = f" → {a.target[:50]}…" if a.target and len(a.target) > 50 else (f" → {a.target}" if a.target else "")
                console.print(f"     [{color}]• [{a.annotation_type.value}] {a.text}{target}[/{color}]")
            if ann_count > 5:
                console.print(f"     [dim]… +{ann_count - 5} more[/dim]")
        else:
            console.print(f"\n  [bold]4.[/bold] Annotations  [green]✓ No issues[/green]")

        # Summary panel
        summary_tbl = Table(show_header=False, box=None, padding=(0, 2))
        summary_tbl.add_column(style="bold")
        summary_tbl.add_column()
        summary_tbl.add_row("Quality", f"{qs_polish.grade} ({qs_polish.overall:.0%})")
        summary_tbl.add_row("Compliance", f"{'PASS' if cr.is_compliant else 'FAIL'} ({cr.score:.0f}/100)")
        summary_tbl.add_row("Readability", f"{ra.reading_level} (Flesch {ra.flesch_reading_ease:.0f})")
        summary_tbl.add_row("Annotations", f"{ann_count} findings")
        console.print()
        console.print(Panel(summary_tbl, title="[bold cyan]Summary[/bold cyan]", border_style="cyan", expand=False))

    # Knowledge graph extraction
    if getattr(opts, "graph", None) is not None:
        from .graph import extract_concept_graph, extract_link_graph, merge_graphs

        console.print()
        console.print(Panel("[bold]Knowledge Graph[/bold]", border_style="cyan", expand=False))
        console.print()

        concept_g = extract_concept_graph(report)
        link_g = extract_link_graph(report)
        graph = merge_graphs(concept_g, link_g)
        graph.name = opts.topic or "research"

        gs = graph.stats()

        # Stats table
        stats_tbl = Table(show_header=False, box=None, padding=(0, 2))
        stats_tbl.add_column(style="bold")
        stats_tbl.add_column()
        stats_tbl.add_row("Nodes", f"{gs.node_count}")
        stats_tbl.add_row("Edges", f"{gs.edge_count}")
        stats_tbl.add_row("Components", f"{gs.components}")
        stats_tbl.add_row("Density", f"{gs.density:.3f}")
        stats_tbl.add_row("Avg Degree", f"{gs.avg_degree:.1f}")
        console.print(stats_tbl)

        fmt = opts.graph
        if fmt == "mermaid":
            output = graph.to_mermaid()
            console.print(f"\n[dim]```mermaid[/dim]")
            print(output)
            console.print(f"[dim]```[/dim]")
        elif fmt == "dot":
            output = graph.to_dot()
            print(output)
        elif fmt == "json":
            import json as _json
            print(_json.dumps(graph.to_dict(), indent=2))
        elif fmt == "stats":
            # Show nodes sorted by degree (most connected first)
            if graph.nodes:
                console.print(f"\n  [bold]Top connected nodes:[/bold]")
                node_degrees = [(n, graph.degree(n.node_id)) for n in graph.nodes]
                node_degrees.sort(key=lambda x: x[1], reverse=True)
                top_tbl = Table(show_header=True, header_style="bold", padding=(0, 1))
                top_tbl.add_column("Node", style="cyan")
                top_tbl.add_column("Type", style="dim")
                top_tbl.add_column("Degree", justify="right")
                for node, deg in node_degrees[:10]:
                    bar = "█" * deg
                    top_tbl.add_row(node.label[:40], node.node_type, f"{deg} {bar}")
                console.print(top_tbl)

        # Save graph to file if --output is specified
        if opts.output and fmt in ("mermaid", "dot"):
            ext = ".mmd" if fmt == "mermaid" else ".dot"
            graph_path = opts.output.rsplit(".", 1)[0] + ext if "." in opts.output else opts.output + ext
            with open(graph_path, "w", encoding="utf-8") as f:
                f.write(output)
            console.print(f"\n[green]✓ Graph saved to {graph_path}[/green]")

    # Show research metrics if requested
    if opts.metrics:
        m = getattr(researcher, "last_metrics", None)
        if m:
            console.print(f"\n[bold]Research Metrics[/bold]")
            console.print(f"  Total time:      {m.total_time:.1f}s")
            console.print(f"  Search time:     {m.search_time:.1f}s")
            console.print(f"  Analysis time:   {m.analysis_time:.1f}s")
            console.print(f"  Synthesis time:  {m.synthesis_time:.1f}s")
            console.print(f"  API calls:       {m.api_calls}")
            console.print(f"  Queries:         {m.search_queries}")
            console.print(f"  Pages fetched:   {m.pages_fetched}")
            console.print(f"  Sources:         {m.sources_analyzed}")
            console.print(f"  Duplicates:      {m.duplicates_skipped}")
            console.print(f"  Fetch rate:      {m.success_rate:.0%}")
            if m.retries > 0:
                console.print(f"  Retries:         {m.retries}")
            if m.errors > 0:
                console.print(f"  Errors:          {m.errors}")

        # Token usage from LLM client
        tracker = getattr(researcher, "last_token_tracker", None)
        if tracker and tracker.call_count > 0:
            console.print(f"\n[bold]Token Usage[/bold]")
            console.print(f"  API calls:       {tracker.call_count}")
            console.print(f"  Input tokens:    {tracker.total_prompt_tokens:,}")
            console.print(f"  Output tokens:   {tracker.total_completion_tokens:,}")
            console.print(f"  Total tokens:    {tracker.total_tokens:,}")
            if tracker.total_cost_usd > 0:
                console.print(f"  Est. cost:       ${tracker.total_cost_usd:.4f}")

    # Export sources if requested
    if opts.export_sources:
        from .sources import export_sources, sources_to_dicts
        source_dicts = sources_to_dicts(getattr(researcher, "last_sources", []))
        if source_dicts:
            path = export_sources(source_dicts, opts.export_sources)
            console.print(f"[green]Sources exported to {path} ({len(source_dicts)} sources)[/green]")
        else:
            console.print("[yellow]No sources to export.[/yellow]")

    # Copy to clipboard if requested
    if opts.copy:
        _copy_to_clipboard(report)

    # Interactive Q&A mode
    if opts.interactive:
        _interactive_qa(config, report, opts.topic, cache)


def _copy_to_clipboard(text: str) -> None:
    """Copy text to system clipboard."""
    import subprocess
    try:
        if sys.platform == "darwin":
            proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            proc.communicate(text.encode("utf-8"))
        elif sys.platform.startswith("linux"):
            for cmd in [["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]]:
                try:
                    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
                    proc.communicate(text.encode("utf-8"))
                    break
                except FileNotFoundError:
                    continue
            else:
                console.print("[yellow]Install xclip or xsel for clipboard support.[/yellow]")
                return
        elif sys.platform == "win32":
            proc = subprocess.Popen(["clip"], stdin=subprocess.PIPE)
            proc.communicate(text.encode("utf-16le"))
        else:
            console.print("[yellow]Clipboard not supported on this platform.[/yellow]")
            return
        console.print("[green]Report copied to clipboard.[/green]")
    except Exception as e:
        console.print(f"[yellow]Could not copy to clipboard: {e}[/yellow]")


def _interactive_qa(config: "Config", report: str, topic: str, cache) -> None:
    """Post-research interactive Q&A loop."""
    from .llm import get_client

    console.print("\n[bold cyan]Interactive mode[/bold cyan] — ask follow-up questions about the report.")
    console.print("[dim]Type 'exit' or press Ctrl+C to quit.[/dim]\n")

    try:
        llm = get_client(config)
    except Exception as e:
        console.print(f"[red]Error initializing LLM: {e}[/red]")
        return

    system_msg = (
        "You are a research assistant. The user has just received the research report below. "
        "Answer follow-up questions using the report content. If the answer isn't in the report, "
        "say so and provide your best knowledge.\n\n"
        f"Research topic: {topic}\n\n"
        f"Report:\n{report[:6000]}"
    )
    messages = [{"role": "system", "content": system_msg}]

    while True:
        try:
            question = console.input("[bold green]Q:[/bold green] ")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Exiting interactive mode.[/dim]")
            break

        question = question.strip()
        if not question:
            continue
        if question.lower() in ("exit", "quit", "q"):
            console.print("[dim]Exiting interactive mode.[/dim]")
            break

        messages.append({"role": "user", "content": question})

        try:
            answer = llm.chat(messages, temperature=0.3)
            messages.append({"role": "assistant", "content": answer})
            console.print(f"\n[bold blue]A:[/bold blue] {answer}\n")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]\n")
            messages.pop()


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
