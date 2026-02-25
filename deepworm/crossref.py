"""Cross-referencing within research reports.

Detect, create, and validate internal cross-references between
sections, figures, tables, and other labeled elements in a report.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class CrossRefTarget:
    """A referenceable target in the report."""

    label: str
    ref_type: str  # section, figure, table, equation, listing, note
    title: str
    line: int = 0
    number: Optional[int] = None

    @property
    def display(self) -> str:
        """Display text for references to this target."""
        prefix = {
            "section": "Section",
            "figure": "Figure",
            "table": "Table",
            "equation": "Equation",
            "listing": "Listing",
            "note": "Note",
        }.get(self.ref_type, "")
        if self.number is not None:
            return f"{prefix} {self.number}"
        return f"{prefix} ({self.title})"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "label": self.label,
            "type": self.ref_type,
            "title": self.title,
            "line": self.line,
            "number": self.number,
        }


@dataclass
class CrossRefLink:
    """A cross-reference link from one location to a target."""

    source_line: int
    target_label: str
    context: str = ""
    resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source_line": self.source_line,
            "target_label": self.target_label,
            "context": self.context,
            "resolved": self.resolved,
        }


@dataclass
class CrossRefIndex:
    """Index of all cross-references in a report."""

    targets: List[CrossRefTarget] = field(default_factory=list)
    links: List[CrossRefLink] = field(default_factory=list)

    def add_target(
        self,
        label: str,
        ref_type: str,
        title: str,
        line: int = 0,
        number: Optional[int] = None,
    ) -> CrossRefTarget:
        """Register a referenceable target."""
        target = CrossRefTarget(
            label=label,
            ref_type=ref_type,
            title=title,
            line=line,
            number=number,
        )
        self.targets.append(target)
        return target

    def add_link(
        self,
        source_line: int,
        target_label: str,
        context: str = "",
    ) -> CrossRefLink:
        """Register a cross-reference link."""
        resolved = any(t.label == target_label for t in self.targets)
        link = CrossRefLink(
            source_line=source_line,
            target_label=target_label,
            context=context,
            resolved=resolved,
        )
        self.links.append(link)
        return link

    def get_target(self, label: str) -> Optional[CrossRefTarget]:
        """Find a target by label."""
        for target in self.targets:
            if target.label == label:
                return target
        return None

    def get_targets_by_type(self, ref_type: str) -> List[CrossRefTarget]:
        """Get all targets of a specific type."""
        return [t for t in self.targets if t.ref_type == ref_type]

    @property
    def unresolved_links(self) -> List[CrossRefLink]:
        """Get links that don't have matching targets."""
        return [l for l in self.links if not l.resolved]

    @property
    def unused_targets(self) -> List[CrossRefTarget]:
        """Get targets that are never referenced."""
        referenced = {l.target_label for l in self.links}
        return [t for t in self.targets if t.label not in referenced]

    @property
    def is_valid(self) -> bool:
        """Check if all cross-references are valid."""
        return len(self.unresolved_links) == 0

    @property
    def stats(self) -> Dict[str, int]:
        """Get cross-reference statistics."""
        return {
            "targets": len(self.targets),
            "links": len(self.links),
            "resolved": sum(1 for l in self.links if l.resolved),
            "unresolved": len(self.unresolved_links),
            "unused_targets": len(self.unused_targets),
        }

    def validate(self) -> List[Dict[str, Any]]:
        """Validate all cross-references.

        Returns list of issues found.
        """
        issues: List[Dict[str, Any]] = []

        for link in self.unresolved_links:
            issues.append({
                "type": "unresolved_reference",
                "line": link.source_line,
                "label": link.target_label,
                "context": link.context,
                "message": f"Reference to '{link.target_label}' has no matching target.",
            })

        # Duplicate labels
        seen_labels: Dict[str, int] = {}
        for target in self.targets:
            if target.label in seen_labels:
                issues.append({
                    "type": "duplicate_label",
                    "line": target.line,
                    "label": target.label,
                    "message": f"Duplicate label '{target.label}' "
                               f"(first at line {seen_labels[target.label]}).",
                })
            else:
                seen_labels[target.label] = target.line

        return issues

    def to_markdown(self) -> str:
        """Render cross-reference index as markdown."""
        lines = ["## Cross-Reference Index\n"]

        if not self.targets:
            lines.append("*No targets found.*\n")
            return "\n".join(lines)

        # Group by type
        types = {}
        for target in self.targets:
            types.setdefault(target.ref_type, []).append(target)

        for ref_type, targets in types.items():
            lines.append(f"### {ref_type.title()}s\n")
            for t in targets:
                ref_count = sum(
                    1 for l in self.links if l.target_label == t.label
                )
                lines.append(
                    f"- **{t.display}**: {t.title} "
                    f"(line {t.line}, {ref_count} references)"
                )
            lines.append("")

        # Issues
        unresolved = self.unresolved_links
        if unresolved:
            lines.append("### Unresolved References\n")
            for link in unresolved:
                lines.append(
                    f"- Line {link.source_line}: `{link.target_label}` — not found"
                )
            lines.append("")

        return "\n".join(lines) + "\n"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "stats": self.stats,
            "targets": [t.to_dict() for t in self.targets],
            "links": [l.to_dict() for l in self.links],
            "issues": self.validate(),
        }


# Patterns for detecting cross-reference targets and links

# Section headings: ## Section Title {#label}
_LABELED_HEADING = re.compile(
    r"^(#{1,6})\s+(.+?)\s*\{#([^}]+)\}\s*$", re.MULTILINE
)

# Figures: ![alt](url) {#fig:label} or <!-- fig:label -->
_FIGURE_LABEL = re.compile(
    r"!\[[^\]]*\]\([^)]+\)\s*\{#(fig:[^}]+)\}", re.MULTILINE
)
_FIGURE_CAPTION = re.compile(
    r"\*\*(?:Figure|Fig\.?)\s+(\d+)[.:]\s*\*\*\s*(.+?)$", re.MULTILINE
)

# Tables: {#tbl:label} or **Table N:**
_TABLE_LABEL = re.compile(
    r"\{#(tbl:[^}]+)\}", re.MULTILINE
)
_TABLE_CAPTION = re.compile(
    r"\*\*Table\s+(\d+)[.:]\s*\*\*\s*(.+?)$", re.MULTILINE
)

# Cross-reference links: {@label} or [see @label] or (see Section N)
_XREF_LINK = re.compile(r"\{@([^}]+)\}")
_SEE_SECTION = re.compile(
    r"(?:see|refer to|as shown in|described in)\s+(?:Section|Figure|Table)\s+(\d+)",
    re.IGNORECASE,
)

# Plain headings (for auto-label generation)
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)$", re.MULTILINE)


def build_crossref_index(text: str) -> CrossRefIndex:
    """Build a cross-reference index from report text.

    Scans for labeled sections, figures, tables, and
    cross-reference links.

    Args:
        text: Report text in markdown.

    Returns:
        CrossRefIndex with all targets and links.
    """
    index = CrossRefIndex()
    lines = text.split("\n")

    section_counter = 0
    figure_counter = 0
    table_counter = 0

    # First pass: find targets
    for line_num, line in enumerate(lines, 1):
        # Labeled headings: ## Title {#label}
        labeled = _LABELED_HEADING.match(line)
        if labeled:
            section_counter += 1
            title = labeled.group(2).strip()
            label = labeled.group(3).strip()
            index.add_target(label, "section", title, line_num, section_counter)
            continue

        # Plain headings → auto-label
        heading = _HEADING.match(line)
        if heading:
            section_counter += 1
            title = heading.group(2).strip()
            label = _slugify(title)
            index.add_target(label, "section", title, line_num, section_counter)
            continue

        # Figure captions
        fig_match = _FIGURE_CAPTION.match(line)
        if fig_match:
            figure_counter += 1
            fig_num = int(fig_match.group(1))
            caption = fig_match.group(2).strip()
            label = f"fig:{fig_num}"
            index.add_target(label, "figure", caption, line_num, fig_num)
            continue

        # Figure labels
        fig_label = _FIGURE_LABEL.search(line)
        if fig_label:
            figure_counter += 1
            label = fig_label.group(1).strip()
            index.add_target(label, "figure", label, line_num, figure_counter)
            continue

        # Table captions
        tbl_match = _TABLE_CAPTION.match(line)
        if tbl_match:
            table_counter += 1
            tbl_num = int(tbl_match.group(1))
            caption = tbl_match.group(2).strip()
            label = f"tbl:{tbl_num}"
            index.add_target(label, "table", caption, line_num, tbl_num)
            continue

        # Table labels
        tbl_label = _TABLE_LABEL.search(line)
        if tbl_label:
            table_counter += 1
            label = tbl_label.group(1).strip()
            index.add_target(label, "table", label, line_num, table_counter)
            continue

    # Second pass: find links
    for line_num, line in enumerate(lines, 1):
        # {@label} references
        for match in _XREF_LINK.finditer(line):
            label = match.group(1).strip()
            context = line.strip()[:100]
            index.add_link(line_num, label, context)

        # "see Section N" references
        for match in _SEE_SECTION.finditer(line):
            num = match.group(1)
            # Try to find matching target by number
            full_match = match.group(0)
            if "Section" in full_match:
                ref_type = "section"
            elif "Figure" in full_match:
                ref_type = "figure"
            else:
                ref_type = "table"

            # Find target with this number
            for target in index.targets:
                if (
                    target.ref_type == ref_type
                    and target.number == int(num)
                ):
                    context = line.strip()[:100]
                    index.add_link(line_num, target.label, context)
                    break

    return index


def inject_crossrefs(text: str, index: CrossRefIndex) -> str:
    """Replace cross-reference markers with formatted links.

    Replaces {@label} with formatted references like
    "Section 1" or "Figure 2".

    Args:
        text: Report text with {@label} markers.
        index: CrossRefIndex with targets.

    Returns:
        Text with resolved cross-references.
    """
    def replace_ref(match: re.Match) -> str:
        label = match.group(1).strip()
        target = index.get_target(label)
        if target:
            return f"**{target.display}**"
        return match.group(0)  # leave unresolved

    return _XREF_LINK.sub(replace_ref, text)


def _slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = text.strip("-")
    return text


def number_elements(text: str) -> str:
    """Auto-number figures and tables in a report.

    Adds numbered captions to figures and tables that
    don't already have them.

    Args:
        text: Report text.

    Returns:
        Text with numbered elements.
    """
    lines = text.split("\n")
    result: List[str] = []
    figure_num = 0
    table_num = 0

    # Count existing numbered figures/tables
    existing_figs = set()
    existing_tbls = set()
    for line in lines:
        fig_match = _FIGURE_CAPTION.match(line)
        if fig_match:
            existing_figs.add(int(fig_match.group(1)))
        tbl_match = _TABLE_CAPTION.match(line)
        if tbl_match:
            existing_tbls.add(int(tbl_match.group(1)))

    figure_num = max(existing_figs) if existing_figs else 0
    table_num = max(existing_tbls) if existing_tbls else 0

    i = 0
    while i < len(lines):
        line = lines[i]

        # Detect unnumbered images (not already captioned)
        if re.match(r"^!\[", line) and not _FIGURE_CAPTION.match(line):
            # Check if next line is already a caption
            next_line = lines[i + 1] if i + 1 < len(lines) else ""
            if not _FIGURE_CAPTION.match(next_line):
                alt = re.match(r"!\[([^\]]*)\]", line)
                if alt and alt.group(1).strip():
                    figure_num += 1
                    result.append(line)
                    result.append(f"**Figure {figure_num}.** {alt.group(1)}")
                    i += 1
                    continue

        # Detect tables (| header | row)
        if (
            re.match(r"^\|", line)
            and i > 0
            and not re.match(r"^\|", lines[i - 1])
        ):
            # Check if there's a caption before
            prev = lines[i - 1].strip() if i > 0 else ""
            if not _TABLE_CAPTION.match(prev) and prev != "":
                # Check if previous line looks like a caption already
                if not prev.startswith("**Table"):
                    table_num += 1
                    # Insert caption before the table
                    result.append(f"**Table {table_num}.** Data")

        result.append(line)
        i += 1

    return "\n".join(result)


def generate_list_of_figures(
    index: CrossRefIndex,
) -> str:
    """Generate a List of Figures from the index."""
    figures = index.get_targets_by_type("figure")
    if not figures:
        return ""

    lines = ["## List of Figures\n"]
    for fig in figures:
        lines.append(f"- **Figure {fig.number}**: {fig.title} (p. {fig.line})")
    return "\n".join(lines) + "\n"


def generate_list_of_tables(
    index: CrossRefIndex,
) -> str:
    """Generate a List of Tables from the index."""
    tables = index.get_targets_by_type("table")
    if not tables:
        return ""

    lines = ["## List of Tables\n"]
    for tbl in tables:
        lines.append(f"- **Table {tbl.number}**: {tbl.title} (p. {tbl.line})")
    return "\n".join(lines) + "\n"
