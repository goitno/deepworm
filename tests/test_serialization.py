"""Tests for deepworm.serialization module."""

import pytest

from deepworm.serialization import (
    DeserializationResult,
    Format,
    SerializationResult,
    convert,
    detect_format,
    from_csv,
    from_json,
    from_markdown_table,
    from_xml,
    from_yaml,
    minify_json,
    pretty_json,
    serialize,
    to_csv,
    to_json,
    to_markdown_table,
    to_xml,
    to_yaml,
)


# ---------------------------------------------------------------------------
# Format enum
# ---------------------------------------------------------------------------


class TestFormat:
    def test_values(self):
        assert Format.JSON.value == "json"
        assert Format.YAML.value == "yaml"
        assert Format.CSV.value == "csv"
        assert Format.XML.value == "xml"
        assert Format.MARKDOWN_TABLE.value == "markdown_table"

    def test_count(self):
        assert len(Format) == 6


# ---------------------------------------------------------------------------
# SerializationResult
# ---------------------------------------------------------------------------


class TestSerializationResult:
    def test_valid(self):
        r = SerializationResult(data='{"a": 1}', format=Format.JSON)
        assert r.is_valid
        assert r.size_bytes > 0

    def test_invalid(self):
        r = SerializationResult(data="", format=Format.JSON, errors=["fail"])
        assert not r.is_valid

    def test_auto_size(self):
        r = SerializationResult(data="hello", format=Format.JSON)
        assert r.size_bytes == 5


# ---------------------------------------------------------------------------
# DeserializationResult
# ---------------------------------------------------------------------------


class TestDeserializationResult:
    def test_valid(self):
        r = DeserializationResult(data={"a": 1}, format=Format.JSON)
        assert r.is_valid

    def test_invalid_no_data(self):
        r = DeserializationResult(format=Format.JSON)
        assert not r.is_valid

    def test_invalid_with_errors(self):
        r = DeserializationResult(data={"a": 1}, format=Format.JSON, errors=["e"])
        assert not r.is_valid


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------


class TestJSON:
    def test_to_json_dict(self):
        result = to_json({"name": "test", "value": 42})
        assert result.is_valid
        assert '"name"' in result.data
        assert '"value": 42' in result.data

    def test_to_json_list(self):
        result = to_json([1, 2, 3])
        assert result.is_valid
        assert "[" in result.data

    def test_to_json_sorted(self):
        result = to_json({"b": 2, "a": 1}, sort_keys=True)
        assert result.data.index('"a"') < result.data.index('"b"')

    def test_from_json_dict(self):
        result = from_json('{"name": "test", "value": 42}')
        assert result.is_valid
        assert result.data["name"] == "test"
        assert result.data["value"] == 42

    def test_from_json_list(self):
        result = from_json("[1, 2, 3]")
        assert result.is_valid
        assert result.data == [1, 2, 3]

    def test_from_json_invalid(self):
        result = from_json("{invalid}")
        assert not result.is_valid

    def test_roundtrip(self):
        original = {"key": "value", "nested": {"a": [1, 2, 3]}}
        serialized = to_json(original)
        restored = from_json(serialized.data)
        assert restored.data == original


# ---------------------------------------------------------------------------
# YAML
# ---------------------------------------------------------------------------


class TestYAML:
    def test_to_yaml_dict(self):
        result = to_yaml({"name": "test", "value": 42})
        assert result.is_valid
        assert "name: test" in result.data
        assert "value: 42" in result.data

    def test_to_yaml_list(self):
        result = to_yaml([1, 2, 3])
        assert result.is_valid
        assert "- 1" in result.data

    def test_to_yaml_nested(self):
        result = to_yaml({"parent": {"child": "value"}})
        assert result.is_valid
        assert "parent:" in result.data
        assert "child: value" in result.data

    def test_to_yaml_bool(self):
        result = to_yaml({"flag": True})
        assert "true" in result.data

    def test_to_yaml_none(self):
        result = to_yaml({"empty": None})
        assert "null" in result.data

    def test_from_yaml_simple(self):
        text = "name: test\nvalue: 42"
        result = from_yaml(text)
        assert result.is_valid
        assert result.data["name"] == "test"
        assert result.data["value"] == 42

    def test_from_yaml_list(self):
        text = "- one\n- two\n- three"
        result = from_yaml(text)
        assert result.is_valid
        assert result.data == ["one", "two", "three"]

    def test_from_yaml_bool(self):
        text = "flag: true"
        result = from_yaml(text)
        assert result.data["flag"] is True

    def test_from_yaml_null(self):
        text = "empty: null"
        result = from_yaml(text)
        assert result.data["empty"] is None


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------


class TestCSV:
    def test_to_csv(self):
        data = [
            {"name": "Alice", "age": "30"},
            {"name": "Bob", "age": "25"},
        ]
        result = to_csv(data)
        assert result.is_valid
        assert "name,age" in result.data
        assert "Alice,30" in result.data

    def test_to_csv_empty(self):
        result = to_csv([])
        assert result.is_valid
        assert result.data == ""

    def test_to_csv_no_header(self):
        data = [{"a": "1", "b": "2"}]
        result = to_csv(data, include_header=False)
        assert "a,b" not in result.data

    def test_to_csv_custom_delimiter(self):
        data = [{"x": "1", "y": "2"}]
        result = to_csv(data, delimiter="\t")
        assert "\t" in result.data

    def test_from_csv(self):
        text = "name,age\nAlice,30\nBob,25"
        result = from_csv(text)
        assert result.is_valid
        assert len(result.data) == 2
        assert result.data[0]["name"] == "Alice"
        assert result.data[1]["age"] == "25"

    def test_from_csv_no_header(self):
        text = "a,b\n1,2"
        result = from_csv(text, has_header=False)
        assert result.is_valid
        assert result.data[0] == ["a", "b"]

    def test_roundtrip(self):
        data = [{"x": "1", "y": "2"}, {"x": "3", "y": "4"}]
        serialized = to_csv(data)
        restored = from_csv(serialized.data)
        assert restored.data == data


# ---------------------------------------------------------------------------
# XML
# ---------------------------------------------------------------------------


class TestXML:
    def test_to_xml_simple(self):
        result = to_xml({"name": "test", "value": "42"})
        assert result.is_valid
        assert "<name>test</name>" in result.data
        assert "<value>42</value>" in result.data
        assert '<?xml version' in result.data

    def test_to_xml_nested(self):
        result = to_xml({"parent": {"child": "val"}})
        assert result.is_valid
        assert "<parent>" in result.data
        assert "<child>val</child>" in result.data

    def test_to_xml_list(self):
        result = to_xml({"items": ["a", "b", "c"]})
        assert result.is_valid
        assert "<item>a</item>" in result.data

    def test_to_xml_escaping(self):
        result = to_xml({"text": "a < b & c"})
        assert "&lt;" in result.data
        assert "&amp;" in result.data

    def test_to_xml_custom_root(self):
        result = to_xml({"name": "test"}, root_tag="data")
        assert "<data>" in result.data
        assert "</data>" in result.data

    def test_from_xml_simple(self):
        xml = "<root><name>test</name><value>42</value></root>"
        result = from_xml(xml)
        assert result.is_valid
        assert result.data["name"] == "test"


# ---------------------------------------------------------------------------
# Markdown table
# ---------------------------------------------------------------------------


class TestMarkdownTable:
    def test_to_markdown_table(self):
        data = [
            {"name": "Alice", "age": "30"},
            {"name": "Bob", "age": "25"},
        ]
        result = to_markdown_table(data)
        assert result.is_valid
        assert "| name | age |" in result.data
        assert "| --- | --- |" in result.data
        assert "| Alice | 30 |" in result.data

    def test_to_markdown_table_empty(self):
        result = to_markdown_table([])
        assert result.is_valid
        assert result.data == ""

    def test_to_markdown_table_alignment(self):
        data = [{"x": "1"}]
        result = to_markdown_table(data, alignment={"x": "center"})
        assert ":---:" in result.data

    def test_from_markdown_table(self):
        text = "| name | age |\n| --- | --- |\n| Alice | 30 |"
        result = from_markdown_table(text)
        assert result.is_valid
        assert result.data[0]["name"] == "Alice"
        assert result.data[0]["age"] == "30"

    def test_from_markdown_table_too_short(self):
        result = from_markdown_table("| a |\n| --- |")
        assert not result.is_valid


# ---------------------------------------------------------------------------
# detect_format
# ---------------------------------------------------------------------------


class TestDetectFormat:
    def test_json_object(self):
        assert detect_format('{"key": "value"}') == Format.JSON

    def test_json_array(self):
        assert detect_format("[1, 2, 3]") == Format.JSON

    def test_xml(self):
        assert detect_format('<?xml version="1.0"?><root></root>') == Format.XML

    def test_xml_tag(self):
        assert detect_format("<root><name>test</name></root>") == Format.XML

    def test_markdown_table(self):
        assert detect_format("| a | b |\n| --- | --- |\n| 1 | 2 |") == Format.MARKDOWN_TABLE

    def test_csv(self):
        assert detect_format("a,b,c\n1,2,3") == Format.CSV

    def test_yaml(self):
        assert detect_format("name: test\nvalue: 42") == Format.YAML


# ---------------------------------------------------------------------------
# convert
# ---------------------------------------------------------------------------


class TestConvert:
    def test_json_to_yaml(self):
        result = convert('{"name": "test", "age": 30}', Format.JSON, Format.YAML)
        assert result.is_valid
        assert "name: test" in result.data

    def test_yaml_to_json(self):
        result = convert("name: test\nage: 30", Format.YAML, Format.JSON)
        assert result.is_valid
        assert '"name"' in result.data

    def test_csv_to_json(self):
        result = convert("name,age\nAlice,30", Format.CSV, Format.JSON)
        assert result.is_valid


# ---------------------------------------------------------------------------
# serialize
# ---------------------------------------------------------------------------


class TestSerialize:
    def test_serialize_json(self):
        r = serialize({"a": 1}, Format.JSON)
        assert r.is_valid

    def test_serialize_csv_requires_list(self):
        r = serialize({"a": 1}, Format.CSV)
        assert not r.is_valid

    def test_serialize_xml_requires_dict(self):
        r = serialize([1, 2], Format.XML)
        assert not r.is_valid


# ---------------------------------------------------------------------------
# pretty/minify JSON
# ---------------------------------------------------------------------------


class TestPrettyMinify:
    def test_pretty_json(self):
        result = pretty_json('{"a":1,"b":2}')
        assert "\n" in result
        assert "  " in result

    def test_minify_json(self):
        result = minify_json('{\n  "a": 1,\n  "b": 2\n}')
        assert result == '{"a":1,"b":2}'

    def test_pretty_invalid(self):
        assert pretty_json("not json") == "not json"

    def test_minify_invalid(self):
        assert minify_json("not json") == "not json"
