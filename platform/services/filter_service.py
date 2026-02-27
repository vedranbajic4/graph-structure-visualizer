# core/services/filter_service.py

import re
from api.api.models.graph import Graph
from api.api.models.node import Node
from api.api.types import TypeValidator
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
        :raises FilterTypeError: If the value cannot be compared with the attribute type
        """
        if query is None or not query.strip():
            raise FilterParseError("Filter query cannot be empty.")

        match = _FILTER_PATTERN.match(query)
        if not match:
            raise FilterParseError("Invalid filter format.")

        attr_name = match.group(1)
        operator = match.group(2)
        target_value_str = match.group(3).strip()

        matching_ids = set()
        for node in graph.get_all_nodes():
            if self._evaluate_node(node, attr_name, operator, target_value_str):
                matching_ids.add(node.node_id)

        return graph.get_subgraph_by_nodes(matching_ids)

    def _evaluate_node(self, node: Node, attr_name: str,
                       operator: str, target_value_str: str) -> bool:
        """
        Evaluate whether a single node satisfies the filter condition.

        :param node: Node to evaluate
        :param attr_name: Attribute name to check
        :param operator: Comparison operator (==, !=, >, <, >=, <=)
        :param target_value_str: Raw string value from the query
        :return: True if the node matches, False otherwise
        :raises FilterTypeError: If the value cannot be converted to the attribute's type
        """
        if attr_name not in node.attributes:
            return False

        attr_type = node.get_attribute_type(attr_name)
        node_val = node.get_attribute(attr_name)

        try:
            target_val = TypeValidator.convert_to_type(target_value_str, attr_type)
            return TypeValidator.compare(node_val, target_val, operator)
        except (ValueError, TypeError):
            raise FilterTypeError(
                f"Incompatible type for attribute '{attr_name}'."
            )
