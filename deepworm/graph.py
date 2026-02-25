"""Document relationship and knowledge graph.

Build, traverse, and visualize graphs of document relationships:
concept maps, topic hierarchies, citation networks, and
dependency analysis.
"""

from __future__ import annotations

import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple


class EdgeType(Enum):
    """Types of relationships between nodes."""
    REFERENCES = "references"
    CONTAINS = "contains"
    RELATED_TO = "related_to"
    DEPENDS_ON = "depends_on"
    PARENT_OF = "parent_of"
    CHILD_OF = "child_of"
    CITES = "cites"
    SIMILAR_TO = "similar_to"
    PRECEDES = "precedes"
    FOLLOWS = "follows"


@dataclass
class Node:
    """A node in the knowledge graph."""

    node_id: str
    label: str = ""
    node_type: str = "concept"
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(self.node_id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Node):
            return self.node_id == other.node_id
        return False

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "id": self.node_id,
            "label": self.label or self.node_id,
            "type": self.node_type,
            "weight": self.weight,
        }
        if self.metadata:
            d["metadata"] = self.metadata
        return d


@dataclass
class Edge:
    """A directed edge in the knowledge graph."""

    source: str
    target: str
    edge_type: EdgeType = EdgeType.RELATED_TO
    weight: float = 1.0
    label: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "type": self.edge_type.value,
            "weight": self.weight,
            "label": self.label,
        }


@dataclass
class GraphStats:
    """Statistics about a graph."""

    node_count: int = 0
    edge_count: int = 0
    density: float = 0.0
    components: int = 0
    avg_degree: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": self.node_count,
            "edges": self.edge_count,
            "density": round(self.density, 4),
            "components": self.components,
            "avg_degree": round(self.avg_degree, 2),
        }


class KnowledgeGraph:
    """A directed graph for document relationships."""

    def __init__(self, name: str = "") -> None:
        self.name = name
        self._nodes: Dict[str, Node] = {}
        self._edges: List[Edge] = []
        self._adjacency: Dict[str, List[str]] = defaultdict(list)
        self._reverse_adj: Dict[str, List[str]] = defaultdict(list)

    def add_node(
        self,
        node_id: str,
        label: str = "",
        node_type: str = "concept",
        weight: float = 1.0,
        **metadata: Any,
    ) -> Node:
        """Add or update a node."""
        node = Node(
            node_id=node_id,
            label=label or node_id,
            node_type=node_type,
            weight=weight,
            metadata=metadata,
        )
        self._nodes[node_id] = node
        return node

    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: EdgeType = EdgeType.RELATED_TO,
        weight: float = 1.0,
        label: str = "",
    ) -> Edge:
        """Add an edge. Creates nodes if they don't exist."""
        if source not in self._nodes:
            self.add_node(source)
        if target not in self._nodes:
            self.add_node(target)

        edge = Edge(
            source=source,
            target=target,
            edge_type=edge_type,
            weight=weight,
            label=label,
        )
        self._edges.append(edge)
        self._adjacency[source].append(target)
        self._reverse_adj[target].append(source)
        return edge

    def get_node(self, node_id: str) -> Optional[Node]:
        return self._nodes.get(node_id)

    def get_edges(
        self,
        source: Optional[str] = None,
        target: Optional[str] = None,
        edge_type: Optional[EdgeType] = None,
    ) -> List[Edge]:
        """Query edges with optional filters."""
        results = list(self._edges)
        if source:
            results = [e for e in results if e.source == source]
        if target:
            results = [e for e in results if e.target == target]
        if edge_type:
            results = [e for e in results if e.edge_type == edge_type]
        return results

    def neighbors(self, node_id: str) -> List[str]:
        """Get outgoing neighbors."""
        return list(self._adjacency.get(node_id, []))

    def predecessors(self, node_id: str) -> List[str]:
        """Get incoming neighbors."""
        return list(self._reverse_adj.get(node_id, []))

    def degree(self, node_id: str) -> int:
        """Get total degree (in + out)."""
        return len(self._adjacency.get(node_id, [])) + len(
            self._reverse_adj.get(node_id, [])
        )

    def remove_node(self, node_id: str) -> bool:
        """Remove a node and its edges."""
        if node_id not in self._nodes:
            return False
        del self._nodes[node_id]
        self._edges = [
            e for e in self._edges if e.source != node_id and e.target != node_id
        ]
        if node_id in self._adjacency:
            del self._adjacency[node_id]
        if node_id in self._reverse_adj:
            del self._reverse_adj[node_id]
        # Clean references
        for adj_list in self._adjacency.values():
            while node_id in adj_list:
                adj_list.remove(node_id)
        for adj_list in self._reverse_adj.values():
            while node_id in adj_list:
                adj_list.remove(node_id)
        return True

    def has_path(self, source: str, target: str) -> bool:
        """Check if a path exists from source to target."""
        if source not in self._nodes or target not in self._nodes:
            return False
        visited: Set[str] = set()
        queue = deque([source])
        while queue:
            current = queue.popleft()
            if current == target:
                return True
            if current in visited:
                continue
            visited.add(current)
            for neighbor in self._adjacency.get(current, []):
                if neighbor not in visited:
                    queue.append(neighbor)
        return False

    def shortest_path(self, source: str, target: str) -> List[str]:
        """Find shortest path using BFS."""
        if source not in self._nodes or target not in self._nodes:
            return []
        if source == target:
            return [source]

        visited: Set[str] = set()
        queue: deque = deque([(source, [source])])

        while queue:
            current, path = queue.popleft()
            if current == target:
                return path
            if current in visited:
                continue
            visited.add(current)
            for neighbor in self._adjacency.get(current, []):
                if neighbor not in visited:
                    queue.append((neighbor, path + [neighbor]))
        return []

    def connected_components(self) -> List[Set[str]]:
        """Find connected components (treating graph as undirected)."""
        visited: Set[str] = set()
        components: List[Set[str]] = []

        for node_id in self._nodes:
            if node_id in visited:
                continue
            component: Set[str] = set()
            queue = deque([node_id])
            while queue:
                current = queue.popleft()
                if current in visited:
                    continue
                visited.add(current)
                component.add(current)
                # Both directions
                for n in self._adjacency.get(current, []):
                    if n not in visited:
                        queue.append(n)
                for n in self._reverse_adj.get(current, []):
                    if n not in visited:
                        queue.append(n)
            components.append(component)

        return components

    def topological_sort(self) -> List[str]:
        """Topological sort (Kahn's algorithm). Returns [] if cycle exists."""
        in_degree: Dict[str, int] = {n: 0 for n in self._nodes}
        for edge in self._edges:
            in_degree[edge.target] = in_degree.get(edge.target, 0) + 1

        queue = deque([n for n, d in in_degree.items() if d == 0])
        result: List[str] = []

        while queue:
            node = queue.popleft()
            result.append(node)
            for neighbor in self._adjacency.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(self._nodes):
            return []  # Cycle detected
        return result

    def subgraph(self, node_ids: Set[str]) -> "KnowledgeGraph":
        """Extract a subgraph containing only specified nodes."""
        g = KnowledgeGraph(name=f"{self.name}_sub")
        for nid in node_ids:
            node = self._nodes.get(nid)
            if node:
                g.add_node(nid, node.label, node.node_type, node.weight, **node.metadata)
        for edge in self._edges:
            if edge.source in node_ids and edge.target in node_ids:
                g.add_edge(edge.source, edge.target, edge.edge_type, edge.weight, edge.label)
        return g

    def stats(self) -> GraphStats:
        """Compute graph statistics."""
        n = len(self._nodes)
        e = len(self._edges)
        density = e / (n * (n - 1)) if n > 1 else 0.0
        components = len(self.connected_components())
        avg_degree = (2 * e) / n if n > 0 else 0.0

        return GraphStats(
            node_count=n,
            edge_count=e,
            density=density,
            components=components,
            avg_degree=avg_degree,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "edges": [e.to_dict() for e in self._edges],
        }

    def to_mermaid(self) -> str:
        """Export as Mermaid diagram."""
        lines = ["graph TD"]
        for node in self._nodes.values():
            label = node.label or node.node_id
            lines.append(f"    {node.node_id}[\"{label}\"]")
        for edge in self._edges:
            label = edge.label or edge.edge_type.value
            lines.append(f"    {edge.source} -->|{label}| {edge.target}")
        return "\n".join(lines)

    def to_dot(self) -> str:
        """Export as DOT (Graphviz) format."""
        lines = [f'digraph "{self.name}" {{']
        for node in self._nodes.values():
            label = node.label or node.node_id
            lines.append(f'    "{node.node_id}" [label="{label}"];')
        for edge in self._edges:
            label = edge.label or edge.edge_type.value
            lines.append(
                f'    "{edge.source}" -> "{edge.target}" [label="{label}"];'
            )
        lines.append("}")
        return "\n".join(lines)

    @property
    def nodes(self) -> List[Node]:
        return list(self._nodes.values())

    @property
    def edges(self) -> List[Edge]:
        return list(self._edges)

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)


# ---------------------------------------------------------------------------
# Graph construction helpers
# ---------------------------------------------------------------------------

def extract_concept_graph(text: str) -> KnowledgeGraph:
    """Extract a concept graph from markdown headings and content.

    Builds a graph from heading hierarchy (parent → child)
    and cross-references between sections.
    """
    g = KnowledgeGraph(name="concept-graph")
    lines = text.splitlines()
    heading_stack: List[Tuple[int, str]] = []

    for line in lines:
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            slug = re.sub(r"[^\w\s-]", "", title.lower())
            slug = re.sub(r"\s+", "-", slug).strip("-")

            g.add_node(slug, label=title, node_type="section")

            # Pop stack to find parent
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()

            if heading_stack:
                parent_slug = heading_stack[-1][1]
                g.add_edge(parent_slug, slug, EdgeType.PARENT_OF)

            heading_stack.append((level, slug))

    return g


def extract_link_graph(text: str) -> KnowledgeGraph:
    """Extract a graph from markdown links."""
    g = KnowledgeGraph(name="link-graph")

    # Find all sections and their links
    lines = text.splitlines()
    current_section = "document"
    g.add_node("document", node_type="section")

    for line in lines:
        heading = re.match(r"^#{1,6}\s+(.+)$", line)
        if heading:
            current_section = heading.group(1).strip()
            slug = re.sub(r"[^\w\s-]", "", current_section.lower())
            slug = re.sub(r"\s+", "-", slug).strip("-")
            g.add_node(slug, label=current_section, node_type="section")
            current_section = slug

        # Find links
        links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", line)
        for link_text, url in links:
            url_slug = re.sub(r"[^\w.-]", "-", url)[:50]
            g.add_node(url_slug, label=link_text, node_type="link")
            g.add_edge(current_section, url_slug, EdgeType.REFERENCES, label=link_text)

    return g


def create_graph(
    nodes: Optional[List[Dict[str, Any]]] = None,
    edges: Optional[List[Dict[str, Any]]] = None,
    name: str = "",
) -> KnowledgeGraph:
    """Create a graph from node/edge dicts."""
    g = KnowledgeGraph(name=name)
    if nodes:
        for n in nodes:
            nid = n.pop("id", n.pop("node_id", ""))
            g.add_node(nid, **n)
    if edges:
        for e in edges:
            et = e.get("edge_type") or e.get("type", "related_to")
            if isinstance(et, str):
                et = EdgeType(et)
            g.add_edge(
                e["source"],
                e["target"],
                edge_type=et,
                weight=e.get("weight", 1.0),
                label=e.get("label", ""),
            )
    return g


def merge_graphs(*graphs: KnowledgeGraph) -> KnowledgeGraph:
    """Merge multiple graphs into one."""
    merged = KnowledgeGraph(name="merged")
    for g in graphs:
        for node in g.nodes:
            if node.node_id not in merged._nodes:
                merged.add_node(
                    node.node_id, node.label, node.node_type, node.weight,
                    **node.metadata,
                )
        for edge in g.edges:
            merged.add_edge(
                edge.source, edge.target, edge.edge_type,
                edge.weight, edge.label,
            )
    return merged
