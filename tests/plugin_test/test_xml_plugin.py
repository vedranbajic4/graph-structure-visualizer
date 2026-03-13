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
    return plugin.parse(file_path=str(sample_xml_path))


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
        # Per SPECS §2.2: "Tagove koji nemaju decu, posmatrati samo kao atribute"
        # (leaf tags without children are stored as attributes on parent node)
        # Nodes: Graph[1], Person[1..4], Organization[1] = 6
        # Plus Person[2]:name (has lang attribute so becomes separate node) = 1
        # Total = 7
        assert parsed_graph.get_number_of_nodes() == 7

    def test_correct_edge_count(self, parsed_graph):
        # Child edges (Graph→Persons + Graph→Org) = 5
        # Relation edges (knows + 2x works_for + 2x manages) = 5
        # Attribute edge (Person[2]→Person[2]:name) = 1
        # Total = 11
        assert parsed_graph.get_number_of_edges() == 11

    def test_graph_id_is_file_path(self, parsed_graph, sample_xml_path):
        assert parsed_graph.graph_id == str(sample_xml_path)


class TestNodeParsing:
    def test_element_nodes_present(self, parsed_graph: Graph):
        expected = {"Person[1]", "Person[2]", "Person[3]", "Person[4]", "Organization[1]"}
        actual = {n.node_id for n in parsed_graph.get_all_nodes()}

        # subset because of attr nodes
        assert expected.issubset(actual)

    def test_attribute_nodes_exist_and_have_values(self, parsed_graph: Graph):
        # Per SPECS §2.2: leaf elements without XML attributes become node attributes
        # Person[1] has name/role as attributes (no separate nodes)
        person1 = parsed_graph.get_node("Person[1]")
        assert person1 is not None
        assert person1.attributes.get('name') == "Alice"
        assert person1.attributes.get('role') == "Engineer"

        # Organization name is also an attribute
        org = parsed_graph.get_node("Organization[1]")
        assert org.attributes.get('name') == "TechCorp"

        # Person[2]:name is a separate node because <name lang="en">Bob</name> has XML attribute
        name_node = parsed_graph.get_node("Person[2]:name")
        assert name_node is not None
        assert name_node.attributes.get('value') == "Bob"
        assert name_node.attributes.get('lang') == "en"

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
        # Only Person[2]:name is a separate node (due to lang attribute)
        edge = self._find_edge(parsed_graph, "Person[2]", "Person[2]:name", "name")
        assert edge is not None

    def test_attr_edge_includes_element_attributes(self, parsed_graph: Graph):
        # Bob's <name lang="en"> - the lang attribute is stored on the node, not the edge
        node = parsed_graph.get_node("Person[2]:name")
        assert node is not None
        assert node.attributes.get('lang') == 'en'
        assert node.attributes.get('value') == 'Bob'



class TestErrorHandling:
    def test_missing_file_path_parameter_raises_value_error(self, plugin):
        with pytest.raises(ValueError, match="file_path"):
            plugin.parse()

    def test_invalid_file_path_raises(self, plugin):
        with pytest.raises(Exception):
            plugin.parse(file_path="nonexistent/path/file.xml")

    def test_empty_xml_file_raises_syntax_error(self, plugin, tmp_path):
        empty = tmp_path / "empty.xml"
        empty.write_text("")  # an empty file is not well-formed XML
        with pytest.raises(etree.XMLSyntaxError):
            plugin.parse(file_path=str(empty))