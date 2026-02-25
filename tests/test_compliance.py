"""Tests for content compliance and quality checking."""

import pytest
from deepworm.compliance import (
    Severity,
    IssueCategory,
    ComplianceIssue,
    ComplianceReport,
    StyleGuide,
    check_compliance,
    create_style_guide,
    academic_style_guide,
    technical_style_guide,
)


# --- ComplianceIssue ---

class TestComplianceIssue:
    def test_basic(self):
        issue = ComplianceIssue(message="Test issue")
        assert issue.message == "Test issue"
        assert issue.severity == Severity.WARNING

    def test_to_dict(self):
        issue = ComplianceIssue(
            message="Test",
            severity=Severity.ERROR,
            category=IssueCategory.STYLE,
            line_number=5,
        )
        d = issue.to_dict()
        assert d["severity"] == "error"
        assert d["category"] == "style"
        assert d["line_number"] == 5


# --- ComplianceReport ---

class TestComplianceReport:
    def test_empty(self):
        report = ComplianceReport()
        assert report.error_count == 0
        assert report.is_compliant

    def test_with_errors(self):
        report = ComplianceReport(issues=[
            ComplianceIssue("err", severity=Severity.ERROR),
            ComplianceIssue("warn", severity=Severity.WARNING),
        ])
        assert report.error_count == 1
        assert report.warning_count == 1
        assert not report.is_compliant

    def test_by_category(self):
        report = ComplianceReport(issues=[
            ComplianceIssue("a", category=IssueCategory.STYLE),
            ComplianceIssue("b", category=IssueCategory.FORMATTING),
            ComplianceIssue("c", category=IssueCategory.STYLE),
        ])
        by_cat = report.by_category
        assert len(by_cat["style"]) == 2
        assert len(by_cat["formatting"]) == 1

    def test_by_severity(self):
        report = ComplianceReport(issues=[
            ComplianceIssue("a", severity=Severity.ERROR),
            ComplianceIssue("b", severity=Severity.ERROR),
        ])
        assert len(report.by_severity["error"]) == 2

    def test_to_markdown(self):
        report = ComplianceReport(
            issues=[ComplianceIssue("test issue", severity=Severity.WARNING)],
            rules_checked=5, rules_passed=4, score=97,
        )
        md = report.to_markdown()
        assert "Compliance Report" in md
        assert "test issue" in md

    def test_to_dict(self):
        report = ComplianceReport(rules_checked=10, rules_passed=8, score=80)
        d = report.to_dict()
        assert d["score"] == 80
        assert d["rules_checked"] == 10


# --- StyleGuide ---

class TestStyleGuide:
    def test_defaults(self):
        guide = StyleGuide()
        assert guide.max_sentence_length == 40
        assert guide.name == "default"

    def test_to_dict(self):
        guide = StyleGuide(name="test", banned_words={"foo"})
        d = guide.to_dict()
        assert d["name"] == "test"
        assert "foo" in d["banned_words"]


# --- check_compliance ---

class TestCheckCompliance:
    def test_clean_text(self):
        report = check_compliance("# Title\n\nThis is a clean document.")
        assert report.rules_checked > 0

    def test_long_sentence(self):
        long = " ".join(["word"] * 50) + "."
        report = check_compliance(long)
        issues = [i for i in report.issues if i.rule_id == "sentence-length"]
        assert len(issues) >= 1

    def test_passive_voice(self):
        report = check_compliance("The report was generated automatically.")
        issues = [i for i in report.issues if i.rule_id == "passive-voice"]
        assert len(issues) >= 1

    def test_weasel_words(self):
        report = check_compliance("This is obviously the best approach.")
        issues = [i for i in report.issues if i.rule_id == "weasel-word"]
        assert len(issues) >= 1

    def test_cliches(self):
        report = check_compliance("At the end of the day, this matters.")
        issues = [i for i in report.issues if i.rule_id == "cliche"]
        assert len(issues) >= 1

    def test_redundant_phrase(self):
        report = check_compliance("The end result was clear.")
        issues = [i for i in report.issues if i.rule_id == "redundant-phrase"]
        assert len(issues) >= 1

    def test_missing_alt_text(self):
        report = check_compliance("![](image.png)")
        issues = [i for i in report.issues if i.rule_id == "alt-text"]
        assert len(issues) >= 1

    def test_alt_text_present(self):
        report = check_compliance("![Description](image.png)")
        issues = [i for i in report.issues if i.rule_id == "alt-text"]
        assert len(issues) == 0

    def test_heading_skip(self):
        report = check_compliance("# H1\n\n### H3 skip\n")
        issues = [i for i in report.issues if i.rule_id == "heading-hierarchy"]
        assert len(issues) >= 1

    def test_banned_words(self):
        guide = StyleGuide(banned_words={"forbidden"})
        report = check_compliance("This contains a forbidden word.", guide)
        issues = [i for i in report.issues if i.rule_id == "banned-word"]
        assert len(issues) >= 1

    def test_preferred_words(self):
        guide = StyleGuide(preferred_words={"utilize": "use"})
        report = check_compliance("We utilize this tool.", guide)
        issues = [i for i in report.issues if i.rule_id == "preferred-word"]
        assert len(issues) >= 1

    def test_consecutive_headings(self):
        text = "# H1\n## H2\n### H3\n\nContent here."
        report = check_compliance(text)
        issues = [i for i in report.issues if i.rule_id == "consecutive-headings"]
        assert len(issues) >= 1

    def test_require_introduction(self):
        guide = StyleGuide(require_introduction=True)
        report = check_compliance("# Methods\n\nSome text.", guide)
        issues = [i for i in report.issues if i.rule_id == "require-introduction"]
        assert len(issues) >= 1

    def test_require_conclusion(self):
        guide = StyleGuide(require_conclusion=True)
        report = check_compliance("# Introduction\n\nSome text.", guide)
        issues = [i for i in report.issues if i.rule_id == "require-conclusion"]
        assert len(issues) >= 1

    def test_score_calculation(self):
        report = check_compliance("Clean short text.")
        assert report.score >= 0
        assert report.score <= 100

    def test_empty_text(self):
        report = check_compliance("")
        assert report.rules_checked > 0


# --- Style guide presets ---

class TestPresets:
    def test_academic(self):
        guide = academic_style_guide()
        assert guide.name == "academic"
        assert guide.require_introduction
        assert guide.require_conclusion

    def test_technical(self):
        guide = technical_style_guide()
        assert guide.name == "technical"
        assert guide.require_alt_text

    def test_create_custom(self):
        guide = create_style_guide("my-guide", max_sentence_length=20)
        assert guide.name == "my-guide"
        assert guide.max_sentence_length == 20
