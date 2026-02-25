"""Tests for deepworm.plugins."""

from deepworm.plugins import PluginManager


def test_transform_queries_hook():
    """Should transform queries via hook."""
    pm = PluginManager()

    @pm.hook("transform_queries")
    def add_year(topic, queries):
        return [f"{q} 2024" for q in queries]

    result = pm.apply_transform_queries("AI", ["machine learning", "deep learning"])
    assert result == ["machine learning 2024", "deep learning 2024"]


def test_filter_source_hook():
    """Should filter sources via hook."""
    pm = PluginManager()

    @pm.hook("filter_source")
    def skip_ads(url, title, content):
        return "advertisement" not in content.lower()

    assert pm.apply_filter_source("https://good.com", "Good", "Real content") is True
    assert pm.apply_filter_source("https://ad.com", "Ad", "This is an advertisement") is False


def test_post_report_hook():
    """Should transform report via hook."""
    pm = PluginManager()

    @pm.hook("post_report")
    def add_disclaimer(topic, report):
        return report + "\n\n*Disclaimer: AI-generated.*"

    result = pm.apply_post_report("test", "# Report")
    assert result.endswith("*Disclaimer: AI-generated.*")


def test_multiple_hooks_chain():
    """Multiple hooks should chain in order."""
    pm = PluginManager()

    @pm.hook("transform_queries")
    def first(topic, queries):
        return [q + " A" for q in queries]

    @pm.hook("transform_queries")
    def second(topic, queries):
        return [q + " B" for q in queries]

    result = pm.apply_transform_queries("t", ["q"])
    assert result == ["q A B"]


def test_hook_error_doesnt_break():
    """Hook errors should not break the pipeline."""
    pm = PluginManager()

    @pm.hook("post_report")
    def bad_hook(topic, report):
        raise ValueError("oops")

    @pm.hook("post_report")
    def good_hook(topic, report):
        return report + " ok"

    result = pm.apply_post_report("t", "report")
    assert result == "report ok"


def test_register_non_decorator():
    """Should support non-decorator registration."""
    pm = PluginManager()
    pm.register("filter_source", lambda url, title, content: True)
    assert pm.apply_filter_source("u", "t", "c") is True


def test_clear_hooks():
    """Should clear hooks."""
    pm = PluginManager()
    pm.register("filter_source", lambda u, t, c: False)
    pm.clear("filter_source")
    assert pm.apply_filter_source("u", "t", "c") is True  # No hooks = pass through


def test_clear_all_hooks():
    """Should clear all hooks."""
    pm = PluginManager()
    pm.register("filter_source", lambda u, t, c: False)
    pm.register("post_report", lambda t, r: r + "x")
    pm.clear()
    assert pm.registered_hooks == {}


def test_registered_hooks():
    """Should report registered hook counts."""
    pm = PluginManager()
    pm.register("filter_source", lambda u, t, c: True)
    pm.register("filter_source", lambda u, t, c: True)
    pm.register("post_report", lambda t, r: r)
    hooks = pm.registered_hooks
    assert hooks["filter_source"] == 2
    assert hooks["post_report"] == 1


def test_unknown_hook_raises():
    """Should raise on unknown hook name."""
    pm = PluginManager()
    try:
        pm.register("nonexistent", lambda: None)
        assert False, "Should have raised"
    except ValueError:
        pass
