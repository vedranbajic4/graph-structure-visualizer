"""
    Platform configuration — serialization fields, default settings.

    Provides a typed, immutable-by-default configuration object that
    controls how graphs are serialized / deserialized and which fields
    are included or excluded.
"""
from dataclasses import dataclass, field
from typing import Optional, Set


@dataclass
class SerializationConfig:
    """
    Controls which fields appear in serialized output.

    Attributes:
        include_node_fields:  If set, ONLY these node attribute keys are serialized.
                              ``None`` means "include all".
        exclude_node_fields:  Node attribute keys to skip.  Applied AFTER
                              ``include_node_fields``.
        include_edge_fields:  Same semantics, for edge attributes.
        exclude_edge_fields:  Same semantics, for edge attributes.
        include_types:        Whether to embed ``attribute_types`` in the output.
        date_format:          strftime format for serializing ``date`` / ``datetime``.
    """
    include_node_fields: Optional[Set[str]] = None
    exclude_node_fields: Set[str] = field(default_factory=set)
    include_edge_fields: Optional[Set[str]] = None
    exclude_edge_fields: Set[str] = field(default_factory=set)
    include_types: bool = True
    date_format: str = "iso"        # "iso" or a strftime pattern

    def effective_node_fields(self, available: Set[str]) -> Set[str]:
        """Compute the final set of node fields to serialize."""
        if self.include_node_fields is not None:
            result = available & self.include_node_fields
        else:
            result = set(available)
        return result - self.exclude_node_fields

    def effective_edge_fields(self, available: Set[str]) -> Set[str]:
        """Compute the final set of edge fields to serialize."""
        if self.include_edge_fields is not None:
            result = available & self.include_edge_fields
        else:
            result = set(available)
        return result - self.exclude_edge_fields


@dataclass
class PlatformConfig:
    """
    Top-level configuration for the Graph Platform.

    Attributes:
        serialization:       Controls serialization / deserialization.
        max_history_depth:   How many graph snapshots a Workspace keeps
                             for undo / reset operations.
        default_visualizer:  Entry-point name of the default visualizer plugin.
        default_data_source: Entry-point name of the default data source plugin.
    """
    serialization: SerializationConfig = field(default_factory=SerializationConfig)
    max_history_depth: int = 50
    default_visualizer: Optional[str] = None
    default_data_source: Optional[str] = None
