"""Tests for deepworm.summary."""

import pytest

from deepworm.summary import (
    Summary,
    extract_key_findings,
    extract_topics,
    summarize,
)

SAMPLE_REPORT = """# Quantum Computing Advances in 2024

Quantum computing has seen significant breakthroughs in 2024, with major
companies investing billions in development. The field has grown by 45% compared
to previous years, demonstrating the increasing importance of quantum technology.

## Hardware Developments

Recent research shows that error correction has improved significantly. IBM
demonstrated a 1000-qubit processor that achieved notably better coherence times.
The decrease in error rates has been a primary driver of practical applications.

### Superconducting Qubits

Superconducting qubit technology has shown a 30% increase in gate fidelity.
According to leading researchers, this represents the most significant advance
in the past decade.

## Software and Algorithms

New quantum algorithms have been discovered that could revolutionize
cryptography and drug discovery. Studies indicate that quantum advantage
has been demonstrated in specific optimization problems.

## Industry Applications

The largest quantum computing market is expected to reach $65 billion by 2030.
Key players include IBM, Google, and startups like IonQ and Rigetti.

## Challenges

Critical challenges remain in scaling quantum systems. Error rates must
decrease further before practical applications become widespread.

## Conclusion

Quantum computing in 2024 showed the most progress in over a decade.
The key findings suggest continued growth and investment in the field.
"""


class TestSummarize:
    def test_executive_summary(self):
        s = summarize(SAMPLE_REPORT, style="executive")
        assert s.style == "executive"
        assert s.word_count > 0
        assert s.source_word_count > 0
        assert len(s.text) > 0

    def test_abstract_summary(self):
        s = summarize(SAMPLE_REPORT, style="abstract")
        assert s.style == "abstract"
        assert "examines" in s.text.lower() or "report" in s.text.lower()

    def test_bullet_summary(self):
        s = summarize(SAMPLE_REPORT, style="bullets")
        assert s.style == "bullets"
        assert "•" in s.text

    def test_tldr_summary(self):
        s = summarize(SAMPLE_REPORT, style="tldr")
        assert s.style == "tldr"
        assert s.text.startswith("TL;DR:")

    def test_max_words(self):
        s = summarize(SAMPLE_REPORT, style="executive", max_words=30)
        assert s.word_count <= 35  # Allow slight over due to findings

    def test_invalid_style_defaults(self):
        s = summarize(SAMPLE_REPORT, style="invalid")
        assert s.style == "executive"

    def test_empty_report(self):
        s = summarize("", style="tldr")
        assert s.text.startswith("TL;DR:")


class TestSummary:
    def test_compression_ratio(self):
        s = Summary(
            text="Short summary.",
            style="executive",
            word_count=2,
            source_word_count=100,
        )
        assert s.compression_ratio == 0.98

    def test_compression_ratio_zero_source(self):
        s = Summary(text="", style="executive", word_count=0, source_word_count=0)
        assert s.compression_ratio == 0.0

    def test_to_dict(self):
        s = Summary(
            text="Hello",
            style="executive",
            word_count=1,
            key_findings=["Finding 1"],
            topics_covered=["Topic A"],
            source_word_count=100,
        )
        d = s.to_dict()
        assert d["style"] == "executive"
        assert d["word_count"] == 1
        assert len(d["key_findings"]) == 1
        assert "compression_ratio" in d


class TestExtractKeyFindings:
    def test_extracts_findings(self):
        findings = extract_key_findings(SAMPLE_REPORT)
        assert len(findings) > 0
        assert len(findings) <= 5

    def test_max_findings(self):
        findings = extract_key_findings(SAMPLE_REPORT, max_findings=2)
        assert len(findings) <= 2

    def test_empty_report(self):
        findings = extract_key_findings("")
        assert findings == []

    def test_finds_percentages(self):
        report = "## Results\n\nThe overall improvement was measured at 45% over the previous baseline results. This demonstrates significant progress in the field.\n"
        findings = extract_key_findings(report, max_findings=3)
        assert any("45%" in f for f in findings)


class TestExtractTopics:
    def test_extracts_headings(self):
        topics = extract_topics(SAMPLE_REPORT)
        assert "Hardware Developments" in topics
        assert "Software and Algorithms" in topics

    def test_skips_generic(self):
        topics = extract_topics(SAMPLE_REPORT)
        assert "Introduction" not in topics
        assert "Conclusion" not in topics

    def test_empty_report(self):
        topics = extract_topics("")
        assert topics == []

    def test_h3_included(self):
        topics = extract_topics(SAMPLE_REPORT)
        assert "Superconducting Qubits" in topics
