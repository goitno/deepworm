"""Tests for deepworm.graph – knowledge graph and relationship analysis."""

import pytest

from deepworm.graph import (
    Edge,
    EdgeType,
    GraphStats,
    KnowledgeGraph,
    Node,
    create_graph,
    extract_concept_graph,
    extract_link_graph,
    merge_graphs,
)


# ---------------------------------------------------------------------------
# Node / Edge
# ---------------------------------------------------------------------------

class TestNode:
    def test_defaults(self):
        n = Node(node_id="a")
        assert n.node_type == "concept"
        assert n.weight == 1.0

    def test_to_dict(self):
        n = Node(node_id="x", label="Test", metadata={"key": "val"})
        d = n.to_dict()
        assert d["id"] == "x"
        assert d["label"] == "Test"
        assert d["metadata"]["key"] == "val"

    def test_equality(self):
        assert Node("a") == Node("a")
        assert Node("a") != Node("b")

    def test_hash(self):
        assert hash(Node("a")) == hash(Node("a"))


class TestEdge:
    def test_to_dict(self):
        e = Edge(source="a", target="b", edge_type=EdgeType.CITES)
        d = e.to_dict()
        assert d["source"] == "a"
        assert d["target"] == "b"
        assert d["type"] == "cites"


class TestEdgeType:
    def test_all_types(self):
        assert len(EdgeType) == 10


# ---------------------------------------------------------------------------
# KnowledgeGraph – basic operations
# ---------------------------------------------------------------------------

class TestKnowledgeGraphBasic:
    def test_add_node(self):
        g = KnowledgeGraph()
        g.add_node("a", label="Node A")
        assert g.node_count == 1
        assert g.get_node("a").label == "Node A"

    def test_add_edge(self):
        g = KnowledgeGraph()
        g.add_edge("a", "b", EdgeType.REFERENCES)
        assert g.edge_count == 1
        assert g.node_count == 2  # auto-created

    def test_neighbors(self):
        g = KnowledgeGraph()
        g.add_edge("a", "b")
        g.add_edge("a", "c")
        assert set(g.neighbors("a")) == {"b", "c"}

    def test_predecessors(self):
        g = KnowledgeGraph()
        g.add_edge("a", "c")
        g.add_edge("b", "c")
        assert set(g.predecessors("c")) == {"a", "b"}

    def test_degree(self):
        g = KnowledgeGraph()
        g.add_edge("a", "b")
        g.add_edge("c", "a")
        assert g.degree("a") == 2  # out:1 + in:1

    def test_remove_node(self):
        g = KnowledgeGraph()
        g.add_edge("a", "b")
        g.add_edge("b", "c")
        assert g.remove_node("b") is True
        assert g.node_count == 2
        assert g.edge_count == 0

    def test_remove_nonexistent(self):
        g = KnowledgeGraph()
        assert g.remove_node("x") is False

    def test_get_edges_filter(self):
        g = KnowledgeGraph()
        g.add_edge("a", "b", EdgeType.REFERENCES)
        g.add_edge("a", "c", EdgeType.CONTAINS)
        refs = g.get_edges(edge_type=EdgeType.REFERENCES)
        assert len(refs) == 1


# ---------------------------------------------------------------------------
# KnowledgeGraph – path finding
# ---------------------------------------------------------------------------

class TestKnowledgeGraphPaths:
    def test_has_path(self):
        g = KnowledgeGraph()
        g.add_edge("a", "b")
        g.add_edge("b", "c")
        assert g.has_path("a", "c") is True
        assert g.has_path("c", "a") is False

    def test_has_path_nonexistent(self):
        g = KnowledgeGraph()
        assert g.has_path("x", "y") is False

    def test_shortest_path(self):
        g = KnowledgeGraph()
        g.add_edge("a", "b")
        g.add_edge("b", "c")
        g.add_edge("a", "c")
        path = g.shortest_path("a", "c")
        assert path == ["a", "c"]

    def test_shortest_path_same(self):
        g = KnowledgeGraph()
        g.add_node("a")
        assert g.shortest_path("a", "a") == ["a"]

    def test_shortest_path_none(self):
        g = KnowledgeGraph()
        g.add_node("a")
        g.add_node("b")
        assert g.shortest_path("a", "b") == []


# ---------------------------------------------------------------------------
# KnowledgeGraph – components and sorting
# ---------------------------------------------------------------------------

class TestKnowledgeGraphAnalysis:
    def test_connected_components(self):
        g = KnowledgeGraph()
        g.add_edge("a", "b")
        g.add_node("c")
        components = g.connected_components()
        assert len(components) == 2

    def test_topological_sort(self):
        g = KnowledgeGraph()
        g.add_edge("a", "b")
        g.add_edge("b", "c")
        order = g.topological_sort()
        assert order.index("a") < order.index("b") < order.index("c")

    def test_topological_sort_cycle(self):
        g = KnowledgeGraph()
        g.add_edge("a", "b")
        g.add_edge("b", "a")
        assert g.topological_sort() == []

    def test_subgraph(self):
        g = KnowledgeGraph()
        g.add_edge("a", "b")
        g.add_edge("b", "c")
        g.add_edge("c", "d")
        sub = g.subgraph({"a", "b"})
        assert sub.node_count == 2
        assert sub.edge_count == 1


# ---------------------------------------------------------------------------
# KnowledgeGraph – stats and export
# ---------------------------------------------------------------------------

class TestKnowledgeGraphExport:
    def test_stats(self):
        g = KnowledgeGraph()
        g.add_edge("a", "b")
        g.add_edge("b", "c")
        s = g.stats()
        assert s.node_count == 3
        assert s.edge_count == 2
        assert s.density > 0

    def test_stats_to_dict(self):
        s = GraphStats(node_count=5, edge_count=3)
        d = s.to_dict()
        assert d["nodes"] == 5

    def test_to_dict(self):
        g = KnowledgeGraph(name="test")
        g.add_edge("a", "b")
        d = g.to_dict()
        assert d["name"] == "test"
        assert len(d["nodes"]) == 2
        assert len(d["edges"]) == 1

    def test_to_mermaid(self):
        g = KnowledgeGraph()
        g.add_node("a", label="Node A")
        g.add_edge("a", "b")
        mermaid = g.to_mermaid()
        assert "graph TD" in mermaid
        assert "Node A" in mermaid

    def test_to_dot(self):
        g = KnowledgeGraph(name="test")
        g.add_edge("a", "b")
        dot = g.to_dot()
        assert "digraph" in dot
        assert "a" in dot


# ---------------------------------------------------------------------------
# Graph construction helpers
# ---------------------------------------------------------------------------

class TestExtractConceptGraph:
    def test_from_headings(self):
        text = "# Main\n## Sub A\n## Sub B\n### Detail"
        g = extract_concept_graph(text)
        assert g.node_count == 4
        assert g.edge_count >= 3

    def test_empty(self):
        g = extract_concept_graph("No headings here.")
        assert g.node_count == 0


class TestExtractLinkGraph:
    def test_from_links(self):
        text = "# Intro\n[Google](https://google.com)\n[GitHub](https://github.com)"
        g = extract_link_graph(text)
        assert g.node_count >= 3

    def test_no_links(self):
        g = extract_link_graph("No links.")
        assert g.edge_count == 0


class TestCreateGraph:
    def test_from_dicts(self):
        g = create_graph(
            nodes=[{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
            edges=[{"source": "a", "target": "b", "type": "cites"}],
            name="test",
        )
        assert g.node_count == 2
        assert g.edge_count == 1

    def test_empty(self):
        g = create_graph()
        assert g.node_count == 0


class TestMergeGraphs:
    def test_merge(self):
        g1 = KnowledgeGraph()
        g1.add_edge("a", "b")
        g2 = KnowledgeGraph()
        g2.add_edge("b", "c")
        merged = merge_graphs(g1, g2)
        assert merged.node_count == 3
        assert merged.edge_count == 2

    def test_merge_deduplicates_nodes(self):
        g1 = KnowledgeGraph()
        g1.add_node("a", label="X")
        g2 = KnowledgeGraph()
        g2.add_node("a", label="Y")
        merged = merge_graphs(g1, g2)
        assert merged.node_count == 1
