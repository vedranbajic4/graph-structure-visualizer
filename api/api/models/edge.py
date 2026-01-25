"""
    Edge model - representation of an edge between nodes.
"""
from typing import Dict, Any, Optional, Tuple
from enum import Enum
from datetime import date, datetime
from ..types import ValueType, TypeValidator
from .node import Node


class EdgeDirection(Enum):
    """Edge direction type"""
    DIRECTED = "directed"
    UNDIRECTED = "undirected"


class Edge:
    """
        Class for an edge between two nodes.
        An edge can be directed or undirected.
    """

    def __init__(
            self,
            edge_id: Any,
            source_node: Node,
            target_node: Node,
            direction: EdgeDirection = EdgeDirection.DIRECTED,
            **attributes
    ):
        """
        Initialize an edge.

        Args:
            edge_id: Unique identifier of the edge (will be converted to str)
            source_node: Source node
            target_node: Target node
            direction: Edge type (DIRECTED or UNDIRECTED)
            **attributes: Arbitrary edge attributes
        """
        # Ensure ID is always a string for consistency
        self.edge_id = str(edge_id)
        self.source_node = source_node
        self.target_node = target_node
        self.direction = direction
        self.attributes: Dict[str, Any] = {}
        self.attribute_types: Dict[str, ValueType] = {}

        # Add attributes with type detection
        for key, value in attributes.items():
            self.set_attribute(key, value)

    def set_attribute(self, key: str, value: Any) -> None:
        """
        Set edge attribute with type detection.
        """
        if value is None:
            self.attributes[key] = None
            self.attribute_types[key] = ValueType.STR
            return

        # This satisfies the requirement that data is not stored only as string
        detected_type = TypeValidator.detect_type(value)
        converted_value = TypeValidator.validate_and_convert(value, detected_type)

        self.attributes[key] = converted_value
        self.attribute_types[key] = detected_type

    def get_attribute(self, key: str) -> Any:
        """Get edge attribute value"""
        return self.attributes.get(key)

    def update_attribute(self, key: str, value: Any) -> None:
        """Update edge attribute"""
        self.set_attribute(key, value)

    def delete_attribute(self, key: str) -> None:
        """Delete edge attribute"""
        if key in self.attributes:
            del self.attributes[key]
            del self.attribute_types[key]

    def get_all_attributes(self) -> Dict[str, Any]:
        """Get all edge attributes"""
        return self.attributes.copy()

    def get_source_target(self) -> Tuple[Node, Node]:
        """Get source and target nodes"""
        return self.source_node, self.target_node

    def get_other_node(self, node: Node) -> Optional[Node]:
        """If edge is undirected, get the other end of the edge"""
        if node == self.source_node:
            return self.target_node
        elif node == self.target_node:
            return self.source_node
        return None

    def is_directed(self) -> bool:
        """Check if edge is directed"""
        return self.direction == EdgeDirection.DIRECTED

    def connects_nodes(self, node1: Node, node2: Node) -> bool:
        """Check if edge connects two nodes"""
        if self.direction == EdgeDirection.DIRECTED:
            return self.source_node == node1 and self.target_node == node2
        else:
            return (self.source_node == node1 and self.target_node == node2) or \
                   (self.source_node == node2 and self.target_node == node1)

    def __repr__(self) -> str:
        """String representation of edge"""
        arrow = "->" if self.direction == EdgeDirection.DIRECTED else "--"
        return f"Edge({self.source_node.node_id} {arrow} {self.target_node.node_id})"

    def __eq__(self, other) -> bool:
        """Two edges are equal if they have the same ID"""
        if not isinstance(other, Edge):
            return False
        return self.edge_id == other.edge_id

    def __hash__(self) -> int:
        """Hash edge by ID"""
        return hash(self.edge_id)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert edge to dictionary for serialization.
        Dates must be strings for JSON response.
        """
        serializable_attrs = {}
        for k, v in self.attributes.items():
            if isinstance(v, (date, datetime)):
                serializable_attrs[k] = v.isoformat()
            else:
                serializable_attrs[k] = v

        return {
            'id': self.edge_id,
            'source': self.source_node.node_id,
            'target': self.target_node.node_id,
            'direction': self.direction.value,
            'attributes': serializable_attrs,
            'types': {k: v.value for k, v in self.attribute_types.items()}
        }