# tests/core_test/test_serialization.py
"""
Tests for GraphSerializer — serialization and deserialization.

Covers:
    • serialize() → dict structure
    • to_json() → valid JSON string
    • deserialize() → fully typed Graph reconstruction
    • from_json() → round-trip from JSON string
    • SerializationConfig field inclusion / exclusion
    • include_types toggle
    • Date formatting (iso / strftime)
    • Round-trip integrity (serialize → deserialize → identical graph)
    • Edge serialization with direction
    • Type hints restoration during deserialization
    • Empty graph serialization
"""
import json
import pytest
from datetime import date, datetime
from copy import deepcopy

from api.models.graph import Graph
from api.models.node import Node
from api.models.edge import Edge, EdgeDirection
from api.types import ValueType

from graph_platform.config import SerializationConfig
from services.serialization_service import GraphSerializer


class ConcreteNode(Node):
    """Minimal concrete Node for testing."""
    pass


# ── Fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def serializer():
    return GraphSerializer()


@pytest.fixture
def custom_serializer():
    """Serializer with custom config: exclude Score, no types."""
    cfg = SerializationConfig(
        exclude_node_fields={"Score"},
        include_types=False,
    )
    return GraphSerializer(cfg)


@pytest.fixture
def small_graph():
    """Small graph: 3 nodes, 2 edges (one directed, one undirected)."""
    g = Graph("test_graph")
    n1 = ConcreteNode("n1", Name="Alice", Age=30, Score=8.5, Born=date(1994, 3, 12))
    n2 = ConcreteNode("n2", Name="Bob", Age=25, Score=7.0, Born=date(1999, 7, 15))
    n3 = ConcreteNode("n3", Name="Carol", Age=35, Score=9.1, Born=date(1989, 1, 20))
    for n in [n1, n2, n3]:
        g.add_node(n)
    g.add_edge(Edge("e1", n1, n2, EdgeDirection.DIRECTED, Relation="friend", Weight=0.9))
    g.add_edge(Edge("e2", n2, n3, EdgeDirection.UNDIRECTED, Relation="colleague", Weight=0.7))
    return g


@pytest.fixture
def empty_graph():
    return Graph("empty")


# ── Serialize ───────────────────────────────────────────────────────────


class TestSerialize:

    def test_serialize_has_required_keys(self, serializer, small_graph):
        data = serializer.serialize(small_graph)
        assert "id" in data
        assert "nodes" in data
        assert "edges" in data

    def test_serialize_graph_id(self, serializer, small_graph):
        data = serializer.serialize(small_graph)
        assert data["id"] == "test_graph"

    def test_serialize_node_count(self, serializer, small_graph):
        data = serializer.serialize(small_graph)
        assert len(data["nodes"]) == 3

    def test_serialize_edge_count(self, serializer, small_graph):
        data = serializer.serialize(small_graph)
        assert len(data["edges"]) == 2

    def test_serialize_node_structure(self, serializer, small_graph):
        data = serializer.serialize(small_graph)
        node_data = data["nodes"][0]
        assert "id" in node_data
        assert "attributes" in node_data
        assert "types" in node_data  # include_types is True by default

    def test_serialize_edge_structure(self, serializer, small_graph):
        data = serializer.serialize(small_graph)
        edge_data = data["edges"][0]
        assert "id" in edge_data
        assert "source" in edge_data
        assert "target" in edge_data
        assert "direction" in edge_data
        assert "attributes" in edge_data

    def test_serialize_edge_direction_values(self, serializer, small_graph):
        data = serializer.serialize(small_graph)
        directions = {e["id"]: e["direction"] for e in data["edges"]}
        assert directions["e1"] == "directed"
        assert directions["e2"] == "undirected"

    def test_serialize_edge_source_target(self, serializer, small_graph):
        data = serializer.serialize(small_graph)
        e1 = next(e for e in data["edges"] if e["id"] == "e1")
        assert e1["source"] == "n1"
        assert e1["target"] == "n2"

    def test_serialize_node_attributes(self, serializer, small_graph):
        data = serializer.serialize(small_graph)
        n1 = next(n for n in data["nodes"] if n["id"] == "n1")
        attrs = n1["attributes"]
        assert attrs["Name"] == "Alice"
        assert attrs["Age"] == 30
        assert attrs["Score"] == 8.5

    def test_serialize_date_as_iso(self, serializer, small_graph):
        """Dates should be formatted as ISO strings by default."""
        data = serializer.serialize(small_graph)
        n1 = next(n for n in data["nodes"] if n["id"] == "n1")
        assert n1["attributes"]["Born"] == "1994-03-12"

    def test_serialize_type_hints(self, serializer, small_graph):
        data = serializer.serialize(small_graph)
        n1 = next(n for n in data["nodes"] if n["id"] == "n1")
        types = n1["types"]
        assert types["Name"] == "str"
        assert types["Age"] == "int"
        assert types["Score"] == "float"
        assert types["Born"] == "date"

    def test_serialize_empty_graph(self, serializer, empty_graph):
        data = serializer.serialize(empty_graph)
        assert data["id"] == "empty"
        assert data["nodes"] == []
        assert data["edges"] == []


# ── SerializationConfig ───────────────────────────────────────────────────────────


class TestFieldControl:

    def test_exclude_node_fields(self, small_graph):
        cfg = SerializationConfig(exclude_node_fields={"Score", "Born"})
        s = GraphSerializer(cfg)
        data = s.serialize(small_graph)
        n1 = next(n for n in data["nodes"] if n["id"] == "n1")
        assert "Score" not in n1["attributes"]
        assert "Born" not in n1["attributes"]
        assert "Name" in n1["attributes"]

    def test_include_node_fields(self, small_graph):
        cfg = SerializationConfig(include_node_fields={"Name"})
        s = GraphSerializer(cfg)
        data = s.serialize(small_graph)
        n1 = next(n for n in data["nodes"] if n["id"] == "n1")
        assert n1["attributes"] == {"Name": "Alice"}

    def test_include_types_false(self, small_graph):
        cfg = SerializationConfig(include_types=False)
        s = GraphSerializer(cfg)
        data = s.serialize(small_graph)
        n1 = next(n for n in data["nodes"] if n["id"] == "n1")
        assert "types" not in n1

    def test_exclude_edge_fields(self, small_graph):
        cfg = SerializationConfig(exclude_edge_fields={"Weight"})
        s = GraphSerializer(cfg)
        data = s.serialize(small_graph)
        e1 = next(e for e in data["edges"] if e["id"] == "e1")
        assert "Weight" not in e1["attributes"]
        assert "Relation" in e1["attributes"]

    def test_include_edge_fields(self, small_graph):
        cfg = SerializationConfig(include_edge_fields={"Relation"})
        s = GraphSerializer(cfg)
        data = s.serialize(small_graph)
        e1 = next(e for e in data["edges"] if e["id"] == "e1")
        assert "Relation" in e1["attributes"]
        assert "Weight" not in e1["attributes"]

    def test_custom_date_format(self, small_graph):
        cfg = SerializationConfig(date_format="%d/%m/%Y")
        s = GraphSerializer(cfg)
        data = s.serialize(small_graph)
        n1 = next(n for n in data["nodes"] if n["id"] == "n1")
        assert n1["attributes"]["Born"] == "12/03/1994"


# ── Deserialize ───────────────────────────────────────────────────────────


class TestDeserialize:

    def test_deserialize_node_count(self, serializer, small_graph):
        data = serializer.serialize(small_graph)
        restored = serializer.deserialize(data)
        assert restored.get_number_of_nodes() == 3

    def test_deserialize_edge_count(self, serializer, small_graph):
        data = serializer.serialize(small_graph)
        restored = serializer.deserialize(data)
        assert restored.get_number_of_edges() == 2

    def test_deserialize_graph_id(self, serializer, small_graph):
        data = serializer.serialize(small_graph)
        restored = serializer.deserialize(data)
        assert restored.graph_id == "test_graph"

    def test_deserialize_node_attributes_typed(self, serializer, small_graph):
        """Deserialized attributes should have proper types, not all strings."""
        data = serializer.serialize(small_graph)
        restored = serializer.deserialize(data)
        n1 = restored.get_node("n1")
        assert isinstance(n1.get_attribute("Name"), str)
        assert isinstance(n1.get_attribute("Age"), int)
        assert isinstance(n1.get_attribute("Score"), float)
        assert isinstance(n1.get_attribute("Born"), date)

    def test_deserialize_node_attribute_values(self, serializer, small_graph):
        data = serializer.serialize(small_graph)
        restored = serializer.deserialize(data)
        n1 = restored.get_node("n1")
        assert n1.get_attribute("Name") == "Alice"
        assert n1.get_attribute("Age") == 30
        assert n1.get_attribute("Score") == 8.5
        assert n1.get_attribute("Born") == date(1994, 3, 12)

    def test_deserialize_edge_direction(self, serializer, small_graph):
        data = serializer.serialize(small_graph)
        restored = serializer.deserialize(data)
        e1 = restored.get_edge("e1")
        e2 = restored.get_edge("e2")
        assert e1.is_directed() is True
        assert e2.is_directed() is False

    def test_deserialize_edge_endpoints(self, serializer, small_graph):
        data = serializer.serialize(small_graph)
        restored = serializer.deserialize(data)
        e1 = restored.get_edge("e1")
        assert e1.source_node.node_id == "n1"
        assert e1.target_node.node_id == "n2"

    def test_deserialize_edge_attributes(self, serializer, small_graph):
        data = serializer.serialize(small_graph)
        restored = serializer.deserialize(data)
        e1 = restored.get_edge("e1")
        assert e1.get_attribute("Relation") == "friend"
        assert e1.get_attribute("Weight") == 0.9

    def test_deserialize_empty_graph(self, serializer):
        data = {"id": "empty", "nodes": [], "edges": []}
        restored = serializer.deserialize(data)
        assert restored.get_number_of_nodes() == 0
        assert restored.get_number_of_edges() == 0

    def test_deserialize_missing_type_hints(self, serializer):
        """Without type hints, values should still be loaded (auto-detected)."""
        data = {
            "id": "no_hints",
            "nodes": [
                {"id": "n1", "attributes": {"Name": "Test", "Age": 25}},
            ],
            "edges": [],
        }
        restored = serializer.deserialize(data)
        n1 = restored.get_node("n1")
        assert n1.get_attribute("Name") == "Test"
        assert n1.get_attribute("Age") == 25

    def test_deserialize_skips_edges_with_missing_nodes(self, serializer):
        """Edges referencing non-existent nodes should be skipped gracefully."""
        data = {
            "id": "partial",
            "nodes": [{"id": "n1", "attributes": {}}],
            "edges": [
                {"id": "e1", "source": "n1", "target": "n_missing", "direction": "directed", "attributes": {}},
            ],
        }
        restored = serializer.deserialize(data)
        assert restored.get_number_of_nodes() == 1
        assert restored.get_number_of_edges() == 0

    def test_deserialize_with_none_values(self, serializer):
        """None attribute values should be handled gracefully."""
        data = {
            "id": "nulls",
            "nodes": [{"id": "n1", "attributes": {"Name": None}}],
            "edges": [],
        }
        restored = serializer.deserialize(data)
        n1 = restored.get_node("n1")
        assert n1.get_attribute("Name") is None


# ── Round-trip ───────────────────────────────────────────────────────────


class TestRoundTrip:

    def test_round_trip_dict(self, serializer, small_graph):
        """serialize → deserialize should preserve all data."""
        data = serializer.serialize(small_graph)
        restored = serializer.deserialize(data)

        assert restored.get_number_of_nodes() == small_graph.get_number_of_nodes()
        assert restored.get_number_of_edges() == small_graph.get_number_of_edges()

        for node in small_graph.get_all_nodes():
            r_node = restored.get_node(node.node_id)
            assert r_node is not None
            for key, value in node.attributes.items():
                assert r_node.get_attribute(key) == value

    def test_round_trip_json(self, serializer, small_graph):
        """to_json → from_json should preserve all data."""
        json_str = serializer.to_json(small_graph)
        restored = serializer.from_json(json_str)

        assert restored.get_number_of_nodes() == small_graph.get_number_of_nodes()
        assert restored.get_number_of_edges() == small_graph.get_number_of_edges()

    def test_round_trip_preserves_edge_direction(self, serializer, small_graph):
        json_str = serializer.to_json(small_graph)
        restored = serializer.from_json(json_str)
        assert restored.get_edge("e1").is_directed() == small_graph.get_edge("e1").is_directed()
        assert restored.get_edge("e2").is_directed() == small_graph.get_edge("e2").is_directed()

    def test_round_trip_preserves_date_values(self, serializer, small_graph):
        data = serializer.serialize(small_graph)
        restored = serializer.deserialize(data)
        orig_born = small_graph.get_node("n1").get_attribute("Born")
        rest_born = restored.get_node("n1").get_attribute("Born")
        assert orig_born == rest_born
        assert isinstance(rest_born, date)

    def test_round_trip_does_not_mutate_original(self, serializer, small_graph):
        """Serialization should not modify the original graph."""
        orig_node_count = small_graph.get_number_of_nodes()
        orig_edge_count = small_graph.get_number_of_edges()
        serializer.serialize(small_graph)
        assert small_graph.get_number_of_nodes() == orig_node_count
        assert small_graph.get_number_of_edges() == orig_edge_count


# ── JSON string ───────────────────────────────────────────────────────────


class TestJsonString:

    def test_to_json_returns_string(self, serializer, small_graph):
        result = serializer.to_json(small_graph)
        assert isinstance(result, str)

    def test_to_json_is_valid_json(self, serializer, small_graph):
        result = serializer.to_json(small_graph)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_from_json_returns_graph(self, serializer, small_graph):
        json_str = serializer.to_json(small_graph)
        result = serializer.from_json(json_str)
        assert isinstance(result, Graph)


# ── Config setter ───────────────────────────────────────────────────────────


class TestConfigSetter:

    def test_config_property(self, serializer):
        assert isinstance(serializer.config, SerializationConfig)

    def test_config_setter_changes_behavior(self, serializer, small_graph):
        """Changing config at runtime should affect subsequent serialization."""
        data1 = serializer.serialize(small_graph)
        n1_v1 = next(n for n in data1["nodes"] if n["id"] == "n1")
        assert "types" in n1_v1

        serializer.config = SerializationConfig(include_types=False)
        data2 = serializer.serialize(small_graph)
        n1_v2 = next(n for n in data2["nodes"] if n["id"] == "n1")
        assert "types" not in n1_v2


# ── Edge cases - type restoration ───────────────────────────────────────────────────────────


class TestTypeRestoration:

    def test_int_type_hint_restores_int(self, serializer):
        data = {
            "id": "typed",
            "nodes": [
                {"id": "n1", "attributes": {"Count": "42"}, "types": {"Count": "int"}},
            ],
            "edges": [],
        }
        restored = serializer.deserialize(data)
        assert restored.get_node("n1").get_attribute("Count") == 42
        assert isinstance(restored.get_node("n1").get_attribute("Count"), int)

    def test_float_type_hint_restores_float(self, serializer):
        data = {
            "id": "typed",
            "nodes": [
                {"id": "n1", "attributes": {"Score": "8.5"}, "types": {"Score": "float"}},
            ],
            "edges": [],
        }
        restored = serializer.deserialize(data)
        assert restored.get_node("n1").get_attribute("Score") == 8.5

    def test_date_type_hint_restores_date(self, serializer):
        data = {
            "id": "typed",
            "nodes": [
                {"id": "n1", "attributes": {"Born": "1994-03-12"}, "types": {"Born": "date"}},
            ],
            "edges": [],
        }
        restored = serializer.deserialize(data)
        assert restored.get_node("n1").get_attribute("Born") == date(1994, 3, 12)

    def test_str_type_hint_keeps_string(self, serializer):
        data = {
            "id": "typed",
            "nodes": [
                {"id": "n1", "attributes": {"Name": "Alice"}, "types": {"Name": "str"}},
            ],
            "edges": [],
        }
        restored = serializer.deserialize(data)
        assert restored.get_node("n1").get_attribute("Name") == "Alice"
        assert isinstance(restored.get_node("n1").get_attribute("Name"), str)

    def test_invalid_type_hint_falls_back(self, serializer):
        """Unknown type hint should fall back to raw value."""
        data = {
            "id": "typed",
            "nodes": [
                {"id": "n1", "attributes": {"X": "hello"}, "types": {"X": "complex_type"}},
            ],
            "edges": [],
        }
        # Should not raise
        restored = serializer.deserialize(data)
        assert restored.get_node("n1") is not None
