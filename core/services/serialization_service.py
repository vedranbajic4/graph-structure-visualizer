"""
    Serialization and deserialization service for Graph models.

    Supports configurable field inclusion / exclusion via
    ``SerializationConfig``.

    Design Pattern: Strategy (serialization strategy is configurable)
    ─────────────────────────────────────────────────────────────────
    The ``SerializationConfig`` acts as a strategy that determines
    which fields are included and how dates are formatted.

    Also provides Factory Method for deserialization:
        Graph.from_dict  →  GraphSerializer.deserialize
"""
import json
from copy import deepcopy
from datetime import date, datetime
from typing import Any, Dict, Optional, Type

from api.models.graph import Graph
from api.models.node import Node
from api.models.edge import Edge, EdgeDirection
from api.types import ValueType, TypeValidator

from graph_platform.config import SerializationConfig


class _ConcreteNode(Node):
    """Minimal concrete Node used during deserialization."""
    pass


class GraphSerializer:
    """
    Serialize / deserialize ``Graph`` instances with configurable field control.

    Usage:
        config = SerializationConfig(exclude_node_fields={'internal_flag'})
        serializer = GraphSerializer(config)
        data = serializer.serialize(graph)       # → dict
        json_str = serializer.to_json(graph)     # → str
        graph = serializer.deserialize(data)     # → Graph
        graph = serializer.from_json(json_str)   # → Graph
    """

    def __init__(self, config: Optional[SerializationConfig] = None):
        self._config = config or SerializationConfig()

    @property
    def config(self) -> SerializationConfig:
        return self._config

    @config.setter
    def config(self, value: SerializationConfig) -> None:
        self._config = value

    # ── Serialization ────────────────────────────────────────────

    def serialize(self, graph: Graph) -> Dict[str, Any]:
        """
        Convert a Graph to a plain dictionary respecting the
        current SerializationConfig.

        Returns:
            dict with keys 'id', 'nodes', 'edges'.
        """
        return {
            'id': graph.graph_id,
            'nodes': [self._serialize_node(n) for n in graph.get_all_nodes()],
            'edges': [self._serialize_edge(e) for e in graph.get_all_edges()],
        }

    def to_json(self, graph: Graph, *, indent: int = 2) -> str:
        """Serialize a Graph directly to a JSON string."""
        return json.dumps(self.serialize(graph), indent=indent, default=str)

    def _serialize_node(self, node: Node) -> Dict[str, Any]:
        available = set(node.attributes.keys())
        fields = self._config.effective_node_fields(available)

        attrs: Dict[str, Any] = {}
        for k in fields:
            v = node.attributes[k]
            attrs[k] = self._format_value(v)

        result: Dict[str, Any] = {
            'id': node.node_id,
            'attributes': attrs,
        }

        if self._config.include_types:
            result['types'] = {
                k: node.attribute_types[k].value
                for k in fields
                if k in node.attribute_types
            }

        return result

    def _serialize_edge(self, edge: Edge) -> Dict[str, Any]:
        available = set(edge.attributes.keys())
        fields = self._config.effective_edge_fields(available)

        attrs: Dict[str, Any] = {}
        for k in fields:
            v = edge.attributes[k]
            attrs[k] = self._format_value(v)

        result: Dict[str, Any] = {
            'id': edge.edge_id,
            'source': edge.source_node.node_id,
            'target': edge.target_node.node_id,
            'direction': edge.direction.value,
            'attributes': attrs,
        }

        if self._config.include_types:
            result['types'] = {
                k: edge.attribute_types[k].value
                for k in fields
                if k in edge.attribute_types
            }

        return result

    def _format_value(self, value: Any) -> Any:
        """Format a single value for serialization (handles dates)."""
        if value is None:
            return None
        if isinstance(value, (date, datetime)):
            if self._config.date_format == "iso":
                return value.isoformat()
            return value.strftime(self._config.date_format)
        return value

    # ── Deserialization ──────────────────────────────────────────

    def deserialize(self, data: Dict[str, Any],
                    node_class: Type[Node] = _ConcreteNode) -> Graph:
        """
        Reconstruct a Graph from a dictionary (inverse of ``serialize``).

        Args:
            data:       Dictionary previously produced by ``serialize()``.
            node_class: The concrete Node subclass to instantiate
                        (defaults to a minimal concrete node).

        Returns:
            Fully reconstructed Graph with nodes, edges, and typed attributes.
        """
        graph_id = data.get('id', 'deserialized')
        graph = Graph(graph_id)

        # --- Nodes ---
        node_registry: Dict[str, Node] = {}
        for node_data in data.get('nodes', []):
            node_id = str(node_data['id'])
            raw_attrs = node_data.get('attributes', {})
            type_hints = node_data.get('types', {})

            # Convert raw attribute values using type hints
            typed_attrs = self._restore_attributes(raw_attrs, type_hints)

            node = node_class(node_id, **typed_attrs)
            graph.add_node(node)
            node_registry[node_id] = node

        # --- Edges ---
        for edge_data in data.get('edges', []):
            edge_id = str(edge_data['id'])
            source_id = str(edge_data['source'])
            target_id = str(edge_data['target'])
            direction_str = edge_data.get('direction', 'directed')
            direction = EdgeDirection(direction_str)

            source_node = node_registry.get(source_id)
            target_node = node_registry.get(target_id)

            if source_node is None or target_node is None:
                continue  # Skip edges referencing missing nodes

            raw_attrs = edge_data.get('attributes', {})
            type_hints = edge_data.get('types', {})
            typed_attrs = self._restore_attributes(raw_attrs, type_hints)

            edge = Edge(edge_id, source_node, target_node, direction, **typed_attrs)
            graph.add_edge(edge)

        return graph

    def from_json(self, json_str: str,
                  node_class: Type[Node] = _ConcreteNode) -> Graph:
        """Deserialize a Graph from a JSON string."""
        data = json.loads(json_str)
        return self.deserialize(data, node_class)

    @staticmethod
    def _restore_attributes(raw_attrs: Dict[str, Any],
                            type_hints: Dict[str, str]) -> Dict[str, Any]:
        """
        Restore typed attribute values using the stored type hints.

        If type hints are absent, ``TypeValidator.detect_type`` is used
        as a fallback (the Node/Edge constructor will handle this).
        """
        result: Dict[str, Any] = {}
        for key, value in raw_attrs.items():
            if value is None:
                result[key] = None
                continue

            hint = type_hints.get(key)
            if hint:
                try:
                    target_type = ValueType(hint)
                    result[key] = TypeValidator.convert_to_type(value, target_type)
                except (ValueError, KeyError):
                    result[key] = value
            else:
                # Let the Node/Edge constructor auto-detect
                result[key] = value

        return result
