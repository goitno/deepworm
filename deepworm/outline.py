"""Report outline generation.

Generate structured outlines for research reports:
- Hierarchical section structure
- Estimated word counts per section
- Key points to cover
- Support for multiple outline styles
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class OutlineSection:
    """A section in a report outline."""
    title: str
    level: int  # 1 = top-level (h1), 2 = sub-section, etc.
    key_points: list[str] = field(default_factory=list)
    estimated_words: int = 0
    children: list["OutlineSection"] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "level": self.level,
            "key_points": self.key_points,
            "estimated_words": self.estimated_words,
            "children": [c.to_dict() for c in self.children],
        }


@dataclass
class ReportOutline:
    """Complete report outline."""
    title: str
    sections: list[OutlineSection] = field(default_factory=list)
    total_estimated_words: int = 0
    style: str = "comprehensive"  # comprehensive, brief, academic

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "sections": [s.to_dict() for s in self.sections],
            "total_estimated_words": self.total_estimated_words,
            "style": self.style,
        }

    def to_markdown(self) -> str:
        """Render the outline as markdown."""
        lines = [
            f"# Outline: {self.title}",
            "",
            f"*Style: {self.style} | Estimated length: ~{self.total_estimated_words} words*",
            "",
        ]

        for section in self.sections:
            lines.extend(_render_section(section))

        return "\n".join(lines)

    @property
    def section_count(self) -> int:
        """Total number of sections (including nested)."""
        return _count_sections(self.sections)


def _render_section(section: OutlineSection, indent: int = 0) -> list[str]:
    """Render a section and its children as markdown."""
    prefix = "  " * indent
    # Use markdown heading for level 1-3, bullets for deeper
    if section.level <= 3 and indent == 0:
        heading = "#" * (section.level + 1)
        lines = [f"{heading} {section.title}"]
    else:
        lines = [f"{prefix}- **{section.title}**"]

    if section.estimated_words:
        lines.append(f"{prefix}  *~{section.estimated_words} words*")

    for point in section.key_points:
        lines.append(f"{prefix}  - {point}")

    for child in section.children:
        lines.extend(_render_section(child, indent + 1))

    lines.append("")
    return lines


def _count_sections(sections: list[OutlineSection]) -> int:
    """Count total sections recursively."""
    total = len(sections)
    for s in sections:
        total += _count_sections(s.children)
    return total


def generate_outline(
    topic: str,
    style: str = "comprehensive",
    num_sections: int | None = None,
) -> ReportOutline:
    """Generate a report outline for a topic.

    Uses heuristic analysis to create an appropriate outline structure
    based on the topic and requested style.

    Args:
        topic: Research topic.
        style: "comprehensive", "brief", or "academic".
        num_sections: Override number of main sections.

    Returns:
        ReportOutline with hierarchical structure.
    """
    style = style if style in ("comprehensive", "brief", "academic") else "comprehensive"

    if style == "brief":
        return _brief_outline(topic, num_sections)
    elif style == "academic":
        return _academic_outline(topic, num_sections)
    else:
        return _comprehensive_outline(topic, num_sections)


def outline_from_report(report: str) -> ReportOutline:
    """Extract an outline from an existing markdown report.

    Parses heading structure to reconstruct the outline.

    Args:
        report: Markdown report text.

    Returns:
        ReportOutline reflecting the report's structure.
    """
    sections: list[OutlineSection] = []
    title = "Report"

    lines = report.split("\n")
    current_sections: dict[int, list[OutlineSection]] = {}

    for line in lines:
        heading_match = re.match(r"^(#{1,6})\s+(.+)", line)
        if heading_match:
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()

            if level == 1:
                title = heading_text
                continue

            section = OutlineSection(
                title=heading_text,
                level=level - 1,  # Normalize: h2 → level 1
            )

            if level == 2:
                sections.append(section)
                current_sections[2] = sections
            else:
                parent_level = level - 1
                parent_list = current_sections.get(parent_level)
                if parent_list and parent_list:
                    parent_list[-1].children.append(section)
                    current_sections[level] = parent_list[-1].children
                else:
                    sections.append(section)

    # Estimate words per section from content
    _estimate_section_words(sections, report)

    total_words = len(report.split())
    return ReportOutline(
        title=title,
        sections=sections,
        total_estimated_words=total_words,
    )


def _estimate_section_words(sections: list[OutlineSection], report: str) -> None:
    """Estimate word count for each section based on report content."""
    lines = report.split("\n")
    section_starts: list[tuple[int, OutlineSection]] = []

    for i, line in enumerate(lines):
        heading_match = re.match(r"^(#{2,6})\s+(.+)", line)
        if heading_match:
            heading_text = heading_match.group(2).strip()
            section = _find_section(sections, heading_text)
            if section:
                section_starts.append((i, section))

    # Calculate word counts between sections
    for idx, (start_line, section) in enumerate(section_starts):
        if idx + 1 < len(section_starts):
            end_line = section_starts[idx + 1][0]
        else:
            end_line = len(lines)
        content = " ".join(lines[start_line + 1:end_line])
        section.estimated_words = len(content.split())


def _find_section(sections: list[OutlineSection], title: str) -> Optional[OutlineSection]:
    """Find a section by title, searching recursively."""
    for s in sections:
        if s.title == title:
            return s
        found = _find_section(s.children, title)
        if found:
            return found
    return None


def _comprehensive_outline(topic: str, num_sections: int | None) -> ReportOutline:
    """Generate a comprehensive outline."""
    n = num_sections or 6
    topic_lower = topic.lower()

    # Detect if it's a comparison topic
    is_comparison = any(w in topic_lower for w in ["vs", "versus", "compare", "comparison"])

    if is_comparison:
        sections = _comparison_sections(topic, n)
    else:
        sections = _standard_sections(topic, n)

    total = sum(s.estimated_words for s in sections)
    return ReportOutline(
        title=topic,
        sections=sections,
        total_estimated_words=total,
        style="comprehensive",
    )


def _brief_outline(topic: str, num_sections: int | None) -> ReportOutline:
    """Generate a brief outline."""
    n = num_sections or 3
    sections = [
        OutlineSection(
            title="Overview",
            level=1,
            key_points=["Define the topic", "Key context"],
            estimated_words=200,
        ),
        OutlineSection(
            title="Key Findings",
            level=1,
            key_points=["Main discoveries", "Evidence and data"],
            estimated_words=300,
        ),
        OutlineSection(
            title="Conclusion",
            level=1,
            key_points=["Summary", "Implications"],
            estimated_words=150,
        ),
    ][:n]

    total = sum(s.estimated_words for s in sections)
    return ReportOutline(
        title=topic, sections=sections,
        total_estimated_words=total, style="brief",
    )


def _academic_outline(topic: str, num_sections: int | None) -> ReportOutline:
    """Generate an academic-style outline."""
    sections = [
        OutlineSection(
            title="Abstract",
            level=1,
            key_points=["Research question", "Methodology", "Key findings"],
            estimated_words=150,
        ),
        OutlineSection(
            title="Introduction",
            level=1,
            key_points=["Background", "Research gap", "Objectives"],
            estimated_words=400,
            children=[
                OutlineSection(title="Background", level=2, estimated_words=200),
                OutlineSection(title="Research Questions", level=2, estimated_words=100),
            ],
        ),
        OutlineSection(
            title="Literature Review",
            level=1,
            key_points=["Existing research", "Theoretical framework"],
            estimated_words=500,
        ),
        OutlineSection(
            title="Methodology",
            level=1,
            key_points=["Approach", "Data sources", "Analysis methods"],
            estimated_words=300,
        ),
        OutlineSection(
            title="Findings",
            level=1,
            key_points=["Primary results", "Supporting data"],
            estimated_words=600,
        ),
        OutlineSection(
            title="Discussion",
            level=1,
            key_points=["Interpretation", "Limitations", "Implications"],
            estimated_words=400,
        ),
        OutlineSection(
            title="Conclusion",
            level=1,
            key_points=["Summary", "Future research directions"],
            estimated_words=200,
        ),
        OutlineSection(
            title="References",
            level=1,
            estimated_words=100,
        ),
    ]

    if num_sections and num_sections < len(sections):
        sections = sections[:num_sections]

    total = sum(s.estimated_words for s in sections)
    for s in sections:
        total += sum(c.estimated_words for c in s.children)

    return ReportOutline(
        title=topic, sections=sections,
        total_estimated_words=total, style="academic",
    )


def _standard_sections(topic: str, n: int) -> list[OutlineSection]:
    """Generate standard sections for a topic."""
    all_sections = [
        OutlineSection(
            title="Introduction",
            level=1,
            key_points=["Define the topic", "Why it matters", "Scope of research"],
            estimated_words=300,
        ),
        OutlineSection(
            title="Background",
            level=1,
            key_points=["Historical context", "Current state", "Key terminology"],
            estimated_words=400,
        ),
        OutlineSection(
            title="Analysis",
            level=1,
            key_points=["Core investigation", "Data and evidence", "Expert perspectives"],
            estimated_words=500,
            children=[
                OutlineSection(title="Key Findings", level=2, estimated_words=300),
                OutlineSection(title="Supporting Evidence", level=2, estimated_words=200),
            ],
        ),
        OutlineSection(
            title="Implications",
            level=1,
            key_points=["Impact assessment", "Stakeholder effects", "Future outlook"],
            estimated_words=350,
        ),
        OutlineSection(
            title="Challenges and Limitations",
            level=1,
            key_points=["Current obstacles", "Open questions"],
            estimated_words=250,
        ),
        OutlineSection(
            title="Conclusion",
            level=1,
            key_points=["Summary of findings", "Recommendations", "Further research"],
            estimated_words=200,
        ),
    ]
    return all_sections[:n]


def _comparison_sections(topic: str, n: int) -> list[OutlineSection]:
    """Generate sections for a comparison topic."""
    all_sections = [
        OutlineSection(
            title="Overview",
            level=1,
            key_points=["What is being compared", "Comparison criteria"],
            estimated_words=250,
        ),
        OutlineSection(
            title="Detailed Comparison",
            level=1,
            key_points=["Feature-by-feature analysis", "Performance data"],
            estimated_words=600,
            children=[
                OutlineSection(title="Features", level=2, estimated_words=200),
                OutlineSection(title="Performance", level=2, estimated_words=200),
                OutlineSection(title="Ecosystem", level=2, estimated_words=200),
            ],
        ),
        OutlineSection(
            title="Strengths and Weaknesses",
            level=1,
            key_points=["Advantages of each", "Disadvantages of each"],
            estimated_words=400,
        ),
        OutlineSection(
            title="Use Cases",
            level=1,
            key_points=["When to choose each option", "Real-world examples"],
            estimated_words=350,
        ),
        OutlineSection(
            title="Community and Support",
            level=1,
            key_points=["Documentation", "Community size", "Updates"],
            estimated_words=250,
        ),
        OutlineSection(
            title="Recommendation",
            level=1,
            key_points=["Summary table", "Final verdict"],
            estimated_words=200,
        ),
    ]
    return all_sections[:n]
