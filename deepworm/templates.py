"""Research templates for common research patterns.

Templates provide pre-configured settings (depth, breadth, persona,
custom prompts) for different types of research tasks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ResearchTemplate:
    """A reusable research configuration template."""

    name: str
    description: str
    depth: int = 2
    breadth: int = 4
    persona: str = ""
    system_prompt: str = ""
    query_prefix: str = ""
    tags: list[str] = field(default_factory=list)

    def apply_to_config(self, config: Any) -> Any:
        """Apply template settings to a Config object."""
        config.depth = self.depth
        config.breadth = self.breadth
        return config


# ── Built-in Templates ──────────────────────────────────────────

TEMPLATES: dict[str, ResearchTemplate] = {}


def register_template(template: ResearchTemplate) -> None:
    """Register a custom template."""
    TEMPLATES[template.name] = template


def get_template(name: str) -> ResearchTemplate | None:
    """Get a template by name."""
    return TEMPLATES.get(name)


def list_templates() -> list[ResearchTemplate]:
    """List all available templates."""
    return list(TEMPLATES.values())


# ── Built-in template definitions ───────────────────────────────

_BUILTIN = [
    ResearchTemplate(
        name="quick",
        description="Fast overview — 1 iteration, 3 queries",
        depth=1,
        breadth=3,
        tags=["speed"],
    ),
    ResearchTemplate(
        name="deep",
        description="Thorough research — 4 iterations, 6 queries each",
        depth=4,
        breadth=6,
        tags=["thorough"],
    ),
    ResearchTemplate(
        name="academic",
        description="Academic-style research with scholarly focus",
        depth=3,
        breadth=5,
        persona="academic researcher writing a literature review",
        query_prefix="scholarly research ",
        tags=["academic", "scholarly"],
    ),
    ResearchTemplate(
        name="market",
        description="Market analysis with business focus",
        depth=3,
        breadth=6,
        persona="market research analyst at a consulting firm",
        tags=["business", "market"],
    ),
    ResearchTemplate(
        name="technical",
        description="Technical deep-dive with implementation details",
        depth=3,
        breadth=5,
        persona="senior software engineer evaluating technologies",
        tags=["technical", "engineering"],
    ),
    ResearchTemplate(
        name="news",
        description="Current events and latest developments",
        depth=2,
        breadth=6,
        persona="investigative journalist",
        query_prefix="latest news ",
        tags=["news", "current"],
    ),
    ResearchTemplate(
        name="competitive",
        description="Competitive analysis of products or companies",
        depth=3,
        breadth=6,
        persona="competitive intelligence analyst",
        tags=["business", "competitive"],
    ),
    ResearchTemplate(
        name="tutorial",
        description="How-to guide and learning resource compilation",
        depth=2,
        breadth=5,
        persona="technical writer creating a comprehensive tutorial",
        tags=["learning", "howto"],
    ),
    ResearchTemplate(
        name="security",
        description="Security analysis and vulnerability research",
        depth=4,
        breadth=5,
        persona="cybersecurity researcher",
        tags=["security", "cybersecurity"],
    ),
    ResearchTemplate(
        name="health",
        description="Health and medical information (not medical advice)",
        depth=3,
        breadth=5,
        persona="health science writer summarizing peer-reviewed research",
        tags=["health", "medical"],
    ),
]

# Register built-in templates
for _t in _BUILTIN:
    register_template(_t)
