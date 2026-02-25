"""Web search using DuckDuckGo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import httpx
from duckduckgo_search import DDGS


@dataclass
class SearchResult:
    """A single search result."""
    title: str
    url: str
    snippet: str
    body: Optional[str] = None


def search_web(
    query: str,
    max_results: int = 8,
    region: str = "wt-wt",
) -> list[SearchResult]:
    """Search the web using DuckDuckGo."""
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, region=region, max_results=max_results):
                results.append(SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    snippet=r.get("body", ""),
                ))
    except Exception:
        pass
    return results


def fetch_page_text(url: str, timeout: float = 10.0) -> str:
    """Fetch and extract text content from a URL."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
        }
        resp = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        if "text/html" not in content_type and "text/plain" not in content_type:
            return ""

        text = resp.text
        text = _extract_text_from_html(text)
        # Truncate to reasonable length
        if len(text) > 8000:
            text = text[:8000]
        return text
    except Exception:
        return ""


def _extract_text_from_html(html: str) -> str:
    """Extract readable text from HTML. Simple approach without BeautifulSoup."""
    import re

    # Remove script and style blocks
    text = re.sub(r'<script[^>]*>.*?</script>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<head[^>]*>.*?</head>', ' ', text, flags=re.DOTALL | re.IGNORECASE)

    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)

    # Decode common HTML entities
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    text = text.replace('&nbsp;', ' ')

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text
