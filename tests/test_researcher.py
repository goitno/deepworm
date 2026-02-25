"""Tests for deepworm.researcher."""

import json

import pytest

from deepworm.config import Config
from deepworm.researcher import (
    DeepResearcher,
    ResearchState,
    Source,
    FOLLOWUP_QUESTIONS_PROMPT,
)


class FakeLLM:
    """Minimal LLM mock for researcher tests."""

    def __init__(self, response="[]"):
        self._response = response

    def chat(self, messages, temperature=0.3):
        return self._response

    def chat_json(self, messages, temperature=0.3):
        text = self._response
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(text)


# --- Follow-up questions ---


def test_generate_followup_questions_returns_list():
    """Follow-up questions method returns a list of strings."""
    questions = ["What is Q1?", "What is Q2?", "How about Q3?", "Why Q4?", "Where Q5?"]
    llm = FakeLLM(json.dumps(questions))
    researcher = DeepResearcher(Config(provider="openai", model="gpt-4o-mini"))
    result = researcher._generate_followup_questions_list(llm, "AI safety", "# Report\n\nSome findings.")
    assert result == questions


def test_generate_followup_questions_truncates_to_five():
    """At most 5 follow-up questions are returned."""
    questions = [f"Q{i}?" for i in range(10)]
    llm = FakeLLM(json.dumps(questions))
    researcher = DeepResearcher(Config(provider="openai", model="gpt-4o-mini"))
    result = researcher._generate_followup_questions_list(llm, "topic", "report")
    assert len(result) == 5


def test_generate_followup_questions_handles_error():
    """Returns empty list on LLM error."""
    llm = FakeLLM("not valid json")
    researcher = DeepResearcher(Config(provider="openai", model="gpt-4o-mini"))
    result = researcher._generate_followup_questions_list(llm, "topic", "report")
    assert result == []


def test_followup_questions_prompt_format():
    """FOLLOWUP_QUESTIONS_PROMPT can be formatted with required keys."""
    formatted = FOLLOWUP_QUESTIONS_PROMPT.format(topic="AI", summary="Summary text")
    assert "AI" in formatted
    assert "Summary text" in formatted


# --- Source scoring ---


def test_score_source_high_quality_domain():
    """Sources from .edu/.gov domains get higher scores."""
    researcher = DeepResearcher(Config(provider="openai", model="gpt-4o-mini"))
    source = Source(
        url="https://example.edu/research",
        title="Academic Research",
        content="This is a detailed research paper about artificial intelligence. " * 100,
        findings="Key findings about AI capabilities and limitations. " * 20,
    )
    score = researcher._score_source(source, "artificial intelligence")
    assert score >= 0.5


def test_score_source_low_quality():
    """Sources with little content get low scores."""
    researcher = DeepResearcher(Config(provider="openai", model="gpt-4o-mini"))
    source = Source(url="https://x.com/post", title="Tweet", content="Short.")
    score = researcher._score_source(source, "artificial intelligence")
    assert score < 0.3


def test_score_source_keyword_overlap():
    """Score increases with keyword overlap between topic and content."""
    researcher = DeepResearcher(Config(provider="openai", model="gpt-4o-mini"))
    source_relevant = Source(
        url="https://example.com/page",
        title="Relevant",
        content="Python programming language features and benefits for developers." * 50,
        findings="Python is widely used." * 10,
    )
    source_irrelevant = Source(
        url="https://example.com/other",
        title="Irrelevant",
        content="Cooking recipes for Italian pasta dishes." * 50,
        findings="Pasta is delicious." * 10,
    )
    score_r = researcher._score_source(source_relevant, "python programming")
    score_i = researcher._score_source(source_irrelevant, "python programming")
    assert score_r > score_i


# --- ResearchState ---


def test_research_state_defaults():
    """ResearchState initializes with empty collections."""
    state = ResearchState(topic="test")
    assert state.topic == "test"
    assert state.queries == []
    assert state.sources == []
    assert state.findings == []
    assert state.gaps == []
    assert state.iterations_done == 0


def test_research_state_track_sources():
    """Can add sources to research state."""
    state = ResearchState(topic="test")
    state.sources.append(Source(url="https://example.com", title="Test", content="Body"))
    assert len(state.sources) == 1
    assert state.sources[0].url == "https://example.com"


# --- Source ---


def test_source_defaults():
    """Source has sensible defaults for optional fields."""
    source = Source(url="https://example.com", title="Test", content="Content")
    assert source.findings == ""
    assert source.relevance == 0.0
