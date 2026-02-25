"""Research chaining – run sequential deep-dives that build on each other.

A chain takes an initial topic, researches it, then uses the report to
generate a more focused follow-up topic, and repeats for the configured
number of steps.  Each step produces a section in the final combined report.

Usage:
    from deepworm.chain import research_chain

    report = research_chain("AI in healthcare", steps=3)
"""

from __future__ import annotations

import json
from typing import Optional

from .config import Config
from .llm import LLMClient, get_client
from .researcher import DeepResearcher


CHAIN_PROMPT = """Based on the research report below, identify the single most important sub-topic that deserves deeper investigation. This should be a specific aspect that was mentioned but not fully explored.

Topic: {topic}

Report excerpt:
{excerpt}

Return a JSON object with two keys:
- "topic": a specific, focused research question (string)
- "reason": brief explanation of why this deserves deeper research (string)

Example: {{"topic": "How does federated learning address data privacy in healthcare?", "reason": "The report mentioned privacy concerns but didn't explore technical solutions."}}"""


def research_chain(
    topic: str,
    steps: int = 3,
    config: Optional[Config] = None,
    verbose: bool = True,
    persona: Optional[str] = None,
    lang: Optional[str] = None,
) -> str:
    """Run a chain of research steps, each building on the previous.

    Args:
        topic: Initial research topic.
        steps: Number of research steps in the chain.
        config: Optional Config override.
        verbose: Show progress output.
        persona: Optional research persona.
        lang: Optional language code.

    Returns:
        Combined report from all chain steps.
    """
    from rich.console import Console
    from rich.panel import Panel

    console = Console()

    cfg = config or Config.auto()
    researcher = DeepResearcher(config=cfg)
    llm = get_client(cfg)

    sections: list[str] = []
    current_topic = topic

    for step in range(steps):
        if verbose:
            console.print(Panel(
                f"[bold]Step {step + 1}/{steps}:[/bold] {current_topic}",
                title="Research Chain",
                border_style="magenta",
            ))

        # Run research on the current topic
        report = researcher.research(
            current_topic,
            verbose=verbose,
            persona=persona,
            followup=False,  # Don't add follow-up questions to intermediate reports
            lang=lang,
        )

        sections.append(f"## Chain Step {step + 1}: {current_topic}\n\n{report}")

        # If not the last step, generate the next topic
        if step < steps - 1:
            next_topic = _generate_next_topic(llm, current_topic, report)
            if next_topic:
                if verbose:
                    console.print(f"\n[bold magenta]Next focus:[/bold magenta] {next_topic}\n")
                current_topic = next_topic
            else:
                if verbose:
                    console.print("[dim]Could not generate next topic, ending chain.[/dim]")
                break

    # Combine all sections
    combined = f"# Research Chain: {topic}\n\n"
    combined += f"*{steps}-step deep dive*\n\n"
    combined += "\n\n---\n\n".join(sections)
    combined += f"\n\n---\n\n## Chain Summary\n\nThis research chain explored **{topic}** "
    combined += f"across {len(sections)} progressive steps, diving deeper into sub-topics "
    combined += "identified during each phase."

    return combined


def _generate_next_topic(llm: LLMClient, topic: str, report: str) -> Optional[str]:
    """Use LLM to pick the next subtopic to research."""
    excerpt = report[:3000]
    prompt = CHAIN_PROMPT.format(topic=topic, excerpt=excerpt)
    try:
        result = llm.chat_json([
            {"role": "system", "content": "You return only valid JSON objects."},
            {"role": "user", "content": prompt},
        ])
        if isinstance(result, dict) and "topic" in result:
            return str(result["topic"])
    except Exception:
        pass
    return None
