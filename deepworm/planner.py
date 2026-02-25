"""Research planning and topic analysis.

Pre-research analysis that generates a structured research plan:
- Identifies key aspects to investigate
- Suggests optimal depth/breadth settings
- Breaks down complex topics into sub-questions
- Estimates research complexity
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


PLAN_PROMPT = """Analyze this research topic and create a structured research plan.

Topic: {topic}

Return a JSON object with these fields:
{{
  "title": "Clear, focused research title",
  "complexity": "low|medium|high",
  "sub_questions": ["list of 3-5 specific sub-questions to investigate"],
  "key_aspects": ["list of 3-5 key aspects/angles to cover"],
  "suggested_depth": 2,
  "suggested_breadth": 4,
  "potential_challenges": ["list of 1-3 research challenges"],
  "related_topics": ["list of 2-3 related topics for further research"]
}}

Be specific and actionable. The sub_questions should directly guide search queries.
The complexity assessment should consider: topic breadth, available information, controversy level.
Adjust suggested_depth (1-5) and suggested_breadth (2-8) based on complexity."""


@dataclass
class ResearchPlan:
    """Structured research plan."""
    title: str
    complexity: str  # low, medium, high
    sub_questions: list[str] = field(default_factory=list)
    key_aspects: list[str] = field(default_factory=list)
    suggested_depth: int = 2
    suggested_breadth: int = 4
    potential_challenges: list[str] = field(default_factory=list)
    related_topics: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "complexity": self.complexity,
            "sub_questions": self.sub_questions,
            "key_aspects": self.key_aspects,
            "suggested_depth": self.suggested_depth,
            "suggested_breadth": self.suggested_breadth,
            "potential_challenges": self.potential_challenges,
            "related_topics": self.related_topics,
        }

    def to_markdown(self) -> str:
        """Format the plan as readable markdown."""
        lines = [
            f"# Research Plan: {self.title}",
            "",
            f"**Complexity:** {self.complexity} | "
            f"**Recommended Depth:** {self.suggested_depth} | "
            f"**Recommended Breadth:** {self.suggested_breadth}",
            "",
        ]

        if self.sub_questions:
            lines.append("## Sub-Questions")
            lines.append("")
            for i, q in enumerate(self.sub_questions, 1):
                lines.append(f"{i}. {q}")
            lines.append("")

        if self.key_aspects:
            lines.append("## Key Aspects")
            lines.append("")
            for aspect in self.key_aspects:
                lines.append(f"- {aspect}")
            lines.append("")

        if self.potential_challenges:
            lines.append("## Potential Challenges")
            lines.append("")
            for ch in self.potential_challenges:
                lines.append(f"- {ch}")
            lines.append("")

        if self.related_topics:
            lines.append("## Related Topics")
            lines.append("")
            for t in self.related_topics:
                lines.append(f"- {t}")
            lines.append("")

        return "\n".join(lines)


def generate_plan(topic: str, llm_client: Any) -> ResearchPlan:
    """Generate a research plan for a topic using LLM.

    Args:
        topic: The research topic.
        llm_client: An LLM client with chat_json method.

    Returns:
        ResearchPlan with structured analysis.
    """
    prompt = PLAN_PROMPT.format(topic=topic)

    try:
        result = llm_client.chat_json([
            {"role": "system", "content": "You return only valid JSON objects."},
            {"role": "user", "content": prompt},
        ])
    except Exception as e:
        logger.debug("Failed to generate plan: %s", e)
        return _fallback_plan(topic)

    if not isinstance(result, dict):
        return _fallback_plan(topic)

    return ResearchPlan(
        title=str(result.get("title", topic)),
        complexity=str(result.get("complexity", "medium")),
        sub_questions=[str(q) for q in result.get("sub_questions", [])[:5]],
        key_aspects=[str(a) for a in result.get("key_aspects", [])[:5]],
        suggested_depth=_clamp(int(result.get("suggested_depth", 2)), 1, 5),
        suggested_breadth=_clamp(int(result.get("suggested_breadth", 4)), 2, 8),
        potential_challenges=[str(c) for c in result.get("potential_challenges", [])[:3]],
        related_topics=[str(t) for t in result.get("related_topics", [])[:3]],
    )


def estimate_complexity(topic: str) -> str:
    """Quick heuristic complexity estimate without LLM.

    Considers topic length, specificity, and keyword signals.
    """
    topic_lower = topic.lower()
    words = topic_lower.split()

    score = 0

    # Longer topics tend to be more specific/complex
    if len(words) > 10:
        score += 2
    elif len(words) > 5:
        score += 1

    # Comparison suggests multi-faceted research
    comparison_words = {"vs", "versus", "compared", "comparison", "difference", "between"}
    if comparison_words & set(words):
        score += 2

    # Technical/scientific topics
    technical_words = {
        "algorithm", "architecture", "benchmark", "framework", "protocol",
        "quantum", "molecular", "genomic", "neural", "optimization",
        "cryptographic", "distributed", "concurrent", "async",
    }
    if technical_words & set(words):
        score += 1

    # Questions suggest well-scoped research
    if topic.strip().endswith("?") or any(w in words for w in ["how", "why", "what"]):
        score -= 1

    if score >= 3:
        return "high"
    elif score >= 1:
        return "medium"
    return "low"


def _fallback_plan(topic: str) -> ResearchPlan:
    """Create a basic plan without LLM."""
    complexity = estimate_complexity(topic)
    depth_map = {"low": 1, "medium": 2, "high": 3}
    breadth_map = {"low": 3, "medium": 4, "high": 6}

    return ResearchPlan(
        title=topic,
        complexity=complexity,
        suggested_depth=depth_map.get(complexity, 2),
        suggested_breadth=breadth_map.get(complexity, 4),
    )


def _clamp(value: int, min_val: int, max_val: int) -> int:
    return max(min_val, min(max_val, value))
