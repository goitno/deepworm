"""Advanced content extraction from web pages and text.

Provides enhanced text extraction beyond basic HTML stripping:
- Extracts article/main content from noisy web pages
- Identifies metadata (title, author, date, description)
- Extracts structured data (headings, lists, code blocks)
- Estimates reading time and content quality signals
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional
from html import unescape


@dataclass
class ExtractedContent:
    """Structured content extracted from a web page."""
    title: str = ""
    text: str = ""
    description: str = ""
    author: str = ""
    date: str = ""
    headings: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    code_blocks: list[str] = field(default_factory=list)
    word_count: int = 0
    reading_time_minutes: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "text": self.text,
            "description": self.description,
            "author": self.author,
            "date": self.date,
            "headings": self.headings,
            "links": self.links,
            "code_blocks": self.code_blocks,
            "word_count": self.word_count,
            "reading_time_minutes": self.reading_time_minutes,
        }


def extract_content(html: str) -> ExtractedContent:
    """Extract structured content from an HTML page.

    Args:
        html: Raw HTML string.

    Returns:
        ExtractedContent with text, metadata, and structure.
    """
    content = ExtractedContent()

    # Extract metadata first (before cleaning)
    content.title = _extract_title(html)
    content.description = _extract_meta(html, "description")
    content.author = _extract_meta(html, "author") or _extract_meta_property(html, "article:author")
    content.date = (
        _extract_meta_property(html, "article:published_time")
        or _extract_meta(html, "date")
        or _extract_time_element(html)
    )

    # Extract code blocks before stripping HTML
    content.code_blocks = _extract_code_blocks(html)

    # Extract headings
    content.headings = _extract_headings(html)

    # Extract links
    content.links = _extract_href_links(html)

    # Extract main text content
    content.text = _extract_article_text(html)

    # Calculate word count and reading time
    words = content.text.split()
    content.word_count = len(words)
    content.reading_time_minutes = round(len(words) / 238, 1)  # avg reading speed

    return content


def extract_article_text(html: str) -> str:
    """Extract just the article text from HTML.

    Tries to identify the main content area and extract clean text,
    ignoring navigation, sidebars, footers, etc.

    Args:
        html: Raw HTML string.

    Returns:
        Clean text content.
    """
    return _extract_article_text(html)


def extract_metadata(html: str) -> dict[str, str]:
    """Extract metadata from an HTML page.

    Args:
        html: Raw HTML string.

    Returns:
        Dict with title, description, author, date.
    """
    return {
        "title": _extract_title(html),
        "description": _extract_meta(html, "description"),
        "author": _extract_meta(html, "author") or _extract_meta_property(html, "article:author"),
        "date": (
            _extract_meta_property(html, "article:published_time")
            or _extract_meta(html, "date")
            or _extract_time_element(html)
        ),
    }


def estimate_content_quality(text: str) -> float:
    """Estimate the quality/usefulness of extracted text.

    Returns a score from 0.0 to 1.0 based on heuristic signals:
    - Length (very short = low quality)
    - Paragraph structure
    - Vocabulary diversity
    - Presence of data/facts
    - Absence of boilerplate patterns

    Args:
        text: Extracted text content.

    Returns:
        Quality score between 0.0 and 1.0.
    """
    if not text or len(text.split()) < 10:
        return 0.0

    score = 0.5  # base score

    words = text.split()
    word_count = len(words)

    # Length bonus (more content = more useful, up to a point)
    if word_count > 100:
        score += 0.1
    if word_count > 300:
        score += 0.1

    # Paragraph structure (well-structured text has paragraphs)
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(paragraphs) > 2:
        score += 0.1

    # Vocabulary diversity
    unique_words = set(w.lower() for w in words)
    diversity = len(unique_words) / max(word_count, 1)
    if diversity > 0.3:
        score += 0.1

    # Factual signals (numbers, dates, proper nouns)
    number_count = len(re.findall(r"\d+", text))
    if number_count > 3:
        score += 0.05

    # Boilerplate penalty
    boilerplate_patterns = [
        r"cookie", r"privacy policy", r"subscribe", r"newsletter",
        r"sign up", r"log in", r"terms of service", r"accept all",
    ]
    boilerplate_hits = sum(
        1 for p in boilerplate_patterns if re.search(p, text, re.IGNORECASE)
    )
    score -= boilerplate_hits * 0.05

    return max(0.0, min(1.0, round(score, 2)))


# --- Internal extraction functions ---

def _extract_title(html: str) -> str:
    """Extract page title."""
    # Try og:title first
    og = _extract_meta_property(html, "og:title")
    if og:
        return og

    # Try <title> tag
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
    if match:
        title = match.group(1).strip()
        # Clean common title patterns like "Article Title | Site Name"
        title = re.split(r"\s*[|–—·]\s*", title)[0].strip()
        return _decode_entities(title)

    return ""


def _extract_meta(html: str, name: str) -> str:
    """Extract content from a <meta name=...> tag."""
    pattern = rf'<meta\s+name=["\']?{re.escape(name)}["\']?\s+content=["\']([^"\']*)["\']'
    match = re.search(pattern, html, re.IGNORECASE)
    if match:
        return _decode_entities(match.group(1).strip())

    # Try reversed attribute order
    pattern2 = rf'<meta\s+content=["\']([^"\']*)["\'].*?name=["\']?{re.escape(name)}["\']?'
    match2 = re.search(pattern2, html, re.IGNORECASE)
    if match2:
        return _decode_entities(match2.group(1).strip())

    return ""


def _extract_meta_property(html: str, prop: str) -> str:
    """Extract content from a <meta property=...> tag (OpenGraph)."""
    pattern = rf'<meta\s+property=["\']?{re.escape(prop)}["\']?\s+content=["\']([^"\']*)["\']'
    match = re.search(pattern, html, re.IGNORECASE)
    if match:
        return _decode_entities(match.group(1).strip())

    pattern2 = rf'<meta\s+content=["\']([^"\']*)["\'].*?property=["\']?{re.escape(prop)}["\']?'
    match2 = re.search(pattern2, html, re.IGNORECASE)
    if match2:
        return _decode_entities(match2.group(1).strip())

    return ""


def _extract_time_element(html: str) -> str:
    """Extract date from <time> element."""
    match = re.search(
        r'<time[^>]*datetime=["\']([^"\']+)["\']',
        html, re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()
    return ""


def _extract_headings(html: str) -> list[str]:
    """Extract all headings (h1-h6)."""
    headings = []
    for match in re.finditer(r"<h[1-6][^>]*>(.*?)</h[1-6]>", html, re.DOTALL | re.IGNORECASE):
        text = re.sub(r"<[^>]+>", "", match.group(1)).strip()
        text = _decode_entities(text)
        if text:
            headings.append(text)
    return headings


def _extract_href_links(html: str) -> list[str]:
    """Extract all href links from anchor tags."""
    links = []
    for match in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\']', html, re.IGNORECASE):
        href = match.group(1).strip()
        if href.startswith(("http://", "https://")):
            links.append(href)
    return list(dict.fromkeys(links))  # deduplicate preserving order


def _extract_code_blocks(html: str) -> list[str]:
    """Extract code blocks from <pre><code> or <pre> tags."""
    blocks = []
    for match in re.finditer(
        r"<pre[^>]*>\s*(?:<code[^>]*>)?(.*?)(?:</code>)?\s*</pre>",
        html, re.DOTALL | re.IGNORECASE,
    ):
        code = re.sub(r"<[^>]+>", "", match.group(1))
        code = _decode_entities(code).strip()
        if code:
            blocks.append(code)
    return blocks


def _extract_article_text(html: str) -> str:
    """Extract main article text, trying to identify content area."""
    # Try to find main content area
    main_content = ""

    # Priority: <article>, <main>, role="main", .content, #content
    for pattern in [
        r"<article[^>]*>(.*?)</article>",
        r"<main[^>]*>(.*?)</main>",
        r'<div[^>]*role=["\']main["\'][^>]*>(.*?)</div>',
        r'<div[^>]*class=["\'][^"\']*content[^"\']*["\'][^>]*>(.*?)</div>',
        r'<div[^>]*id=["\']content["\'][^>]*>(.*?)</div>',
    ]:
        match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
        if match and len(match.group(1)) > 200:
            main_content = match.group(1)
            break

    if not main_content:
        # Fall back to body
        body_match = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.IGNORECASE)
        main_content = body_match.group(1) if body_match else html

    return _html_to_text(main_content)


def _html_to_text(html: str) -> str:
    """Convert HTML fragment to clean text."""
    # Remove non-content elements
    for tag in ["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]:
        html = re.sub(
            rf"<{tag}[^>]*>.*?</{tag}>", " ", html,
            flags=re.DOTALL | re.IGNORECASE,
        )
    html = re.sub(r"<!--.*?-->", " ", html, flags=re.DOTALL)

    # Add newlines for block elements
    for tag in ["p", "br", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "blockquote"]:
        html = re.sub(rf"</?{tag}[^>]*>", "\n", html, flags=re.IGNORECASE)

    # Strip remaining tags
    text = re.sub(r"<[^>]+>", " ", html)

    # Decode entities
    text = _decode_entities(text)

    # Normalize whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n", "\n\n", text)
    text = text.strip()

    return text


def _decode_entities(text: str) -> str:
    """Decode HTML entities."""
    try:
        return unescape(text)
    except Exception:
        # Fallback manual decoding
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&quot;", '"')
        text = text.replace("&#39;", "'")
        text = text.replace("&nbsp;", " ")
        return text
