"""
Core services — filter, search, serialization, and base abstractions.

Note: GraphSerializer is intentionally NOT imported eagerly to avoid
circular imports with ``core.graph_platform.config``.  Import it
directly: ``from core.services.serialization_service import GraphSerializer``.
"""
from .base_service import GraphQueryService
from .filter_service import FilterService
from .search_service import SearchService
from .exceptions import FilterParseError, FilterTypeError, SearchParseError

__all__ = [
    'GraphQueryService',
    'FilterService',
    'SearchService',
    'FilterParseError',
    'FilterTypeError',
    'SearchParseError',
]
