# tests/conftest.py
"""
Shared test fixtures.
Stub graph: social network with 15 nodes and 25 edges.
Mixed attribute types, all undirected edges, contains a cycle.
"""
import pytest
from datetime import date
from api.models.graph import Graph
from api.models.edge import Edge, EdgeDirection
from api.models.node import Node


class ConcreteNode(Node):
    """Minimal concrete Node for testing purposes."""
    pass


# ── Node definitions ─────────────────────────────────────────────
_NODES = [
    ("n1",  dict(Name="Alice",   Age=30,  Score=8.5,  City="Paris",   Born=date(1994, 3,  12))),
    ("n2",  dict(Name="Bob",     Age=25,  Score=7.0,  City="London",  Born=date(1999, 7,  15))),
    ("n3",  dict(Name="Carol",   Age=35,  Score=9.1,  City="Paris",   Born=date(1989, 1,  20))),
    ("n4",  dict(Name="David",   Age=28,  Score=6.5,  City="Berlin",  Born=date(1996, 11,  5))),
    ("n5",  dict(Name="Eve",     Age=22,  Score=8.0,  City="Pancevo", Born=date(2002, 5,  30))),
    ("n6",  dict(Name="Frank",   Age=40,  Score=5.5,  City="Rome",    Born=date(1984, 9,  18))),
    ("n7",  dict(Name="Grace",   Age=33,  Score=7.8,  City="Berlin",  Born=date(1991, 4,   2))),
    ("n8",  dict(Name="Hank",    Age=27,  Score=9.0,  City="London",  Born=date(1997, 8,  22))),
    ("n9",  dict(Name="Iris",    Age=31,  Score=6.0,  City="Paris",   Born=date(1993, 12,  9))),
    ("n10", dict(Name="Jack",    Age=45,  Score=7.5,  City="Rome",    Born=date(1979, 2,  14))),
    ("n11", dict(Name="Karen",   Age=29,  Score=8.2,  City="Pancevo", Born=date(1995, 6,  28))),
    ("n12", dict(Name="Leo",     Age=38,  Score=5.0,  City="Berlin",  Born=date(1986, 10,  3))),
    ("n13", dict(Name="Mia",     Age=24,  Score=9.5,  City="London",  Born=date(2000, 1,  17))),
    ("n14", dict(Name="Nathan",  Age=50,  Score=4.5,  City="Paris",   Born=date(1974, 7,   8))),
    ("n15", dict(Name="Olivia",  Age=26,  Score=8.8,  City="Pancevo", Born=date(1998, 3,  25))),
]

# ── Edge definitions (all UNDIRECTED) ────────────────────────────
_EDGES = [
    ("e1",  "n1",  "n2",  dict(Relation="friend",    Since=date(2015, 1,  1), Weight=0.9)),
    ("e2",  "n1",  "n3",  dict(Relation="colleague", Since=date(2018, 3,  1), Weight=0.7)),
    ("e3",  "n2",  "n4",  dict(Relation="friend",    Since=date(2016, 5,  1), Weight=0.8)),
    ("e4",  "n3",  "n5",  dict(Relation="mentor",    Since=date(2020, 9,  1), Weight=0.6)),
    ("e5",  "n4",  "n6",  dict(Relation="colleague", Since=date(2017, 2,  1), Weight=0.5)),
    ("e6",  "n5",  "n7",  dict(Relation="friend",    Since=date(2019, 11, 1), Weight=0.95)),
    ("e7",  "n6",  "n8",  dict(Relation="friend",    Since=date(2014, 7,  1), Weight=0.4)),
    ("e8",  "n7",  "n9",  dict(Relation="mentor",    Since=date(2021, 1,  1), Weight=0.85)),
    ("e9",  "n8",  "n10", dict(Relation="colleague", Since=date(2013, 6,  1), Weight=0.3)),
    ("e10", "n9",  "n11", dict(Relation="friend",    Since=date(2022, 4,  1), Weight=0.75)),
    ("e11", "n10", "n12", dict(Relation="family",    Since=date(2000, 1,  1), Weight=1.0)),
    ("e12", "n11", "n13", dict(Relation="friend",    Since=date(2023, 2,  1), Weight=0.65)),
    ("e13", "n12", "n14", dict(Relation="colleague", Since=date(2010, 8,  1), Weight=0.55)),
    ("e14", "n13", "n15", dict(Relation="friend",    Since=date(2021, 5,  1), Weight=0.7)),
    ("e15", "n14", "n1",  dict(Relation="family",    Since=date(1994, 3, 12), Weight=0.9)),
    ("e16", "n2",  "n7",  dict(Relation="colleague", Since=date(2019, 3,  1), Weight=0.6)),
    ("e17", "n3",  "n8",  dict(Relation="friend",    Since=date(2020, 7,  1), Weight=0.8)),
    ("e18", "n4",  "n9",  dict(Relation="mentor",    Since=date(2018, 1,  1), Weight=0.7)),
    ("e19", "n5",  "n10", dict(Relation="colleague", Since=date(2022, 9,  1), Weight=0.45)),
    ("e20", "n6",  "n11", dict(Relation="friend",    Since=date(2016, 4,  1), Weight=0.6)),
    ("e21", "n7",  "n12", dict(Relation="colleague", Since=date(2015, 6,  1), Weight=0.5)),
    ("e22", "n8",  "n13", dict(Relation="friend",    Since=date(2023, 1,  1), Weight=0.75)),
    ("e23", "n9",  "n14", dict(Relation="mentor",    Since=date(2017, 11, 1), Weight=0.55)),
    ("e24", "n10", "n15", dict(Relation="friend",    Since=date(2021, 8,  1), Weight=0.65)),
    # Cycle: n15 — n1 (closes the loop back to Alice)
    ("e25", "n15", "n1",  dict(Relation="friend",    Since=date(2020, 1,  1), Weight=0.8)),
]


def _build_graph(graph_id: str = "stub_social") -> Graph:
    g = Graph(graph_id)

    for node_id, attrs in _NODES:
        g.add_node(ConcreteNode(node_id, **attrs))

    for edge_id, src, tgt, attrs in _EDGES:
        g.add_edge(Edge(
            edge_id,
            g.get_node(src),
            g.get_node(tgt),
            EdgeDirection.UNDIRECTED,
            **attrs
        ))

    return g


# ── Pytest fixtures ──────────────────────────────────────────────

@pytest.fixture
def stub_graph() -> Graph:
    """Full stub graph: 15 nodes, 25 undirected edges, contains a cycle."""
    return _build_graph()


@pytest.fixture
def stub_graph_copy() -> Graph:
    """Freshly built each time — use when a test mutates the graph."""
    return _build_graph()


@pytest.fixture
def acyclic_graph() -> Graph:
    """Same graph without e25 (n15—n1) — acyclic version for cycle detection tests."""
    g = _build_graph("stub_acyclic")
    g.remove_edge("e25")
    return g
