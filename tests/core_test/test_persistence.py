# tests/core_test/test_persistence.py
"""
Tests for workspace persistence — save / load round-trip.

Covers:
    • Workspace.save() writes a valid JSON file
    • Workspace.load() restores all metadata and graph data
    • Round-trip: save → load preserves workspace identity
    • History is preserved across save/load
    • GraphPlatform.save_workspace / load_workspace integration
    • Load after filter preserves filtered state
"""
import json
import os
import pytest
from datetime import date

from api.models.graph import Graph
from api.models.node import Node
from api.models.edge import Edge, EdgeDirection

from graph_platform.workspace import Workspace
from graph_platform.core import GraphPlatform
from graph_platform.config import PlatformConfig


# ── Concrete Node ────────────────────────────────────────────────

class _PersistNode(Node):
    """Concrete Node for persistence tests."""
    pass


# ── Helpers ──────────────────────────────────────────────────────

def _build_graph() -> Graph:
    g = Graph("persist_test")
    n1 = _PersistNode("n1", Name="Alice", Age=30, City="Paris", Born=date(1994, 3, 12))
    n2 = _PersistNode("n2", Name="Bob", Age=25, City="London", Born=date(1999, 7, 15))
    n3 = _PersistNode("n3", Name="Carol", Age=35, City="Berlin", Born=date(1989, 1, 20))
    for n in [n1, n2, n3]:
        g.add_node(n)
    g.add_edge(Edge("e1", n1, n2, EdgeDirection.DIRECTED, Relation="friend", Weight=0.9))
    g.add_edge(Edge("e2", n2, n3, EdgeDirection.UNDIRECTED, Relation="colleague", Weight=0.7))
    return g


# ═════════════════════════════════════════════════════════════════
#  WORKSPACE SAVE
# ═════════════════════════════════════════════════════════════════

class TestWorkspaceSave:

    def test_save_creates_file(self, tmp_path):
        ws = Workspace(_build_graph(), data_source="json", name="SaveTest")
        file_path = ws.save(str(tmp_path))
        assert os.path.isfile(file_path)

    def test_save_file_is_valid_json(self, tmp_path):
        ws = Workspace(_build_graph(), name="JsonTest")
        file_path = ws.save(str(tmp_path))
        with open(file_path, 'r') as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_save_contains_metadata(self, tmp_path):
        ws = Workspace(_build_graph(), data_source="json", file_path="/test.json", name="MetaTest")
        file_path = ws.save(str(tmp_path))
        with open(file_path, 'r') as f:
            data = json.load(f)
        assert data["workspace_id"] == ws.workspace_id
        assert data["name"] == "MetaTest"
        assert data["data_source"] == "json"
        assert data["file_path"] == "/test.json"

    def test_save_contains_graphs(self, tmp_path):
        ws = Workspace(_build_graph(), name="GraphTest")
        file_path = ws.save(str(tmp_path))
        with open(file_path, 'r') as f:
            data = json.load(f)
        assert "original_graph" in data
        assert "current_graph" in data
        assert len(data["original_graph"]["nodes"]) == 3

    def test_save_creates_directory(self, tmp_path):
        nested_dir = str(tmp_path / "a" / "b" / "c")
        ws = Workspace(_build_graph(), name="DirTest")
        file_path = ws.save(nested_dir)
        assert os.path.isfile(file_path)


# ═════════════════════════════════════════════════════════════════
#  WORKSPACE LOAD
# ═════════════════════════════════════════════════════════════════

class TestWorkspaceLoad:

    def test_load_restores_workspace_id(self, tmp_path):
        ws1 = Workspace(_build_graph(), name="IDTest")
        file_path = ws1.save(str(tmp_path))
        ws2 = Workspace.load(file_path)
        assert ws2.workspace_id == ws1.workspace_id

    def test_load_restores_name(self, tmp_path):
        ws1 = Workspace(_build_graph(), name="NameTest")
        file_path = ws1.save(str(tmp_path))
        ws2 = Workspace.load(file_path)
        assert ws2.name == "NameTest"

    def test_load_restores_data_source(self, tmp_path):
        ws1 = Workspace(_build_graph(), data_source="xml")
        file_path = ws1.save(str(tmp_path))
        ws2 = Workspace.load(file_path)
        assert ws2.data_source == "xml"

    def test_load_restores_file_path(self, tmp_path):
        ws1 = Workspace(_build_graph(), file_path="/data/test.json")
        file_path = ws1.save(str(tmp_path))
        ws2 = Workspace.load(file_path)
        assert ws2.file_path == "/data/test.json"

    def test_load_restores_node_count(self, tmp_path):
        ws1 = Workspace(_build_graph())
        file_path = ws1.save(str(tmp_path))
        ws2 = Workspace.load(file_path)
        assert ws2.current_graph.get_number_of_nodes() == 3

    def test_load_restores_edge_count(self, tmp_path):
        ws1 = Workspace(_build_graph())
        file_path = ws1.save(str(tmp_path))
        ws2 = Workspace.load(file_path)
        assert ws2.current_graph.get_number_of_edges() == 2

    def test_load_restores_node_attributes(self, tmp_path):
        ws1 = Workspace(_build_graph())
        file_path = ws1.save(str(tmp_path))
        ws2 = Workspace.load(file_path)
        n1 = ws2.current_graph.get_node("n1")
        assert n1 is not None
        assert n1.get_attribute("Name") == "Alice"
        assert n1.get_attribute("Age") == 30

    def test_load_restores_date_attributes(self, tmp_path):
        ws1 = Workspace(_build_graph())
        file_path = ws1.save(str(tmp_path))
        ws2 = Workspace.load(file_path)
        n1 = ws2.current_graph.get_node("n1")
        assert n1 is not None
        assert n1.get_attribute("Born") == date(1994, 3, 12)

    def test_load_restores_edge_direction(self, tmp_path):
        ws1 = Workspace(_build_graph())
        file_path = ws1.save(str(tmp_path))
        ws2 = Workspace.load(file_path)
        e1 = ws2.current_graph.get_edge("e1")
        e2 = ws2.current_graph.get_edge("e2")
        assert e1 is not None
        assert e2 is not None
        assert e1.is_directed() is True
        assert e2.is_directed() is False


# ═════════════════════════════════════════════════════════════════
#  ROUND-TRIP
# ═════════════════════════════════════════════════════════════════

class TestRoundTrip:

    def test_round_trip_preserves_original_graph(self, tmp_path):
        ws1 = Workspace(_build_graph())
        ws1.apply_filter("Age >= 30")  # Modify current but original stays
        file_path = ws1.save(str(tmp_path))
        ws2 = Workspace.load(file_path)
        # Original should have all 3 nodes
        assert ws2.original_graph.get_number_of_nodes() == 3

    def test_round_trip_preserves_filtered_state(self, tmp_path):
        ws1 = Workspace(_build_graph())
        ws1.apply_filter("Age >= 30")
        file_path = ws1.save(str(tmp_path))
        ws2 = Workspace.load(file_path)
        # Current should have filtered nodes (Alice=30, Carol=35)
        assert ws2.current_graph.get_number_of_nodes() == 2

    def test_round_trip_preserves_history(self, tmp_path):
        ws1 = Workspace(_build_graph(), max_history=5)
        ws1.apply_filter("Age >= 25")  # history: 1
        ws1.apply_filter("Age >= 30")  # history: 2
        file_path = ws1.save(str(tmp_path))
        ws2 = Workspace.load(file_path)
        assert ws2.history_depth == 2

    def test_loaded_workspace_can_undo(self, tmp_path):
        ws1 = Workspace(_build_graph())
        ws1.apply_filter("Age >= 30")
        file_path = ws1.save(str(tmp_path))
        ws2 = Workspace.load(file_path)
        result = ws2.undo()
        assert result is not None
        assert result.get_number_of_nodes() == 3

    def test_loaded_workspace_can_filter(self, tmp_path):
        ws1 = Workspace(_build_graph())
        file_path = ws1.save(str(tmp_path))
        ws2 = Workspace.load(file_path)
        result = ws2.apply_filter("Age >= 30")
        assert result.get_number_of_nodes() == 2

    def test_loaded_workspace_can_reset(self, tmp_path):
        ws1 = Workspace(_build_graph())
        ws1.apply_filter("Age >= 30")
        file_path = ws1.save(str(tmp_path))
        ws2 = Workspace.load(file_path)
        result = ws2.reset()
        assert result.get_number_of_nodes() == 3


# ═════════════════════════════════════════════════════════════════
#  PLATFORM INTEGRATION
# ═════════════════════════════════════════════════════════════════

class TestPlatformPersistence:

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        GraphPlatform.reset_instance()
        yield
        GraphPlatform.reset_instance()

    def test_save_workspace_via_platform(self, tmp_path):
        platform = GraphPlatform(PlatformConfig())
        platform.create_workspace(_build_graph(), name="SaveWS")
        file_path = platform.save_workspace(str(tmp_path))
        assert os.path.isfile(file_path)

    def test_load_workspace_via_platform(self, tmp_path):
        platform = GraphPlatform(PlatformConfig())
        ws1 = platform.create_workspace(_build_graph(), name="LoadWS")
        file_path = platform.save_workspace(str(tmp_path))

        # Create a new platform to simulate restart
        platform2 = GraphPlatform(PlatformConfig())
        ws2 = platform2.load_workspace(file_path)

        assert ws2.workspace_id == ws1.workspace_id
        assert ws2.name == "LoadWS"
        assert ws2.current_graph.get_number_of_nodes() == 3
        assert platform2.get_active_workspace() is ws2

    def test_load_workspace_fires_event(self, tmp_path):
        platform = GraphPlatform(PlatformConfig())
        ws1 = platform.create_workspace(_build_graph())
        file_path = platform.save_workspace(str(tmp_path))

        events = []
        platform2 = GraphPlatform(PlatformConfig())
        platform2.subscribe("workspace_created", lambda **kw: events.append(kw))
        platform2.load_workspace(file_path)
        assert len(events) == 1
