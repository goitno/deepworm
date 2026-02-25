"""Tests for deepworm.templates module."""

from deepworm.templates import (
    ResearchTemplate,
    get_template,
    list_templates,
    register_template,
)


def test_list_templates():
    templates = list_templates()
    assert len(templates) >= 10
    names = [t.name for t in templates]
    assert "quick" in names
    assert "deep" in names
    assert "academic" in names


def test_get_template():
    t = get_template("quick")
    assert t is not None
    assert t.depth == 1
    assert t.breadth == 3


def test_get_template_not_found():
    assert get_template("nonexistent") is None


def test_deep_template():
    t = get_template("deep")
    assert t is not None
    assert t.depth == 4
    assert t.breadth == 6


def test_academic_template():
    t = get_template("academic")
    assert t is not None
    assert "academic" in t.persona.lower()
    assert t.query_prefix != ""


def test_register_custom_template():
    custom = ResearchTemplate(
        name="custom_test",
        description="Test template",
        depth=5,
        breadth=8,
    )
    register_template(custom)
    found = get_template("custom_test")
    assert found is not None
    assert found.depth == 5


def test_apply_to_config():
    from deepworm.config import Config

    config = Config.auto()
    t = get_template("deep")
    t.apply_to_config(config)
    assert config.depth == 4
    assert config.breadth == 6


def test_template_has_tags():
    t = get_template("academic")
    assert "academic" in t.tags
    assert "scholarly" in t.tags
