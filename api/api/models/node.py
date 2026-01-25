"""
    Node model - representation of a node in the graph
"""
from typing import Dict, Any, Optional
from abc import ABC
from datetime import date, datetime
from ..types import ValueType, TypeValidator


class Node(ABC):
    """
    Abstract class for a node in the graph.
    Each node has an ID and arbitrary attributes.
    """

    def __init__(self, node_id: Any, **attributes):
        """
        Initialize a node.

        Args:
            node_id: Unique identifier of the node (will be converted to str)
            **attributes: Arbitrary node attributes
        """
        # Ensure ID is always a string for consistency in comparisons
        self.node_id = str(node_id)
        self.attributes: Dict[str, Any] = {}
        self.attribute_types: Dict[str, ValueType] = {}

        # Add attributes with type detection
        for key, value in attributes.items():
            self.set_attribute(key, value)

    def set_attribute(self, key: str, value: Any) -> None:
        """
        Set node attribute with type detection.
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
        return self.attributes.get(key)

    def update_attribute(self, key: str, value: Any) -> None:
        self.set_attribute(key, value)

    def delete_attribute(self, key: str) -> None:
        if key in self.attributes:
            del self.attributes[key]
            del self.attribute_types[key]

    def get_attribute_type(self, key: str) -> Optional[ValueType]:
        return self.attribute_types.get(key)

    def get_all_attributes(self) -> Dict[str, Any]:
        return self.attributes.copy()

    def contains_in_attributes(self, query: str) -> bool:
        """
        Check if query exists in attribute name or value.
        Case-insensitive search.
        """
        if not query:
            return False

        query_lower = query.lower()

        # Search in attribute names
        if any(query_lower in key.lower() for key in self.attributes.keys()):
            return True

        # Search in attribute values
        for value in self.attributes.values():
            if value is None:
                continue
            # Convert to string only for search purposes
            if query_lower in str(value).lower():
                return True

        return False

    def __repr__(self) -> str:
        attrs = ", ".join(f"{k}={v}" for k, v in self.attributes.items())
        return f"Node({self.node_id}, {attrs})"

    def __eq__(self, other) -> bool:
        """Two nodes are equal if they have the same ID"""
        if not isinstance(other, Node):
            return False
        return self.node_id == other.node_id

    def __hash__(self) -> int:
        """Hash node by ID"""
        return hash(self.node_id)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert node to dictionary for serialization.
        Dates must be strings for JSON response.
        """
        serializable_attrs = {}
        for k, v in self.attributes.items():
            if isinstance(v, (date, datetime)):
                serializable_attrs[k] = v.isoformat()
            else:
                serializable_attrs[k] = v

        return {
            'id': self.node_id,
            'attributes': serializable_attrs,
            'types': {k: v.value for k, v in self.attribute_types.items()}
        }


