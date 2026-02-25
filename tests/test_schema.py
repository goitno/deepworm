"""Tests for deepworm.schema – document schema validation."""

import pytest

from deepworm.schema import (
    DocumentSchema,
    FieldType,
    SchemaField,
    SectionRule,
    ValidationError,
    ValidationResult,
    create_schema,
    report_schema,
    article_schema,
)


# ---------------------------------------------------------------------------
# FieldType
# ---------------------------------------------------------------------------

class TestFieldType:
    def test_all_values(self):
        names = {ft.value for ft in FieldType}
        assert "string" in names
        assert "integer" in names
        assert "float" in names
        assert "boolean" in names
        assert "list" in names
        assert "url" in names
        assert "email" in names

    def test_from_string(self):
        assert FieldType("string") is FieldType.STRING
        assert FieldType("url") is FieldType.URL


# ---------------------------------------------------------------------------
# SchemaField validation
# ---------------------------------------------------------------------------

class TestSchemaField:
    def test_required_missing(self):
        sf = SchemaField(name="title", required=True)
        errors = sf.validate(None)
        assert len(errors) == 1
        assert "required" in errors[0]

    def test_required_empty_string(self):
        sf = SchemaField(name="title", required=True)
        errors = sf.validate("")
        assert len(errors) == 1

    def test_optional_none(self):
        sf = SchemaField(name="note", required=False)
        assert sf.validate(None) == []

    def test_string_min_length(self):
        sf = SchemaField(name="t", field_type=FieldType.STRING, min_length=5)
        assert sf.validate("abc") != []
        assert sf.validate("abcdef") == []

    def test_string_max_length(self):
        sf = SchemaField(name="t", field_type=FieldType.STRING, max_length=3)
        assert sf.validate("abcd") != []
        assert sf.validate("ab") == []

    def test_string_pattern(self):
        sf = SchemaField(name="t", field_type=FieldType.STRING, pattern=r"^\d+$")
        assert sf.validate("123") == []
        assert sf.validate("abc") != []

    def test_string_choices(self):
        sf = SchemaField(name="t", field_type=FieldType.STRING, choices=["a", "b"])
        assert sf.validate("a") == []
        assert sf.validate("c") != []

    def test_integer_validation(self):
        sf = SchemaField(name="n", field_type=FieldType.INTEGER, min_value=0, max_value=100)
        assert sf.validate(50) == []
        assert sf.validate(-1) != []
        assert sf.validate(101) != []

    def test_integer_rejects_bool(self):
        sf = SchemaField(name="n", field_type=FieldType.INTEGER)
        assert sf.validate(True) != []

    def test_float_validation(self):
        sf = SchemaField(name="n", field_type=FieldType.FLOAT, min_value=0.0)
        assert sf.validate(3.14) == []
        assert sf.validate(-0.5) != []

    def test_boolean_validation(self):
        sf = SchemaField(name="b", field_type=FieldType.BOOLEAN)
        assert sf.validate(True) == []
        assert sf.validate("yes") != []

    def test_list_validation(self):
        sf = SchemaField(name="l", field_type=FieldType.LIST, min_length=2)
        assert sf.validate([1, 2]) == []
        assert sf.validate([1]) != []
        assert sf.validate("not-a-list") != []

    def test_dict_validation(self):
        sf = SchemaField(name="d", field_type=FieldType.DICT)
        assert sf.validate({"a": 1}) == []
        assert sf.validate("nope") != []

    def test_url_validation(self):
        sf = SchemaField(name="u", field_type=FieldType.URL)
        assert sf.validate("https://example.com") == []
        assert sf.validate("not-a-url") != []

    def test_email_validation(self):
        sf = SchemaField(name="e", field_type=FieldType.EMAIL)
        assert sf.validate("user@example.com") == []
        assert sf.validate("invalid") != []

    def test_to_dict(self):
        sf = SchemaField(name="age", field_type=FieldType.INTEGER, required=True, min_value=0)
        d = sf.to_dict()
        assert d["name"] == "age"
        assert d["type"] == "integer"
        assert d["required"] is True
        assert d["min_value"] == 0


# ---------------------------------------------------------------------------
# SectionRule
# ---------------------------------------------------------------------------

class TestSectionRule:
    def test_basic(self):
        rule = SectionRule(heading="Introduction", required=True, min_words=20)
        assert rule.heading == "Introduction"
        assert rule.required is True

    def test_to_dict(self):
        rule = SectionRule(heading="Results", level=2)
        d = rule.to_dict()
        assert d["heading"] == "Results"
        assert d["level"] == 2


# ---------------------------------------------------------------------------
# ValidationResult
# ---------------------------------------------------------------------------

class TestValidationResult:
    def test_initially_valid(self):
        r = ValidationResult()
        assert r.valid is True
        assert r.errors == []

    def test_add_error(self):
        r = ValidationResult()
        r.add_error("title", "too short")
        assert r.valid is False
        assert len(r.errors) == 1

    def test_add_warning(self):
        r = ValidationResult()
        r.add_warning("extra field")
        assert r.valid is True
        assert len(r.warnings) == 1

    def test_to_markdown_valid(self):
        r = ValidationResult()
        md = r.to_markdown()
        assert "VALID" in md
        assert "No issues" in md

    def test_to_markdown_invalid(self):
        r = ValidationResult()
        r.add_error("x", "bad")
        md = r.to_markdown()
        assert "INVALID" in md
        assert "bad" in md

    def test_to_dict(self):
        r = ValidationResult()
        r.add_error("f", "msg")
        d = r.to_dict()
        assert d["valid"] is False
        assert d["error_count"] == 1


# ---------------------------------------------------------------------------
# DocumentSchema – data validation
# ---------------------------------------------------------------------------

class TestDocumentSchemaData:
    def test_add_field_string(self):
        s = DocumentSchema()
        s.add_field("title", FieldType.STRING, required=True)
        assert "title" in s.fields

    def test_add_field_from_string(self):
        s = DocumentSchema()
        s.add_field("count", "integer")
        assert s.fields["count"].field_type == FieldType.INTEGER

    def test_validate_data_valid(self):
        s = DocumentSchema()
        s.add_field("title", FieldType.STRING, required=True)
        s.add_field("count", FieldType.INTEGER)
        r = s.validate_data({"title": "Hello", "count": 5})
        assert r.valid is True

    def test_validate_data_missing_required(self):
        s = DocumentSchema()
        s.add_field("title", FieldType.STRING, required=True)
        r = s.validate_data({})
        assert r.valid is False

    def test_validate_data_warns_unknown(self):
        s = DocumentSchema()
        s.add_field("name", FieldType.STRING)
        r = s.validate_data({"name": "test", "extra": 42})
        assert len(r.warnings) == 1
        assert "extra" in r.warnings[0]


# ---------------------------------------------------------------------------
# DocumentSchema – document validation
# ---------------------------------------------------------------------------

class TestDocumentSchemaDoc:
    @pytest.fixture
    def sample_doc(self):
        return (
            "# Introduction\n\n"
            "This is the introduction section with enough words to pass the "
            "minimum word count for the section rule check.\n\n"
            "## Methods\n\n"
            "We used several methods.\n\n"
            "## Results\n\n"
            "Here are the results.\n\n"
            "# Conclusion\n\n"
            "In conclusion, this is the summary of the document with enough words.\n"
        )

    def test_validate_doc_passes(self, sample_doc):
        s = DocumentSchema()
        s.add_section("Introduction", required=True, min_words=5)
        s.add_section("Conclusion", required=True, min_words=5)
        r = s.validate_document(sample_doc)
        assert r.valid is True

    def test_required_section_missing(self):
        s = DocumentSchema()
        s.add_section("Abstract", required=True)
        r = s.validate_document("# Introduction\nHello")
        assert r.valid is False
        assert any("Abstract" in e.message for e in r.errors)

    def test_section_too_short(self, sample_doc):
        s = DocumentSchema()
        s.add_section("Methods", required=True, min_words=100)
        r = s.validate_document(sample_doc)
        assert r.valid is False
        assert any("too short" in e.message for e in r.errors)


# ---------------------------------------------------------------------------
# DocumentSchema – export
# ---------------------------------------------------------------------------

class TestDocumentSchemaExport:
    def test_to_dict(self):
        s = DocumentSchema(name="test")
        s.add_field("title", FieldType.STRING, required=True)
        s.add_section("Intro", required=True)
        d = s.to_dict()
        assert d["name"] == "test"
        assert "title" in d["fields"]
        assert len(d["sections"]) == 1

    def test_to_json_schema(self):
        s = DocumentSchema()
        s.add_field("title", FieldType.STRING, required=True, description="Title")
        s.add_field("count", FieldType.INTEGER, min_value=0)
        js = s.to_json_schema()
        assert js["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert "title" in js["properties"]
        assert js["required"] == ["title"]
        assert js["properties"]["count"]["minimum"] == 0

    def test_json_schema_includes_enum(self):
        s = DocumentSchema()
        s.add_field("status", FieldType.STRING, choices=["draft", "published"])
        js = s.to_json_schema()
        assert js["properties"]["status"]["enum"] == ["draft", "published"]


# ---------------------------------------------------------------------------
# create_schema helper
# ---------------------------------------------------------------------------

class TestCreateSchema:
    def test_from_dicts(self):
        s = create_schema(
            name="test",
            fields={
                "title": {"type": "string", "required": True, "min_length": 3},
                "score": {"type": "float", "min_value": 0.0},
            },
            sections=[
                {"heading": "Summary", "required": True},
            ],
        )
        assert s.name == "test"
        assert s.fields["title"].required is True
        assert s.fields["score"].field_type == FieldType.FLOAT
        assert len(s.sections) == 1

    def test_empty_schema(self):
        s = create_schema()
        assert s.name == ""
        assert len(s.fields) == 0


# ---------------------------------------------------------------------------
# Preset schemas
# ---------------------------------------------------------------------------

class TestPresetSchemas:
    def test_report_schema(self):
        s = report_schema()
        assert s.name == "research-report"
        assert "title" in s.fields
        assert s.fields["title"].required is True
        assert len(s.sections) == 4

    def test_article_schema(self):
        s = article_schema()
        assert s.name == "article"
        assert "author" in s.fields
        assert s.fields["author"].required is True

    def test_report_validates_good(self):
        s = report_schema()
        data = {"title": "My Report", "topic": "Python research topic"}
        r = s.validate_data(data)
        assert r.valid is True

    def test_report_validates_bad(self):
        s = report_schema()
        r = s.validate_data({})
        assert r.valid is False
        assert len(r.errors) >= 2
