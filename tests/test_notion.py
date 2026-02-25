"""Tests for deepworm.notion."""

import pytest

from deepworm.notion import (
    BULLETED_LIST,
    CODE,
    DIVIDER,
    HEADING_1,
    HEADING_2,
    HEADING_3,
    NUMBERED_LIST,
    PARAGRAPH,
    QUOTE,
    TABLE,
    NotionBlock,
    NotionPage,
    _normalize_language,
    _text_to_rich_text,
    export_notion_json,
    markdown_to_notion,
    notion_to_markdown,
)


class TestMarkdownToNotion:
    def test_heading_extraction(self):
        md = "# My Report\n\n## Section 1\n\nParagraph text."
        page = markdown_to_notion(md)
        assert page.title == "My Report"
        assert page.blocks[0].block_type == HEADING_2
        assert page.blocks[0].content == "Section 1"
        assert page.blocks[1].block_type == PARAGRAPH

    def test_code_block(self):
        md = "# Title\n\n```python\nprint('hello')\n```"
        page = markdown_to_notion(md)
        code = page.blocks[0]
        assert code.block_type == CODE
        assert code.content == "print('hello')"
        assert code.language == "python"

    def test_blockquote(self):
        md = "# Title\n\n> This is a quote\n> continued"
        page = markdown_to_notion(md)
        assert page.blocks[0].block_type == QUOTE
        assert "This is a quote" in page.blocks[0].content

    def test_bullet_list(self):
        md = "# Title\n\n- Item 1\n- Item 2\n- Item 3"
        page = markdown_to_notion(md)
        bullets = [b for b in page.blocks if b.block_type == BULLETED_LIST]
        assert len(bullets) == 3

    def test_numbered_list(self):
        md = "# Title\n\n1. First\n2. Second"
        page = markdown_to_notion(md)
        nums = [b for b in page.blocks if b.block_type == NUMBERED_LIST]
        assert len(nums) == 2

    def test_horizontal_rule(self):
        md = "# Title\n\n---\n\nText after"
        page = markdown_to_notion(md)
        dividers = [b for b in page.blocks if b.block_type == DIVIDER]
        assert len(dividers) == 1

    def test_table(self):
        md = "# Title\n\n| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |"
        page = markdown_to_notion(md)
        tables = [b for b in page.blocks if b.block_type == TABLE]
        assert len(tables) == 1
        assert tables[0].table_width == 2
        assert len(tables[0].children) == 3  # header + 2 data rows

    def test_h3_heading(self):
        md = "# Title\n\n### Sub-section"
        page = markdown_to_notion(md)
        assert page.blocks[0].block_type == HEADING_3

    def test_empty_markdown(self):
        page = markdown_to_notion("")
        assert page.title == "Research Report"
        assert page.blocks == []


class TestNotionBlock:
    def test_paragraph_to_dict(self):
        block = NotionBlock(block_type=PARAGRAPH, content="Hello world")
        d = block.to_dict()
        assert d["type"] == PARAGRAPH
        assert d[PARAGRAPH]["rich_text"][0]["text"]["content"] == "Hello world"

    def test_code_to_dict(self):
        block = NotionBlock(block_type=CODE, content="x = 1", language="python")
        d = block.to_dict()
        assert d[CODE]["language"] == "python"

    def test_divider_to_dict(self):
        block = NotionBlock(block_type=DIVIDER)
        d = block.to_dict()
        assert d["type"] == DIVIDER
        assert d[DIVIDER] == {}

    def test_heading_to_dict(self):
        block = NotionBlock(block_type=HEADING_1, content="Title")
        d = block.to_dict()
        assert d["type"] == HEADING_1


class TestNotionPage:
    def test_to_dict(self):
        page = NotionPage(title="Test", blocks=[
            NotionBlock(block_type=PARAGRAPH, content="Hello"),
        ])
        d = page.to_dict()
        assert d["properties"]["title"]["title"][0]["text"]["content"] == "Test"
        assert len(d["children"]) == 1

    def test_block_count(self):
        page = NotionPage(title="Test", blocks=[
            NotionBlock(block_type=PARAGRAPH, content="A"),
            NotionBlock(block_type=PARAGRAPH, content="B"),
        ])
        assert page.block_count == 2

    def test_icon(self):
        page = NotionPage(title="Test", icon="🔬")
        d = page.to_dict()
        assert d["icon"]["emoji"] == "🔬"


class TestNotionToMarkdown:
    def test_roundtrip_basic(self):
        md = "# My Report\n\n## Introduction\n\nSome text here.\n\n## Conclusion\n\nFinal words.\n"
        page = markdown_to_notion(md)
        result = notion_to_markdown(page)
        assert "# My Report" in result
        assert "## Introduction" in result
        assert "Some text here." in result

    def test_code_roundtrip(self):
        md = "# Title\n\n```python\nprint('hi')\n```\n"
        page = markdown_to_notion(md)
        result = notion_to_markdown(page)
        assert "```python" in result
        assert "print('hi')" in result

    def test_list_roundtrip(self):
        md = "# Title\n\n- Item alpha\n- Item beta"
        page = markdown_to_notion(md)
        result = notion_to_markdown(page)
        assert "- Item alpha" in result
        assert "- Item beta" in result


class TestExportNotionJson:
    def test_returns_dict(self):
        result = export_notion_json("# Test\n\nHello world.")
        assert isinstance(result, dict)
        assert "properties" in result
        assert "children" in result


class TestRichText:
    def test_plain_text(self):
        rt = _text_to_rich_text("Hello world")
        assert rt[0]["text"]["content"] == "Hello world"

    def test_bold(self):
        rt = _text_to_rich_text("This is **bold** text")
        assert any(
            r.get("annotations", {}).get("bold") for r in rt
        )

    def test_italic(self):
        rt = _text_to_rich_text("This is *italic* text")
        assert any(
            r.get("annotations", {}).get("italic") for r in rt
        )

    def test_inline_code(self):
        rt = _text_to_rich_text("Use `print()` function")
        assert any(
            r.get("annotations", {}).get("code") for r in rt
        )

    def test_link(self):
        rt = _text_to_rich_text("Visit [Google](https://google.com)")
        assert any(
            r.get("text", {}).get("link", {}).get("url") == "https://google.com"
            for r in rt
        )

    def test_empty_text(self):
        rt = _text_to_rich_text("")
        assert len(rt) == 1


class TestNormalizeLanguage:
    def test_python_alias(self):
        assert _normalize_language("py") == "python"

    def test_javascript_alias(self):
        assert _normalize_language("js") == "javascript"

    def test_shell_alias(self):
        assert _normalize_language("bash") == "shell"

    def test_passthrough(self):
        assert _normalize_language("rust") == "rust"

    def test_empty(self):
        assert _normalize_language("") == "plain text"
