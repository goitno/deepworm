"""Tests for deepworm.scoring — report quality scoring."""

from deepworm.scoring import QualityScore, score_report


GOOD_REPORT = """# Quantum Computing in 2024

## Executive Summary

Quantum computing has made significant advances in 2024, with **breakthroughs** in error correction
and practical applications. The global quantum computing market is expected to reach $65 billion by
2030, growing at a CAGR of 32.7%. Key players include IBM, Google, and IonQ.

## Key Developments

- IBM demonstrated a 1,121-qubit processor called Condor
- Google achieved quantum error correction below the threshold
- IonQ announced a 35-qubit trapped-ion system with 99.7% fidelity
- The quantum advantage was demonstrated in drug discovery simulations

However, practical quantum computing remains years away for most applications.

### Hardware Advances

The race for qubit counts has shifted toward quality over quantity. Unlike previous years, companies
are focusing on error rates and coherence times. Compared to classical supercomputers, quantum systems
show advantages only in specific domains.

### Software and Algorithms

New quantum algorithms have emerged for optimization, simulation, and machine learning. In contrast
to gate-based approaches, adiabatic quantum computing has seen renewed interest.

## Industry Impact

The pharmaceutical industry has invested $2.3 billion in quantum computing research. On the other hand,
financial services firms are exploring quantum algorithms for portfolio optimization.

## Key Takeaways

- **Error correction** is the critical bottleneck for practical quantum computing
- Cloud-based quantum access has democratized experimentation
- Hybrid classical-quantum approaches are the most promising near-term strategy
- Government funding has increased by 45% year-over-year

## Sources

1. https://arxiv.org/quantum-2024-review
2. https://nature.com/articles/quantum-advances
3. https://ibm.com/quantum-roadmap-2024
4. https://google.com/quantum-ai-research
5. https://ionq.com/press/2024-announcements
6. https://mckinsey.com/quantum-outlook

## Follow-up Questions

1. How close are we to fault-tolerant quantum computing?
2. What industries will benefit most from quantum computing first?
"""

SHORT_REPORT = "Some text without any headings or structure."


def test_score_good_report():
    qs = score_report(GOOD_REPORT)
    assert qs.overall > 0.5
    assert qs.grade in ("A+", "A", "A-", "B+", "B")


def test_score_poor_report():
    qs = score_report(SHORT_REPORT)
    assert qs.overall < 0.4


def test_structure_score():
    qs = score_report(GOOD_REPORT)
    assert qs.structure > 0.5  # Has h1, h2, h3


def test_depth_score_with_data():
    qs = score_report(GOOD_REPORT)
    assert qs.depth > 0.4  # Has numbers, bullets, comparisons


def test_sources_score():
    qs = score_report(GOOD_REPORT)
    assert qs.sources > 0.5  # Has URLs and Sources section


def test_readability_score():
    qs = score_report(GOOD_REPORT)
    assert qs.readability > 0.4


def test_completeness_score():
    qs = score_report(GOOD_REPORT)
    assert qs.completeness > 0.6  # Has summary, takeaways, sources, follow-up


def test_grade_mapping():
    q = QualityScore(structure=1.0, depth=1.0, sources=1.0, readability=1.0, completeness=1.0)
    assert q.grade == "A+"
    assert q.overall == 1.0


def test_grade_low():
    q = QualityScore(structure=0.1, depth=0.1, sources=0.1, readability=0.1, completeness=0.1)
    assert q.grade == "F"


def test_to_dict():
    qs = score_report(GOOD_REPORT)
    d = qs.to_dict()
    assert "overall" in d
    assert "grade" in d
    assert "structure" in d


def test_suggestions_for_poor_report():
    qs = score_report(SHORT_REPORT)
    assert len(qs.suggestions) > 0


def test_suggestions_for_good_report():
    qs = score_report(GOOD_REPORT)
    # Good report should have fewer or no suggestions
    assert len(qs.suggestions) < 3
