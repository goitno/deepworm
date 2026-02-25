"""Tests for the template_engine module."""

import pytest

from deepworm.template_engine import (
    MacroDef,
    RenderResult,
    TemplateContext,
    TemplateError,
    Token,
    TokenType,
    create_context,
    extract_variables,
    list_filters,
    render_template,
    report_template,
    comparison_template,
    validate_template,
)


# ---------------------------------------------------------------------------
# Token / TokenType
# ---------------------------------------------------------------------------


class TestToken:
    def test_to_dict(self):
        tok = Token(TokenType.VARIABLE, "name", line=3)
        d = tok.to_dict()
        assert d["type"] == "variable"
        assert d["value"] == "name"
        assert d["line"] == 3

    def test_all_token_types(self):
        assert len(TokenType) == 17


# ---------------------------------------------------------------------------
# TemplateContext
# ---------------------------------------------------------------------------


class TestTemplateContext:
    def test_get_simple(self):
        ctx = TemplateContext(variables={"name": "Alice"})
        assert ctx.get("name") == "Alice"
        assert ctx.get("missing") is None
        assert ctx.get("missing", "default") == "default"

    def test_get_dot_notation(self):
        ctx = TemplateContext(variables={"user": {"name": "Bob", "age": 30}})
        assert ctx.get("user.name") == "Bob"
        assert ctx.get("user.age") == 30
        assert ctx.get("user.missing") is None

    def test_child_context(self):
        parent = TemplateContext(variables={"x": 1})
        child = parent.child()
        child.set("y", 2)
        assert child.get("x") == 1
        assert child.get("y") == 2

    def test_apply_builtin_filter(self):
        ctx = TemplateContext()
        assert ctx.apply_filter("upper", "hello") == "HELLO"

    def test_apply_custom_filter(self):
        ctx = TemplateContext(filters={"double": lambda v: str(v) * 2})
        assert ctx.apply_filter("double", "ab") == "abab"

    def test_apply_unknown_filter(self):
        ctx = TemplateContext()
        with pytest.raises(TemplateError, match="Unknown filter"):
            ctx.apply_filter("nonexistent", "x")


# ---------------------------------------------------------------------------
# MacroDef
# ---------------------------------------------------------------------------


class TestMacroDef:
    def test_to_dict(self):
        m = MacroDef(name="greet", params=["name"], body="Hello {{ name }}")
        d = m.to_dict()
        assert d["name"] == "greet"
        assert d["params"] == ["name"]


# ---------------------------------------------------------------------------
# render_template — variables
# ---------------------------------------------------------------------------


class TestRenderVariables:
    def test_simple_variable(self):
        result = render_template("Hello {{ name }}!", {"name": "World"})
        assert result.output == "Hello World!"
        assert result.success
        assert "name" in result.variables_used

    def test_missing_variable(self):
        result = render_template("Hello {{ name }}!")
        assert result.output == "Hello !"

    def test_dot_notation(self):
        result = render_template("{{ user.name }}", {"user": {"name": "Alice"}})
        assert result.output == "Alice"

    def test_multiple_variables(self):
        result = render_template("{{ a }} and {{ b }}", {"a": "X", "b": "Y"})
        assert result.output == "X and Y"

    def test_numeric_variable(self):
        result = render_template("Count: {{ n }}", {"n": 42})
        assert result.output == "Count: 42"


# ---------------------------------------------------------------------------
# render_template — filters
# ---------------------------------------------------------------------------


class TestRenderFilters:
    def test_upper(self):
        result = render_template("{{ name | upper }}", {"name": "alice"})
        assert result.output == "ALICE"

    def test_lower(self):
        result = render_template("{{ name | lower }}", {"name": "HELLO"})
        assert result.output == "hello"

    def test_title(self):
        result = render_template("{{ s | title }}", {"s": "hello world"})
        assert result.output == "Hello World"

    def test_default(self):
        result = render_template('{{ missing | default:"N/A" }}')
        assert result.output == "N/A"

    def test_length(self):
        result = render_template("{{ items | length }}", {"items": [1, 2, 3]})
        assert result.output == "3"

    def test_join(self):
        result = render_template("{{ items | join }}", {"items": ["a", "b", "c"]})
        assert result.output == "a, b, c"

    def test_truncate(self):
        result = render_template('{{ text | truncate:10 }}', {"text": "This is a long text string"})
        assert result.output == "This is..."

    def test_chain_filters(self):
        result = render_template("{{ name | lower | strip }}", {"name": " HELLO "})
        assert result.output == "hello"

    def test_custom_filter(self):
        filters = {"exclaim": lambda v: str(v) + "!!!"}
        result = render_template("{{ msg | exclaim }}", {"msg": "wow"}, filters=filters)
        assert result.output == "wow!!!"

    def test_first_last(self):
        r1 = render_template("{{ items | first }}", {"items": [10, 20, 30]})
        assert r1.output == "10"
        r2 = render_template("{{ items | last }}", {"items": [10, 20, 30]})
        assert r2.output == "30"

    def test_reverse(self):
        result = render_template("{{ s | reverse }}", {"s": "abc"})
        assert result.output == "cba"

    def test_sort(self):
        result = render_template("{{ items | sort | join }}", {"items": [3, 1, 2]})
        assert result.output == "1, 2, 3"

    def test_unique(self):
        result = render_template("{{ items | unique | join }}", {"items": [1, 2, 2, 3]})
        assert result.output == "1, 2, 3"

    def test_wordcount(self):
        result = render_template("{{ text | wordcount }}", {"text": "one two three"})
        assert result.output == "3"

    def test_capitalize(self):
        result = render_template("{{ s | capitalize }}", {"s": "hello"})
        assert result.output == "Hello"

    def test_replace(self):
        result = render_template('{{ text | replace:"world","earth" }}', {"text": "hello world"})
        assert result.output == "hello earth"


# ---------------------------------------------------------------------------
# render_template — conditionals
# ---------------------------------------------------------------------------


class TestRenderConditionals:
    def test_if_true(self):
        result = render_template("{% if show %}visible{% endif %}", {"show": True})
        assert result.output == "visible"

    def test_if_false(self):
        result = render_template("{% if show %}visible{% endif %}", {"show": False})
        assert result.output == ""

    def test_if_else(self):
        tpl = "{% if admin %}Admin{% else %}User{% endif %}"
        assert render_template(tpl, {"admin": True}).output == "Admin"
        assert render_template(tpl, {"admin": False}).output == "User"

    def test_elif(self):
        tpl = "{% if level == 1 %}A{% elif level == 2 %}B{% else %}C{% endif %}"
        assert render_template(tpl, {"level": 1}).output == "A"
        assert render_template(tpl, {"level": 2}).output == "B"
        assert render_template(tpl, {"level": 3}).output == "C"

    def test_nested_if(self):
        tpl = "{% if a %}{% if b %}both{% endif %}{% endif %}"
        assert render_template(tpl, {"a": True, "b": True}).output == "both"
        assert render_template(tpl, {"a": True, "b": False}).output == ""

    def test_comparison_operators(self):
        assert render_template("{% if x > 5 %}big{% endif %}", {"x": 10}).output == "big"
        assert render_template("{% if x < 5 %}small{% endif %}", {"x": 3}).output == "small"
        assert render_template("{% if x != 5 %}diff{% endif %}", {"x": 3}).output == "diff"

    def test_boolean_operators(self):
        tpl = "{% if a and b %}yes{% endif %}"
        assert render_template(tpl, {"a": True, "b": True}).output == "yes"
        assert render_template(tpl, {"a": True, "b": False}).output == ""

        tpl2 = "{% if a or b %}yes{% endif %}"
        assert render_template(tpl2, {"a": False, "b": True}).output == "yes"

    def test_not(self):
        tpl = "{% if not done %}pending{% endif %}"
        assert render_template(tpl, {"done": False}).output == "pending"


# ---------------------------------------------------------------------------
# render_template — loops
# ---------------------------------------------------------------------------


class TestRenderLoops:
    def test_simple_for(self):
        tpl = "{% for item in items %}{{ item }} {% endfor %}"
        result = render_template(tpl, {"items": ["a", "b", "c"]})
        assert result.output == "a b c "

    def test_loop_index(self):
        tpl = "{% for x in items %}{{ loop.index }}.{{ x }} {% endfor %}"
        result = render_template(tpl, {"items": ["a", "b"]})
        assert result.output == "1.a 2.b "

    def test_loop_first_last(self):
        tpl = "{% for x in items %}{% if loop.first %}[{% endif %}{{ x }}{% if loop.last %}]{% endif %}{% endfor %}"
        result = render_template(tpl, {"items": ["a", "b", "c"]})
        assert result.output == "[abc]"

    def test_nested_loops(self):
        tpl = "{% for row in rows %}{% for col in row %}{{ col }}{% endfor %} {% endfor %}"
        result = render_template(tpl, {"rows": [[1, 2], [3, 4]]})
        assert result.output == "12 34 "

    def test_empty_loop(self):
        tpl = "{% for x in items %}{{ x }}{% endfor %}"
        result = render_template(tpl, {"items": []})
        assert result.output == ""

    def test_loop_with_dict_items(self):
        tpl = "{% for x in items %}{{ x.name }}:{{ x.val }} {% endfor %}"
        items = [{"name": "a", "val": 1}, {"name": "b", "val": 2}]
        result = render_template(tpl, {"items": items})
        assert result.output == "a:1 b:2 "


# ---------------------------------------------------------------------------
# render_template — comments
# ---------------------------------------------------------------------------


class TestRenderComments:
    def test_comment_stripped(self):
        result = render_template("Hello{# this is a comment #} World")
        assert result.output == "Hello World"

    def test_multiline_comment(self):
        result = render_template("A{# multi\nline\ncomment #}B")
        assert result.output == "AB"


# ---------------------------------------------------------------------------
# render_template — includes and extends
# ---------------------------------------------------------------------------


class TestRenderIncludes:
    def test_include(self):
        templates = {"header": "=== {{ title }} ==="}
        result = render_template(
            "{% include 'header' %}\nBody",
            {"title": "Test"},
            templates=templates,
        )
        assert "=== Test ===" in result.output

    def test_include_missing(self):
        result = render_template("{% include 'missing' %}")
        assert not result.success
        assert any("not found" in e for e in result.errors)


class TestRenderExtends:
    def test_extends_basic(self):
        parent = "Header {% block content %}default{% endblock %} Footer"
        child = "{% extends 'base' %}{% block content %}custom{% endblock %}"
        templates = {"base": parent}
        result = render_template(child, templates=templates)
        assert "Header" in result.output
        assert "custom" in result.output
        assert "Footer" in result.output
        assert "default" not in result.output

    def test_extends_default_block(self):
        parent = "{% block title %}Default Title{% endblock %}"
        child = "{% extends 'base' %}"
        templates = {"base": parent}
        result = render_template(child, templates=templates)
        assert result.output == "Default Title"


# ---------------------------------------------------------------------------
# render_template — macros
# ---------------------------------------------------------------------------


class TestRenderMacros:
    def test_macro_define_and_call(self):
        tpl = "{% macro greet(name) %}Hello {{ name }}{% endmacro %}{% call greet('World') %}"
        result = render_template(tpl, {"World": "World"})
        assert "Hello World" in result.output

    def test_macro_multiple_params(self):
        tpl = '{% macro link(url, text) %}[{{ text }}]({{ url }}){% endmacro %}{% call link("https://x.com", "Click") %}'
        result = render_template(tpl)
        assert "[Click](https://x.com)" in result.output


# ---------------------------------------------------------------------------
# render_template — expressions
# ---------------------------------------------------------------------------


class TestExpressions:
    def test_string_literal(self):
        result = render_template('{{ "hello" }}')
        assert result.output == "hello"

    def test_numeric_literal(self):
        result = render_template("{% if 1 == 1 %}yes{% endif %}")
        assert result.output == "yes"

    def test_boolean_literal(self):
        result = render_template("{% if true %}yes{% endif %}")
        assert result.output == "yes"


# ---------------------------------------------------------------------------
# validate_template
# ---------------------------------------------------------------------------


class TestValidateTemplate:
    def test_valid(self):
        issues = validate_template("{% if x %}{{ x }}{% endif %}")
        assert issues == []

    def test_unclosed_if(self):
        issues = validate_template("{% if x %}hello")
        assert any("Unclosed if" in i for i in issues)

    def test_unclosed_for(self):
        issues = validate_template("{% for x in items %}{{ x }}")
        assert any("Unclosed for" in i for i in issues)

    def test_unexpected_endif(self):
        issues = validate_template("{% endif %}")
        assert any("Unexpected endif" in i for i in issues)

    def test_empty_variable(self):
        issues = validate_template("{{  }}")
        assert any("Empty variable" in i for i in issues)


# ---------------------------------------------------------------------------
# extract_variables
# ---------------------------------------------------------------------------


class TestExtractVariables:
    def test_simple(self):
        variables = extract_variables("{{ name }} {{ age }}")
        assert "name" in variables
        assert "age" in variables

    def test_with_filters(self):
        variables = extract_variables("{{ name | upper }}")
        assert "name" in variables

    def test_from_conditions(self):
        variables = extract_variables("{% if show %}...{% endif %}")
        assert "show" in variables

    def test_from_loops(self):
        variables = extract_variables("{% for x in items %}{{ x }}{% endfor %}")
        assert "items" in variables


# ---------------------------------------------------------------------------
# list_filters
# ---------------------------------------------------------------------------


class TestListFilters:
    def test_returns_sorted(self):
        filters = list_filters()
        assert filters == sorted(filters)
        assert "upper" in filters
        assert "lower" in filters
        assert "default" in filters
        assert len(filters) >= 15


# ---------------------------------------------------------------------------
# create_context
# ---------------------------------------------------------------------------


class TestCreateContext:
    def test_basic(self):
        ctx = create_context({"x": 1})
        assert ctx.get("x") == 1

    def test_with_filters(self):
        ctx = create_context(filters={"bang": lambda v: str(v) + "!"})
        assert ctx.apply_filter("bang", "hi") == "hi!"


# ---------------------------------------------------------------------------
# RenderResult
# ---------------------------------------------------------------------------


class TestRenderResult:
    def test_success(self):
        r = RenderResult(output="hello", variables_used=["name"], errors=[])
        assert r.success
        d = r.to_dict()
        assert d["success"] is True
        assert d["output"] == "hello"

    def test_failure(self):
        r = RenderResult(output="", errors=["something broke"])
        assert not r.success


# ---------------------------------------------------------------------------
# Preset templates
# ---------------------------------------------------------------------------


class TestPresetTemplates:
    def test_report_template(self):
        tpl = report_template()
        assert "{{ title }}" in tpl
        assert "{% for section in sections %}" in tpl

    def test_comparison_template(self):
        tpl = comparison_template()
        assert "{{ title" in tpl
        assert "{% for item in items %}" in tpl


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_template(self):
        result = render_template("")
        assert result.output == ""
        assert result.success

    def test_plain_text(self):
        result = render_template("Hello World")
        assert result.output == "Hello World"

    def test_special_chars_in_text(self):
        result = render_template("Price: $100 <tag> & more")
        assert result.output == "Price: $100 <tag> & more"

    def test_none_variable(self):
        result = render_template("{{ x }}", {"x": None})
        assert result.output == ""
