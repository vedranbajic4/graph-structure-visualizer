import json
import uuid
from typing import Any, Dict, List, Optional, Set

from api.plugins import DataSourcePlugin
from api.models.graph import Graph
from api.models.edge import Edge, EdgeDirection
from api.models.node import Node


class JSONNode(Node):
    """Concrete Node implementation for JSON-sourced data."""
    pass


class JsonDataSourcePlugin(DataSourcePlugin):

    def get_plugin_name(self) -> str:
        return "JSON Parser"

    def parse(self, file_path: str) -> Graph:
        with open(file_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        graph = Graph(graph_id=file_path)

        # Two-pass approach so forward @id references resolve correctly
        id_registry: Dict[str, Any] = {}
        roots = data if isinstance(data, list) else [data]
        for root in roots:
            self._collect_ids(root, id_registry)

        visited: Set[str] = set()
        edge_counter = [0]
        for root in roots:
            self._parse_object(
                obj=root,
                graph=graph,
                id_registry=id_registry,
                visited=visited,
                edge_counter=edge_counter,
                parent_node=None,
                edge_label=None,
            )

        return graph

    # ── pass 1: collect all @id values ───────────────────────────────────────

    def _collect_ids(self, obj: Any, registry: Dict[str, Any]) -> None:
        if isinstance(obj, dict):
            node_id = obj.get("@id")
            if node_id is not None:
                registry[str(node_id)] = obj
            for value in obj.values():
                self._collect_ids(value, registry)
        elif isinstance(obj, list):
            for item in obj:
                self._collect_ids(item, registry)

    # ── pass 2: build nodes and edges ────────────────────────────────────────

    def _parse_object(
        self,
        obj: Any,
        graph: Graph,
        id_registry: Dict[str, Any],
        visited: Set[str],
        edge_counter: List[int],
        parent_node: Optional[JSONNode],
        edge_label: Optional[str],
    ) -> Optional[JSONNode]:
        """
        Recursively turn a JSON object into a node, connect it to its parent,
        then recurse into nested objects.  Returns the created JSONNode.
        """
        if not isinstance(obj, dict):
            return None

        # Determine node ID
        raw_id = obj.get("@id")
        node_id = str(raw_id) if raw_id is not None else f"node_{uuid.uuid4().hex[:8]}"

        # Retrieve existing node or create a new one
        current_node = graph.get_node(node_id)
        if current_node is None:
            scalar_attrs = self._extract_scalars(obj, id_registry)
            current_node = JSONNode(node_id, **scalar_attrs)
            graph.add_node(current_node)

        # Connect to parent
        if parent_node is not None and edge_label is not None:
            self._add_edge(graph, edge_counter, parent_node, current_node, edge_label)

        # Guard against infinite recursion on cycles
        if node_id in visited:
            return current_node
        visited.add(node_id)

        # Recurse into nested objects and handle reference strings
        for key, value in obj.items():
            if key == "@id":
                continue

            if isinstance(value, dict):
                # Nested object → child node
                self._parse_object(value, graph, id_registry, visited,
                                   edge_counter, current_node, key)

            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        self._parse_object(item, graph, id_registry, visited,
                                           edge_counter, current_node, key)
                    elif isinstance(item, str) and item in id_registry:
                        target = self._resolve_reference(
                            item, graph, id_registry, visited, edge_counter)
                        if target is not None:
                            self._add_edge(graph, edge_counter, current_node, target, key)

            elif isinstance(value, str) and value in id_registry:
                # String reference to another @id → edge, not attribute
                target = self._resolve_reference(
                    value, graph, id_registry, visited, edge_counter)
                if target is not None:
                    self._add_edge(graph, edge_counter, current_node, target, key)

        return current_node

    def _resolve_reference(
        self,
        ref_id: str,
        graph: Graph,
        id_registry: Dict[str, Any],
        visited: Set[str],
        edge_counter: List[int],
    ) -> Optional[JSONNode]:
        """Return the node for ref_id, creating it first if necessary."""
        node = graph.get_node(ref_id)
        if node is None:
            node = self._parse_object(
                obj=id_registry[ref_id],
                graph=graph,
                id_registry=id_registry,
                visited=visited,
                edge_counter=edge_counter,
                parent_node=None,
                edge_label=None,
            )
        return node

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_scalars(obj: dict, id_registry: Dict[str, Any]) -> dict:
        """
        Pull out scalar key/value pairs from a JSON object.
        Skips: "@id", nested dicts, lists, and strings that are @id references.
        """
        attrs = {}
        for key, value in obj.items():
            if key == "@id":
                continue
            if isinstance(value, (dict, list)):
                continue
            if isinstance(value, str) and value in id_registry:
                continue  # reference → becomes an edge, not an attribute
            attrs[key] = value
        return attrs

    @staticmethod
    def _add_edge(
        graph: Graph,
        edge_counter: List[int],
        source: JSONNode,
        target: JSONNode,
        label: str,
    ) -> None:
        """Add a directed edge, skipping exact duplicates."""
        # Avoid duplicate edges (can happen when a cycle is first resolved)
        for existing in graph.get_outgoing_edges(source):
            if (existing.target_node.node_id == target.node_id
                    and existing.get_attribute("label") == label):
                return

        eid = f"e{edge_counter[0]}_{label}"
        edge_counter[0] += 1
        graph.add_edge(Edge(
            edge_id=eid,
            source_node=source,
            target_node=target,
            direction=EdgeDirection.DIRECTED,
            label=label,
        ))
def print_test_data():
    plugin = JsonDataSourcePlugin()
    graph = plugin.parse("tests/plugin_test/fixtures/json_graph1.json")

    print(f"Plugin: {plugin.get_plugin_name()}")
    print(repr(graph))
    print()

    print(f"=== NODES ({graph.get_number_of_nodes()}) ===")
    for node in graph.get_all_nodes():
        print(f"  ID    : {node.node_id}")
        print(f"  Attrs : {node.get_all_attributes()}")
        print()

    print(f"=== EDGES ({graph.get_number_of_edges()}) ===")
    for edge in graph.get_all_edges():
        print(f"  {edge.source_node.node_id}  --[{edge.get_attribute('label')}]-->  {edge.target_node.node_id}")
        print(f"  ID       : {edge.edge_id}")
        print(f"  Direction: {edge.direction.value}")
        print()

if __name__ == '__main__':
    print_test_data()
    pass