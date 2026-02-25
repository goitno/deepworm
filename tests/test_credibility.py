"""Tests for deepworm.credibility."""

import pytest

from deepworm.credibility import (
    CredibilityReport,
    CredibilityScore,
    _score_content,
    _score_domain,
    _score_freshness,
    score_source,
    score_sources,
)


class TestScoreSource:
    def test_tier1_domain(self):
        s = score_source("https://arxiv.org/abs/2301.00001")
        assert s.domain_score >= 0.85
        assert s.tier == "tier1"
        assert s.label in ("High", "Medium")

    def test_tier2_domain(self):
        s = score_source("https://medium.com/some-article")
        assert s.tier == "tier2"
        assert s.domain_score >= 0.7

    def test_low_credibility_domain(self):
        s = score_source("https://buzzfeed.com/listicle")
        assert s.tier == "low"
        assert s.domain_score <= 0.3

    def test_edu_domain(self):
        s = score_source("https://www.mit.edu/research/paper")
        assert s.tier == "tier1"
        assert s.domain_score >= 0.85

    def test_gov_domain(self):
        s = score_source("https://data.gov/dataset/123")
        assert s.tier == "tier1"

    def test_unknown_domain(self):
        s = score_source("https://random-site-12345.com/page")
        assert s.tier == "standard"
        assert s.domain_score == 0.5

    def test_subdomain_tier1(self):
        s = score_source("https://docs.github.com/en/actions")
        assert s.tier == "tier1"

    def test_with_content(self):
        content = """
        This research study analyzed data from 500 participants.
        The findings indicate a significant correlation (p < 0.05).
        Results were verified through cross-validation.
        Multiple references cited in the bibliography section.
        """ * 50  # Make it substantial
        s = score_source("https://example.com/paper", content=content)
        assert s.content_score > 0.5

    def test_with_spam_content(self):
        content = "BUY NOW!!! Limited time offer $$$ FREE GUARANTEED results click here"
        s = score_source("https://example.com/spam", content=content)
        assert s.content_score < 0.5

    def test_with_date_recent(self):
        s = score_source("https://example.com/article", published_date="2025-01-15")
        assert s.freshness_score >= 0.8

    def test_with_date_old(self):
        s = score_source("https://example.com/article", published_date="2005-06-01")
        assert s.freshness_score < 0.5

    def test_to_dict(self):
        s = score_source("https://arxiv.org/abs/123")
        d = s.to_dict()
        assert "url" in d
        assert "domain" in d
        assert "overall_score" in d
        assert "label" in d
        assert "tier" in d
        assert "signals" in d


class TestCredibilityScore:
    def test_label_high(self):
        s = CredibilityScore(
            url="", domain="", overall_score=0.9,
            domain_score=0.9, content_score=0.9, freshness_score=0.9,
        )
        assert s.label == "High"

    def test_label_medium(self):
        s = CredibilityScore(
            url="", domain="", overall_score=0.6,
            domain_score=0.6, content_score=0.6, freshness_score=0.6,
        )
        assert s.label == "Medium"

    def test_label_low(self):
        s = CredibilityScore(
            url="", domain="", overall_score=0.35,
            domain_score=0.3, content_score=0.3, freshness_score=0.3,
        )
        assert s.label == "Low"

    def test_label_very_low(self):
        s = CredibilityScore(
            url="", domain="", overall_score=0.1,
            domain_score=0.1, content_score=0.1, freshness_score=0.1,
        )
        assert s.label == "Very Low"


class TestScoreSources:
    def test_multiple_sources(self):
        urls = [
            "https://arxiv.org/abs/123",
            "https://medium.com/article",
            "https://example.com/page",
        ]
        report = score_sources(urls)
        assert len(report.scores) == 3
        assert report.average_score > 0

    def test_with_contents(self):
        urls = ["https://example.com/a"]
        contents = {"https://example.com/a": "Some content with research data."}
        report = score_sources(urls, contents=contents)
        assert len(report.scores) == 1

    def test_empty_list(self):
        report = score_sources([])
        assert report.average_score == 0.0
        assert report.high_credibility_count == 0


class TestCredibilityReport:
    def test_to_markdown(self):
        report = score_sources([
            "https://arxiv.org/abs/1",
            "https://medium.com/x",
        ])
        md = report.to_markdown()
        assert "Source Credibility Report" in md
        assert "Score" in md
        assert "Tier" in md

    def test_to_dict(self):
        report = score_sources(["https://arxiv.org/abs/1"])
        d = report.to_dict()
        assert "average_score" in d
        assert "scores" in d
        assert len(d["scores"]) == 1

    def test_high_low_counts(self):
        report = CredibilityReport(scores=[
            CredibilityScore(
                url="", domain="", overall_score=0.9,
                domain_score=0.9, content_score=0.9, freshness_score=0.9,
            ),
            CredibilityScore(
                url="", domain="", overall_score=0.1,
                domain_score=0.1, content_score=0.1, freshness_score=0.1,
            ),
        ])
        assert report.high_credibility_count == 1
        assert report.low_credibility_count == 1


class TestScoreDomain:
    def test_tier1(self):
        score, tier = _score_domain("nature.com", [], [])
        assert tier == "tier1"
        assert score >= 0.9

    def test_tier2(self):
        score, tier = _score_domain("wikipedia.org", [], [])
        assert tier == "tier2"

    def test_standard(self):
        score, tier = _score_domain("unknown-site.io", [], [])
        assert tier == "standard"


class TestScoreContent:
    def test_empty(self):
        assert _score_content("", [], []) == 0.5

    def test_long_quality_content(self):
        content = "research study findings data analysis " * 200
        content += "\nReferences\n1. Author (2024).\n"
        score = _score_content(content, [], [])
        assert score > 0.6

    def test_promotional_content(self):
        content = "Buy now! Limited time offer! Click here to get started!"
        score = _score_content(content, [], [])
        assert score < 0.5


class TestScoreFreshness:
    def test_no_date(self):
        assert _score_freshness(None, [], []) == 0.5

    def test_recent(self):
        score = _score_freshness("2025-01-01", [], [])
        assert score >= 0.8

    def test_old(self):
        score = _score_freshness("2000-01-01", [], [])
        assert score <= 0.3

    def test_invalid_date(self):
        score = _score_freshness("not-a-date", [], [])
        assert score == 0.5
