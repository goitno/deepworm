"""Serialization and deserialization utilities for deepworm.

Provides converters between common data formats: JSON, YAML, TOML, CSV, XML.
Includes schema-aware serialization and pretty printing.
"""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


class Format(Enum):
    """Supported serialization formats."""

    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
    CSV = "csv"
    XML = "xml"
    MARKDOWN_TABLE = "markdown_table"


@dataclass
class SerializationResult:
    """Result of a serialization operation."""

    data: str
    format: Format
    size_bytes: int = 0
    errors: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.size_bytes:
            self.size_bytes = len(self.data.encode("utf-8"))

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


@dataclass
class DeserializationResult:
    """Result of a deserialization operation."""

    data: Any = None
    format: Format = Format.JSON
    errors: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0 and self.data is not None


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------


def to_json(
    data: Any,
    *,
    indent: int = 2,
    sort_keys: bool = False,
    ensure_ascii: bool = False,
) -> SerializationResult:
    """Serialize data to JSON."""
    try:
        result = json.dumps(
            data, indent=indent, sort_keys=sort_keys,
            ensure_ascii=ensure_ascii, default=str,
        )
        return SerializationResult(data=result, format=Format.JSON)
    except Exception as e:
        return SerializationResult(data="", format=Format.JSON, errors=[str(e)])


def from_json(text: str) -> DeserializationResult:
    """Deserialize JSON string to data."""
    try:
        data = json.loads(text)
        return DeserializationResult(data=data, format=Format.JSON)
    except Exception as e:
        return DeserializationResult(format=Format.JSON, errors=[str(e)])


# ---------------------------------------------------------------------------
# YAML (simple implementation without external deps)
# ---------------------------------------------------------------------------


def to_yaml(data: Any, *, indent: int = 2) -> SerializationResult:
    """Serialize data to YAML format (simple implementation)."""
    try:
        lines = _yaml_serialize(data, indent=indent, level=0)
        result = "\n".join(lines) + "\n" if lines else ""
        return SerializationResult(data=result, format=Format.YAML)
    except Exception as e:
        return SerializationResult(data="", format=Format.YAML, errors=[str(e)])


def _yaml_serialize(data: Any, indent: int, level: int) -> List[str]:
    """Recursively serialize data to YAML lines."""
    prefix = " " * (indent * level)

    if data is None:
        return ["null"]
    if isinstance(data, bool):
        return ["true" if data else "false"]
    if isinstance(data, (int, float)):
        return [str(data)]
    if isinstance(data, str):
        if "\n" in data or ":" in data or "#" in data or data.startswith("{"):
            return [f'"{data}"']
        return [data] if data else ['""']
    if isinstance(data, list):
        if not data:
            return ["[]"]
        lines = []
        for item in data:
            sub = _yaml_serialize(item, indent, level + 1)
            if len(sub) == 1 and not isinstance(item, (dict, list)):
                lines.append(f"{prefix}- {sub[0]}")
            else:
                lines.append(f"{prefix}- {sub[0].lstrip()}")
                for s in sub[1:]:
                    lines.append(s)
        return lines
    if isinstance(data, dict):
        if not data:
            return ["{}"]
        lines = []
        for key, value in data.items():
            sub = _yaml_serialize(value, indent, level + 1)
            if len(sub) == 1 and not isinstance(value, (dict, list)):
                lines.append(f"{prefix}{key}: {sub[0]}")
            else:
                lines.append(f"{prefix}{key}:")
                for s in sub:
                    lines.append(s)
        return lines

    return [str(data)]


def from_yaml(text: str) -> DeserializationResult:
    """Deserialize simple YAML to data (supports basic key:value, lists, nesting)."""
    try:
        data = _yaml_parse(text)
        return DeserializationResult(data=data, format=Format.YAML)
    except Exception as e:
        return DeserializationResult(format=Format.YAML, errors=[str(e)])


def _yaml_parse(text: str) -> Any:
    """Simple YAML parser for basic structures."""
    lines = text.strip().split("\n")
    if not lines or (len(lines) == 1 and not lines[0].strip()):
        return None

    # Check if it's a simple value
    if len(lines) == 1:
        stripped = lines[0].strip()
        if ":" in stripped and not stripped.startswith('"'):
            return _yaml_parse_dict(lines, 0)[0]
        if stripped.startswith("- "):
            return _yaml_parse_list(lines, 0)[0]
        return _yaml_parse_value(stripped)

    # Try to parse as dict or list
    first = lines[0].strip()
    if first.startswith("- "):
        return _yaml_parse_list(lines, 0)[0]
    if ":" in first:
        return _yaml_parse_dict(lines, 0)[0]

    return _yaml_parse_value(text.strip())


def _yaml_parse_value(s: str) -> Any:
    """Parse a single YAML value."""
    if s == "null" or s == "~":
        return None
    if s == "true":
        return True
    if s == "false":
        return False
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    if s.startswith("'") and s.endswith("'"):
        return s[1:-1]
    if s == "[]":
        return []
    if s == "{}":
        return {}
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def _get_indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _yaml_parse_list(lines: List[str], base_indent: int) -> Tuple[list, int]:
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        indent = _get_indent(line)
        if indent < base_indent:
            break
        stripped = line.strip()
        if stripped.startswith("- "):
            value_str = stripped[2:].strip()
            if ":" in value_str and not value_str.startswith('"'):
                # Inline dict within list item
                result.append(_yaml_parse_value(value_str))
            else:
                result.append(_yaml_parse_value(value_str))
            i += 1
        else:
            break
    return result, i


def _yaml_parse_dict(lines: List[str], base_indent: int) -> Tuple[dict, int]:
    result = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        indent = _get_indent(line)
        if indent < base_indent:
            break
        stripped = line.strip()
        if ":" in stripped:
            colon_pos = stripped.index(":")
            key = stripped[:colon_pos].strip()
            value_str = stripped[colon_pos + 1:].strip()
            if value_str:
                result[key] = _yaml_parse_value(value_str)
                i += 1
            else:
                # Value is on next lines (nested)
                i += 1
                if i < len(lines):
                    next_line = lines[i]
                    next_indent = _get_indent(next_line)
                    if next_indent > indent:
                        if next_line.strip().startswith("- "):
                            sub_list, consumed = _yaml_parse_list(
                                lines[i:], next_indent,
                            )
                            result[key] = sub_list
                            i += consumed
                        else:
                            sub_dict, consumed = _yaml_parse_dict(
                                lines[i:], next_indent,
                            )
                            result[key] = sub_dict
                            i += consumed
                    else:
                        result[key] = None
                else:
                    result[key] = None
        else:
            i += 1
    return result, i


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------


def to_csv(
    data: List[Dict[str, Any]],
    *,
    delimiter: str = ",",
    include_header: bool = True,
) -> SerializationResult:
    """Serialize list of dicts to CSV."""
    if not data:
        return SerializationResult(data="", format=Format.CSV)

    try:
        output = io.StringIO()
        fieldnames = list(data[0].keys())
        writer = csv.DictWriter(
            output, fieldnames=fieldnames, delimiter=delimiter,
        )
        if include_header:
            writer.writeheader()
        for row in data:
            writer.writerow({k: str(v) for k, v in row.items()})
        return SerializationResult(data=output.getvalue(), format=Format.CSV)
    except Exception as e:
        return SerializationResult(data="", format=Format.CSV, errors=[str(e)])


def from_csv(
    text: str,
    *,
    delimiter: str = ",",
    has_header: bool = True,
) -> DeserializationResult:
    """Deserialize CSV to list of dicts."""
    try:
        reader_input = io.StringIO(text)
        if has_header:
            reader = csv.DictReader(reader_input, delimiter=delimiter)
            data = [dict(row) for row in reader]
        else:
            reader_raw = csv.reader(reader_input, delimiter=delimiter)
            data = [row for row in reader_raw]
        return DeserializationResult(data=data, format=Format.CSV)
    except Exception as e:
        return DeserializationResult(format=Format.CSV, errors=[str(e)])


# ---------------------------------------------------------------------------
# XML (simple implementation)
# ---------------------------------------------------------------------------


def to_xml(
    data: Dict[str, Any],
    *,
    root_tag: str = "root",
    indent: int = 2,
) -> SerializationResult:
    """Serialize dict to XML."""
    try:
        lines = [f'<?xml version="1.0" encoding="UTF-8"?>']
        lines.append(f"<{root_tag}>")
        lines.extend(_xml_serialize(data, indent=indent, level=1))
        lines.append(f"</{root_tag}>")
        return SerializationResult(
            data="\n".join(lines), format=Format.XML,
        )
    except Exception as e:
        return SerializationResult(data="", format=Format.XML, errors=[str(e)])


def _xml_serialize(data: Any, indent: int, level: int) -> List[str]:
    """Recursively serialize to XML elements."""
    prefix = " " * (indent * level)
    lines = []

    if isinstance(data, dict):
        for key, value in data.items():
            tag = re.sub(r"[^a-zA-Z0-9_]", "_", str(key))
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}<{tag}>")
                lines.extend(_xml_serialize(value, indent, level + 1))
                lines.append(f"{prefix}</{tag}>")
            else:
                escaped = _xml_escape(str(value) if value is not None else "")
                lines.append(f"{prefix}<{tag}>{escaped}</{tag}>")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}<item>")
                lines.extend(_xml_serialize(item, indent, level + 1))
                lines.append(f"{prefix}</item>")
            else:
                escaped = _xml_escape(str(item))
                lines.append(f"{prefix}<item>{escaped}</item>")
    else:
        escaped = _xml_escape(str(data) if data is not None else "")
        lines.append(f"{prefix}{escaped}")

    return lines


def _xml_escape(text: str) -> str:
    """Escape special XML characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def from_xml(text: str) -> DeserializationResult:
    """Deserialize simple XML to dict (basic parser)."""
    try:
        text = text.strip()
        # Remove XML declaration
        text = re.sub(r'<\?xml[^?]*\?>', '', text).strip()
        data = _xml_parse_element(text)
        return DeserializationResult(data=data, format=Format.XML)
    except Exception as e:
        return DeserializationResult(format=Format.XML, errors=[str(e)])


def _xml_unescape(text: str) -> str:
    return (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&apos;", "'")
    )


def _xml_parse_element(text: str) -> Any:
    """Parse a single XML element and its children."""
    text = text.strip()
    # Match root element
    match = re.match(r'^<(\w+)>(.*)</\1>$', text, re.DOTALL)
    if not match:
        return _xml_unescape(text)

    tag = match.group(1)
    content = match.group(2).strip()

    # Check if content has child elements
    children = re.findall(r'<(\w+)>(.*?)</\1>', content, re.DOTALL)
    if not children:
        return {tag: _xml_unescape(content)}

    result: Dict[str, Any] = {}
    for child_tag, child_content in children:
        child_content = child_content.strip()
        # Check if child has nested elements
        if re.search(r'<\w+>', child_content):
            value = _xml_parse_element(f"<{child_tag}>{child_content}</{child_tag}>")
            if isinstance(value, dict) and child_tag in value:
                value = value[child_tag]
        else:
            value = _xml_unescape(child_content)

        if child_tag == "item":
            if "items" not in result:
                result["items"] = []
            result["items"].append(value)
        else:
            result[child_tag] = value

    return {tag: result} if tag != "root" else result


# ---------------------------------------------------------------------------
# Markdown table
# ---------------------------------------------------------------------------


def to_markdown_table(
    data: List[Dict[str, Any]],
    *,
    alignment: Optional[Dict[str, str]] = None,
) -> SerializationResult:
    """Serialize list of dicts to markdown table."""
    if not data:
        return SerializationResult(data="", format=Format.MARKDOWN_TABLE)

    try:
        headers = list(data[0].keys())
        align = alignment or {}

        # Build header row
        header_row = "| " + " | ".join(headers) + " |"

        # Build separator
        sep_parts = []
        for h in headers:
            a = align.get(h, "left")
            if a == "center":
                sep_parts.append(":---:")
            elif a == "right":
                sep_parts.append("---:")
            else:
                sep_parts.append("---")
        sep_row = "| " + " | ".join(sep_parts) + " |"

        # Build data rows
        rows = []
        for item in data:
            cells = [str(item.get(h, "")) for h in headers]
            rows.append("| " + " | ".join(cells) + " |")

        result = "\n".join([header_row, sep_row] + rows)
        return SerializationResult(data=result, format=Format.MARKDOWN_TABLE)
    except Exception as e:
        return SerializationResult(
            data="", format=Format.MARKDOWN_TABLE, errors=[str(e)],
        )


def from_markdown_table(text: str) -> DeserializationResult:
    """Deserialize markdown table to list of dicts."""
    try:
        lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
        if len(lines) < 3:
            return DeserializationResult(
                format=Format.MARKDOWN_TABLE,
                errors=["Table must have at least header, separator, and data row"],
            )

        # Parse header
        headers = [h.strip() for h in lines[0].split("|") if h.strip()]
        # Skip separator (lines[1])

        # Parse data rows
        data = []
        for line in lines[2:]:
            cells = [c.strip() for c in line.split("|") if c.strip()]
            row = {}
            for i, header in enumerate(headers):
                row[header] = cells[i] if i < len(cells) else ""
            data.append(row)

        return DeserializationResult(data=data, format=Format.MARKDOWN_TABLE)
    except Exception as e:
        return DeserializationResult(
            format=Format.MARKDOWN_TABLE, errors=[str(e)],
        )


# ---------------------------------------------------------------------------
# Format detection and conversion
# ---------------------------------------------------------------------------


def detect_format(text: str) -> Format:
    """Detect the format of a text string."""
    text = text.strip()
    if not text:
        return Format.JSON

    # XML
    if text.startswith("<?xml") or text.startswith("<"):
        return Format.XML

    # JSON
    if text.startswith("{") or text.startswith("["):
        try:
            json.loads(text)
            return Format.JSON
        except json.JSONDecodeError:
            pass

    # Markdown table
    if text.startswith("|") and "---" in text:
        return Format.MARKDOWN_TABLE

    # CSV (has commas and multiple lines)
    lines = text.split("\n")
    if len(lines) > 1 and "," in lines[0]:
        return Format.CSV

    # YAML-like (key: value)
    if re.match(r'^[\w]+:', lines[0]):
        return Format.YAML

    return Format.JSON


def convert(
    text: str,
    from_format: Format,
    to_format: Format,
) -> SerializationResult:
    """Convert between formats."""
    # Deserialize
    if from_format == Format.JSON:
        parsed = from_json(text)
    elif from_format == Format.YAML:
        parsed = from_yaml(text)
    elif from_format == Format.CSV:
        parsed = from_csv(text)
    elif from_format == Format.XML:
        parsed = from_xml(text)
    elif from_format == Format.MARKDOWN_TABLE:
        parsed = from_markdown_table(text)
    else:
        return SerializationResult(
            data="", format=to_format, errors=[f"Unsupported source format: {from_format}"],
        )

    if not parsed.is_valid:
        return SerializationResult(
            data="", format=to_format, errors=parsed.errors,
        )

    # Serialize
    return serialize(parsed.data, to_format)


def serialize(data: Any, fmt: Format) -> SerializationResult:
    """Serialize data to the given format."""
    if fmt == Format.JSON:
        return to_json(data)
    elif fmt == Format.YAML:
        return to_yaml(data)
    elif fmt == Format.CSV:
        if isinstance(data, list):
            return to_csv(data)
        return SerializationResult(
            data="", format=fmt, errors=["CSV requires list of dicts"],
        )
    elif fmt == Format.XML:
        if isinstance(data, dict):
            return to_xml(data)
        return SerializationResult(
            data="", format=fmt, errors=["XML requires dict"],
        )
    elif fmt == Format.MARKDOWN_TABLE:
        if isinstance(data, list):
            return to_markdown_table(data)
        return SerializationResult(
            data="", format=fmt, errors=["Markdown table requires list of dicts"],
        )
    return SerializationResult(
        data="", format=fmt, errors=[f"Unsupported format: {fmt}"],
    )


def pretty_json(text: str, indent: int = 2) -> str:
    """Pretty-print a JSON string."""
    try:
        data = json.loads(text)
        return json.dumps(data, indent=indent, ensure_ascii=False)
    except json.JSONDecodeError:
        return text


def minify_json(text: str) -> str:
    """Minify a JSON string."""
    try:
        data = json.loads(text)
        return json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    except json.JSONDecodeError:
        return text
