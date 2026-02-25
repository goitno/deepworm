"""Tests for sentiment and tone analysis."""

import pytest
from deepworm.sentiment import (
    SentimentScore,
    ToneAnalysis,
    SentimentReport,
    analyze_sentiment,
    analyze_tone,
    analyze_report_sentiment,
    sentiment_diff,
    _tokenize,
    _is_negated,
    _get_intensity,
)


# --- SentimentScore ---

class TestSentimentScore:
    def test_default_values(self):
        score = SentimentScore()
        assert score.positive == 0.0
        assert score.negative == 0.0
        assert score.neutral == 0.0
        assert score.label == "neutral"

    def test_to_dict(self):
        score = SentimentScore(
            positive=0.7, negative=0.2, neutral=0.1,
            compound=0.5, label="positive", confidence=0.8,
            word_count=100,
        )
        d = score.to_dict()
        assert d["positive"] == 0.7
        assert d["label"] == "positive"
        assert d["word_count"] == 100


# --- ToneAnalysis ---

class TestToneAnalysis:
    def test_default_values(self):
        tone = ToneAnalysis()
        assert tone.formality == 0.0
        assert tone.objectivity == 0.0
        assert tone.tone_label == "neutral"

    def test_to_dict(self):
        tone = ToneAnalysis(
            formality=0.8, objectivity=0.9, tone_label="academic",
            hedging_count=3, assertion_count=5,
        )
        d = tone.to_dict()
        assert d["formality"] == 0.8
        assert d["tone_label"] == "academic"
        assert d["hedging_count"] == 3


# --- Analyze Sentiment ---

class TestAnalyzeSentiment:
    def test_positive_text(self):
        text = "This is an excellent and innovative approach with great results."
        score = analyze_sentiment(text)
        assert score.label == "positive"
        assert score.compound > 0
        assert len(score.positive_words) > 0

    def test_negative_text(self):
        text = "This is a terrible failure with many serious problems and flaws."
        score = analyze_sentiment(text)
        assert score.label == "negative"
        assert score.compound < 0
        assert len(score.negative_words) > 0

    def test_neutral_text(self):
        text = "The table has four legs and is made of wood."
        score = analyze_sentiment(text)
        assert score.label == "neutral"

    def test_empty_text(self):
        score = analyze_sentiment("")
        assert score.label == "neutral"
        assert score.confidence == 0.0

    def test_negation(self):
        text = "This is not good and not effective at all."
        score = analyze_sentiment(text)
        # Negated positive → negative
        assert score.compound < 0 or score.label in ("negative", "mixed")

    def test_intensifier(self):
        text_normal = "The results are good."
        text_intense = "The results are extremely good."
        score_normal = analyze_sentiment(text_normal)
        score_intense = analyze_sentiment(text_intense)
        assert score_intense.compound >= score_normal.compound

    def test_mixed_sentiment(self):
        text = "While there are excellent benefits, there are also serious risks and problems."
        score = analyze_sentiment(text)
        assert len(score.positive_words) > 0
        assert len(score.negative_words) > 0

    def test_word_count(self):
        text = "This is a good test with five six seven eight words."
        score = analyze_sentiment(text)
        assert score.word_count > 0

    def test_compound_range(self):
        text = "Excellent great wonderful amazing perfect outstanding remarkable."
        score = analyze_sentiment(text)
        assert -1.0 <= score.compound <= 1.0

    def test_markdown_stripped(self):
        text = "## Heading\n**This** is an *excellent* approach."
        score = analyze_sentiment(text)
        assert "excellent" in score.positive_words


# --- Analyze Tone ---

class TestAnalyzeTone:
    def test_academic_tone(self):
        text = (
            "Furthermore, the results demonstrate that the methodology "
            "yields significant improvements. Moreover, the data confirms "
            "the hypothesis. Nevertheless, additional research is warranted. "
            "Therefore, we conclude that the approach is viable."
        )
        tone = analyze_tone(text)
        assert tone.formality > 0.5

    def test_informal_tone(self):
        text = (
            "So basically this thing is pretty cool and actually works "
            "really well. It's awesome stuff that totally makes things easier."
        )
        tone = analyze_tone(text)
        assert tone.formality < 0.5

    def test_hedging_detection(self):
        text = "This might suggest that results could possibly indicate a trend."
        tone = analyze_tone(text)
        assert tone.hedging_count >= 2

    def test_bias_detection_certainty(self):
        text = "Obviously this is the best approach. Clearly everyone agrees."
        tone = analyze_tone(text)
        assert len(tone.bias_indicators) >= 2

    def test_bias_detection_absolute(self):
        text = "Everyone knows this. It always works and never fails."
        tone = analyze_tone(text)
        bias_types = [b["type"] for b in tone.bias_indicators]
        assert "absolute_language" in bias_types

    def test_objectivity_first_person(self):
        text = "I think this is great. In my opinion, we should use this approach."
        tone = analyze_tone(text)
        assert tone.objectivity < 0.8

    def test_empty_text(self):
        tone = analyze_tone("")
        assert tone.formality == 0.0

    def test_to_dict(self):
        text = "The method demonstrates results. However, limitations exist."
        tone = analyze_tone(text)
        d = tone.to_dict()
        assert "formality" in d
        assert "objectivity" in d
        assert "bias_count" in d


# --- Analyze Report Sentiment ---

SAMPLE_REPORT = """
# Research Report

## Introduction

This report examines the excellent progress in machine learning.
The field has achieved remarkable breakthroughs in recent years.

## Challenges

However, there are serious problems with current approaches.
The lack of interpretability remains a critical concern.
Many models fail in edge cases and pose dangerous risks.

## Conclusion

Despite the challenges, the future looks promising.
Innovative solutions are being developed to address these issues.
"""


class TestAnalyzeReportSentiment:
    def test_returns_report(self):
        report = analyze_report_sentiment(SAMPLE_REPORT)
        assert isinstance(report, SentimentReport)

    def test_overall_sentiment(self):
        report = analyze_report_sentiment(SAMPLE_REPORT)
        assert report.overall.word_count > 0

    def test_section_breakdown(self):
        report = analyze_report_sentiment(SAMPLE_REPORT)
        assert len(report.sections) >= 2

    def test_section_labels(self):
        report = analyze_report_sentiment(SAMPLE_REPORT)
        labels = [s["label"] for s in report.sections]
        # Should have at least one positive and one negative section
        assert any(l in ("positive", "mixed") for l in labels)

    def test_tone_analysis(self):
        report = analyze_report_sentiment(SAMPLE_REPORT)
        assert report.tone is not None

    def test_sentence_sentiments(self):
        report = analyze_report_sentiment(SAMPLE_REPORT)
        assert len(report.sentence_sentiments) > 0

    def test_to_markdown(self):
        report = analyze_report_sentiment(SAMPLE_REPORT)
        md = report.to_markdown()
        assert "## Sentiment Analysis" in md
        assert "Overall Sentiment" in md
        assert "Tone" in md

    def test_to_dict(self):
        report = analyze_report_sentiment(SAMPLE_REPORT)
        d = report.to_dict()
        assert "overall" in d
        assert "tone" in d
        assert "sections" in d
        assert "sentence_count" in d

    def test_markdown_table(self):
        report = analyze_report_sentiment(SAMPLE_REPORT)
        md = report.to_markdown()
        assert "| Section |" in md


# --- Sentiment Diff ---

class TestSentimentDiff:
    def test_diff_positive_to_negative(self):
        text_a = "Excellent results with great performance."
        text_b = "Terrible failure with serious problems."
        diff = sentiment_diff(text_a, text_b)
        assert diff["shifted"] is True
        assert diff["shift_direction"] == "more_negative"

    def test_diff_stable(self):
        text_a = "The table has four legs."
        text_b = "The chair has four legs."
        diff = sentiment_diff(text_a, text_b)
        assert diff["shift_direction"] == "stable"

    def test_diff_structure(self):
        diff = sentiment_diff("Good results.", "Bad results.")
        assert "text_a" in diff
        assert "text_b" in diff
        assert "compound_diff" in diff
        assert "shifted" in diff


# --- Helpers ---

class TestHelpers:
    def test_tokenize_basic(self):
        tokens = _tokenize("Hello World, this is a test!")
        assert "hello" in tokens
        assert "world" in tokens

    def test_tokenize_strips_markdown(self):
        tokens = _tokenize("## Heading\n**Bold** and `code`")
        assert "heading" in tokens
        assert "bold" in tokens

    def test_tokenize_strips_code_blocks(self):
        tokens = _tokenize("Text before\n```python\ncode here\n```\nText after")
        assert "text" in tokens
        assert "code" not in tokens

    def test_is_negated(self):
        words = ["this", "is", "not", "good"]
        assert _is_negated(words, 3) is True
        assert _is_negated(words, 1) is False

    def test_get_intensity_normal(self):
        words = ["this", "is", "good"]
        assert _get_intensity(words, 2) == 1.0

    def test_get_intensity_intensified(self):
        words = ["this", "is", "extremely", "good"]
        assert _get_intensity(words, 3) == 1.5
