# core/services/exceptions.py

class FilterParseError(Exception):
    """Raised when filter query has invalid syntax."""
    pass

class FilterTypeError(Exception):
    """Raised when comparator is incompatible with attribute type."""
    pass

class SearchParseError(Exception):
    """Raised when search query is empty or malformed."""
    pass