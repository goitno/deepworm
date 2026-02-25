"""Tests for the research planner module."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from deepworm.planner import (
    ResearchPlan,
    _clamp,
    _fallback_plan,
    estimate_complexity,
    generate_plan,
)


# --- ResearchPlan dataclass ---

class TestResearchPlan:
    def test_defaults(self):
        plan = ResearchPlan(title="Test", complexity="low")
        assert plan.title == "Test"
        assert plan.complexity == "low"
        assert plan.sub_questions == []
        assert plan.key_aspects == []
        assert plan.suggested_depth == 2
        assert plan.suggested_breadth == 4
        assert plan.potential_challenges == []
        assert plan.related_topics == []

    def test_to_dict(self):
        plan = ResearchPlan(
            title="AI Research",
            complexity="high",
            sub_questions=["Q1", "Q2"],
            key_aspects=["A1"],
            suggested_depth=3,
            suggested_breadth=6,
            potential_challenges=["C1"],
            related_topics=["T1"],
        )
        d = plan.to_dict()
        assert d["title"] == "AI Research"
        assert d["complexity"] == "high"
        assert d["sub_questions"] == ["Q1", "Q2"]
        assert d["key_aspects"] == ["A1"]
        assert d["suggested_depth"] == 3
        assert d["suggested_breadth"] == 6
        assert d["potential_challenges"] == ["C1"]
        assert d["related_topics"] == ["T1"]

    def test_to_markdown_minimal(self):
        plan = ResearchPlan(title="Test Plan", complexity="low")
        md = plan.to_markdown()
        assert "# Research Plan: Test Plan" in md
        assert "**Complexity:** low" in md
        assert "**Recommended Depth:** 2" in md
        assert "**Recommended Breadth:** 4" in md

    def test_to_markdown_full(self):
        plan = ResearchPlan(
            title="Full Plan",
            complexity="high",
            sub_questions=["How does X work?", "Why is Y important?"],
            key_aspects=["Architecture", "Performance"],
            potential_challenges=["Limited data"],
            related_topics=["Machine Learning"],
            suggested_depth=4,
            suggested_breadth=6,
        )
        md = plan.to_markdown()
        assert "## Sub-Questions" in md
        assert "1. How does X work?" in md
        assert "2. Why is Y important?" in md
        assert "## Key Aspects" in md
        assert "- Architecture" in md
        assert "## Potential Challenges" in md
        assert "- Limited data" in md
        assert "## Related Topics" in md
        assert "- Machine Learning" in md

    def test_to_dict_roundtrip(self):
        plan = ResearchPlan(
            title="Test",
            complexity="medium",
            sub_questions=["Q1"],
            key_aspects=["A1", "A2"],
        )
        d = plan.to_dict()
        plan2 = ResearchPlan(**d)
        assert plan == plan2


# --- estimate_complexity ---

class TestEstimateComplexity:
    def test_simple_topic(self):
        result = estimate_complexity("what is python")
        assert result == "low"

    def test_comparison_topic(self):
        result = estimate_complexity("Python vs JavaScript for web development comparison")
        assert result in ("medium", "high")

    def test_technical_topic(self):
        result = estimate_complexity("distributed algorithm optimization for neural networks")
        assert result in ("medium", "high")

    def test_long_complex_topic(self):
        result = estimate_complexity(
            "compare the performance and architecture of distributed "
            "concurrent systems using quantum optimization algorithms "
            "versus traditional approaches in molecular simulations"
        )
        assert result == "high"

    def test_short_question(self):
        result = estimate_complexity("what is AI?")
        assert result == "low"


# --- _fallback_plan ---

class TestFallbackPlan:
    def test_returns_plan(self):
        plan = _fallback_plan("test topic")
        assert isinstance(plan, ResearchPlan)
        assert plan.title == "test topic"

    def test_simple_topic_settings(self):
        plan = _fallback_plan("what is python?")
        assert plan.complexity == "low"
        assert plan.suggested_depth == 1
        assert plan.suggested_breadth == 3

    def test_complex_topic_settings(self):
        plan = _fallback_plan(
            "compare the architecture of distributed concurrent "
            "quantum optimization systems versus classical approaches"
        )
        assert plan.complexity == "high"
        assert plan.suggested_depth == 3
        assert plan.suggested_breadth == 6


# --- _clamp ---

class TestClamp:
    def test_within_range(self):
        assert _clamp(3, 1, 5) == 3

    def test_below_min(self):
        assert _clamp(0, 1, 5) == 1

    def test_above_max(self):
        assert _clamp(10, 1, 5) == 5

    def test_at_boundaries(self):
        assert _clamp(1, 1, 5) == 1
        assert _clamp(5, 1, 5) == 5


# --- generate_plan with mock LLM ---

class TestGeneratePlan:
    def _make_mock_llm(self, response: dict | None = None, raises: bool = False):
        mock = MagicMock()
        if raises:
            mock.chat_json.side_effect = Exception("LLM failure")
        else:
            mock.chat_json.return_value = response or {}
        return mock

    def test_successful_generation(self):
        response = {
            "title": "AI Ethics",
            "complexity": "high",
            "sub_questions": ["What are key ethical concerns?", "How to regulate AI?"],
            "key_aspects": ["Privacy", "Bias"],
            "suggested_depth": 3,
            "suggested_breadth": 5,
            "potential_challenges": ["Rapidly evolving field"],
            "related_topics": ["Machine Learning Ethics"],
        }
        llm = self._make_mock_llm(response)
        plan = generate_plan("AI ethics in society", llm)
        assert plan.title == "AI Ethics"
        assert plan.complexity == "high"
        assert len(plan.sub_questions) == 2
        assert plan.suggested_depth == 3
        assert plan.suggested_breadth == 5

    def test_llm_failure_returns_fallback(self):
        llm = self._make_mock_llm(raises=True)
        plan = generate_plan("test topic", llm)
        assert isinstance(plan, ResearchPlan)
        assert plan.title == "test topic"

    def test_non_dict_response_returns_fallback(self):
        mock = MagicMock()
        mock.chat_json.return_value = "not a dict"
        plan = generate_plan("test topic", mock)
        assert isinstance(plan, ResearchPlan)
        assert plan.title == "test topic"

    def test_partial_response(self):
        response = {
            "title": "Partial",
            "complexity": "medium",
        }
        llm = self._make_mock_llm(response)
        plan = generate_plan("test", llm)
        assert plan.title == "Partial"
        assert plan.complexity == "medium"
        assert plan.sub_questions == []  # defaults

    def test_clamps_depth_and_breadth(self):
        response = {
            "title": "Test",
            "complexity": "low",
            "suggested_depth": 100,
            "suggested_breadth": 0,
        }
        llm = self._make_mock_llm(response)
        plan = generate_plan("test", llm)
        assert plan.suggested_depth == 5  # clamped to max
        assert plan.suggested_breadth == 2  # clamped to min

    def test_limits_list_lengths(self):
        response = {
            "title": "Test",
            "complexity": "low",
            "sub_questions": [f"Q{i}" for i in range(10)],
            "key_aspects": [f"A{i}" for i in range(10)],
            "potential_challenges": [f"C{i}" for i in range(10)],
            "related_topics": [f"T{i}" for i in range(10)],
        }
        llm = self._make_mock_llm(response)
        plan = generate_plan("test", llm)
        assert len(plan.sub_questions) <= 5
        assert len(plan.key_aspects) <= 5
        assert len(plan.potential_challenges) <= 3
        assert len(plan.related_topics) <= 3
