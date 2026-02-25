"""Document schema validation and structured data extraction.

Define, validate, and enforce document schemas covering structure,
required sections, metadata, and content constraints.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union


class FieldType(Enum):
    """Schema field types."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    DATE = "date"
    URL = "url"
    EMAIL = "email"
    MARKDOWN = "markdown"


@dataclass
class SchemaField:
    """A single field in a document schema."""

    name: str
    field_type: FieldType = FieldType.STRING
    required: bool = False
    description: str = ""
    default: Any = None
    min_length: int = 0
    max_length: int = 0
    pattern: str = ""
    choices: List[str] = field(default_factory=list)
    min_value: Optional[float] = None
    max_value: Optional[float] = None

    def validate(self, value: Any) -> List[str]:
        """Validate a value against this field's constraints.

        Returns:
            List of error messages (empty if valid).
        """
        errors: List[str] = []

        if value is None or value == "":
            if self.required:
                errors.append(f"Field '{self.name}' is required")
            return errors

        # Type checks
        if self.field_type == FieldType.STRING:
            if not isinstance(value, str):
                errors.append(f"Field '{self.name}' must be a string")
                return errors
            if self.min_length and len(value) < self.min_length:
                errors.append(
                    f"Field '{self.name}' must be at least {self.min_length} characters"
                )
            if self.max_length and len(value) > self.max_length:
                errors.append(
                    f"Field '{self.name}' must be at most {self.max_length} characters"
                )
            if self.pattern and not re.search(self.pattern, value):
                errors.append(
                    f"Field '{self.name}' must match pattern: {self.pattern}"
                )
            if self.choices and value not in self.choices:
                errors.append(
                    f"Field '{self.name}' must be one of: {', '.join(self.choices)}"
                )

        elif self.field_type in (FieldType.INTEGER, FieldType.FLOAT):
            if self.field_type == FieldType.INTEGER:
                if not isinstance(value, int) or isinstance(value, bool):
                    errors.append(f"Field '{self.name}' must be an integer")
                    return errors
            else:
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    errors.append(f"Field '{self.name}' must be a number")
                    return errors
            if self.min_value is not None and value < self.min_value:
                errors.append(f"Field '{self.name}' must be >= {self.min_value}")
            if self.max_value is not None and value > self.max_value:
                errors.append(f"Field '{self.name}' must be <= {self.max_value}")

        elif self.field_type == FieldType.BOOLEAN:
            if not isinstance(value, bool):
                errors.append(f"Field '{self.name}' must be a boolean")

        elif self.field_type == FieldType.LIST:
            if not isinstance(value, list):
                errors.append(f"Field '{self.name}' must be a list")
            elif self.min_length and len(value) < self.min_length:
                errors.append(
                    f"Field '{self.name}' must have at least {self.min_length} items"
                )

        elif self.field_type == FieldType.DICT:
            if not isinstance(value, dict):
                errors.append(f"Field '{self.name}' must be a dict")

        elif self.field_type == FieldType.URL:
            if not isinstance(value, str):
                errors.append(f"Field '{self.name}' must be a string")
            elif not re.match(r"https?://\S+", value):
                errors.append(f"Field '{self.name}' must be a valid URL")

        elif self.field_type == FieldType.EMAIL:
            if not isinstance(value, str):
                errors.append(f"Field '{self.name}' must be a string")
            elif not re.match(r"[^@]+@[^@]+\.[^@]+", value):
                errors.append(f"Field '{self.name}' must be a valid email")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "name": self.name,
            "type": self.field_type.value,
            "required": self.required,
        }
        if self.description:
            d["description"] = self.description
        if self.default is not None:
            d["default"] = self.default
        if self.min_length:
            d["min_length"] = self.min_length
        if self.max_length:
            d["max_length"] = self.max_length
        if self.pattern:
            d["pattern"] = self.pattern
        if self.choices:
            d["choices"] = self.choices
        if self.min_value is not None:
            d["min_value"] = self.min_value
        if self.max_value is not None:
            d["max_value"] = self.max_value
        return d


@dataclass
class SectionRule:
    """Rule for a required or expected document section."""

    heading: str
    required: bool = False
    min_words: int = 0
    max_words: int = 0
    level: int = 0  # 0 = any level
    pattern: str = ""  # regex for heading text

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"heading": self.heading, "required": self.required}
        if self.min_words:
            d["min_words"] = self.min_words
        if self.max_words:
            d["max_words"] = self.max_words
        if self.level:
            d["level"] = self.level
        return d


@dataclass
class ValidationError:
    """A single schema validation error."""

    field: str
    message: str
    value: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "message": self.message,
        }


@dataclass
class ValidationResult:
    """Result of schema validation."""

    valid: bool = True
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, field_name: str, message: str, value: Any = None) -> None:
        self.errors.append(ValidationError(field=field_name, message=message, value=value))
        self.valid = False

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def to_markdown(self) -> str:
        lines = ["## Validation Result", ""]
        lines.append(f"**Status:** {'VALID' if self.valid else 'INVALID'}")
        lines.append("")
        if self.errors:
            lines.append("### Errors")
            for err in self.errors:
                lines.append(f"- **{err.field}**: {err.message}")
            lines.append("")
        if self.warnings:
            lines.append("### Warnings")
            for warn in self.warnings:
                lines.append(f"- {warn}")
            lines.append("")
        if not self.errors and not self.warnings:
            lines.append("No issues found.")
            lines.append("")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": [e.to_dict() for e in self.errors],
            "warnings": self.warnings,
        }


@dataclass
class DocumentSchema:
    """A complete document schema definition."""

    name: str = ""
    version: str = "1.0"
    description: str = ""
    fields: Dict[str, SchemaField] = field(default_factory=dict)
    sections: List[SectionRule] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_field(
        self,
        name: str,
        field_type: Union[FieldType, str] = FieldType.STRING,
        required: bool = False,
        **kwargs: Any,
    ) -> SchemaField:
        """Add a field to the schema."""
        if isinstance(field_type, str):
            field_type = FieldType(field_type)
        sf = SchemaField(name=name, field_type=field_type, required=required, **kwargs)
        self.fields[name] = sf
        return sf

    def add_section(
        self,
        heading: str,
        required: bool = False,
        **kwargs: Any,
    ) -> SectionRule:
        """Add a section rule to the schema."""
        rule = SectionRule(heading=heading, required=required, **kwargs)
        self.sections.append(rule)
        return rule

    def validate_data(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate a data dict against this schema's fields."""
        result = ValidationResult()
        for name, sf in self.fields.items():
            value = data.get(name)
            errors = sf.validate(value)
            for msg in errors:
                result.add_error(name, msg, value)
        # Check for unknown fields
        known = set(self.fields.keys())
        for key in data:
            if key not in known:
                result.add_warning(f"Unknown field: '{key}'")
        return result

    def validate_document(self, text: str) -> ValidationResult:
        """Validate a markdown document against section rules."""
        result = ValidationResult()

        # Extract headings
        headings = re.findall(r"^(#{1,6})\s+(.+)$", text, re.MULTILINE)
        heading_titles = [h[1].strip().lower() for h in headings]
        heading_map: Dict[str, Tuple[int, str]] = {}
        for hashes, title in headings:
            heading_map[title.strip().lower()] = (len(hashes), title.strip())

        # Check section rules
        for rule in self.sections:
            heading_lower = rule.heading.lower()
            found = False

            if rule.pattern:
                for ht in heading_titles:
                    if re.search(rule.pattern, ht, re.IGNORECASE):
                        found = True
                        break
            else:
                found = heading_lower in heading_titles

            if rule.required and not found:
                result.add_error(
                    "section",
                    f"Required section missing: '{rule.heading}'",
                )

            if found and rule.level:
                actual = heading_map.get(heading_lower)
                if actual and actual[0] != rule.level:
                    result.add_warning(
                        f"Section '{rule.heading}' should be level {rule.level}, "
                        f"found level {actual[0]}"
                    )

            # Word count check
            if found and (rule.min_words or rule.max_words):
                section_text = _extract_section_text(text, rule.heading)
                word_count = len(section_text.split())
                if rule.min_words and word_count < rule.min_words:
                    result.add_error(
                        "section",
                        f"Section '{rule.heading}' too short "
                        f"({word_count} words, min {rule.min_words})",
                    )
                if rule.max_words and word_count > rule.max_words:
                    result.add_warning(
                        f"Section '{rule.heading}' too long "
                        f"({word_count} words, max {rule.max_words})"
                    )

        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "fields": {k: v.to_dict() for k, v in self.fields.items()},
            "sections": [s.to_dict() for s in self.sections],
        }

    def to_json_schema(self) -> Dict[str, Any]:
        """Export as JSON Schema compatible format."""
        type_map = {
            FieldType.STRING: "string",
            FieldType.INTEGER: "integer",
            FieldType.FLOAT: "number",
            FieldType.BOOLEAN: "boolean",
            FieldType.LIST: "array",
            FieldType.DICT: "object",
            FieldType.DATE: "string",
            FieldType.URL: "string",
            FieldType.EMAIL: "string",
            FieldType.MARKDOWN: "string",
        }
        properties: Dict[str, Any] = {}
        required: List[str] = []
        for name, sf in self.fields.items():
            prop: Dict[str, Any] = {"type": type_map.get(sf.field_type, "string")}
            if sf.description:
                prop["description"] = sf.description
            if sf.min_length:
                prop["minLength"] = sf.min_length
            if sf.max_length:
                prop["maxLength"] = sf.max_length
            if sf.pattern:
                prop["pattern"] = sf.pattern
            if sf.choices:
                prop["enum"] = sf.choices
            if sf.min_value is not None:
                prop["minimum"] = sf.min_value
            if sf.max_value is not None:
                prop["maximum"] = sf.max_value
            if sf.default is not None:
                prop["default"] = sf.default
            properties[name] = prop
            if sf.required:
                required.append(name)

        schema: Dict[str, Any] = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": properties,
        }
        if required:
            schema["required"] = required
        if self.description:
            schema["description"] = self.description
        return schema


def _extract_section_text(text: str, heading: str) -> str:
    """Extract text content under a heading."""
    heading_lower = heading.lower()
    lines = text.splitlines()
    collecting = False
    result: List[str] = []

    for line in lines:
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if match:
            if match.group(2).strip().lower() == heading_lower:
                collecting = True
                continue
            elif collecting:
                # Another heading at same or higher level
                break
        if collecting:
            result.append(line)

    return "\n".join(result).strip()


def create_schema(
    name: str = "",
    fields: Optional[Dict[str, Dict[str, Any]]] = None,
    sections: Optional[List[Dict[str, Any]]] = None,
) -> DocumentSchema:
    """Create a document schema from dictionaries.

    Args:
        name: Schema name.
        fields: Dict of field name → field definition dicts.
        sections: List of section rule dicts.

    Returns:
        DocumentSchema instance.
    """
    schema = DocumentSchema(name=name)
    if fields:
        for fname, fdef in fields.items():
            ft = fdef.pop("type", "string")
            if isinstance(ft, str):
                ft = FieldType(ft)
            schema.add_field(fname, field_type=ft, **fdef)
    if sections:
        for sdef in sections:
            schema.add_section(**sdef)
    return schema


def report_schema() -> DocumentSchema:
    """Schema for a standard research report."""
    schema = DocumentSchema(
        name="research-report",
        description="Standard research report schema",
    )
    schema.add_field("title", FieldType.STRING, required=True, min_length=3)
    schema.add_field("author", FieldType.STRING, required=False)
    schema.add_field("date", FieldType.DATE, required=False)
    schema.add_field("topic", FieldType.STRING, required=True, min_length=5)
    schema.add_field("version", FieldType.STRING, required=False)

    schema.add_section("Introduction", required=True, min_words=20)
    schema.add_section("Methods", required=False)
    schema.add_section("Results", required=False)
    schema.add_section("Conclusion", required=True, min_words=15)

    return schema


def article_schema() -> DocumentSchema:
    """Schema for a standard article."""
    schema = DocumentSchema(
        name="article",
        description="Standard article schema",
    )
    schema.add_field("title", FieldType.STRING, required=True, min_length=5)
    schema.add_field("author", FieldType.STRING, required=True)
    schema.add_field("tags", FieldType.LIST, required=False, min_length=1)

    schema.add_section("Introduction", required=True)
    schema.add_section("Conclusion", required=True)

    return schema
