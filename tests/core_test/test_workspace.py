# tests/core_test/test_workspace.py
"""
Tests for Workspace — filter/search state, undo, reset, history management.

Covers:
    • Creation and properties (workspace_id, name, data_source, file_path)
    • apply_filter → subgraph
    • apply_search → subgraph
    • Successive filter/search chains
    • undo → restores previous graph
    • undo on empty history → None
    • reset → original graph restored, history cleared
    • history_depth tracking
    • max_history overflow (oldest snapshot dropped)
    • original_graph returns deep copy (immutable)
    • current_graph property
    • to_dict metadata
"""
import pytest
from copy import deepcopy
from datetime import date

from api.models.graph import Graph
from api.models.node import Node
from api.models.edge import Edge, EdgeDirection

from graph_platform.workspace import Workspace


# ── Concrete Node ────────────────────────────────────────────────

class _WsNode(Node):
    """Concrete Node for workspace tests."""
    pass


# ── Fixtures ─────────────────────────────────────────────────────

def _build_ws_graph() -> Graph:
    """
    5-node graph for workspace tests:
        n1(Alice,30,Paris) -- n2(Bob,25,London) -- n3(Carol,35,Paris)
                                  |
                              n4(David,28,Berlin) -- n5(Eve,22,Pancevo)
    """
    g = Graph("ws_test")
    n1 = _WsNode("n1", Name="Alice", Age=30, City="Paris")
    n2 = _WsNode("n2", Name="Bob", Age=25, City="London")
    n3 = _WsNode("n3", Name="Carol", Age=35, City="Paris")
    n4 = _WsNode("n4", Name="David", Age=28, City="Berlin")
    n5 = _WsNode("n5", Name="Eve", Age=22, City="Pancevo")
    for n in [n1, n2, n3, n4, n5]:
        g.add_node(n)
    g.add_edge(Edge("e1", n1, n2, EdgeDirection.UNDIRECTED, Relation="friend"))
    g.add_edge(Edge("e2", n2, n3, EdgeDirection.UNDIRECTED, Relation="colleague"))
    g.add_edge(Edge("e3", n2, n4, EdgeDirection.UNDIRECTED, Relation="friend"))
    g.add_edge(Edge("e4", n4, n5, EdgeDirection.UNDIRECTED, Relation="mentor"))
    return g


@pytest.fixture
def ws() -> Workspace:
    return Workspace(
        _build_ws_graph(),
        data_source="json",
        file_path="/tmp/test.json",
        name="Test WS",
        max_history=5,
    )


@pytest.fixture
def ws_fresh() -> Workspace:
    """Fresh copy each time — use when test mutates workspace heavily."""
    return Workspace(_build_ws_graph(), name="Fresh WS")


# ── Creation ─────────────────────────────────────────────────────


class TestCreation:

    def test_workspace_id_is_uuid(self, ws):
        assert len(ws.workspace_id) == 36  # UUID format: 8-4-4-4-12
        assert ws.workspace_id.count("-") == 4

    def test_name(self, ws):
        assert ws.name == "Test WS"

    def test_default_name(self):
        ws = Workspace(Graph("g"))
        assert ws.name.startswith("Workspace-")

    def test_data_source(self, ws):
        assert ws.data_source == "json"

    def test_file_path(self, ws):
        assert ws.file_path == "/tmp/test.json"

    def test_current_graph_has_all_nodes(self, ws):
        assert ws.current_graph.get_number_of_nodes() == 5

    def test_current_graph_has_all_edges(self, ws):
        assert ws.current_graph.get_number_of_edges() == 4


# ── Original graph immutability ────────────────────────────────


class TestOriginalGraphImmutability:

    def test_original_graph_is_deep_copy(self, ws):
        """Modifying the returned original_graph should not affect workspace."""
        orig = ws.original_graph
        orig.remove_node("n1")
        assert ws.original_graph.get_node("n1") is not None

    def test_original_graph_unchanged_after_filter(self, ws):
        ws.apply_filter("Age >= 30")
        orig = ws.original_graph
        assert orig.get_number_of_nodes() == 5

    def test_current_graph_is_not_original(self, ws):
        """current_graph and original_graph are independent objects."""
        ws.apply_filter("Age >= 30")
        assert ws.current_graph.get_number_of_nodes() < ws.original_graph.get_number_of_nodes()


# ── Filter ─────────────────────────────────────────────────────


class TestFilter:

    def test_filter_reduces_nodes(self, ws):
        result = ws.apply_filter("Age >= 30")
        assert result.get_number_of_nodes() == 2  # Alice(30), Carol(35)

    def test_filter_returns_current_graph(self, ws):
        result = ws.apply_filter("Age >= 30")
        assert result is ws.current_graph

    def test_filter_preserves_only_matching_edges(self, ws):
        result = ws.apply_filter("City == Paris")
        # Paris: n1(Alice), n3(Carol) — no direct edge between them
        # e1 connects n1-n2 (London), e2 connects n2-n3 (London)
        # So no edges should survive if only Paris nodes remain
        for edge in result.get_all_edges():
            assert edge.source_node.node_id in result.nodes
            assert edge.target_node.node_id in result.nodes


# ── Search ─────────────────────────────────────────────────────


class TestSearch:

    def test_search_by_attribute_name(self, ws):
        result = ws.apply_search("Name")
        # All nodes have Name
        assert result.get_number_of_nodes() == 5

    def test_search_by_value(self, ws):
        result = ws.apply_search("Name=Alice")
        assert result.get_number_of_nodes() == 1
        assert result.get_node("n1") is not None

    def test_search_no_match(self, ws):
        result = ws.apply_search("Name=Nobody")
        assert result.get_number_of_nodes() == 0


# ── Successive operations ────────────────────────────────────────


class TestSuccessiveOperations:

    def test_filter_then_search(self, ws):
        """Filter → Search on the filtered subgraph."""
        ws.apply_filter("Age >= 25")  # n1(30), n2(25), n3(35), n4(28)
        result = ws.apply_search("City=Paris")  # n1, n3
        assert set(result.nodes.keys()) == {"n1", "n3"}

    def test_search_then_filter(self, ws):
        """Search → Filter on the search result."""
        ws.apply_search("City")  # all 5
        result = ws.apply_filter("Age > 28")  # n1(30), n3(35)
        assert set(result.nodes.keys()) == {"n1", "n3"}

    def test_multiple_filters(self, ws):
        ws.apply_filter("Age >= 25")  # 4 nodes
        result = ws.apply_filter("Age <= 30")  # n1(30), n2(25), n4(28)
        assert result.get_number_of_nodes() == 3


# ── Undo ──────────────────────────────────────────────────────────


class TestUndo:

    def test_undo_restores_previous_graph(self, ws):
        ws.apply_filter("Age >= 30")
        assert ws.current_graph.get_number_of_nodes() == 2
        result = ws.undo()
        assert result is not None
        assert result.get_number_of_nodes() == 5

    def test_undo_on_empty_history_returns_none(self, ws):
        result = ws.undo()
        assert result is None

    def test_undo_decrements_history_depth(self, ws):
        ws.apply_filter("Age >= 30")
        assert ws.history_depth == 1
        ws.undo()
        assert ws.history_depth == 0

    def test_multiple_undos(self, ws):
        ws.apply_filter("Age >= 25")   # history: 1
        ws.apply_filter("Age <= 30")   # history: 2
        ws.apply_search("Name=Bob")    # history: 3

        ws.undo()
        assert ws.history_depth == 2
        ws.undo()
        assert ws.history_depth == 1
        ws.undo()
        assert ws.history_depth == 0
        assert ws.current_graph.get_number_of_nodes() == 5

    def test_undo_after_undo_returns_none(self, ws):
        ws.apply_filter("Age >= 30")
        ws.undo()
        result = ws.undo()
        assert result is None


# ── Reset ──────────────────────────────────────────────────────────


class TestReset:

    def test_reset_restores_original_graph(self, ws):
        ws.apply_filter("Age >= 30")
        ws.apply_search("Name=Carol")
        assert ws.current_graph.get_number_of_nodes() == 1

        result = ws.reset()
        assert result.get_number_of_nodes() == 5

    def test_reset_clears_history(self, ws):
        ws.apply_filter("Age >= 30")
        ws.apply_filter("Age <= 40")
        assert ws.history_depth == 2

        ws.reset()
        assert ws.history_depth == 0

    def test_reset_on_fresh_workspace(self, ws):
        """Reset on unmodified workspace should still work."""
        result = ws.reset()
        assert result.get_number_of_nodes() == 5


# ── History ──────────────────────────────────────────────────────────


class TestHistoryManagement:

    def test_history_depth_increments_on_filter(self, ws):
        assert ws.history_depth == 0
        ws.apply_filter("Age >= 30")
        assert ws.history_depth == 1

    def test_history_depth_increments_on_search(self, ws):
        ws.apply_search("Name")
        assert ws.history_depth == 1

    def test_max_history_overflow_drops_oldest(self):
        """When max_history is exceeded, oldest snapshot is dropped."""
        ws = Workspace(_build_ws_graph(), max_history=3)

        ws.apply_filter("Age >= 20")  # 1
        ws.apply_filter("Age >= 21")  # 2
        ws.apply_filter("Age >= 22")  # 3
        assert ws.history_depth == 3

        ws.apply_filter("Age >= 23")  # 4 → oldest (original) dropped
        assert ws.history_depth == 3  # capped at max

    def test_after_max_overflow_undo_still_works(self):
        ws = Workspace(_build_ws_graph(), max_history=2)
        ws.apply_filter("Age >= 20")
        ws.apply_filter("Age >= 25")
        ws.apply_filter("Age >= 30")
        # Only 2 snapshots kept
        assert ws.history_depth == 2
        ws.undo()
        assert ws.history_depth == 1


# ── To dictionary ──────────────────────────────────────────────────────────


class TestToDict:

    def test_to_dict_keys(self, ws):
        d = ws.to_dict()
        expected_keys = {"workspace_id", "name", "data_source", "file_path",
                         "nodes", "edges", "history_depth"}
        assert expected_keys == set(d.keys())

    def test_to_dict_values(self, ws):
        d = ws.to_dict()
        assert d["name"] == "Test WS"
        assert d["data_source"] == "json"
        assert d["file_path"] == "/tmp/test.json"
        assert d["nodes"] == 5
        assert d["edges"] == 4
        assert d["history_depth"] == 0

    def test_to_dict_after_filter(self, ws):
        ws.apply_filter("Age >= 30")
        d = ws.to_dict()
        assert d["nodes"] == 2
        assert d["history_depth"] == 1

    def test_to_dict_workspace_id_matches(self, ws):
        d = ws.to_dict()
        assert d["workspace_id"] == ws.workspace_id


# ── Repr ──────────────────────────────────────────────────────────


class TestRepr:

    def test_repr_contains_key_info(self, ws):
        r = repr(ws)
        assert "Test WS" in r
        assert "json" in r
