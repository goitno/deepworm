"""Content compliance and quality checking.

Check reports for compliance with style guides, detect common issues,
and enforce writing standards including spelling, grammar patterns,
formatting consistency, and content policies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class Severity(Enum):
    """Issue severity level."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SUGGESTION = "suggestion"


class IssueCategory(Enum):
    """Category of compliance issue."""
    FORMATTING = "formatting"
    STYLE = "style"
    CONSISTENCY = "consistency"
    CONTENT = "content"
    ACCESSIBILITY = "accessibility"
    STRUCTURE = "structure"


@dataclass
class ComplianceIssue:
    """A single compliance issue found in the text."""

    message: str
    severity: Severity = Severity.WARNING
    category: IssueCategory = IssueCategory.STYLE
    line_number: int = 0
    column: int = 0
    context: str = ""
    suggestion: str = ""
    rule_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "severity": self.severity.value,
            "category": self.category.value,
            "line_number": self.line_number,
            "column": self.column,
            "context": self.context,
            "suggestion": self.suggestion,
            "rule_id": self.rule_id,
        }


@dataclass
class ComplianceReport:
    """Result of a compliance check."""

    issues: List[ComplianceIssue] = field(default_factory=list)
    score: float = 100.0  # 0-100
    rules_checked: int = 0
    rules_passed: int = 0

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.WARNING)

    @property
    def is_compliant(self) -> bool:
        return self.error_count == 0

    @property
    def by_category(self) -> Dict[str, List[ComplianceIssue]]:
        result: Dict[str, List[ComplianceIssue]] = {}
        for issue in self.issues:
            cat = issue.category.value
            if cat not in result:
                result[cat] = []
            result[cat].append(issue)
        return result

    @property
    def by_severity(self) -> Dict[str, List[ComplianceIssue]]:
        result: Dict[str, List[ComplianceIssue]] = {}
        for issue in self.issues:
            sev = issue.severity.value
            if sev not in result:
                result[sev] = []
            result[sev].append(issue)
        return result

    def to_markdown(self) -> str:
        lines = [
            "## Compliance Report",
            "",
            f"**Score:** {self.score:.0f}/100 | "
            f"**Status:** {'PASS' if self.is_compliant else 'FAIL'}",
            f"**Rules checked:** {self.rules_checked} | "
            f"**Passed:** {self.rules_passed}",
            "",
        ]
        if self.issues:
            lines.append(f"### Issues ({len(self.issues)})")
            lines.append("")
            severity_icons = {
                Severity.ERROR: "X",
                Severity.WARNING: "!",
                Severity.INFO: "i",
                Severity.SUGGESTION: "?",
            }
            for issue in self.issues:
                icon = severity_icons.get(issue.severity, "?")
                loc = f"L{issue.line_number}" if issue.line_number else ""
                lines.append(
                    f"- [{icon}] {issue.message}"
                    + (f" ({loc})" if loc else "")
                    + (f" — {issue.suggestion}" if issue.suggestion else "")
                )
            lines.append("")
        else:
            lines.append("No issues found.")
            lines.append("")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 1),
            "is_compliant": self.is_compliant,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "rules_checked": self.rules_checked,
            "rules_passed": self.rules_passed,
            "issues": [i.to_dict() for i in self.issues],
        }


@dataclass
class StyleGuide:
    """A configurable style guide for compliance checking."""

    name: str = "default"
    max_sentence_length: int = 40  # words
    max_paragraph_length: int = 200  # words
    max_heading_level: int = 4
    require_alt_text: bool = True
    require_heading_hierarchy: bool = True
    banned_words: Set[str] = field(default_factory=set)
    preferred_words: Dict[str, str] = field(default_factory=dict)
    min_heading_count: int = 0
    max_consecutive_headings: int = 2
    require_introduction: bool = False
    require_conclusion: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "max_sentence_length": self.max_sentence_length,
            "max_paragraph_length": self.max_paragraph_length,
            "max_heading_level": self.max_heading_level,
            "require_alt_text": self.require_alt_text,
            "require_heading_hierarchy": self.require_heading_hierarchy,
            "banned_words": sorted(self.banned_words),
            "preferred_words": self.preferred_words,
        }


# Common passive voice indicators
_PASSIVE_PATTERNS = [
    r"\b(?:is|are|was|were|been|being)\s+\w+ed\b",
    r"\b(?:is|are|was|were|been|being)\s+\w+en\b",
]

# Weasel words
_WEASEL_WORDS = {
    "clearly", "obviously", "simply", "basically", "essentially",
    "actually", "really", "very", "quite", "somewhat", "rather",
    "fairly", "arguably", "perhaps", "possibly", "probably",
    "relatively", "virtually", "practically",
}

# Cliches
_CLICHES = [
    "at the end of the day",
    "in terms of",
    "it goes without saying",
    "needless to say",
    "it should be noted",
    "it is worth noting",
    "the fact that",
    "in order to",
    "due to the fact",
    "at this point in time",
    "for all intents and purposes",
    "last but not least",
]

# Redundant phrases
_REDUNDANT = {
    "absolutely essential": "essential",
    "advance planning": "planning",
    "basic fundamentals": "fundamentals",
    "completely eliminate": "eliminate",
    "each and every": "each",
    "end result": "result",
    "exact same": "same",
    "final outcome": "outcome",
    "first and foremost": "first",
    "free gift": "gift",
    "future plans": "plans",
    "past history": "history",
    "repeat again": "repeat",
    "true fact": "fact",
    "unexpected surprise": "surprise",
}


def check_compliance(
    text: str,
    guide: Optional[StyleGuide] = None,
) -> ComplianceReport:
    """Check text for compliance with style guide rules.

    Args:
        text: The text to check.
        guide: Style guide to use. Defaults to standard guide.

    Returns:
        ComplianceReport with all issues found.
    """
    if guide is None:
        guide = StyleGuide()

    report = ComplianceReport()
    lines = text.splitlines()

    # Rule checks
    _check_sentence_length(text, guide, report)
    _check_paragraph_length(text, guide, report)
    _check_heading_hierarchy(text, guide, report, lines)
    _check_alt_text(text, guide, report, lines)
    _check_banned_words(text, guide, report, lines)
    _check_preferred_words(text, guide, report, lines)
    _check_passive_voice(text, report, lines)
    _check_weasel_words(text, report, lines)
    _check_cliches(text, report)
    _check_redundant_phrases(text, report)
    _check_formatting(text, report, lines)
    _check_consecutive_headings(text, guide, report, lines)
    _check_structure(text, guide, report)

    # Calculate score
    if report.rules_checked > 0:
        report.score = max(0, 100 - (report.error_count * 10) - (report.warning_count * 3))
    report.rules_passed = report.rules_checked - len(report.issues)

    return report


def _check_sentence_length(
    text: str, guide: StyleGuide, report: ComplianceReport,
) -> None:
    """Check for sentences exceeding max length."""
    report.rules_checked += 1
    # Remove code blocks
    cleaned = re.sub(r"```[\s\S]*?```", "", text)
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    for sent in sentences:
        words = sent.split()
        if len(words) > guide.max_sentence_length:
            report.issues.append(ComplianceIssue(
                message=f"Sentence too long ({len(words)} words, max {guide.max_sentence_length})",
                severity=Severity.WARNING,
                category=IssueCategory.STYLE,
                context=sent[:80] + "..." if len(sent) > 80 else sent,
                suggestion=f"Break into shorter sentences (max {guide.max_sentence_length} words)",
                rule_id="sentence-length",
            ))


def _check_paragraph_length(
    text: str, guide: StyleGuide, report: ComplianceReport,
) -> None:
    """Check for paragraphs exceeding max length."""
    report.rules_checked += 1
    paragraphs = re.split(r"\n\s*\n", text)
    for para in paragraphs:
        words = para.split()
        if len(words) > guide.max_paragraph_length:
            report.issues.append(ComplianceIssue(
                message=f"Paragraph too long ({len(words)} words, max {guide.max_paragraph_length})",
                severity=Severity.WARNING,
                category=IssueCategory.STYLE,
                context=para[:80] + "...",
                suggestion="Break into smaller paragraphs",
                rule_id="paragraph-length",
            ))


def _check_heading_hierarchy(
    text: str, guide: StyleGuide, report: ComplianceReport, lines: List[str],
) -> None:
    """Check heading hierarchy (no skipped levels)."""
    if not guide.require_heading_hierarchy:
        return
    report.rules_checked += 1
    prev_level = 0
    for i, line in enumerate(lines, 1):
        match = re.match(r"^(#{1,6})\s", line)
        if match:
            level = len(match.group(1))
            if level > guide.max_heading_level:
                report.issues.append(ComplianceIssue(
                    message=f"Heading level {level} exceeds max ({guide.max_heading_level})",
                    severity=Severity.WARNING,
                    category=IssueCategory.STRUCTURE,
                    line_number=i,
                    context=line.strip(),
                    rule_id="heading-level",
                ))
            if prev_level > 0 and level > prev_level + 1:
                report.issues.append(ComplianceIssue(
                    message=f"Skipped heading level (h{prev_level} → h{level})",
                    severity=Severity.WARNING,
                    category=IssueCategory.STRUCTURE,
                    line_number=i,
                    context=line.strip(),
                    suggestion=f"Use h{prev_level + 1} instead",
                    rule_id="heading-hierarchy",
                ))
            prev_level = level


def _check_alt_text(
    text: str, guide: StyleGuide, report: ComplianceReport, lines: List[str],
) -> None:
    """Check images have alt text."""
    if not guide.require_alt_text:
        return
    report.rules_checked += 1
    for i, line in enumerate(lines, 1):
        for match in re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", line):
            alt = match.group(1).strip()
            if not alt:
                report.issues.append(ComplianceIssue(
                    message="Image missing alt text",
                    severity=Severity.ERROR,
                    category=IssueCategory.ACCESSIBILITY,
                    line_number=i,
                    context=match.group(0),
                    suggestion="Add descriptive alt text for accessibility",
                    rule_id="alt-text",
                ))


def _check_banned_words(
    text: str, guide: StyleGuide, report: ComplianceReport, lines: List[str],
) -> None:
    """Check for banned words."""
    if not guide.banned_words:
        return
    report.rules_checked += 1
    text_lower = text.lower()
    for word in guide.banned_words:
        if word.lower() in text_lower:
            for i, line in enumerate(lines, 1):
                if word.lower() in line.lower():
                    report.issues.append(ComplianceIssue(
                        message=f"Banned word found: '{word}'",
                        severity=Severity.ERROR,
                        category=IssueCategory.CONTENT,
                        line_number=i,
                        context=line.strip()[:80],
                        rule_id="banned-word",
                    ))
                    break


def _check_preferred_words(
    text: str, guide: StyleGuide, report: ComplianceReport, lines: List[str],
) -> None:
    """Check for words that should be replaced with preferred alternatives."""
    if not guide.preferred_words:
        return
    report.rules_checked += 1
    text_lower = text.lower()
    for word, preferred in guide.preferred_words.items():
        if word.lower() in text_lower:
            for i, line in enumerate(lines, 1):
                if word.lower() in line.lower():
                    report.issues.append(ComplianceIssue(
                        message=f"Use '{preferred}' instead of '{word}'",
                        severity=Severity.SUGGESTION,
                        category=IssueCategory.STYLE,
                        line_number=i,
                        context=line.strip()[:80],
                        suggestion=f"Replace '{word}' with '{preferred}'",
                        rule_id="preferred-word",
                    ))
                    break


def _check_passive_voice(
    text: str, report: ComplianceReport, lines: List[str],
) -> None:
    """Detect passive voice constructions."""
    report.rules_checked += 1
    for i, line in enumerate(lines, 1):
        # Skip headings and code
        if line.strip().startswith("#") or line.strip().startswith("`"):
            continue
        for pattern in _PASSIVE_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                report.issues.append(ComplianceIssue(
                    message="Passive voice detected",
                    severity=Severity.INFO,
                    category=IssueCategory.STYLE,
                    line_number=i,
                    context=line.strip()[:80],
                    suggestion="Consider using active voice",
                    rule_id="passive-voice",
                ))
                break


def _check_weasel_words(
    text: str, report: ComplianceReport, lines: List[str],
) -> None:
    """Detect weasel words."""
    report.rules_checked += 1
    for i, line in enumerate(lines, 1):
        if line.strip().startswith("#"):
            continue
        words_in_line = re.findall(r"\b\w+\b", line.lower())
        for word in words_in_line:
            if word in _WEASEL_WORDS:
                report.issues.append(ComplianceIssue(
                    message=f"Weasel word: '{word}'",
                    severity=Severity.SUGGESTION,
                    category=IssueCategory.STYLE,
                    line_number=i,
                    context=line.strip()[:80],
                    suggestion=f"Consider removing or replacing '{word}'",
                    rule_id="weasel-word",
                ))


def _check_cliches(text: str, report: ComplianceReport) -> None:
    """Detect clichés in text."""
    report.rules_checked += 1
    text_lower = text.lower()
    for cliche in _CLICHES:
        if cliche in text_lower:
            report.issues.append(ComplianceIssue(
                message=f"Cliché found: '{cliche}'",
                severity=Severity.SUGGESTION,
                category=IssueCategory.STYLE,
                suggestion="Rephrase to be more direct",
                rule_id="cliche",
            ))


def _check_redundant_phrases(text: str, report: ComplianceReport) -> None:
    """Detect redundant phrases."""
    report.rules_checked += 1
    text_lower = text.lower()
    for phrase, replacement in _REDUNDANT.items():
        if phrase in text_lower:
            report.issues.append(ComplianceIssue(
                message=f"Redundant phrase: '{phrase}'",
                severity=Severity.SUGGESTION,
                category=IssueCategory.STYLE,
                suggestion=f"Use '{replacement}' instead",
                rule_id="redundant-phrase",
            ))


def _check_formatting(
    text: str, report: ComplianceReport, lines: List[str],
) -> None:
    """Check for formatting issues."""
    report.rules_checked += 1
    for i, line in enumerate(lines, 1):
        # Trailing whitespace
        if line != line.rstrip() and line.strip():
            report.issues.append(ComplianceIssue(
                message="Trailing whitespace",
                severity=Severity.INFO,
                category=IssueCategory.FORMATTING,
                line_number=i,
                rule_id="trailing-whitespace",
            ))
        # Multiple consecutive blank lines
        if i > 1 and not line.strip() and not lines[i - 2].strip():
            if i > 2 and not lines[i - 3].strip():
                report.issues.append(ComplianceIssue(
                    message="Multiple consecutive blank lines",
                    severity=Severity.INFO,
                    category=IssueCategory.FORMATTING,
                    line_number=i,
                    suggestion="Use at most two consecutive blank lines",
                    rule_id="blank-lines",
                ))


def _check_consecutive_headings(
    text: str, guide: StyleGuide, report: ComplianceReport, lines: List[str],
) -> None:
    """Check for consecutive headings without content between them."""
    report.rules_checked += 1
    consecutive = 0
    for i, line in enumerate(lines, 1):
        if re.match(r"^#{1,6}\s", line):
            consecutive += 1
            if consecutive > guide.max_consecutive_headings:
                report.issues.append(ComplianceIssue(
                    message=f"Too many consecutive headings ({consecutive})",
                    severity=Severity.WARNING,
                    category=IssueCategory.STRUCTURE,
                    line_number=i,
                    context=line.strip(),
                    suggestion="Add content between headings",
                    rule_id="consecutive-headings",
                ))
        elif line.strip():
            consecutive = 0


def _check_structure(
    text: str, guide: StyleGuide, report: ComplianceReport,
) -> None:
    """Check document structure requirements."""
    report.rules_checked += 1
    headings = re.findall(r"^#{1,6}\s+(.+)$", text, re.MULTILINE)
    heading_titles = [h.lower().strip() for h in headings]

    if guide.require_introduction:
        if not any("introduction" in h or "intro" in h for h in heading_titles):
            report.issues.append(ComplianceIssue(
                message="Missing Introduction section",
                severity=Severity.WARNING,
                category=IssueCategory.STRUCTURE,
                suggestion="Add an Introduction heading",
                rule_id="require-introduction",
            ))

    if guide.require_conclusion:
        if not any("conclusion" in h or "summary" in h for h in heading_titles):
            report.issues.append(ComplianceIssue(
                message="Missing Conclusion section",
                severity=Severity.WARNING,
                category=IssueCategory.STRUCTURE,
                suggestion="Add a Conclusion or Summary heading",
                rule_id="require-conclusion",
            ))

    if guide.min_heading_count and len(headings) < guide.min_heading_count:
        report.issues.append(ComplianceIssue(
            message=f"Too few headings ({len(headings)}, min {guide.min_heading_count})",
            severity=Severity.WARNING,
            category=IssueCategory.STRUCTURE,
            rule_id="min-headings",
        ))


def create_style_guide(
    name: str = "custom",
    **kwargs: Any,
) -> StyleGuide:
    """Create a custom style guide.

    Args:
        name: Name of the style guide.
        **kwargs: StyleGuide field overrides.

    Returns:
        Configured StyleGuide.
    """
    return StyleGuide(name=name, **kwargs)


def academic_style_guide() -> StyleGuide:
    """Style guide for academic writing."""
    return StyleGuide(
        name="academic",
        max_sentence_length=35,
        max_paragraph_length=150,
        require_heading_hierarchy=True,
        require_introduction=True,
        require_conclusion=True,
        min_heading_count=3,
        preferred_words={
            "shows": "demonstrates",
            "big": "significant",
            "a lot": "substantially",
            "things": "elements",
            "good": "effective",
            "bad": "detrimental",
        },
    )


def technical_style_guide() -> StyleGuide:
    """Style guide for technical documentation."""
    return StyleGuide(
        name="technical",
        max_sentence_length=30,
        max_paragraph_length=120,
        max_heading_level=4,
        require_alt_text=True,
        require_heading_hierarchy=True,
        min_heading_count=2,
    )
