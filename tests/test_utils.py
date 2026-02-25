"""Tests for deepworm.utils."""

from deepworm.utils import estimate_cost, estimate_tokens, truncate_text


def test_estimate_tokens():
    assert estimate_tokens("hello world") > 0
    assert estimate_tokens("a" * 4000) == 1000


def test_estimate_cost_gpt4o_mini():
    cost = estimate_cost(1_000_000, 500_000, model="gpt-4o-mini")
    # input: 0.15/M, output: 0.60/M  → 0.15 + 0.30 = 0.45
    assert abs(cost - 0.45) < 0.001


def test_estimate_cost_unknown_model():
    cost = estimate_cost(1_000_000, 1_000_000, model="unknown-model")
    assert cost > 0  # uses fallback pricing


def test_truncate_text_short():
    text = "hello world"
    assert truncate_text(text, 100) == "hello world"


def test_truncate_text_long():
    text = "hello " * 1000
    result = truncate_text(text, 100)
    assert len(result) <= 104  # max_chars + "..."
    assert result.endswith("...")
