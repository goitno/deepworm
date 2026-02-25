"""Tests for deepworm.links."""

from __future__ import annotations

import pytest

from deepworm.links import (
    LinkInfo,
    LinkReport,
    LinkStatus,
    _is_valid_url,
    check_links,
    extract_links,
)

SAMPLE_MD = """# Test Report

This is a report about [Python](https://python.org) and
[JavaScript](https://javascript.info/intro).

Check out https://example.com for more.

## References

More info at [docs][1] and [API][2].

[1]: https://docs.example.com
[2]: https://api.example.com/v1
"""


class TestExtractLinks:
    def test_inline_links(self):
        links = extract_links(SAMPLE_MD)
        urls = [l.url for l in links]
        assert "https://python.org" in urls
        assert "https://javascript.info/intro" in urls

    def test_bare_urls(self):
        links = extract_links(SAMPLE_MD)
        urls = [l.url for l in links]
        assert "https://example.com" in urls

    def test_reference_links(self):
        links = extract_links(SAMPLE_MD)
        urls = [l.url for l in links]
        assert "https://docs.example.com" in urls
        assert "https://api.example.com/v1" in urls

    def test_line_numbers(self):
        links = extract_links(SAMPLE_MD)
        python_link = next(l for l in links if "python.org" in l.url)
        assert python_link.line > 0

    def test_deduplication(self):
        md = "[a](https://example.com) and [b](https://example.com)"
        links = extract_links(md)
        assert len(links) == 1

    def test_empty_markdown(self):
        links = extract_links("")
        assert links == []

    def test_no_links(self):
        links = extract_links("Just plain text, no links here.")
        assert links == []

    def test_skips_local_links(self):
        md = "[section](#heading) and [file](./local.md)"
        links = extract_links(md)
        assert len(links) == 0  # no http/https links

    def test_link_text_preserved(self):
        md = "[Deep Research](https://example.com/deep)"
        links = extract_links(md)
        assert links[0].text == "Deep Research"

    def test_bare_url_strips_punctuation(self):
        md = "Visit https://example.com/page."
        links = extract_links(md)
        assert links[0].url == "https://example.com/page"


class TestLinkInfo:
    def test_unchecked_by_default(self):
        info = LinkInfo(url="https://x.com", text="x", line=1)
        assert info.status == LinkStatus.UNCHECKED
        assert not info.is_ok
        assert not info.is_broken

    def test_ok_status(self):
        info = LinkInfo(url="https://x.com", text="x", line=1, status=LinkStatus.OK)
        assert info.is_ok
        assert not info.is_broken

    def test_broken_status(self):
        info = LinkInfo(url="https://x.com", text="x", line=1, status=LinkStatus.BROKEN)
        assert info.is_broken
        assert not info.is_ok

    def test_invalid_is_broken(self):
        info = LinkInfo(url="bad", text="x", line=1, status=LinkStatus.INVALID)
        assert info.is_broken


class TestLinkReport:
    def _make_report(self, statuses: list[LinkStatus]) -> LinkReport:
        links = [
            LinkInfo(url=f"https://example.com/{i}", text=f"link{i}", line=i, status=s)
            for i, s in enumerate(statuses, 1)
        ]
        return LinkReport(links=links)

    def test_counts(self):
        report = self._make_report([
            LinkStatus.OK, LinkStatus.OK, LinkStatus.BROKEN, LinkStatus.UNCHECKED,
        ])
        assert report.total == 4
        assert report.ok_count == 2
        assert report.broken_count == 1
        assert report.unchecked_count == 1

    def test_health_score(self):
        report = self._make_report([LinkStatus.OK, LinkStatus.OK, LinkStatus.BROKEN])
        assert report.health_score == pytest.approx(0.67, abs=0.01)

    def test_health_score_all_ok(self):
        report = self._make_report([LinkStatus.OK, LinkStatus.OK])
        assert report.health_score == 1.0

    def test_health_score_empty(self):
        report = LinkReport()
        assert report.health_score == 1.0

    def test_broken_links_list(self):
        report = self._make_report([LinkStatus.OK, LinkStatus.BROKEN, LinkStatus.INVALID])
        broken = report.broken_links
        assert len(broken) == 2

    def test_to_markdown(self):
        report = self._make_report([LinkStatus.OK, LinkStatus.BROKEN])
        md = report.to_markdown()
        assert "# Link Check Report" in md
        assert "OK" in md
        assert "Broken" in md


class TestCheckLinks:
    def test_without_verification(self):
        report = check_links(SAMPLE_MD, verify=False)
        assert report.total > 0
        assert report.unchecked_count == report.total

    def test_empty_markdown(self):
        report = check_links("", verify=False)
        assert report.total == 0


class TestIsValidUrl:
    def test_valid_urls(self):
        assert _is_valid_url("https://example.com")
        assert _is_valid_url("http://test.org/page?q=1")

    def test_invalid_urls(self):
        assert not _is_valid_url("not-a-url")
        assert not _is_valid_url("ftp://files.com")
        assert not _is_valid_url("")
