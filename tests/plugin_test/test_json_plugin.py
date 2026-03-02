import json
import pytest
from datetime import date, datetime
from pathlib import Path

from api.models.graph import Graph
from api.models.edge import EdgeDirection
from api.plugins.base import DataSourcePlugin

from data_source_plugin_json.plugin import JsonDataSourcePlugin, JSONNode

FIXTURES_DIR     = Path(__file__).parent / "fixtures"
GRAPH_PATH       = FIXTURES_DIR / "json_graph1.json"
CYCLIC_PATH      = FIXTURES_DIR / "json_cyclic1.json"


@pytest.fixture
def plugin():
    return JsonDataSourcePlugin()

@pytest.fixture
def graph(plugin):
    return plugin.parse(str(GRAPH_PATH))

@pytest.fixture
def cyclic_graph(plugin):
    return plugin.parse(str(CYCLIC_PATH))


# ── Plugin metadata ───────────────────────────────────────────────────────────

class TestPluginMetadata:
    def test_plugin_name(self, plugin):
        assert plugin.get_plugin_name() == "JSON Parser"

    def test_is_data_source_plugin(self, plugin):
        assert isinstance(plugin, DataSourcePlugin)


# ── Graph structure ───────────────────────────────────────────────────────────

class TestGraphStructure:
    def test_returns_graph_instance(self, graph):
        assert isinstance(graph, Graph)

    def test_graph_id_is_file_path(self, graph):
        assert graph.graph_id == str(GRAPH_PATH)

    def test_node_count(self, graph):
        # alice, techcorp, skill_python, skill_docker, bob, carol
        assert graph.get_number_of_nodes() == 6

    def test_edge_count(self, graph):
        # see fixture for full list
        assert graph.get_number_of_edges() == 10

    def test_all_nodes_are_jsonnode_instances(self, graph):
        for node in graph.get_all_nodes():
            assert isinstance(node, JSONNode)


# ── Node parsing ──────────────────────────────────────────────────────────────

class TestNodeParsing:
    def test_all_node_ids_present(self, graph):
        ids = {n.node_id for n in graph.get_all_nodes()}
        assert ids == {"alice", "bob", "carol", "techcorp", "skill_python", "skill_docker"}

    def test_string_attribute(self, graph):
        assert graph.get_node("alice").get_attribute("name") == "Alice"
        assert graph.get_node("alice").get_attribute("role") == "Engineer"

    def test_int_attribute(self, graph):
        salary = graph.get_node("alice").get_attribute("salary")
        assert salary == 85000
        assert isinstance(salary, int)

    def test_float_attribute(self, graph):
        rating = graph.get_node("alice").get_attribute("rating")
        assert isinstance(rating, float)
        assert rating == pytest.approx(4.7)

    def test_bool_attribute(self, graph):
        assert graph.get_node("alice").get_attribute("active") is True

    def test_date_attribute(self, graph):
        hire = graph.get_node("alice").get_attribute("hire_date")
        assert isinstance(hire, (date, datetime))

    def test_at_id_not_stored_as_attribute(self, graph):
        for node in graph.get_all_nodes():
            assert "@id" not in node.get_all_attributes()

    def test_reference_string_not_stored_as_attribute(self, graph):
        # bob.knows = "alice" is a reference -> edge, not stored as attr
        assert graph.get_node("bob").get_attribute("knows") is None

    def test_nested_object_scalars_on_own_node(self, graph):
        tc = graph.get_node("techcorp")
        assert tc.get_attribute("name") == "TechCorp"
        assert tc.get_attribute("founded") == 1998


# ── Edge parsing ──────────────────────────────────────────────────────────────

class TestEdgeParsing:
    def _find(self, graph, src, tgt, label=None):
        for e in graph.get_all_edges():
            if e.source_node.node_id == src and e.target_node.node_id == tgt:
                if label is None or e.get_attribute("label") == label:
                    return e
        return None

    def test_nested_object_creates_edge(self, graph):
        # alice.employer = {…techcorp…} -> edge alice→techcorp labeled "employer"
        assert self._find(graph, "alice", "techcorp", "employer") is not None

    def test_array_of_objects_creates_edges(self, graph):
        # alice.skills = [{skill_python}, {skill_docker}]
        assert self._find(graph, "alice", "skill_python", "skills") is not None
        assert self._find(graph, "alice", "skill_docker", "skills") is not None

    def test_string_reference_creates_edge(self, graph):
        # bob.knows = "alice"  (alice is a known @id)
        assert self._find(graph, "bob", "knows", "alice") is not None \
            or self._find(graph, "bob", "alice", "knows") is not None

    def test_array_of_references_creates_edges(self, graph):
        # carol.manages = ["alice", "bob"]
        assert self._find(graph, "carol", "alice", "manages") is not None
        assert self._find(graph, "carol", "bob",   "manages") is not None

    def test_shared_target_node_not_duplicated(self, graph):
        # Both alice and bob and carol point to techcorp -> still only 1 techcorp node
        assert graph.get_number_of_nodes() == 6

    def test_all_edges_are_directed(self, graph):
        for e in graph.get_all_edges():
            assert e.direction == EdgeDirection.DIRECTED

    def test_graph_has_cycle(self, graph):
        # alice→bob (colleagues), bob -> alice (knows) forms a cycle
        assert graph.has_cycle() is True


# ── Cyclic fixture ────────────────────────────────────────────

class TestCyclicFormat:
    def test_node_count(self, cyclic_graph):
        assert cyclic_graph.get_number_of_nodes() == 3

    def test_edge_count(self, cyclic_graph):
        assert cyclic_graph.get_number_of_edges() == 5

    def test_back_reference_creates_edge(self, cyclic_graph):
        back = [e for e in cyclic_graph.get_all_edges()
                if e.target_node.node_id == "parent-001"]
        assert len(back) == 2

    def test_is_cyclic(self, cyclic_graph):
        assert cyclic_graph.has_cycle() is True


# ── Works with any JSON shape ─────────────────────────────────────────────────

class TestArbitraryJSON:
    def test_plain_object_no_at_id(self, plugin, tmp_path):
        # No @id at all - object still becomes a node with an auto-generated id
        data = {"name": "Alice", "age": 30}
        p = tmp_path / "f.json"
        p.write_text(json.dumps(data))
        g = plugin.parse(str(p))
        assert g.get_number_of_nodes() == 1
        node = g.get_all_nodes()[0]
        assert node.get_attribute("name") == "Alice"
        assert node.get_attribute("age") == 30

    def test_root_array(self, plugin, tmp_path):
        # Root is a list of objects - each becomes a node
        data = [{"@id": "x", "val": 1}, {"@id": "y", "val": 2}]
        p = tmp_path / "f.json"
        p.write_text(json.dumps(data))
        g = plugin.parse(str(p))
        assert g.get_number_of_nodes() == 2
        assert g.get_node("x").get_attribute("val") == 1
        assert g.get_node("y").get_attribute("val") == 2

    def test_deeply_nested(self, plugin, tmp_path):
        data = {"@id": "a", "child": {"@id": "b", "child": {"@id": "c", "leaf": True}}}
        p = tmp_path / "f.json"
        p.write_text(json.dumps(data))
        g = plugin.parse(str(p))
        assert g.get_number_of_nodes() == 3
        assert g.get_number_of_edges() == 2

    def test_empty_object(self, plugin, tmp_path):
        p = tmp_path / "f.json"
        p.write_text("{}")
        g = plugin.parse(str(p))
        assert g.get_number_of_nodes() == 1

    def test_empty_array(self, plugin, tmp_path):
        p = tmp_path / "f.json"
        p.write_text("[]")
        g = plugin.parse(str(p))
        assert g.get_number_of_nodes() == 0


# ── Error handling ────────────────────────────────────────────────────────────

class TestErrorHandling:
    def test_missing_file_raises(self, plugin):
        with pytest.raises(FileNotFoundError):
            plugin.parse("nonexistent/path/file.json")

    def test_invalid_json_raises(self, plugin, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{not valid json")
        with pytest.raises(json.JSONDecodeError):
            plugin.parse(str(p))