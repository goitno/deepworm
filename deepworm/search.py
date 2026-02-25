"""Web search using DuckDuckGo."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote_plus, unquote

import httpx


@dataclass
class SearchResult:
    """A single search result."""
    title: str
    url: str
    snippet: str
    body: Optional[str] = None


_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
}


def search_web(
    query: str,
    max_results: int = 8,
    region: str = "wt-wt",
) -> list[SearchResult]:
    """Search the web using DuckDuckGo HTML."""
    results: list[SearchResult] = []
    try:
        # Try the duckduckgo_search / ddgs library first
        results = _search_ddgs(query, max_results)
    except Exception:
        pass

    if not results:
        # Fallback: DuckDuckGo HTML scraping
        try:
            results = _search_html(query, max_results)
        except Exception:
            pass

    return results[:max_results]


def _search_ddgs(query: str, max_results: int) -> list[SearchResult]:
    """Try the ddgs/duckduckgo_search library."""
    results = []
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    snippet=r.get("body", ""),
                ))
    except ImportError:
        try:
            from ddgs import DDGS
            ddgs = DDGS()
            for r in ddgs.text(query, max_results=max_results):
                results.append(SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    snippet=r.get("body", ""),
                ))
        except (ImportError, Exception):
            raise
    return results


def _search_html(query: str, max_results: int) -> list[SearchResult]:
    """Fallback: scrape DuckDuckGo HTML results."""
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    resp = httpx.get(url, headers=_HEADERS, timeout=15.0, follow_redirects=True)
    resp.raise_for_status()

    results = []
    # Parse result blocks
    blocks = re.findall(
        r'<a[^>]+class="result__a"[^>]+href="([^"]*)"[^>]*>(.*?)</a>.*?'
        r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
        resp.text,
        re.DOTALL,
    )
    for href, title, snippet in blocks[:max_results]:
        # DuckDuckGo wraps URLs in a redirect
        actual_url = _extract_ddg_url(href)
        clean_title = re.sub(r'<[^>]+>', '', title).strip()
        clean_snippet = re.sub(r'<[^>]+>', '', snippet).strip()
        if actual_url and clean_title:
            results.append(SearchResult(
                title=clean_title,
                url=actual_url,
                snippet=clean_snippet,
            ))

    return results


def _extract_ddg_url(href: str) -> str:
    """Extract real URL from DuckDuckGo redirect URL."""
    if "duckduckgo.com" in href and "uddg=" in href:
        match = re.search(r'uddg=([^&]+)', href)
        if match:
            return unquote(match.group(1))
    return href


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
