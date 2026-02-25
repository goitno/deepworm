"""Topic validation and sanitization.

Validates research topics before execution:
- Checks for empty/too-short/too-long topics
- Detects potentially problematic content
- Normalizes whitespace and formatting
- Suggests improvements for vague topics
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ValidationResult:
    """Result of topic validation."""
    is_valid: bool
    topic: str  # Sanitized topic
    original: str
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    @property
    def has_suggestions(self) -> bool:
        return len(self.suggestions) > 0


# Minimum and maximum topic lengths
MIN_TOPIC_LENGTH = 3
MAX_TOPIC_LENGTH = 500

# Words that suggest very vague topics
VAGUE_WORDS = {
    "stuff", "things", "something", "anything", "everything",
    "misc", "random", "whatever", "idk",
}

# Single-word topics that are too broad
TOO_BROAD_SINGLE = {
    "python", "javascript", "java", "science", "history",
    "technology", "programming", "computer", "internet", "ai",
    "math", "physics", "biology", "chemistry", "music", "art",
    "sports", "food", "travel", "health", "business", "education",
}


def validate_topic(topic: str) -> ValidationResult:
    """Validate and sanitize a research topic.

    Args:
        topic: The raw topic string to validate.

    Returns:
        ValidationResult with is_valid flag, sanitized topic, and any
        warnings/suggestions.
    """
    original = topic
    warnings: list[str] = []
    suggestions: list[str] = []

    # Normalize whitespace
    topic = _normalize_whitespace(topic)

    # Check empty
    if not topic:
        return ValidationResult(
            is_valid=False,
            topic="",
            original=original,
            error="Topic cannot be empty.",
        )

    # Check minimum length
    if len(topic) < MIN_TOPIC_LENGTH:
        return ValidationResult(
            is_valid=False,
            topic=topic,
            original=original,
            error=f"Topic too short (minimum {MIN_TOPIC_LENGTH} characters).",
        )

    # Check maximum length
    if len(topic) > MAX_TOPIC_LENGTH:
        return ValidationResult(
            is_valid=False,
            topic=topic,
            original=original,
            error=f"Topic too long (maximum {MAX_TOPIC_LENGTH} characters).",
        )

    # Check for URL-only topics
    if _is_url_only(topic):
        warnings.append("Topic appears to be just a URL. Consider adding context about what to research.")
        suggestions.append(f"Try: 'Analyze the content and impact of {topic}'")

    # Check for vagueness
    words = set(topic.lower().split())
    if words & VAGUE_WORDS and len(words) <= 3:
        warnings.append("Topic seems vague. More specific topics produce better results.")

    # Check for single-word broad topics
    if len(words) == 1 and topic.lower().strip("?") in TOO_BROAD_SINGLE:
        suggestions.append(
            f"'{topic}' is very broad. Try narrowing it: "
            f"e.g., 'Recent advances in {topic.lower()}' or "
            f"'{topic} best practices in 2024'"
        )

    # Check for excessive punctuation
    if _has_excessive_punctuation(topic):
        warnings.append("Topic contains excessive punctuation. This may affect search quality.")
        topic = _clean_punctuation(topic)

    # Check for all-caps
    if topic.isupper() and len(topic) > 5:
        warnings.append("Topic is in ALL CAPS. Converting to normal case.")
        topic = topic.capitalize()

    # Suggest question format for short statements
    if len(words) <= 4 and not topic.endswith("?") and not any(
        w in words for w in {"vs", "versus", "compare", "comparison"}
    ):
        suggestions.append(
            f"Consider framing as a question for deeper research: "
            f"'What are the key aspects of {topic.lower()}?'"
        )

    return ValidationResult(
        is_valid=True,
        topic=topic,
        original=original,
        warnings=warnings,
        suggestions=suggestions,
    )


def _normalize_whitespace(text: str) -> str:
    """Normalize whitespace: trim and collapse internal spaces."""
    return re.sub(r"\s+", " ", text.strip())


def _is_url_only(text: str) -> bool:
    """Check if text is just a URL."""
    url_pattern = r"^https?://\S+$"
    return bool(re.match(url_pattern, text.strip()))


def _has_excessive_punctuation(text: str) -> bool:
    """Check for excessive repeated punctuation."""
    return bool(re.search(r"[!?]{3,}|\.{4,}", text))


def _clean_punctuation(text: str) -> str:
    """Clean up excessive punctuation."""
    text = re.sub(r"([!?])\1{2,}", r"\1", text)
    text = re.sub(r"\.{4,}", "...", text)
    return text
