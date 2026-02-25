"""Markdown link validation.

Check links in markdown reports for validity:
- Detect broken inline links
- Detect broken reference-style links
- Check URL accessibility (optional, async-capable)
- Generate a link health report
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class LinkStatus(Enum):
    """Status of a checked link."""
    OK = "ok"
    BROKEN = "broken"
    TIMEOUT = "timeout"
    UNCHECKED = "unchecked"
    INVALID = "invalid"  # malformed URL


@dataclass
class LinkInfo:
    """Information about a single link."""
    url: str
    text: str
    line: int  # 1-indexed line number
    status: LinkStatus = LinkStatus.UNCHECKED
    status_code: int = 0
    error: str = ""

    @property
    def is_ok(self) -> bool:
        return self.status == LinkStatus.OK

    @property
    def is_broken(self) -> bool:
        return self.status in (LinkStatus.BROKEN, LinkStatus.INVALID)


@dataclass
class LinkReport:
    """Summary of link checking results."""
    links: list[LinkInfo] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.links)

    @property
    def ok_count(self) -> int:
        return sum(1 for l in self.links if l.status == LinkStatus.OK)

    @property
    def broken_count(self) -> int:
        return sum(1 for l in self.links if l.is_broken)

    @property
    def unchecked_count(self) -> int:
        return sum(1 for l in self.links if l.status == LinkStatus.UNCHECKED)

    @property
    def broken_links(self) -> list[LinkInfo]:
        return [l for l in self.links if l.is_broken]

    @property
    def health_score(self) -> float:
        """Link health as a ratio (0.0 to 1.0). 1.0 means all links are OK."""
        checked = [l for l in self.links if l.status != LinkStatus.UNCHECKED]
        if not checked:
            return 1.0
        ok = sum(1 for l in checked if l.is_ok)
        return round(ok / len(checked), 2)

    def to_markdown(self) -> str:
        """Generate a markdown report of link status."""
        lines = [
            "# Link Check Report",
            "",
            f"**Total:** {self.total} | "
            f"**OK:** {self.ok_count} | "
            f"**Broken:** {self.broken_count} | "
            f"**Unchecked:** {self.unchecked_count} | "
            f"**Health:** {self.health_score:.0%}",
            "",
        ]

        if self.broken_links:
            lines.append("## Broken Links")
            lines.append("")
            for link in self.broken_links:
                lines.append(
                    f"- **Line {link.line}**: [{link.text}]({link.url}) — {link.error or link.status.value}"
                )
            lines.append("")

        return "\n".join(lines)


def extract_links(markdown: str) -> list[LinkInfo]:
    """Extract all links from markdown text.

    Finds:
    - Inline links: [text](url)
    - Bare URLs: https://example.com
    - Reference links: [text][ref] with [ref]: url

    Args:
        markdown: Markdown text to scan.

    Returns:
        List of LinkInfo objects.
    """
    links: list[LinkInfo] = []
    lines = markdown.split("\n")

    # Collect reference definitions
    ref_defs: dict[str, str] = {}
    for line_text in lines:
        ref_match = re.match(r"^\s*\[([^\]]+)\]:\s*(\S+)", line_text)
        if ref_match:
            ref_defs[ref_match.group(1).lower()] = ref_match.group(2)

    for line_num, line_text in enumerate(lines, 1):
        # Inline links: [text](url)
        for match in re.finditer(r"\[([^\]]*)\]\(([^)]+)\)", line_text):
            text = match.group(1)
            url = match.group(2).strip()
            if url.startswith(("http://", "https://")):
                links.append(LinkInfo(url=url, text=text, line=line_num))

        # Reference links: [text][ref]
        for match in re.finditer(r"\[([^\]]+)\]\[([^\]]*)\]", line_text):
            text = match.group(1)
            ref = match.group(2).lower() or text.lower()
            if ref in ref_defs:
                url = ref_defs[ref]
                if url.startswith(("http://", "https://")):
                    links.append(LinkInfo(url=url, text=text, line=line_num))

        # Bare URLs (not inside markdown link syntax)
        for match in re.finditer(r"(?<!\()(https?://\S+)(?!\))", line_text):
            url = match.group(1).rstrip(".,;:!?)")
            # Skip if it's part of a markdown link
            start = match.start()
            before = line_text[:start]
            if before.endswith("]("):
                continue
            # Skip reference definitions
            if re.match(r"^\s*\[[^\]]+\]:", line_text):
                continue
            links.append(LinkInfo(url=url, text=url, line=line_num))

    # Deduplicate by URL, keeping first occurrence
    seen: set[str] = set()
    unique: list[LinkInfo] = []
    for link in links:
        if link.url not in seen:
            seen.add(link.url)
            unique.append(link)

    return unique


def check_links(
    markdown: str,
    timeout: float = 5.0,
    verify: bool = True,
) -> LinkReport:
    """Extract and optionally verify links in markdown.

    Args:
        markdown: Markdown text to check.
        timeout: HTTP request timeout in seconds.
        verify: Whether to actually check URLs (makes HTTP requests).

    Returns:
        LinkReport with results.
    """
    links = extract_links(markdown)
    report = LinkReport(links=links)

    if not verify:
        return report

    # Validate URLs without making requests (basic format check)
    for link in links:
        if not _is_valid_url(link.url):
            link.status = LinkStatus.INVALID
            link.error = "Malformed URL"
            continue

    # Check URLs with HTTP HEAD requests
    try:
        import httpx
    except ImportError:
        logger.debug("httpx not available, skipping URL verification")
        return report

    for link in links:
        if link.status != LinkStatus.UNCHECKED:
            continue
        try:
            resp = httpx.head(
                link.url,
                timeout=timeout,
                follow_redirects=True,
                headers={"User-Agent": "deepworm-link-checker/1.0"},
            )
            link.status_code = resp.status_code
            if resp.status_code < 400:
                link.status = LinkStatus.OK
            else:
                link.status = LinkStatus.BROKEN
                link.error = f"HTTP {resp.status_code}"
        except httpx.TimeoutException:
            link.status = LinkStatus.TIMEOUT
            link.error = "Request timed out"
        except Exception as e:
            link.status = LinkStatus.BROKEN
            link.error = str(e)[:100]

    return report


def _is_valid_url(url: str) -> bool:
    """Basic URL format validation."""
    return bool(re.match(r"^https?://[^\s]+\.[^\s]+", url))
