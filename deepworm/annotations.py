"""Report annotation and commenting system.

Add, manage, and render inline annotations, comments,
and review notes on research reports.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class AnnotationType(str, Enum):
    """Types of annotations."""

    COMMENT = "comment"
    HIGHLIGHT = "highlight"
    QUESTION = "question"
    TODO = "todo"
    WARNING = "warning"
    FACT_CHECK = "fact_check"


@dataclass
class Annotation:
    """A single annotation on a report."""

    id: int
    text: str
    annotation_type: AnnotationType = AnnotationType.COMMENT
    target: str = ""  # The text being annotated
    line: int = 0
    author: str = ""
    resolved: bool = False

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "text": self.text,
            "type": self.annotation_type.value,
            "resolved": self.resolved,
        }
        if self.target:
            d["target"] = self.target
        if self.line:
            d["line"] = self.line
        if self.author:
            d["author"] = self.author
        return d


@dataclass
class AnnotationSet:
    """Collection of annotations for a report."""

    annotations: list[Annotation] = field(default_factory=list)
    _next_id: int = 1

    def add(
        self,
        text: str,
        annotation_type: AnnotationType = AnnotationType.COMMENT,
        target: str = "",
        line: int = 0,
        author: str = "",
    ) -> Annotation:
        """Add a new annotation."""
        ann = Annotation(
            id=self._next_id,
            text=text,
            annotation_type=annotation_type,
            target=target,
            line=line,
            author=author,
        )
        self.annotations.append(ann)
        self._next_id += 1
        return ann

    def get(self, ann_id: int) -> Optional[Annotation]:
        """Get annotation by ID."""
        for ann in self.annotations:
            if ann.id == ann_id:
                return ann
        return None

    def resolve(self, ann_id: int) -> bool:
        """Mark annotation as resolved."""
        ann = self.get(ann_id)
        if ann:
            ann.resolved = True
            return True
        return False

    def remove(self, ann_id: int) -> bool:
        """Remove an annotation."""
        for i, ann in enumerate(self.annotations):
            if ann.id == ann_id:
                self.annotations.pop(i)
                return True
        return False

    @property
    def unresolved(self) -> list[Annotation]:
        """Get unresolved annotations."""
        return [a for a in self.annotations if not a.resolved]

    @property
    def resolved_list(self) -> list[Annotation]:
        """Get resolved annotations."""
        return [a for a in self.annotations if a.resolved]

    def by_type(self, annotation_type: AnnotationType) -> list[Annotation]:
        """Filter by annotation type."""
        return [a for a in self.annotations if a.annotation_type == annotation_type]

    def by_line(self, line: int) -> list[Annotation]:
        """Get annotations for a specific line."""
        return [a for a in self.annotations if a.line == line]

    @property
    def summary(self) -> dict[str, int]:
        """Summary counts by type and status."""
        counts: dict[str, int] = {
            "total": len(self.annotations),
            "unresolved": len(self.unresolved),
            "resolved": len(self.resolved_list),
        }
        for t in AnnotationType:
            counts[t.value] = len(self.by_type(t))
        return counts

    def to_markdown(self) -> str:
        """Render annotations as markdown."""
        if not self.annotations:
            return ""

        lines = ["## Annotations", ""]
        type_icons = {
            AnnotationType.COMMENT: "💬",
            AnnotationType.HIGHLIGHT: "🔆",
            AnnotationType.QUESTION: "❓",
            AnnotationType.TODO: "📋",
            AnnotationType.WARNING: "⚠️",
            AnnotationType.FACT_CHECK: "🔍",
        }

        for ann in self.annotations:
            icon = type_icons.get(ann.annotation_type, "📝")
            status = "✅" if ann.resolved else "⬜"
            line_ref = f" (line {ann.line})" if ann.line else ""
            author_ref = f" — {ann.author}" if ann.author else ""

            entry = f"{status} {icon} **[{ann.id}]** {ann.text}{line_ref}{author_ref}"
            if ann.target:
                entry += f"\n  > {ann.target}"
            lines.append(entry)
            lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "annotations": [a.to_dict() for a in self.annotations],
            "summary": self.summary,
        }


def annotate_report(
    report: str,
    annotations: AnnotationSet,
    style: str = "inline",
) -> str:
    """Inject annotations into a report.

    Args:
        report: Markdown report text.
        annotations: Annotations to inject.
        style: 'inline' (markers in text) or 'append' (section at end).

    Returns:
        Report with annotations.
    """
    if not annotations.annotations:
        return report

    if style == "append":
        return _annotate_append(report, annotations)
    return _annotate_inline(report, annotations)


def extract_annotations(text: str) -> tuple[str, AnnotationSet]:
    """Extract annotations from annotated text.

    Finds inline annotation markers like <!-- [comment] text --> or
    {>> text <<} and creates an AnnotationSet.

    Args:
        text: Annotated text.

    Returns:
        Tuple of (clean_text, annotations).
    """
    ann_set = AnnotationSet()

    # HTML comment annotations: <!-- [type] text -->
    def _replace_html(m: re.Match) -> str:
        type_str = m.group(1).strip().lower() if m.group(1) else "comment"
        content = m.group(2).strip()

        try:
            ann_type = AnnotationType(type_str)
        except ValueError:
            ann_type = AnnotationType.COMMENT

        ann_set.add(content, annotation_type=ann_type)
        return ""

    clean = re.sub(
        r"<!--\s*\[(\w+)\]\s*(.*?)\s*-->",
        _replace_html,
        text,
        flags=re.DOTALL,
    )

    # CriticMarkup comments: {>> text <<}
    def _replace_critic(m: re.Match) -> str:
        content = m.group(1).strip()
        ann_set.add(content, annotation_type=AnnotationType.COMMENT)
        return ""

    clean = re.sub(r"\{>>\s*(.*?)\s*<<\}", _replace_critic, clean)

    # Clean up extra blank lines
    clean = re.sub(r"\n{3,}", "\n\n", clean)

    return clean.strip(), ann_set


def auto_annotate(text: str) -> AnnotationSet:
    """Automatically generate annotations for a report.

    Identifies potential issues like:
    - Unsupported claims (no citation)
    - Vague language
    - Missing methodology details

    Args:
        text: Report text.

    Returns:
        AnnotationSet with auto-generated annotations.
    """
    ann_set = AnnotationSet()
    lines = text.split("\n")

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Check for vague language
        vague_patterns = [
            r"\bmany\s+(?:people|experts|studies)\b",
            r"\bsome\s+(?:research|studies|experts)\b",
            r"\bit\s+is\s+(?:known|believed|thought)\b",
            r"\bgenerally\s+(?:accepted|believed|agreed)\b",
        ]
        for pattern in vague_patterns:
            if re.search(pattern, stripped, re.IGNORECASE):
                ann_set.add(
                    "Vague language detected — consider citing specific sources",
                    AnnotationType.WARNING,
                    target=stripped[:80],
                    line=i,
                )
                break

        # Check for unsupported statistics
        if re.search(r"\b\d+%", stripped):
            if not re.search(r"\([^)]*\d{4}[^)]*\)", stripped) and "[" not in stripped:
                ann_set.add(
                    "Statistic without citation",
                    AnnotationType.FACT_CHECK,
                    target=stripped[:80],
                    line=i,
                )

        # Check for TODO markers
        if re.search(r"\bTODO\b|\bFIXME\b|\bXXX\b", stripped):
            ann_set.add(
                "Unresolved TODO marker",
                AnnotationType.TODO,
                target=stripped[:80],
                line=i,
            )

    return ann_set


# ── Internal helpers ──


def _annotate_inline(report: str, annotations: AnnotationSet) -> str:
    """Add inline annotation markers."""
    lines = report.split("\n")
    result_lines: list[str] = []

    for i, line in enumerate(lines, 1):
        result_lines.append(line)
        line_anns = annotations.by_line(i)
        for ann in line_anns:
            marker = f"<!-- [{ann.annotation_type.value}] {ann.text} -->"
            result_lines.append(marker)

    # Add annotations without line numbers at the end
    no_line = [a for a in annotations.annotations if a.line == 0]
    if no_line:
        result_lines.append("")
        for ann in no_line:
            result_lines.append(f"<!-- [{ann.annotation_type.value}] {ann.text} -->")

    return "\n".join(result_lines)


def _annotate_append(report: str, annotations: AnnotationSet) -> str:
    """Append annotations section at the end."""
    md = annotations.to_markdown()
    return f"{report.rstrip()}\n\n---\n\n{md}"
