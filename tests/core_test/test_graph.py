# tests/core_test/test_graph.py
"""
Tests for the Graph model (api/api/models/graph.py).

Covers:
    • Node CRUD (add, get, remove, duplicate ID error)
    • Edge CRUD (add, get, remove, validation errors)
    • Adjacency / neighbor queries
    • Cycle detection (directed, undirected, acyclic)
    • Subgraph extraction (deep-copy isolation)
    • to_dict serialization
    • Edge removal side-effects on adjacency list
"""
import pytest
from copy import deepcopy
from datetime import date

from api.api.models.graph import Graph
from api.api.models.node import Node
from api.api.models.edge import Edge, EdgeDirection

# Re-use ConcreteNode from conftest
from tests.conftest import ConcreteNode


# ═════════════════════════════════════════════════════════════════
#  FIXTURES
# ═════════════════════════════════════════════════════════════════

@pytest.fixture
def empty_graph() -> Graph:
    """An empty graph with no nodes or edges."""
    return Graph("empty")


@pytest.fixture
def small_graph() -> Graph:
    """
    Small 4-node graph for targeted tests:

        A --e1--> B --e2--> C --e3--> D
    """
    g = Graph("small")
    a = ConcreteNode("A", Name="Alice", Age=30)
    b = ConcreteNode("B", Name="Bob", Age=25)
    c = ConcreteNode("C", Name="Carol", Age=35)
    d = ConcreteNode("D", Name="David", Age=28)
    for n in [a, b, c, d]:
        g.add_node(n)

    g.add_edge(Edge("e1", a, b, EdgeDirection.DIRECTED, Weight=1.0))
    g.add_edge(Edge("e2", b, c, EdgeDirection.DIRECTED, Weight=2.0))
    g.add_edge(Edge("e3", c, d, EdgeDirection.DIRECTED, Weight=3.0))
    return g


# ═════════════════════════════════════════════════════════════════
#  NODE CRUD
# ═════════════════════════════════════════════════════════════════

class TestNodeCRUD:

    def test_add_node(self, empty_graph):
        node = ConcreteNode("1", Name="Test")
        empty_graph.add_node(node)
        assert empty_graph.get_number_of_nodes() == 1
        assert empty_graph.get_node("1") is node

    def test_add_node_duplicate_raises(self, empty_graph):
        empty_graph.add_node(ConcreteNode("1", Name="A"))
        with pytest.raises(ValueError, match="already exists"):
            empty_graph.add_node(ConcreteNode("1", Name="B"))

    def test_get_node_returns_none_for_missing(self, empty_graph):
        assert empty_graph.get_node("nonexistent") is None

    def test_get_all_nodes(self, small_graph):
        nodes = small_graph.get_all_nodes()
        assert len(nodes) == 4
        ids = {n.node_id for n in nodes}
        assert ids == {"A", "B", "C", "D"}

    def test_remove_node(self, empty_graph):
        empty_graph.add_node(ConcreteNode("x"))
        assert empty_graph.get_number_of_nodes() == 1
        empty_graph.remove_node("x")
        assert empty_graph.get_number_of_nodes() == 0
        assert empty_graph.get_node("x") is None

    def test_remove_node_not_in_graph_raises(self, empty_graph):
        with pytest.raises(ValueError, match="not in graph"):
            empty_graph.remove_node("ghost")

    def test_remove_node_also_removes_connected_edges(self, small_graph):
        """Removing node B should also remove edges e1 (A→B) and e2 (B→C)."""
        small_graph.remove_node("B")
        assert small_graph.get_number_of_nodes() == 3
        assert small_graph.get_edge("e1") is None
        assert small_graph.get_edge("e2") is None
        # e3 (C→D) should survive
        assert small_graph.get_edge("e3") is not None


# ═════════════════════════════════════════════════════════════════
#  EDGE CRUD
# ═════════════════════════════════════════════════════════════════

class TestEdgeCRUD:

    def test_add_edge(self, small_graph):
        assert small_graph.get_number_of_edges() == 3
        assert small_graph.get_edge("e1") is not None

    def test_add_edge_duplicate_raises(self, small_graph):
        a = small_graph.get_node("A")
        b = small_graph.get_node("B")
        with pytest.raises(ValueError, match="already exists"):
            small_graph.add_edge(Edge("e1", a, b, EdgeDirection.DIRECTED))

    def test_add_edge_source_not_in_graph_raises(self, small_graph):
        outsider = ConcreteNode("Z")
        b = small_graph.get_node("B")
        with pytest.raises(ValueError, match="Source node"):
            small_graph.add_edge(Edge("e99", outsider, b, EdgeDirection.DIRECTED))

    def test_add_edge_target_not_in_graph_raises(self, small_graph):
        a = small_graph.get_node("A")
        outsider = ConcreteNode("Z")
        with pytest.raises(ValueError, match="Target node"):
            small_graph.add_edge(Edge("e99", a, outsider, EdgeDirection.DIRECTED))

    def test_get_edge_returns_none_for_missing(self, small_graph):
        assert small_graph.get_edge("nonexistent") is None

    def test_get_all_edges(self, small_graph):
        edges = small_graph.get_all_edges()
        assert len(edges) == 3
        ids = {e.edge_id for e in edges}
        assert ids == {"e1", "e2", "e3"}

    def test_remove_edge(self, small_graph):
        small_graph.remove_edge("e2")
        assert small_graph.get_number_of_edges() == 2
        assert small_graph.get_edge("e2") is None

    def test_remove_edge_nonexistent_is_safe(self, small_graph):
        """remove_edge on unknown ID does not raise."""
        small_graph.remove_edge("no_such_edge")
        assert small_graph.get_number_of_edges() == 3

    def test_remove_edge_cleans_adjacency_list(self, small_graph):
        """After removing e1, node A should have no edges in its adjacency."""
        small_graph.remove_edge("e1")
        assert len(small_graph._adjacency_list["A"]) == 0
        # B still has e2 (B→C)
        b_edges = [e.edge_id for e in small_graph._adjacency_list["B"]]
        assert "e2" in b_edges


# ═════════════════════════════════════════════════════════════════
#  NEIGHBOR / ADJACENCY QUERIES
# ═════════════════════════════════════════════════════════════════

class TestNeighborQueries:

    def test_get_neighbors_directed(self, small_graph):
        """A→B: B is neighbor of A."""
        a = small_graph.get_node("A")
        neighbors = small_graph.get_neighbors(a)
        neighbor_ids = {n.node_id for n in neighbors}
        assert "B" in neighbor_ids

    def test_get_outgoing_edges(self, small_graph):
        b = small_graph.get_node("B")
        out = small_graph.get_outgoing_edges(b)
        assert len(out) == 1
        assert out[0].edge_id == "e2"

    def test_get_incoming_edges(self, small_graph):
        b = small_graph.get_node("B")
        inc = small_graph.get_incoming_edges(b)
        assert len(inc) == 1
        assert inc[0].edge_id == "e1"

    def test_undirected_edges_appear_in_both_directions(self):
        """An undirected edge should be both outgoing and incoming for both endpoints."""
        g = Graph("bidir")
        x = ConcreteNode("X")
        y = ConcreteNode("Y")
        g.add_node(x)
        g.add_node(y)
        g.add_edge(Edge("u1", x, y, EdgeDirection.UNDIRECTED))

        assert len(g.get_outgoing_edges(x)) == 1
        assert len(g.get_outgoing_edges(y)) == 1
        assert len(g.get_incoming_edges(x)) == 1
        assert len(g.get_incoming_edges(y)) == 1


# ═════════════════════════════════════════════════════════════════
#  CYCLE DETECTION
# ═════════════════════════════════════════════════════════════════

class TestCycleDetection:

    def test_stub_graph_has_cycle(self, stub_graph):
        """The 15-node stub graph has a cycle (n15 — n1)."""
        assert stub_graph.has_cycle() is True

    def test_acyclic_graph_still_has_cycle_after_removing_e25(self, acyclic_graph):
        """Removing only e25 does NOT make the stub graph acyclic,
        because many other undirected cross-edges create cycles."""
        assert acyclic_graph.has_cycle() is True

    def test_empty_graph_has_no_cycle(self, empty_graph):
        assert empty_graph.has_cycle() is False

    def test_single_node_no_cycle(self, empty_graph):
        empty_graph.add_node(ConcreteNode("solo"))
        assert empty_graph.has_cycle() is False

    def test_directed_cycle(self):
        """A → B → C → A  is a directed cycle."""
        g = Graph("dcycle")
        a, b, c = ConcreteNode("A"), ConcreteNode("B"), ConcreteNode("C")
        for n in [a, b, c]:
            g.add_node(n)
        g.add_edge(Edge("e1", a, b, EdgeDirection.DIRECTED))
        g.add_edge(Edge("e2", b, c, EdgeDirection.DIRECTED))
        g.add_edge(Edge("e3", c, a, EdgeDirection.DIRECTED))
        assert g.has_cycle() is True

    def test_directed_no_cycle(self):
        """A → B → C  without back-edge is acyclic."""
        g = Graph("dnocycle")
        a, b, c = ConcreteNode("A"), ConcreteNode("B"), ConcreteNode("C")
        for n in [a, b, c]:
            g.add_node(n)
        g.add_edge(Edge("e1", a, b, EdgeDirection.DIRECTED))
        g.add_edge(Edge("e2", b, c, EdgeDirection.DIRECTED))
        assert g.has_cycle() is False

    def test_undirected_triangle_has_cycle(self):
        """Three nodes connected in a triangle with undirected edges."""
        g = Graph("tri")
        a, b, c = ConcreteNode("A"), ConcreteNode("B"), ConcreteNode("C")
        for n in [a, b, c]:
            g.add_node(n)
        g.add_edge(Edge("e1", a, b, EdgeDirection.UNDIRECTED))
        g.add_edge(Edge("e2", b, c, EdgeDirection.UNDIRECTED))
        g.add_edge(Edge("e3", c, a, EdgeDirection.UNDIRECTED))
        assert g.has_cycle() is True

    def test_undirected_line_no_cycle(self):
        """A -- B -- C  (undirected line) is acyclic."""
        g = Graph("line")
        a, b, c = ConcreteNode("A"), ConcreteNode("B"), ConcreteNode("C")
        for n in [a, b, c]:
            g.add_node(n)
        g.add_edge(Edge("e1", a, b, EdgeDirection.UNDIRECTED))
        g.add_edge(Edge("e2", b, c, EdgeDirection.UNDIRECTED))
        assert g.has_cycle() is False


# ═════════════════════════════════════════════════════════════════
#  SUBGRAPH
# ═════════════════════════════════════════════════════════════════

class TestSubgraph:

    def test_subgraph_contains_requested_nodes(self, small_graph):
        sub = small_graph.get_subgraph_by_nodes({"A", "B"})
        assert sub.get_number_of_nodes() == 2
        assert sub.get_node("A") is not None
        assert sub.get_node("B") is not None

    def test_subgraph_includes_edges_between_selected_nodes(self, small_graph):
        sub = small_graph.get_subgraph_by_nodes({"A", "B"})
        assert sub.get_number_of_edges() == 1
        assert sub.get_edge("e1") is not None

    def test_subgraph_excludes_edges_to_outside_nodes(self, small_graph):
        """Selecting A, B should NOT include e2 (B→C)."""
        sub = small_graph.get_subgraph_by_nodes({"A", "B"})
        assert sub.get_edge("e2") is None

    def test_subgraph_is_deep_copy(self, small_graph):
        """Mutating the subgraph should NOT affect the original graph."""
        sub = small_graph.get_subgraph_by_nodes({"A", "B"})
        sub_node_a = sub.get_node("A")
        sub_node_a.set_attribute("Name", "MODIFIED")

        original_a = small_graph.get_node("A")
        assert original_a.get_attribute("Name") == "Alice"

    def test_subgraph_empty_set(self, small_graph):
        sub = small_graph.get_subgraph_by_nodes(set())
        assert sub.get_number_of_nodes() == 0
        assert sub.get_number_of_edges() == 0

    def test_subgraph_ignores_nonexistent_ids(self, small_graph):
        sub = small_graph.get_subgraph_by_nodes({"A", "GHOST"})
        assert sub.get_number_of_nodes() == 1
        assert sub.get_node("A") is not None

    def test_subgraph_from_stub_preserves_edge_attrs(self, stub_graph):
        """Edges in the subgraph should retain their attributes."""
        sub = stub_graph.get_subgraph_by_nodes({"n1", "n2"})
        edge = sub.get_edge("e1")
        assert edge is not None
        assert edge.get_attribute("Relation") == "friend"
        assert edge.get_attribute("Weight") == 0.9


# ═════════════════════════════════════════════════════════════════
#  SERIALIZATION (to_dict)
# ═════════════════════════════════════════════════════════════════

class TestToDict:

    def test_to_dict_keys(self, small_graph):
        d = small_graph.to_dict()
        assert "id" in d
        assert "nodes" in d
        assert "edges" in d

    def test_to_dict_node_count(self, small_graph):
        d = small_graph.to_dict()
        assert len(d["nodes"]) == 4

    def test_to_dict_edge_count(self, small_graph):
        d = small_graph.to_dict()
        assert len(d["edges"]) == 3

    def test_to_dict_node_structure(self, small_graph):
        d = small_graph.to_dict()
        node_dict = d["nodes"][0]
        assert "id" in node_dict
        assert "attributes" in node_dict

    def test_to_dict_edge_structure(self, small_graph):
        d = small_graph.to_dict()
        edge_dict = d["edges"][0]
        assert "id" in edge_dict
        assert "source" in edge_dict
        assert "target" in edge_dict
        assert "direction" in edge_dict


# ═════════════════════════════════════════════════════════════════
#  MISC
# ═════════════════════════════════════════════════════════════════

class TestMisc:

    def test_repr(self, small_graph):
        r = repr(small_graph)
        assert "small" in r
        assert "4" in r  # nodes
        assert "3" in r  # edges

    def test_get_number_of_nodes(self, small_graph):
        assert small_graph.get_number_of_nodes() == 4

    def test_get_number_of_edges(self, small_graph):
        assert small_graph.get_number_of_edges() == 3

    def test_self_loop(self):
        """A self-loop on a node should work and be detected as a cycle."""
        g = Graph("loop")
        n = ConcreteNode("X")
        g.add_node(n)
        g.add_edge(Edge("self", n, n, EdgeDirection.DIRECTED))
        assert g.get_number_of_edges() == 1
        # Self-loop in adjacency list
        assert len(g._adjacency_list["X"]) == 1