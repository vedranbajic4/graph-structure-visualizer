# tests/core_test/test_filter_service.py

import pytest
from services.filter_service import FilterService
from services.exceptions import FilterParseError, FilterTypeError
from api.models.node import Node

class ConcreteNode(Node):
    """Minimal concrete Node for testing purposes."""
    pass

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


class TestGraphFiltering:
    """Integration tests using the full stub_graph fixture."""

    def test_filter_by_age_greater_than(self, service, stub_graph):
        """Age >= 35 should match Carol(35), Leo(38), Frank(40), Jack(45), Nathan(50)."""
        result = service.filter(stub_graph, "Age >= 35")

        result_ids = set(result.nodes.keys())
        assert result_ids == {"n3", "n6", "n10", "n12", "n14"}

    def test_filter_preserves_edges_between_matching_nodes(self, service, stub_graph):
        """Only edges where both endpoints match should survive."""
        result = service.filter(stub_graph, "Age >= 35")

        for edge in result.get_all_edges():
            assert edge.source_node.node_id in result.nodes
            assert edge.target_node.node_id in result.nodes

    def test_filter_discards_edges_to_non_matching_nodes(self, service, stub_graph):
        """Edges that touch a non-matching node must be absent."""
        result = service.filter(stub_graph, "Age >= 35")

        original_edge_ids = set(stub_graph.edges.keys())
        result_edge_ids = set(result.edges.keys())
        assert result_edge_ids < original_edge_ids  # strict subset

    def test_filter_by_city_equals(self, service, stub_graph):
        """City == Paris should match Alice, Carol, Iris, Nathan."""
        result = service.filter(stub_graph, "City == Paris")
        assert set(result.nodes.keys()) == {"n1", "n3", "n9", "n14"}


class TestSuccessiveApplication:
    """Chaining filter and search operations on successive subgraphs."""

    def test_successive_filters(self, service, stub_graph):
        """Filter City==Paris then Age>30 → only Carol(n3) and Iris(n9)."""
        g2 = service.filter(stub_graph, "City == Paris")
        assert set(g2.nodes.keys()) == {"n1", "n3", "n9", "n14"}

        g3 = service.filter(g2, "Age > 30")
        result_ids = set(g3.nodes.keys())
        assert result_ids == {"n3", "n9", "n14"}

    def test_search_then_filter(self, service, stub_graph):
        """SearchService produces a subgraph; FilterService must accept it."""
        from services.search_service import SearchService

        search = SearchService()
        g2 = search.search(stub_graph, "City")       # all nodes have City
        assert len(g2.nodes) == 15

        g3 = service.filter(g2, "Age >= 35")
        assert set(g3.nodes.keys()) == {"n3", "n6", "n10", "n12", "n14"}

    def test_filter_then_search(self, service, stub_graph):
        """FilterService output must be accepted by SearchService."""
        from services.search_service import SearchService

        g2 = service.filter(stub_graph, "City == Berlin")
        assert set(g2.nodes.keys()) == {"n4", "n7", "n12"}

        search = SearchService()
        g3 = search.search(g2, "Name=Grace")
        assert set(g3.nodes.keys()) == {"n7"}


class TestDateAndAdvanced:
    """Date type filtering and advanced edge-case scenarios."""

    def test_filter_by_date(self, service, stub_graph):
        """Born > 2000-01-01 should match Eve(n5, 2002-05-30) and Mia(n13, 2000-01-17)."""
        result = service.filter(stub_graph, "Born > 2000-01-01")

        result_ids = set(result.nodes.keys())
        assert result_ids == {"n5", "n13"}

        # Verify the Born values are actual date objects, not strings
        for node in result.get_all_nodes():
            born_val = node.get_attribute("Born")
            from datetime import date
            assert isinstance(born_val, date), (
                f"Node {node.node_id} Born should be a date, got {type(born_val)}"
            )

    def test_filter_missing_attributes(self, service, stub_graph):
        """Filtering by an attribute that only some nodes have should not crash;
        nodes lacking the attribute are simply excluded."""
        # Add a 'Hobby' attribute to only two nodes
        stub_graph.get_node("n1").set_attribute("Hobby", "chess")
        stub_graph.get_node("n2").set_attribute("Hobby", "painting")

        result = service.filter(stub_graph, "Hobby == chess")

        # Only n1 has Hobby=="chess"
        assert set(result.nodes.keys()) == {"n1"}
        # No crash — 13 other nodes simply lacked the attribute