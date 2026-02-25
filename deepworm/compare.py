"""Comparison research: research multiple topics and compare them."""

from __future__ import annotations

from typing import Optional

from rich.console import Console

from .config import Config
from .researcher import DeepResearcher

console = Console()

COMPARISON_PROMPT = """You have research reports on the following topics. Write a comparison analysis.

{reports_section}

Write a comprehensive comparison in Markdown format:
1. Title: "Comparison: {topics_joined}"
2. Executive summary comparing key differences and similarities
3. Side-by-side comparison table of key attributes
4. Detailed analysis of differences
5. Detailed analysis of similarities
6. Which is better suited for different use cases
7. Conclusion with recommendation

Be specific and use data from the individual reports. Write clearly and concisely."""


def compare(
    topics: list[str],
    config: Optional[Config] = None,
    verbose: bool = True,
    persona: str | None = None,
) -> str:
    """Research multiple topics and produce a comparison report."""
    config = config or Config.auto()
    researcher = DeepResearcher(config=config)

    reports = {}
    for i, topic in enumerate(topics):
        if verbose:
            console.print(f"\n[bold magenta]Researching topic {i + 1}/{len(topics)}: {topic}[/bold magenta]")
        reports[topic] = researcher.research(topic, verbose=verbose, persona=persona)

    # Synthesize comparison
    if verbose:
        console.print("\n[bold green]Generating comparison...[/bold green]")

    reports_section = ""
    for topic, report in reports.items():
        # Truncate individual reports to avoid token limits
        truncated = report[:3000] if len(report) > 3000 else report
        reports_section += f"\n## Report: {topic}\n{truncated}\n"

    from .llm import get_client
    llm = get_client(config)

    prompt = COMPARISON_PROMPT.format(
        reports_section=reports_section,
        topics_joined=" vs ".join(topics),
    )

    try:
        comparison = llm.chat_with_retry([
            {"role": "system", "content": "You are an expert at comparative analysis."},
            {"role": "user", "content": prompt},
        ], temperature=0.4)
    except Exception as e:
        comparison = f"# Comparison Failed\n\nError: {e}\n\n## Individual Reports\n\n"
        for topic, report in reports.items():
            comparison += f"\n---\n## {topic}\n{report}\n"

    if verbose:
        console.print("[bold green]Done![/bold green]")

    return comparison
