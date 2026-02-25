"""Tests for cross-referencing module."""

import pytest
from deepworm.crossref import (
    CrossRefTarget,
    CrossRefLink,
    CrossRefIndex,
    build_crossref_index,
    inject_crossrefs,
    generate_list_of_figures,
    generate_list_of_tables,
    _slugify,
)


# --- CrossRefTarget ---

class TestCrossRefTarget:
    def test_basic(self):
        target = CrossRefTarget(label="intro", ref_type="section", title="Introduction")
        assert target.label == "intro"
        assert target.ref_type == "section"

    def test_display_numbered(self):
        target = CrossRefTarget(
            label="sec1", ref_type="section", title="Intro", number=1
        )
        assert target.display == "Section 1"

    def test_display_figure(self):
        target = CrossRefTarget(
            label="fig1", ref_type="figure", title="Chart", number=3
        )
        assert target.display == "Figure 3"

    def test_display_no_number(self):
        target = CrossRefTarget(label="x", ref_type="table", title="Data")
        assert "Data" in target.display

    def test_to_dict(self):
        target = CrossRefTarget(
            label="sec1", ref_type="section", title="Intro", line=5, number=1
        )
        d = target.to_dict()
        assert d["label"] == "sec1"
        assert d["line"] == 5


# --- CrossRefLink ---

class TestCrossRefLink:
    def test_basic(self):
        link = CrossRefLink(source_line=10, target_label="sec1")
        assert link.source_line == 10
        assert link.resolved is False

    def test_to_dict(self):
        link = CrossRefLink(source_line=10, target_label="sec1", context="see section")
        d = link.to_dict()
        assert d["source_line"] == 10
        assert d["target_label"] == "sec1"


# --- CrossRefIndex ---

class TestCrossRefIndex:
    def test_empty(self):
        index = CrossRefIndex()
        assert len(index.targets) == 0
        assert len(index.links) == 0

    def test_add_target(self):
        index = CrossRefIndex()
        target = index.add_target("intro", "section", "Introduction", 5, 1)
        assert len(index.targets) == 1
        assert target.label == "intro"

    def test_add_link_resolved(self):
        index = CrossRefIndex()
        index.add_target("intro", "section", "Introduction")
        link = index.add_link(10, "intro", "see intro")
        assert link.resolved is True

    def test_add_link_unresolved(self):
        index = CrossRefIndex()
        link = index.add_link(10, "missing", "see missing")
        assert link.resolved is False

    def test_get_target(self):
        index = CrossRefIndex()
        index.add_target("intro", "section", "Introduction")
        assert index.get_target("intro") is not None
        assert index.get_target("missing") is None

    def test_get_targets_by_type(self):
        index = CrossRefIndex()
        index.add_target("s1", "section", "A")
        index.add_target("f1", "figure", "B")
        index.add_target("s2", "section", "C")
        sections = index.get_targets_by_type("section")
        assert len(sections) == 2

    def test_unresolved_links(self):
        index = CrossRefIndex()
        index.add_target("intro", "section", "Introduction")
        index.add_link(10, "intro")
        index.add_link(20, "missing")
        assert len(index.unresolved_links) == 1

    def test_unused_targets(self):
        index = CrossRefIndex()
        index.add_target("intro", "section", "Introduction")
        index.add_target("methods", "section", "Methods")
        index.add_link(10, "intro")
        unused = index.unused_targets
        assert len(unused) == 1
        assert unused[0].label == "methods"

    def test_is_valid(self):
        index = CrossRefIndex()
        index.add_target("intro", "section", "Introduction")
        index.add_link(10, "intro")
        assert index.is_valid is True

    def test_is_invalid(self):
        index = CrossRefIndex()
        index.add_link(10, "missing")
        assert index.is_valid is False

    def test_stats(self):
        index = CrossRefIndex()
        index.add_target("intro", "section", "Introduction")
        index.add_link(10, "intro")
        index.add_link(20, "missing")
        stats = index.stats
        assert stats["targets"] == 1
        assert stats["links"] == 2
        assert stats["resolved"] == 1
        assert stats["unresolved"] == 1

    def test_validate_unresolved(self):
        index = CrossRefIndex()
        index.add_link(10, "missing")
        issues = index.validate()
        assert len(issues) >= 1
        assert issues[0]["type"] == "unresolved_reference"

    def test_validate_duplicate_labels(self):
        index = CrossRefIndex()
        index.add_target("intro", "section", "Introduction", 5)
        index.add_target("intro", "section", "Also Introduction", 15)
        issues = index.validate()
        assert any(i["type"] == "duplicate_label" for i in issues)

    def test_to_markdown(self):
        index = CrossRefIndex()
        index.add_target("intro", "section", "Introduction", 5, 1)
        index.add_link(10, "intro")
        md = index.to_markdown()
        assert "## Cross-Reference Index" in md
        assert "Introduction" in md

    def test_to_markdown_empty(self):
        index = CrossRefIndex()
        md = index.to_markdown()
        assert "No targets found" in md

    def test_to_dict(self):
        index = CrossRefIndex()
        index.add_target("intro", "section", "Introduction")
        d = index.to_dict()
        assert "stats" in d
        assert "targets" in d
        assert "links" in d
        assert "issues" in d


# --- Build Index ---

SAMPLE_REPORT = """# Research Report

## Introduction {#intro}

This report covers machine learning advances.

## Methods {#methods}

As described in {@intro}, we use several approaches.

See {@results} for the main findings.

## Results {#results}

**Figure 1.** Training accuracy over epochs

**Table 1.** Performance comparison

The data in {@methods} shows our methodology.

## Conclusion

As shown in Figure 1 and Table 1.
"""


class TestBuildIndex:
    def test_finds_sections(self):
        index = build_crossref_index(SAMPLE_REPORT)
        sections = index.get_targets_by_type("section")
        assert len(sections) >= 3

    def test_finds_labeled_sections(self):
        index = build_crossref_index(SAMPLE_REPORT)
        assert index.get_target("intro") is not None
        assert index.get_target("methods") is not None
        assert index.get_target("results") is not None

    def test_finds_figures(self):
        index = build_crossref_index(SAMPLE_REPORT)
        figures = index.get_targets_by_type("figure")
        assert len(figures) >= 1

    def test_finds_tables(self):
        index = build_crossref_index(SAMPLE_REPORT)
        tables = index.get_targets_by_type("table")
        assert len(tables) >= 1

    def test_finds_xref_links(self):
        index = build_crossref_index(SAMPLE_REPORT)
        assert len(index.links) >= 2

    def test_resolves_links(self):
        index = build_crossref_index(SAMPLE_REPORT)
        resolved = [l for l in index.links if l.resolved]
        assert len(resolved) >= 2

    def test_empty_text(self):
        index = build_crossref_index("")
        assert len(index.targets) == 0


# --- Inject Crossrefs ---

class TestInjectCrossrefs:
    def test_resolves_references(self):
        text = "See {@intro} for more details."
        index = CrossRefIndex()
        index.add_target("intro", "section", "Introduction", number=1)
        result = inject_crossrefs(text, index)
        assert "**Section 1**" in result
        assert "{@intro}" not in result

    def test_leaves_unresolved(self):
        text = "See {@missing} for more details."
        index = CrossRefIndex()
        result = inject_crossrefs(text, index)
        assert "{@missing}" in result

    def test_multiple_refs(self):
        text = "Compare {@intro} and {@methods}."
        index = CrossRefIndex()
        index.add_target("intro", "section", "Introduction", number=1)
        index.add_target("methods", "section", "Methods", number=2)
        result = inject_crossrefs(text, index)
        assert "**Section 1**" in result
        assert "**Section 2**" in result


# --- Lists ---

class TestListGeneration:
    def test_list_of_figures(self):
        index = CrossRefIndex()
        index.add_target("fig:1", "figure", "Training curves", 10, 1)
        index.add_target("fig:2", "figure", "Loss landscape", 25, 2)
        lof = generate_list_of_figures(index)
        assert "## List of Figures" in lof
        assert "Training curves" in lof
        assert "Loss landscape" in lof

    def test_list_of_figures_empty(self):
        index = CrossRefIndex()
        assert generate_list_of_figures(index) == ""

    def test_list_of_tables(self):
        index = CrossRefIndex()
        index.add_target("tbl:1", "table", "Results", 15, 1)
        lot = generate_list_of_tables(index)
        assert "## List of Tables" in lot
        assert "Results" in lot

    def test_list_of_tables_empty(self):
        index = CrossRefIndex()
        assert generate_list_of_tables(index) == ""


# --- Helpers ---

class TestHelpers:
    def test_slugify(self):
        assert _slugify("Hello World") == "hello-world"
        assert _slugify("Section 1: Introduction") == "section-1-introduction"
        assert _slugify("  Spaces  ") == "spaces"

    def test_slugify_special(self):
        assert _slugify("What's New?") == "whats-new"
