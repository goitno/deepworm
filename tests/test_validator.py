"""Tests for deepworm.validator."""

from __future__ import annotations

import pytest

from deepworm.validator import (
    ValidationResult,
    _clean_punctuation,
    _has_excessive_punctuation,
    _is_url_only,
    _normalize_whitespace,
    validate_topic,
)


class TestValidationResult:
    def test_defaults(self):
        r = ValidationResult(is_valid=True, topic="test", original="test")
        assert r.is_valid
        assert not r.has_warnings
        assert not r.has_suggestions
        assert r.error is None

    def test_with_warnings(self):
        r = ValidationResult(
            is_valid=True, topic="test", original="test",
            warnings=["Something to note"],
        )
        assert r.has_warnings
        assert not r.has_suggestions

    def test_with_suggestions(self):
        r = ValidationResult(
            is_valid=True, topic="test", original="test",
            suggestions=["Try this instead"],
        )
        assert r.has_suggestions


class TestValidateTopic:
    def test_valid_topic(self):
        result = validate_topic("How does quantum computing work?")
        assert result.is_valid
        assert result.error is None

    def test_empty_topic(self):
        result = validate_topic("")
        assert not result.is_valid
        assert "empty" in result.error.lower()

    def test_whitespace_only(self):
        result = validate_topic("   ")
        assert not result.is_valid

    def test_too_short(self):
        result = validate_topic("ai")
        assert not result.is_valid
        assert "short" in result.error.lower()

    def test_too_long(self):
        result = validate_topic("x" * 501)
        assert not result.is_valid
        assert "long" in result.error.lower()

    def test_url_only_warning(self):
        result = validate_topic("https://example.com/article")
        assert result.is_valid
        assert result.has_warnings
        assert any("URL" in w for w in result.warnings)

    def test_vague_topic_warning(self):
        result = validate_topic("random stuff")
        assert result.is_valid
        assert result.has_warnings

    def test_single_broad_topic_suggestion(self):
        result = validate_topic("python")
        assert result.is_valid
        assert result.has_suggestions
        assert any("broad" in s.lower() for s in result.suggestions)

    def test_excessive_punctuation(self):
        result = validate_topic("What is AI!!!!")
        assert result.is_valid
        assert result.has_warnings
        assert "!" not in result.topic or result.topic.count("!") < 4

    def test_all_caps_conversion(self):
        result = validate_topic("QUANTUM COMPUTING ADVANCES")
        assert result.is_valid
        assert not result.topic.isupper()

    def test_whitespace_normalization(self):
        result = validate_topic("  what   is   AI  ")
        assert result.is_valid
        assert result.topic == "what is AI"

    def test_short_statement_suggestion(self):
        result = validate_topic("machine learning")
        assert result.is_valid
        assert result.has_suggestions
        assert any("question" in s.lower() for s in result.suggestions)

    def test_comparison_no_question_suggestion(self):
        result = validate_topic("Python vs JavaScript")
        assert result.is_valid
        # Comparisons should not get the "frame as question" suggestion
        assert not any("question" in s.lower() for s in result.suggestions)

    def test_preserves_original(self):
        original = "  messy   topic  "
        result = validate_topic(original)
        assert result.original == original
        assert result.topic == "messy topic"


class TestHelpers:
    def test_normalize_whitespace(self):
        assert _normalize_whitespace("  hello   world  ") == "hello world"
        assert _normalize_whitespace("\n\ttab\nnewline\n") == "tab newline"

    def test_is_url_only(self):
        assert _is_url_only("https://example.com")
        assert _is_url_only("http://test.com/page?q=1")
        assert not _is_url_only("check out https://example.com")
        assert not _is_url_only("just text")

    def test_has_excessive_punctuation(self):
        assert _has_excessive_punctuation("what!!!")
        assert _has_excessive_punctuation("really????")
        assert _has_excessive_punctuation("wait....")
        assert not _has_excessive_punctuation("normal text!")
        assert not _has_excessive_punctuation("ok?")

    def test_clean_punctuation(self):
        assert _clean_punctuation("what!!!!") == "what!"
        assert _clean_punctuation("really??????") == "really?"
        assert _clean_punctuation("wait......") == "wait..."
