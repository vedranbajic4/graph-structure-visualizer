import pytest
from pathlib import Path
from lxml import etree

from api.models.graph import Graph, Node
from api.models.edge import EdgeDirection, Edge
from api.plugins.base import DataSourcePlugin

from data_source_plugin_xml.plugin import XmlDataSourcePlugin, XMLNode

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_XML_PATH = FIXTURES_DIR / "xml_graph1.xml"

@pytest.fixture
def plugin():
    return XmlDataSourcePlugin()

@pytest.fixture
def sample_xml_path():
    return SAMPLE_XML_PATH

@pytest.fixture
def parsed_graph(plugin, sample_xml_path):
    return plugin.parse(str(sample_xml_path))


# ── Plugin metadata ───────────────────────────────────────────────────────────

class TestPluginMetadata:
    def test_plugin_name(self, plugin):
        assert plugin.get_plugin_name() == "XML Parser"

    def test_plugin_is_data_source_plugin(self, plugin):
        assert isinstance(plugin, DataSourcePlugin)

# ── Graph structure ───────────────────────────────────────────────────────────

class TestGraphStructure:
    def test_returns_graph_instance(self, parsed_graph):
        assert isinstance(parsed_graph, Graph)

    def test_graph_id_is_file_path(self, parsed_graph, sample_xml_path):
        assert parsed_graph.graph_id == str(sample_xml_path)

    def test_correct_node_count(self, parsed_graph):
        # Nodes: Graph[1], Person[1..4], Organization[1] = 6
        # Attribute nodes (leaf elements): name+role for 4 persons = 8, plus name for org = 1 -> 9
        # total = 6 + 9 = 15
        assert parsed_graph.get_number_of_nodes() == 15

    def test_correct_edge_count(self, parsed_graph):
        # attr edges (9) + relation edges (10) = 19
        assert parsed_graph.get_number_of_edges() == 19

    def test_graph_id_is_file_path(self, parsed_graph, sample_xml_path):
        assert parsed_graph.graph_id == str(sample_xml_path)


class TestNodeParsing:
    def test_element_nodes_present(self, parsed_graph: Graph):
        expected = {"Person[1]", "Person[2]", "Person[3]", "Person[4]", "Organization[1]"}
        actual = {n.node_id for n in parsed_graph.get_all_nodes()}

        # subset because of attr nodes
        assert expected.issubset(actual)

    def test_attribute_nodes_exist_and_have_values(self, parsed_graph: Graph):
        # name node for Person[1]
        name_node = parsed_graph.get_node("Person[1]:name")
        assert name_node is not None
        assert name_node.attributes['value'] == "Alice"

        # role node for Person[1]
        role_node = parsed_graph.get_node("Person[1]:role")
        assert role_node is not None
        assert role_node.attributes['value'] == "Engineer"

        # organization name
        org_name_node = parsed_graph.get_node("Organization[1]:name")
        assert org_name_node.attributes['value'] == "TechCorp"

    def test_nodes_are_xmlnode_instances(self, parsed_graph):
        for node in parsed_graph.get_all_nodes():
            assert isinstance(node, XMLNode)


class TestEdgeParsing:
    def _find_edge(self, graph: Graph, src_id: Node, tgt_id: Node, relation: str) -> Edge:
        for edge in graph.get_all_edges():
            if edge.source_node.node_id == src_id and edge.target_node.node_id == tgt_id and edge.attributes['label'] == relation:
                return edge
        return None

    def test_knows_edge_alice_to_bob(self, parsed_graph):
        edge = self._find_edge(parsed_graph, "Person[1]", "Person[2]", "knows")
        assert edge is not None

    def test_works_for_alice_to_techcorp(self, parsed_graph):
        edge = self._find_edge(parsed_graph, "Person[1]", "Organization[1]", "works_for")
        assert edge is not None

    def test_manages_edges_carol(self, parsed_graph):
        e1 = self._find_edge(parsed_graph, "Person[3]", "Person[1]", "manages")
        e2 = self._find_edge(parsed_graph, "Person[3]", "Person[2]", "manages")
        assert e1 is not None and e2 is not None

    def test_attribute_edges_exist(self, parsed_graph):
        edge = self._find_edge(parsed_graph, "Person[1]", "Person[1]:name", "name")
        assert edge is not None

    def test_attr_edge_includes_element_attributes(self, parsed_graph: Graph):
        # I.e. Bob's <name lang="en"> should cause the attr edge Person[2] -> Person[2]:name to have 'lang' attribute
        edge = self._find_edge(parsed_graph, "Person[2]", "Person[2]:name", "name")
        assert edge is not None
        assert edge.attributes['lang'] == 'en'



class TestErrorHandling:
    def test_invalid_file_path_raises(self, plugin):
        with pytest.raises(Exception):
            plugin.parse("nonexistent/path/file.xml")

    def test_empty_xml_file_raises_syntax_error(self, plugin, tmp_path):
        empty = tmp_path / "empty.xml"
        empty.write_text("")  # an empty file is not well-formed XML
        with pytest.raises(etree.XMLSyntaxError):
            plugin.parse(str(empty))