# tests/core_test/test_filter_service.py

import pytest
from core.services.filter_service import FilterService
from core.services.exceptions import FilterParseError, FilterTypeError
from tests.conftest import ConcreteNode


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


class TestNodeEvaluation:
    """Unit tests for _evaluate_node with isolated Node instances."""

    @pytest.fixture
    def node_age_30(self):
        return ConcreteNode("t1", Age=30, Name="Alice")

    def test_evaluate_node_match(self, service, node_age_30):
        assert service._evaluate_node(node_age_30, "Age", ">", "25") is True
        assert service._evaluate_node(node_age_30, "Age", ">=", "30") is True
        assert service._evaluate_node(node_age_30, "Age", "==", "30") is True

    def test_evaluate_node_no_match(self, service, node_age_30):
        assert service._evaluate_node(node_age_30, "Age", "<", "20") is False
        assert service._evaluate_node(node_age_30, "Age", ">", "40") is False
        assert service._evaluate_node(node_age_30, "Age", "!=", "30") is False

    def test_evaluate_node_missing_attribute(self, service, node_age_30):
        """Node without the queried attribute should return False."""
        assert service._evaluate_node(node_age_30, "Height", ">", "100") is False

    def test_evaluate_node_incompatible_type(self, service, node_age_30):
        """Non-numeric value for an int attribute must raise FilterTypeError."""
        with pytest.raises(FilterTypeError):
            service._evaluate_node(node_age_30, "Age", ">", "twenty")