"""Utility functions for deepworm."""

from __future__ import annotations


def estimate_tokens(text: str) -> int:
    """Rough estimate of token count (approx 4 chars per token)."""
    return len(text) // 4


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str = "gpt-4o-mini",
) -> float:
    """Estimate API cost in USD.

    Prices are approximate and may change.
    """
    prices = {
        "gpt-4o-mini": (0.15, 0.60),      # per 1M tokens: (input, output)
        "gpt-4o": (2.50, 10.00),
        "gpt-4-turbo": (10.00, 30.00),
        "claude-3-5-haiku-latest": (0.80, 4.00),
        "claude-3-5-sonnet-latest": (3.00, 15.00),
        "claude-sonnet-4-20250514": (3.00, 15.00),
        "gemini-2.0-flash": (0.10, 0.40),
    }

    input_price, output_price = prices.get(model, (1.00, 3.00))
    cost = (input_tokens * input_price + output_tokens * output_price) / 1_000_000
    return round(cost, 6)


def truncate_text(text: str, max_chars: int = 4000) -> str:
    """Truncate text to a maximum number of characters at a word boundary."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_space = truncated.rfind(' ')
    if last_space > max_chars * 0.8:
        truncated = truncated[:last_space]
    return truncated + "..."
