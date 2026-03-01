import pytest
from pathlib import Path

from api.api.models.edge import EdgeDirection
from api.api.models.graph import Graph
from data_source_plugin_rdf.data_source_plugin_rdf.plugin import RDFTurtleDataSourcePlugin, RDFNode
from api.api.plugins.base import DataSourcePlugin


FIXTURES_DIR = Path(__file__).parent / "fixtures"

ALICE_URI = "http://example.org/graph#Alice"
BOB_URI   = "http://example.org/graph#Bob"
CAROL_URI = "http://example.org/graph#Carol"
DAVE_URI  = "http://example.org/graph#Dave"
CORP_URI  = "http://example.org/graph#TechCorp"


# ── Plugin metadata ───────────────────────────────────────────────────────────

class TestPluginMetadata:
    def test_plugin_name(self, plugin):
        assert plugin.get_plugin_name() == "RDF Turtle Parser"

    def test_plugin_is_data_source_plugin(self, plugin):
        assert isinstance(plugin, DataSourcePlugin)


# ── Graph structure ───────────────────────────────────────────────────────────

class TestGraphStructure:

    def test_returns_graph_instance(self, parsed_graph):
        assert isinstance(parsed_graph, Graph)

    def test_correct_node_count(self, parsed_graph):
        # Alice, Bob, Carol, Dave, TechCorp = 5 nodes
        assert parsed_graph.get_number_of_nodes() == 5

    def test_correct_edge_count(self, parsed_graph):
        # knows(Alice->Bob), knows(Alice->Dave), manages(Carol->Alice),
        # manages(Carol->Bob), works_for(Alice->TechCorp), works_for(Bob->TechCorp) = 6
        assert parsed_graph.get_number_of_edges() == 6

    def test_graph_id_is_file_path(self, parsed_graph, sample_ttl_path):
        assert parsed_graph.graph_id == sample_ttl_path


# ── Node parsing ──────────────────────────────────────────────────────────────

class TestNodeParsing:

    def test_all_expected_nodes_present(self, parsed_graph):
        expected_uris = {ALICE_URI, BOB_URI, CAROL_URI, DAVE_URI, CORP_URI}
        actual_ids = {node.node_id for node in parsed_graph.get_all_nodes()}
        assert expected_uris == actual_ids

    def test_nodes_are_rdf_node_instances(self, parsed_graph):
        for node in parsed_graph.get_all_nodes():
            assert isinstance(node, RDFNode)

    def test_node_label_is_local_name(self, parsed_graph):
        alice = parsed_graph.get_node(ALICE_URI)
        assert alice.get_attribute("label") == "Alice"

    def test_node_literal_attributes_extracted(self, parsed_graph):
        alice = parsed_graph.get_node(ALICE_URI)
        assert alice.get_attribute("name") == "Alice"
        assert alice.get_attribute("role") == "Engineer"

    def test_org_node_literal_attribute(self, parsed_graph):
        corp = parsed_graph.get_node(CORP_URI)
        assert corp.get_attribute("name") == "TechCorp"

    def test_rdf_type_not_stored_as_attribute_key_type(self, parsed_graph):
        # rdf:type triples should not create edges, but 'type' may appear
        # as literal if explicitly set — here it's not, so it must be absent
        alice = parsed_graph.get_node(ALICE_URI)
        assert alice.get_attribute("type") is None


# ── Edge parsing ──────────────────────────────────────────────────────────────

class TestEdgeParsing:

    def _find_edge(self, graph, source_uri, target_uri, label):
        """Helper: find an edge by source, target, and label attribute."""
        for edge in graph.get_all_edges():
            if (
                edge.source_node.node_id == source_uri
                and edge.target_node.node_id == target_uri
                and edge.get_attribute("label") == label
            ):
                return edge
        return None

    def test_knows_edge_alice_to_bob(self, parsed_graph):
        edge = self._find_edge(parsed_graph, ALICE_URI, BOB_URI, "knows")
        assert edge is not None

    def test_knows_edge_alice_to_dave(self, parsed_graph):
        edge = self._find_edge(parsed_graph, ALICE_URI, DAVE_URI, "knows")
        assert edge is not None

    def test_manages_edge_carol_to_alice(self, parsed_graph):
        edge = self._find_edge(parsed_graph, CAROL_URI, ALICE_URI, "manages")
        assert edge is not None

    def test_manages_edge_carol_to_bob(self, parsed_graph):
        edge = self._find_edge(parsed_graph, CAROL_URI, BOB_URI, "manages")
        assert edge is not None

    def test_works_for_alice_to_techcorp(self, parsed_graph):
        edge = self._find_edge(parsed_graph, ALICE_URI, CORP_URI, "works_for")
        assert edge is not None

    def test_works_for_bob_to_techcorp(self, parsed_graph):
        edge = self._find_edge(parsed_graph, BOB_URI, CORP_URI, "works_for")
        assert edge is not None

    def test_all_edges_are_directed(self, parsed_graph):
        for edge in parsed_graph.get_all_edges():
            assert edge.direction == EdgeDirection.DIRECTED

    def test_edges_have_label_attribute(self, parsed_graph):
        for edge in parsed_graph.get_all_edges():
            assert edge.get_attribute("label") is not None

    def test_edges_have_predicate_attribute(self, parsed_graph):
        for edge in parsed_graph.get_all_edges():
            assert edge.get_attribute("predicate") is not None

    def test_rdf_type_triples_not_parsed_as_edges(self, parsed_graph):
        # No edge should have label "type" since rdf:type is skipped
        for edge in parsed_graph.get_all_edges():
            assert edge.get_attribute("label") != "type"


# ── Error handling ────────────────────────────────────────────────────────────

class TestErrorHandling:
    def test_invalid_file_path_raises(self, plugin):
        with pytest.raises(Exception):
            plugin.parse("nonexistent/path/file.ttl")

    def test_empty_ttl_file_returns_empty_graph(self, plugin, tmp_path):
        empty_ttl = tmp_path / "empty.ttl"
        empty_ttl.write_text("")
        graph = plugin.parse(str(empty_ttl))
        assert graph.get_number_of_nodes() == 0
        assert graph.get_number_of_edges() == 0

    def test_ttl_with_only_literal_triples_has_no_edges(self, plugin, tmp_path):
        # Only literals — no URI objects — so no edges should be created
        ttl = tmp_path / "literals_only.ttl"
        ttl.write_text(
            '@prefix ex: <http://example.org/> .\n'
            'ex:Node1 ex:name "OnlyLiterals" .\n'
        )
        graph = plugin.parse(str(ttl))
        assert graph.get_number_of_edges() == 0
        assert graph.get_number_of_nodes() == 1
