"""
    Generic base service for graph query operations.

    Design Pattern: Template Method
    ─────────────────────────────────
    Defines the skeleton of a graph query operation (validate → execute → build subgraph),
    letting concrete subclasses (FilterService, SearchService) override specific steps.

    Genericity:
    ─────────────────────────
    Uses Generic[TQuery] so each service explicitly declares its query type,
    enforcing type safety across the platform.
"""
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Set
from api.api.models.graph import Graph

# Generic type variable for the query parameter
TQuery = TypeVar('TQuery')


class GraphQueryService(ABC, Generic[TQuery]):
    """
    Abstract generic base for all services that query a graph
    and produce a subgraph as result.

    Concrete subclasses must implement:
        - _validate_query(query)   → raise on invalid input
        - _find_matching_nodes(graph, query) → set of matching node IDs
    """

    def execute(self, graph: Graph, query: TQuery) -> Graph:
        """
        Template Method: validate → find matching nodes → build subgraph.

        Args:
            graph:  The input graph to query.
            query:  Query object (type depends on the concrete service).

        Returns:
            A new subgraph containing only the matching nodes and their
            interconnecting edges.
        """
        self._validate_query(query)
        matching_ids = self._find_matching_nodes(graph, query)
        return graph.get_subgraph_by_nodes(matching_ids)

    @abstractmethod
    def _validate_query(self, query: TQuery) -> None:
        """
        Validate the query; raise an appropriate exception on failure.
        """
        ...

    @abstractmethod
    def _find_matching_nodes(self, graph: Graph, query: TQuery) -> Set[str]:
        """
        Return the set of node IDs that satisfy the query.
        """
        ...
