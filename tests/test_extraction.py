"""Tests for deepworm.extraction."""

from __future__ import annotations

from deepworm.extraction import (
    ExtractedContent,
    _decode_entities,
    _extract_code_blocks,
    _extract_headings,
    _extract_href_links,
    _extract_meta,
    _extract_meta_property,
    _extract_time_element,
    _extract_title,
    _html_to_text,
    estimate_content_quality,
    extract_article_text,
    extract_content,
    extract_metadata,
)

SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Article | Example Site</title>
    <meta name="description" content="A test article about AI research.">
    <meta name="author" content="John Doe">
    <meta property="og:title" content="Test Article">
    <meta property="article:published_time" content="2024-01-15">
</head>
<body>
<nav>Navigation links here</nav>
<article>
    <h1>Test Article on AI Research</h1>
    <time datetime="2024-01-15">January 15, 2024</time>
    <p>This is the first paragraph about artificial intelligence.
       It contains important information about machine learning.</p>
    <h2>Methods</h2>
    <p>We used various methods including deep learning and
       natural language processing to analyze the data.</p>
    <pre><code>print("hello world")</code></pre>
    <p>Results show significant improvements. More details at
       <a href="https://example.com/details">this link</a> and
       <a href="https://example.com/data">data source</a>.</p>
</article>
<footer>Copyright 2024</footer>
</body>
</html>
"""


class TestExtractContent:
    def test_full_extraction(self):
        result = extract_content(SAMPLE_HTML)
        assert isinstance(result, ExtractedContent)
        assert result.title == "Test Article"
        assert "artificial intelligence" in result.text
        assert result.word_count > 0
        assert result.reading_time_minutes >= 0

    def test_description(self):
        result = extract_content(SAMPLE_HTML)
        assert result.description == "A test article about AI research."

    def test_author(self):
        result = extract_content(SAMPLE_HTML)
        assert result.author == "John Doe"

    def test_date(self):
        result = extract_content(SAMPLE_HTML)
        assert "2024-01-15" in result.date

    def test_headings(self):
        result = extract_content(SAMPLE_HTML)
        assert "Test Article on AI Research" in result.headings
        assert "Methods" in result.headings

    def test_links(self):
        result = extract_content(SAMPLE_HTML)
        assert "https://example.com/details" in result.links
        assert "https://example.com/data" in result.links

    def test_code_blocks(self):
        result = extract_content(SAMPLE_HTML)
        assert len(result.code_blocks) > 0
        assert 'print("hello world")' in result.code_blocks[0]

    def test_to_dict(self):
        result = extract_content(SAMPLE_HTML)
        d = result.to_dict()
        assert "title" in d
        assert "text" in d
        assert "word_count" in d

    def test_empty_html(self):
        result = extract_content("")
        assert result.text == ""
        assert result.word_count == 0


class TestExtractArticleText:
    def test_extracts_article(self):
        text = extract_article_text(SAMPLE_HTML)
        assert "artificial intelligence" in text
        assert "machine learning" in text

    def test_removes_nav_footer(self):
        text = extract_article_text(SAMPLE_HTML)
        assert "Navigation links" not in text
        assert "Copyright" not in text

    def test_plain_text(self):
        text = extract_article_text("<p>Just plain text</p>")
        assert "plain text" in text


class TestExtractMetadata:
    def test_extracts_all_metadata(self):
        meta = extract_metadata(SAMPLE_HTML)
        assert meta["title"] == "Test Article"
        assert "AI research" in meta["description"]
        assert meta["author"] == "John Doe"
        assert "2024" in meta["date"]

    def test_empty_html(self):
        meta = extract_metadata("")
        assert meta["title"] == ""


class TestEstimateContentQuality:
    def test_empty_text(self):
        assert estimate_content_quality("") == 0.0

    def test_very_short_text(self):
        assert estimate_content_quality("just a few words") == 0.0

    def test_medium_quality(self):
        text = "This is a paragraph about a topic. " * 20
        score = estimate_content_quality(text)
        assert 0.3 <= score <= 0.8

    def test_high_quality_text(self):
        paragraphs = []
        for i in range(5):
            paragraphs.append(
                f"Section {i}: This paragraph discusses unique concepts "
                f"with diverse vocabulary including specific data points "
                f"like {i * 100}% improvement and {2024 + i} projections."
            )
        text = "\n\n".join(paragraphs)
        score = estimate_content_quality(text)
        assert score > 0.5

    def test_boilerplate_penalty(self):
        text = (
            "Please accept our cookie policy. Subscribe to our newsletter. "
            "Sign up now for privacy policy updates. " * 10
        )
        score = estimate_content_quality(text)
        assert score < 0.7  # penalized for boilerplate


class TestHelperFunctions:
    def test_extract_title_og(self):
        html = '<meta property="og:title" content="OG Title">'
        assert _extract_title(html) == "OG Title"

    def test_extract_title_tag(self):
        html = "<title>Page Title | Site</title>"
        assert _extract_title(html) == "Page Title"

    def test_extract_meta(self):
        html = '<meta name="description" content="My description">'
        assert _extract_meta(html, "description") == "My description"

    def test_extract_meta_reversed_order(self):
        html = '<meta content="Author Name" name="author">'
        assert _extract_meta(html, "author") == "Author Name"

    def test_extract_meta_property(self):
        html = '<meta property="og:title" content="Title">'
        assert _extract_meta_property(html, "og:title") == "Title"

    def test_extract_time_element(self):
        html = '<time datetime="2024-03-15">March 15</time>'
        assert _extract_time_element(html) == "2024-03-15"

    def test_extract_headings(self):
        html = "<h1>Title</h1><h2>Section A</h2><h3>Sub</h3>"
        headings = _extract_headings(html)
        assert headings == ["Title", "Section A", "Sub"]

    def test_extract_href_links(self):
        html = '<a href="https://a.com">A</a> <a href="https://b.com">B</a>'
        links = _extract_href_links(html)
        assert "https://a.com" in links
        assert "https://b.com" in links

    def test_extract_href_links_dedup(self):
        html = '<a href="https://a.com">1</a><a href="https://a.com">2</a>'
        links = _extract_href_links(html)
        assert len(links) == 1

    def test_extract_code_blocks(self):
        html = "<pre><code>x = 1</code></pre>"
        blocks = _extract_code_blocks(html)
        assert len(blocks) == 1
        assert "x = 1" in blocks[0]

    def test_html_to_text(self):
        html = "<p>Hello</p><p>World</p>"
        text = _html_to_text(html)
        assert "Hello" in text
        assert "World" in text

    def test_decode_entities(self):
        assert _decode_entities("&amp;") == "&"
        assert _decode_entities("&lt;div&gt;") == "<div>"
        assert _decode_entities("&quot;hello&quot;") == '"hello"'
