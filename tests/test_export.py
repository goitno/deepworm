"""Tests for research export hub."""

import json

from deepworm.export import (
    ExportFormat,
    ExportOptions,
    ExportResult,
    export_report,
    batch_export,
    _extract_title,
    _generate_toc,
    _parse_sections,
    _strip_to_plain,
    _word_wrap,
    _html_escape,
)

SAMPLE_REPORT = """# AI in Healthcare

## Introduction

Artificial intelligence is transforming healthcare delivery.
Machine learning algorithms analyze medical data with impressive accuracy.

## Key Findings

- Deep learning outperforms traditional methods
- Natural language processing extracts clinical insights
- Computer vision improves diagnostic accuracy

## Methodology

We reviewed 50 peer-reviewed papers from 2020-2024.
Data was collected from [PubMed](https://pubmed.ncbi.nlm.nih.gov/).

## Conclusion

AI adoption in healthcare continues to accelerate.
"""


class TestExportFormat:
    def test_values(self):
        assert ExportFormat.MARKDOWN == "markdown"
        assert ExportFormat.HTML == "html"
        assert ExportFormat.JSON == "json"
        assert ExportFormat.TEXT == "text"
        assert ExportFormat.NOTION == "notion"
        assert ExportFormat.CSV == "csv"


class TestExportOptions:
    def test_defaults(self):
        opts = ExportOptions()
        assert opts.include_toc is True
        assert opts.include_metadata is True
        assert opts.include_sources is True
        assert opts.wrap_width == 80

    def test_to_dict(self):
        opts = ExportOptions(include_toc=False, wrap_width=100)
        d = opts.to_dict()
        assert d["include_toc"] is False
        assert d["wrap_width"] == 100


class TestExportResult:
    def test_size_bytes(self):
        result = ExportResult(content="hello", format=ExportFormat.MARKDOWN)
        assert result.size_bytes == 5

    def test_to_dict(self):
        result = ExportResult(
            content="test",
            format=ExportFormat.HTML,
            metadata={"title": "Test"},
        )
        d = result.to_dict()
        assert d["format"] == "html"
        assert d["metadata"]["title"] == "Test"


class TestExportReport:
    def test_markdown_export(self):
        result = export_report(SAMPLE_REPORT, ExportFormat.MARKDOWN)
        assert result.format == ExportFormat.MARKDOWN
        assert "AI in Healthcare" in result.content
        assert result.size_bytes > 0

    def test_markdown_with_toc(self):
        result = export_report(SAMPLE_REPORT, ExportFormat.MARKDOWN)
        assert "Table of Contents" in result.content
        assert "Introduction" in result.content

    def test_markdown_no_toc(self):
        opts = ExportOptions(include_toc=False)
        result = export_report(SAMPLE_REPORT, ExportFormat.MARKDOWN, options=opts)
        assert "Table of Contents" not in result.content

    def test_html_export(self):
        result = export_report(SAMPLE_REPORT, ExportFormat.HTML, title="Test Report")
        assert "<!DOCTYPE html>" in result.content
        assert "<title>Test Report</title>" in result.content
        assert "deepworm-report" in result.content

    def test_html_custom_css_class(self):
        opts = ExportOptions(css_class="my-report")
        result = export_report(SAMPLE_REPORT, ExportFormat.HTML, options=opts)
        assert "my-report" in result.content

    def test_json_export(self):
        result = export_report(SAMPLE_REPORT, ExportFormat.JSON)
        data = json.loads(result.content)
        assert "title" in data
        assert "sections" in data
        assert len(data["sections"]) > 0

    def test_json_metadata(self):
        result = export_report(SAMPLE_REPORT, ExportFormat.JSON)
        data = json.loads(result.content)
        assert "metadata" in data
        assert data["metadata"]["word_count"] > 0

    def test_text_export(self):
        result = export_report(SAMPLE_REPORT, ExportFormat.TEXT)
        assert "AI IN HEALTHCARE" in result.content
        assert "**" not in result.content
        assert "#" not in result.content

    def test_notion_export(self):
        result = export_report(SAMPLE_REPORT, ExportFormat.NOTION)
        data = json.loads(result.content)
        assert "children" in data
        assert "properties" in data
        assert len(data["children"]) > 0

    def test_csv_export(self):
        result = export_report(SAMPLE_REPORT, ExportFormat.CSV)
        assert "section,level,content" in result.content
        assert "Introduction" in result.content

    def test_auto_title_detection(self):
        result = export_report(SAMPLE_REPORT, ExportFormat.JSON)
        data = json.loads(result.content)
        assert data["title"] == "AI in Healthcare"

    def test_custom_title(self):
        result = export_report(SAMPLE_REPORT, ExportFormat.JSON, title="Custom Title")
        data = json.loads(result.content)
        assert data["title"] == "Custom Title"

    def test_empty_text(self):
        result = export_report("", ExportFormat.MARKDOWN)
        assert result.format == ExportFormat.MARKDOWN


class TestBatchExport:
    def test_multiple_formats(self):
        formats = [ExportFormat.MARKDOWN, ExportFormat.HTML, ExportFormat.JSON]
        results = batch_export(SAMPLE_REPORT, formats)
        assert len(results) == 3
        assert ExportFormat.MARKDOWN in results
        assert ExportFormat.HTML in results
        assert ExportFormat.JSON in results

    def test_all_formats(self):
        all_fmts = list(ExportFormat)
        results = batch_export(SAMPLE_REPORT, all_fmts, title="Full Test")
        assert len(results) == len(all_fmts)

    def test_single_format(self):
        results = batch_export(SAMPLE_REPORT, [ExportFormat.TEXT])
        assert len(results) == 1


class TestExtractTitle:
    def test_from_h1(self):
        assert _extract_title("# My Title\n\nBody") == "My Title"

    def test_missing_h1(self):
        assert _extract_title("No heading here") == "Untitled Report"

    def test_h2_not_title(self):
        assert _extract_title("## Subtitle") == "Untitled Report"


class TestGenerateToc:
    def test_basic_toc(self):
        text = "## Intro\n## Methods\n## Results"
        toc = _generate_toc(text, 3)
        assert "Intro" in toc
        assert "Methods" in toc
        assert "Results" in toc

    def test_nested_toc(self):
        text = "## Main\n### Sub\n## Another"
        toc = _generate_toc(text, 3)
        assert "Main" in toc
        assert "Sub" in toc

    def test_depth_limit(self):
        text = "## H2\n### H3\n#### H4"
        toc = _generate_toc(text, 2)
        assert "H2" in toc
        assert "H4" not in toc


class TestParseSections:
    def test_basic_parsing(self):
        text = "# Title\n\nIntro\n\n## Section 1\n\nContent 1\n\n## Section 2\n\nContent 2"
        sections = _parse_sections(text)
        assert len(sections) >= 2

    def test_heading_levels(self):
        text = "# H1\n\nBody\n\n## H2\n\nBody 2"
        sections = _parse_sections(text)
        levels = [s["level"] for s in sections]
        assert 1 in levels
        assert 2 in levels


class TestStripToPlain:
    def test_removes_markdown(self):
        result = _strip_to_plain("**bold** and *italic*")
        assert "bold" in result
        assert "**" not in result

    def test_removes_links(self):
        result = _strip_to_plain("[text](http://url.com)")
        assert "text" in result
        assert "http" not in result


class TestWordWrap:
    def test_wraps_long_line(self):
        text = "word " * 20
        result = _word_wrap(text.strip(), 40)
        for line in result.split("\n"):
            assert len(line) <= 45  # Allow small overflow for long words

    def test_short_lines_unchanged(self):
        text = "Short line"
        assert _word_wrap(text, 80) == text


class TestHtmlEscape:
    def test_escapes_special(self):
        assert _html_escape("<>&\"") == "&lt;&gt;&amp;&quot;"

    def test_plain_text_unchanged(self):
        assert _html_escape("hello world") == "hello world"
