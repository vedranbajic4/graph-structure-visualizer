# core/services/filter_service.py

from api.api.models.graph import Graph
from .exceptions import FilterParseError, FilterTypeError


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

        # TODO: parsing and filtering logic
        return Graph(f"{graph.graph_id}_filtered")
