# core/services/filter_service.py

import re
from api.api.models.graph import Graph
from .exceptions import FilterParseError, FilterTypeError

# Regex: attribute  operator  value
_FILTER_PATTERN = re.compile(r'^\s*(\w+)\s*(==|!=|>=|<=|>|<)\s*(.+)\s*$')


class FilterService:
    """
    Filters graph nodes based on a query of the form:
        <attribute_name> <comparator> <value>
    """

    def filter(self, graph: Graph, query: str) -> Graph:
        """
        :param graph: Input graph to filter
        :param query: Filter query string (e.g. "Age >= 30")
        :return: Subgraph containing only matching nodes
        :raises FilterParseError: If query is None, empty, or has invalid syntax
        """
        if query is None or not query.strip():
            raise FilterParseError("Filter query cannot be empty.")

        match = _FILTER_PATTERN.match(query)
        if not match:
            raise FilterParseError("Invalid filter format.")

        attr_name = match.group(1)
        operator = match.group(2)
        target_value_str = match.group(3).strip()

        # TODO: node evaluation and subgraph construction
        return Graph(f"{graph.graph_id}_filtered")
