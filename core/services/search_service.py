# core/services/search_service.py
"""
    SearchService — searches graph nodes by attribute name or value.

    Extends ``GraphQueryService[str]`` (Template Method + Genericity).
"""
import re
from typing import Set

from api.api.models.graph import Graph
from .base_service import GraphQueryService
from .exceptions import SearchParseError

# Regex za "Name=Vedran" ili "City=New York"
_VALUE_PATTERN = re.compile(r'^(\w+)=(.+)$')


class SearchService(GraphQueryService[str]):
    """
    Two search modes:
    - By attribute name:  "Age"         → nodes that have attribute named 'Age'
    - By attribute value: "Name=Vedran" → nodes where attribute 'Name' contains 'Vedran'

    Extends ``GraphQueryService[str]`` — the generic base provides
    the Template Method ``execute(graph, query)`` which calls:
        1. ``_validate_query(query)``
        2. ``_find_matching_nodes(graph, query)``
        3. ``graph.get_subgraph_by_nodes(matching_ids)``
    """

    # ── Public convenience method (backward-compatible) ──────────

    def search(self, graph: Graph, query: str) -> Graph:
        """
        Convenience wrapper around the generic ``execute()``.

        :param graph: Input graph
        :param query: 'AttrName' or 'AttrName=value'
        :return: Subgraph of matching nodes
        :raises SearchParseError: If query is empty
        """
        return self.execute(graph, query)

    # ── Template Method hooks (from GraphQueryService[str]) ──────

    def _validate_query(self, query: str) -> None:
        """Validate that the search query is non-empty."""
        if not query or not query.strip():
            raise SearchParseError("Search query cannot be empty.")

    def _find_matching_nodes(self, graph: Graph, query: str) -> Set[str]:
        """Return IDs of all nodes matching the search query."""
        query = query.strip()
        match = _VALUE_PATTERN.match(query)

        if match:
            attr_name = match.group(1)
            search_value = match.group(2).strip()
            return self._find_by_value(graph, attr_name, search_value)
        else:
            return self._find_by_name(graph, query)

    def _find_by_name(self, graph: Graph, attr_name: str) -> Set[str]:
        """Return IDs of nodes that have an attribute with this name (case-insensitive)."""
        attr_lower = attr_name.lower()
        return {
            node.node_id
            for node in graph.get_all_nodes()
            if any(attr_lower in key.lower() for key in node.attributes.keys())
        }

    def _find_by_value(self, graph: Graph, attr_name: str, value: str) -> Set[str]:
        """Return IDs of nodes where attribute 'attr_name' contains 'value' (case-insensitive)."""
        attr_lower = attr_name.lower()
        value_lower = value.lower()

        matching_ids = set()
        for node in graph.get_all_nodes():
            for key, attr_val in node.attributes.items():
                if key.lower() == attr_lower:
                    if attr_val is not None and value_lower in str(attr_val).lower():
                        matching_ids.add(node.node_id)
                        break

        return matching_ids
