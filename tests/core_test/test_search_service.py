# tests/core_test/test_search_service.py
import pytest
from core.services.search_service import SearchService
from core.services.exceptions import SearchParseError
# ── Search by attribute NAME ────────────────────────────────────

def test_search_by_name_all_nodes_have_attribute(stub_graph):
    """All 15 nodes have 'Name' attribute."""
    result = SearchService().search(stub_graph, "Name")
    assert len(result.nodes) == 15


def test_search_by_name_all_nodes_have_score(stub_graph):
    """All 15 nodes have 'Score' attribute."""
    result = SearchService().search(stub_graph, "Score")
    assert len(result.nodes) == 15


def test_search_by_name_partial_match(stub_graph):
    """'orn' matches 'Born' — all 15 nodes have Born."""
    result = SearchService().search(stub_graph, "orn")
    assert len(result.nodes) == 15


def test_search_by_name_case_insensitive(stub_graph):
    """'city' should match 'City' attribute."""
    result = SearchService().search(stub_graph, "city")
    assert len(result.nodes) == 15


def test_search_by_name_no_match(stub_graph):
    """No node has attribute 'Salary'."""
    result = SearchService().search(stub_graph, "Salary")
    assert len(result.nodes) == 0


def test_search_by_name_returns_graph_instance(stub_graph):
    """Result must be a Graph instance, not None or a list."""
    from api.api.models.graph import Graph
    result = SearchService().search(stub_graph, "Age")
    assert isinstance(result, Graph)


def test_search_by_name_preserves_edges(stub_graph):
    """
    All nodes have 'Age' → full graph returned.
    All original edges should be preserved.
    """
    result = SearchService().search(stub_graph, "Age")
    assert result.get_number_of_edges() == stub_graph.get_number_of_edges()


# ── Search by attribute VALUE ───────────────────────────────────

def test_search_by_value_exact_city(stub_graph):
    """Nodes with City == 'Paris': Alice(n1), Carol(n3), Iris(n9), Nathan(n14)."""
    result = SearchService().search(stub_graph, "City=Paris")
    assert set(result.nodes.keys()) == {"n1", "n3", "n9", "n14"}


def test_search_by_value_partial_city(stub_graph):
    """'Pan' is contained in 'Pancevo': Eve(n5), Karen(n11), Olivia(n15)."""
    result = SearchService().search(stub_graph, "City=Pan")
    assert set(result.nodes.keys()) == {"n5", "n11", "n15"}


def test_search_by_value_exact_name(stub_graph):
    """Only Alice has Name containing 'Alice'."""
    result = SearchService().search(stub_graph, "Name=Alice")
    assert set(result.nodes.keys()) == {"n1"}


def test_search_by_value_case_insensitive(stub_graph):
    """'paris' lowercase should match 'Paris'."""
    result = SearchService().search(stub_graph, "City=paris")
    assert set(result.nodes.keys()) == {"n1", "n3", "n9", "n14"}


def test_search_by_value_int_attribute_as_string(stub_graph):
    """Age is int — '3' matches 30(n1), 35(n3), 33(n7), 31(n9), 38(n12)."""
    result = SearchService().search(stub_graph, "Age=3")
    expected = {"n1", "n3", "n7", "n9", "n12"}
    assert set(result.nodes.keys()) == expected


def test_search_by_value_nonexistent_attribute(stub_graph):
    """No node has 'Salary' attribute — result is empty graph."""
    result = SearchService().search(stub_graph, "Salary=1000")
    assert len(result.nodes) == 0


def test_search_by_value_no_value_match(stub_graph):
    """No city named 'Tokyo'."""
    result = SearchService().search(stub_graph, "City=Tokyo")
    assert len(result.nodes) == 0


def test_search_by_value_single_city_london(stub_graph):
    """Nodes with City containing 'London': Bob(n2), Hank(n8), Mia(n13)."""
    result = SearchService().search(stub_graph, "City=London")
    assert set(result.nodes.keys()) == {"n2", "n8", "n13"}


def test_search_by_value_single_city_berlin(stub_graph):
    """Nodes with City containing 'Berlin': David(n4), Grace(n7), Leo(n12)."""
    result = SearchService().search(stub_graph, "City=Berlin")
    assert set(result.nodes.keys()) == {"n4", "n7", "n12"}


# ── Subgraph edges ──────────────────────────────────────────────

def test_search_subgraph_only_has_edges_between_matching_nodes(stub_graph):
    """
    Paris nodes: n1, n3, n9, n14.
    Only edges where BOTH endpoints are Paris nodes should be in result.
    e2: n1->n3 (both Paris) ✓
    e15: n14--n1 (both Paris) ✓
    e23: n9->n14 (both Paris) ✓
    """
    result = SearchService().search(stub_graph, "City=Paris")
    for edge in result.get_all_edges():
        assert edge.source_node.node_id in result.nodes
        assert edge.target_node.node_id in result.nodes


def test_search_subgraph_edges_paris(stub_graph):
    """Exact edge count between Paris nodes."""
    result = SearchService().search(stub_graph, "City=Paris")
    # e2(n1->n3), e15(n14--n1), e23(n9->n14)
    assert result.get_number_of_edges() == 3


def test_search_empty_subgraph_has_no_edges(stub_graph):
    """No match means empty graph with no nodes and no edges."""
    result = SearchService().search(stub_graph, "City=Tokyo")
    assert result.get_number_of_nodes() == 0
    assert result.get_number_of_edges() == 0


# ── Successive application ──────────────────────────────────────

def test_search_then_search(stub_graph):
    """Search on subgraph: first get Paris nodes, then filter by name 'Alice'."""
    g2 = SearchService().search(stub_graph, "City=Paris")   # n1, n3, n9, n14
    g3 = SearchService().search(g2, "Name=Alice")           # only n1
    assert set(g3.nodes.keys()) == {"n1"}


def test_search_does_not_mutate_original(stub_graph):
    """Original graph must remain unchanged after search."""
    original_node_count = stub_graph.get_number_of_nodes()
    original_edge_count = stub_graph.get_number_of_edges()

    SearchService().search(stub_graph, "City=Paris")

    assert stub_graph.get_number_of_nodes() == original_node_count
    assert stub_graph.get_number_of_edges() == original_edge_count


# ── Error handling ──────────────────────────────────────────────

def test_empty_query_raises(stub_graph):
    with pytest.raises(SearchParseError):
        SearchService().search(stub_graph, "")


def test_whitespace_query_raises(stub_graph):
    with pytest.raises(SearchParseError):
        SearchService().search(stub_graph, "   ")
