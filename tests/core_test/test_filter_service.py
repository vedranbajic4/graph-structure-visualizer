# tests/core_test/test_filter_service.py

import pytest
from core.services.filter_service import FilterService
from core.services.exceptions import FilterParseError


@pytest.fixture
def service():
    return FilterService()


class TestValidation:

    def test_filter_empty_query_raises_error(self, service, stub_graph):
        with pytest.raises(FilterParseError):
            service.filter(stub_graph, "")

        with pytest.raises(FilterParseError):
            service.filter(stub_graph, "   ")

    def test_filter_none_query_raises_error(self, service, stub_graph):
        with pytest.raises(FilterParseError):
            service.filter(stub_graph, None)


class TestParser:

    @pytest.mark.parametrize("query", [
        "Age >= 30",
        "Name==Alice",
        "City != London",
        "Score < 7.5",
        "Age>25",
    ])
    def test_parser_valid_syntax(self, service, stub_graph, query):
        """Valid filter expressions must not raise errors."""
        # Should not raise - just verify no exception
        service.filter(stub_graph, query)

    @pytest.mark.parametrize("query", [
        "Age >> 30",
        "Age 30",
        "== 30",
        ">= 30",
        "Age =! 30",
    ])
    def test_parser_invalid_syntax_raises_error(self, service, stub_graph, query):
        """Malformed expressions must raise FilterParseError."""
        with pytest.raises(FilterParseError):
            service.filter(stub_graph, query)