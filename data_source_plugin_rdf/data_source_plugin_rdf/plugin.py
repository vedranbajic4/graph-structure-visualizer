from rdflib import Graph as RDFGraph, URIRef, Literal
from rdflib.namespace import RDF


from api.plugins import DataSourcePlugin

from api.models.graph import Graph
from api.models.edge import Edge, EdgeDirection
from api.models.node import Node

class RDFNode(Node):
    """Concrete Node implementation for RDF-sourced data."""
    pass


class RDFTurtleDataSourcePlugin(DataSourcePlugin):
    """
    DataSourcePlugin for RDF Turtle (.ttl) files.
    Parses RDF triples into a Graph with RDFNode and Edge instances.
    """

    def get_plugin_name(self) -> str:
        return "RDF Turtle Parser"

    def parse(self, file_path: str) -> Graph:
        rdf_graph = RDFGraph()
        rdf_graph.parse(file_path, format="turtle")

        graph = Graph(graph_id=file_path)

        # --- Pass 1: collect all URI subjects and objects as nodes ---
        node_uris: set[str] = set()
        for subject, predicate, obj in rdf_graph:
            if isinstance(subject, URIRef):
                node_uris.add(str(subject))
            if isinstance(obj, URIRef) and predicate != RDF.type:
                node_uris.add(str(obj))

        for uri in node_uris:
            label = self._local_name(uri)
            literal_attrs = self._extract_literal_attributes(rdf_graph, URIRef(uri))
            node = RDFNode(node_id=uri, label=label, **literal_attrs)
            graph.add_node(node)

        # --- Pass 2: URI-object triples (excluding rdf:type) become edges ---
        edge_counter = 0
        for subject, predicate, obj in rdf_graph:
            if isinstance(subject, URIRef) and isinstance(obj, URIRef):
                if predicate == RDF.type:
                    continue

                source_node = graph.get_node(str(subject))
                target_node = graph.get_node(str(obj))

                if source_node is None or target_node is None:
                    continue

                edge_id = f"e{edge_counter}_{self._local_name(str(predicate))}"
                edge = Edge(
                    edge_id=edge_id,
                    source_node=source_node,
                    target_node=target_node,
                    direction=EdgeDirection.DIRECTED,
                    predicate=str(predicate),
                    label=self._local_name(str(predicate))
                )
                graph.add_edge(edge)
                edge_counter += 1

        return graph

    def _local_name(self, uri: str) -> str:
        """Extract the local fragment from a URI (after # or last /)."""
        if "#" in uri:
            return uri.split("#")[-1]
        return uri.rstrip("/").split("/")[-1]

    def _extract_literal_attributes(self, rdf_graph: RDFGraph, uri: URIRef) -> dict:
        """Collect all Literal property values for a URI as a flat dict."""
        attributes = {}
        for predicate, obj in rdf_graph.predicate_objects(uri):
            if isinstance(obj, Literal):
                key = self._local_name(str(predicate))
                attributes[key] = str(obj)
        return attributes


def print_test_data():
    plugin = RDFTurtleDataSourcePlugin()
    graph = plugin.parse("../../tests/plugin_test/fixtures/simple_graph1.ttl")

    print(f"Plugin: {plugin.get_plugin_name()}")
    print(repr(graph))
    print()

    print(f"=== NODES ({graph.get_number_of_nodes()}) ===")
    for node in graph.get_all_nodes():
        print(f"  ID    : {node.node_id}")
        print(f"  Label : {node.get_attribute('label')}")
        print(f"  Attrs : {node.get_all_attributes()}")
        print()

    print(f"=== EDGES ({graph.get_number_of_edges()}) ===")
    for edge in graph.get_all_edges():
        src_label = edge.source_node.get_attribute('label')
        tgt_label = edge.target_node.get_attribute('label')
        rel_label = edge.get_attribute('label')
        print(f"  {src_label}  --[{rel_label}]-->  {tgt_label}")
        print(f"  ID       : {edge.edge_id}")
        print(f"  Predicate: {edge.get_attribute('predicate')}")
        print(f"  Direction: {edge.direction.value}")
        print()

if __name__ == '__main__':
    # print_test_data()
    pass
