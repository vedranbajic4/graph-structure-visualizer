# core/services/search_service.py
import re
from api.api.models.graph import Graph
from .exceptions import SearchParseError

# Regex za "Name=Vedran" ili "City=New York"
_VALUE_PATTERN = re.compile(r'^(\w+)=(.+)$')


class SearchService:
    """
    Two search modes:
    - By attribute name:  "Age"         → nodes that have attribute named 'Age'
    - By attribute value: "Name=Vedran" → nodes where attribute 'Name' contains 'Vedran'
    """

    def search(self, graph: Graph, query: str) -> Graph:
        """
        :param graph: Input graph
        :param query: 'AttrName' or 'AttrName=value'
        :return: Subgraph of matching nodes
        :raises SearchParseError: If query is empty
        """
        if not query or not query.strip():
            raise SearchParseError("Search query cannot be empty.")

        query = query.strip()
        match = _VALUE_PATTERN.match(query)

        if match:
            # Mode 2: "Name=Vedran" — search by attribute VALUE
            attr_name = match.group(1)
            search_value = match.group(2).strip()
            return self._search_by_value(graph, attr_name, search_value)
        else:
            # Mode 1: "Age" — search by attribute NAME
            return self._search_by_name(graph, query)

    def _search_by_name(self, graph: Graph, attr_name: str) -> Graph:
        """Return nodes that have an attribute with this name (case-insensitive)."""
        attr_lower = attr_name.lower()
        matching_ids = {
            node.node_id
            for node in graph.get_all_nodes()
            if any(attr_lower in key.lower() for key in node.attributes.keys())
        }
        return graph.get_subgraph_by_nodes(matching_ids)

    def _search_by_value(self, graph: Graph, attr_name: str, value: str) -> Graph:
        """Return nodes where attribute 'attr_name' contains 'value' (case-insensitive)."""
        attr_lower = attr_name.lower()
        value_lower = value.lower()

        matching_ids = set()
        for node in graph.get_all_nodes():
            for key, attr_val in node.attributes.items():
                if key.lower() == attr_lower:
                    if attr_val is not None and value_lower in str(attr_val).lower():
                        matching_ids.add(node.node_id)
                        break

        return graph.get_subgraph_by_nodes(matching_ids)
