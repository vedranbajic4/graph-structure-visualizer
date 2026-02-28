# tests/cli_test/test_cli.py
"""
Comprehensive CLI tests — commands, command processor, parsing, undo, edge cases.
"""
import pytest
from copy import deepcopy

from api.api.models.graph import Graph
from api.api.models.node import Node
from api.api.models.edge import Edge, EdgeDirection

from core.graph_platform.cli.commands import (
    Command,
    CommandResult,
    CreateNodeCommand,
    EditNodeCommand,
    DeleteNodeCommand,
    CreateEdgeCommand,
    EditEdgeCommand,
    DeleteEdgeCommand,
    FilterCommand,
    SearchCommand,
    ClearCommand,
    UndoCommand,
    ResetCommand,
    InfoCommand,
    HelpCommand,
    ListCommand,
)
from core.graph_platform.cli.command_processor import CommandProcessor


# ── Helpers ──────────────────────────────────────────────────────

class _TestNode(Node):
    """Concrete Node for test use."""
    pass


def _empty_graph(graph_id: str = "test") -> Graph:
    return Graph(graph_id)


def _small_graph() -> Graph:
    """Graph with 3 nodes, 2 edges for quick tests."""
    g = Graph("small")
    g.add_node(_TestNode("A", Name="Alice", Age=30))
    g.add_node(_TestNode("B", Name="Bob", Age=25))
    g.add_node(_TestNode("C", Name="Carol", Age=35))
    g.add_edge(Edge("e1", g.get_node("A"), g.get_node("B"), EdgeDirection.DIRECTED, Relation="friend"))
    g.add_edge(Edge("e2", g.get_node("B"), g.get_node("C"), EdgeDirection.UNDIRECTED, Relation="colleague"))
    return g


# ═════════════════════════════════════════════════════════════════
#  CommandResult
# ═════════════════════════════════════════════════════════════════

class TestCommandResult:

    def test_default_fields(self):
        r = CommandResult(True, "ok")
        assert r.success is True
        assert r.message == "ok"
        assert r.graph is None
        assert r.data == {}

    def test_with_graph_and_data(self):
        g = _empty_graph()
        r = CommandResult(False, "fail", g, {"key": 1})
        assert r.graph is g
        assert r.data == {"key": 1}


# ═════════════════════════════════════════════════════════════════
#  NODE COMMANDS (direct execution)
# ═════════════════════════════════════════════════════════════════

class TestCreateNodeCommand:

    def test_create_node_success(self):
        g = _empty_graph()
        cmd = CreateNodeCommand("n1", {"Name": "Alice"})
        r = cmd.execute(g)
        assert r.success is True
        assert g.get_node("n1") is not None
        assert g.get_node("n1").get_attribute("Name") == "Alice"

    def test_create_node_no_properties(self):
        g = _empty_graph()
        cmd = CreateNodeCommand("n1")
        r = cmd.execute(g)
        assert r.success is True
        assert "0 attribute(s)" in r.message

    def test_create_node_duplicate_fails(self):
        g = _empty_graph()
        CreateNodeCommand("n1").execute(g)
        r = CreateNodeCommand("n1").execute(g)
        assert r.success is False
        assert "already exists" in r.message

    def test_create_node_supports_undo(self):
        cmd = CreateNodeCommand("n1")
        assert cmd.supports_undo is True

    def test_create_node_undo(self):
        g = _empty_graph()
        cmd = CreateNodeCommand("n1", {"X": "1"})
        cmd.execute(g)
        assert g.get_number_of_nodes() == 1
        r = cmd.undo(g)
        assert r.success is True
        assert g.get_number_of_nodes() == 0

    def test_create_node_undo_nonexistent(self):
        g = _empty_graph()
        cmd = CreateNodeCommand("n1")
        r = cmd.undo(g)
        assert r.success is False


class TestEditNodeCommand:

    def test_edit_existing_node(self):
        g = _empty_graph()
        CreateNodeCommand("n1", {"Name": "Alice"}).execute(g)
        cmd = EditNodeCommand("n1", {"Name": "Alicia", "Age": "30"})
        r = cmd.execute(g)
        assert r.success is True
        assert g.get_node("n1").get_attribute("Name") == "Alicia"

    def test_edit_nonexistent_node(self):
        g = _empty_graph()
        r = EditNodeCommand("x", {"Name": "X"}).execute(g)
        assert r.success is False
        assert "not found" in r.message

    def test_edit_node_undo_restores_old_value(self):
        g = _empty_graph()
        CreateNodeCommand("n1", {"Name": "Alice"}).execute(g)
        cmd = EditNodeCommand("n1", {"Name": "Bob"})
        cmd.execute(g)
        assert g.get_node("n1").get_attribute("Name") == "Bob"
        cmd.undo(g)
        assert g.get_node("n1").get_attribute("Name") == "Alice"

    def test_edit_node_undo_removes_new_attribute(self):
        g = _empty_graph()
        CreateNodeCommand("n1", {"Name": "Alice"}).execute(g)
        cmd = EditNodeCommand("n1", {"Color": "blue"})
        cmd.execute(g)
        assert g.get_node("n1").get_attribute("Color") == "blue"
        cmd.undo(g)
        # Color was not present before, undo should delete it
        assert g.get_node("n1").get_attribute("Color") is None

    def test_edit_node_supports_undo(self):
        assert EditNodeCommand("n1", {"X": "1"}).supports_undo is True


class TestDeleteNodeCommand:

    def test_delete_isolated_node(self):
        g = _empty_graph()
        CreateNodeCommand("n1").execute(g)
        r = DeleteNodeCommand("n1").execute(g)
        assert r.success is True
        assert g.get_node("n1") is None

    def test_delete_nonexistent_node(self):
        g = _empty_graph()
        r = DeleteNodeCommand("x").execute(g)
        assert r.success is False

    def test_delete_node_with_edges_fails(self):
        g = _small_graph()
        r = DeleteNodeCommand("A").execute(g)
        assert r.success is False
        assert "connected edge" in r.message

    def test_delete_node_undo_restores(self):
        g = _empty_graph()
        CreateNodeCommand("n1", {"Name": "Alice"}).execute(g)
        cmd = DeleteNodeCommand("n1")
        cmd.execute(g)
        assert g.get_node("n1") is None
        r = cmd.undo(g)
        assert r.success is True
        assert g.get_node("n1") is not None

    def test_delete_node_undo_already_exists(self):
        g = _empty_graph()
        CreateNodeCommand("n1").execute(g)
        cmd = DeleteNodeCommand("n1")
        cmd.execute(g)
        CreateNodeCommand("n1").execute(g)  # re-create
        r = cmd.undo(g)
        assert r.success is False
        assert "already exists" in r.message

    def test_delete_node_supports_undo(self):
        assert DeleteNodeCommand("n1").supports_undo is True


# ═════════════════════════════════════════════════════════════════
#  EDGE COMMANDS (direct execution)
# ═════════════════════════════════════════════════════════════════

class TestCreateEdgeCommand:

    def test_create_directed_edge(self):
        g = _empty_graph()
        CreateNodeCommand("A").execute(g)
        CreateNodeCommand("B").execute(g)
        cmd = CreateEdgeCommand("e1", "A", "B", directed=True, properties={"W": "1"})
        r = cmd.execute(g)
        assert r.success is True
        assert g.get_edge("e1") is not None
        assert "->" in r.message

    def test_create_undirected_edge(self):
        g = _empty_graph()
        CreateNodeCommand("A").execute(g)
        CreateNodeCommand("B").execute(g)
        cmd = CreateEdgeCommand("e1", "A", "B", directed=False)
        r = cmd.execute(g)
        assert r.success is True
        assert "--" in r.message

    def test_create_edge_missing_source(self):
        g = _empty_graph()
        CreateNodeCommand("B").execute(g)
        r = CreateEdgeCommand("e1", "A", "B").execute(g)
        assert r.success is False
        assert "Source" in r.message

    def test_create_edge_missing_target(self):
        g = _empty_graph()
        CreateNodeCommand("A").execute(g)
        r = CreateEdgeCommand("e1", "A", "B").execute(g)
        assert r.success is False
        assert "Target" in r.message

    def test_create_edge_duplicate_fails(self):
        g = _small_graph()
        r = CreateEdgeCommand("e1", "A", "B").execute(g)
        assert r.success is False
        assert "already exists" in r.message

    def test_create_edge_undo(self):
        g = _empty_graph()
        CreateNodeCommand("A").execute(g)
        CreateNodeCommand("B").execute(g)
        cmd = CreateEdgeCommand("e1", "A", "B")
        cmd.execute(g)
        assert g.get_number_of_edges() == 1
        r = cmd.undo(g)
        assert r.success is True
        assert g.get_number_of_edges() == 0

    def test_create_edge_undo_not_found(self):
        g = _empty_graph()
        cmd = CreateEdgeCommand("e1", "A", "B")
        r = cmd.undo(g)
        assert r.success is False


class TestEditEdgeCommand:

    def test_edit_existing_edge(self):
        g = _small_graph()
        cmd = EditEdgeCommand("e1", {"Relation": "enemy"})
        r = cmd.execute(g)
        assert r.success is True
        assert g.get_edge("e1").get_attribute("Relation") == "enemy"

    def test_edit_nonexistent_edge(self):
        g = _empty_graph()
        r = EditEdgeCommand("x", {"W": "1"}).execute(g)
        assert r.success is False

    def test_edit_edge_undo(self):
        g = _small_graph()
        cmd = EditEdgeCommand("e1", {"Relation": "enemy"})
        cmd.execute(g)
        cmd.undo(g)
        assert g.get_edge("e1").get_attribute("Relation") == "friend"

    def test_edit_edge_supports_undo(self):
        assert EditEdgeCommand("e1", {"W": "1"}).supports_undo is True


class TestDeleteEdgeCommand:

    def test_delete_edge(self):
        g = _small_graph()
        r = DeleteEdgeCommand("e1").execute(g)
        assert r.success is True
        assert g.get_edge("e1") is None

    def test_delete_nonexistent_edge(self):
        g = _empty_graph()
        r = DeleteEdgeCommand("x").execute(g)
        assert r.success is False

    def test_delete_edge_undo_restores(self):
        g = _small_graph()
        cmd = DeleteEdgeCommand("e1")
        cmd.execute(g)
        assert g.get_edge("e1") is None
        r = cmd.undo(g)
        assert r.success is True
        assert g.get_edge("e1") is not None

    def test_delete_edge_undo_already_exists(self):
        g = _small_graph()
        cmd = DeleteEdgeCommand("e1")
        cmd.execute(g)
        # Re-create same id
        CreateEdgeCommand("e1", "A", "B").execute(g)
        r = cmd.undo(g)
        assert r.success is False

    def test_delete_edge_undo_endpoint_removed(self):
        g = _empty_graph()
        CreateNodeCommand("A").execute(g)
        CreateNodeCommand("B").execute(g)
        CreateEdgeCommand("e1", "A", "B").execute(g)
        cmd = DeleteEdgeCommand("e1")
        cmd.execute(g)
        # Remove one endpoint
        DeleteNodeCommand("A").execute(g)
        r = cmd.undo(g)
        assert r.success is False
        assert "endpoint" in r.message


# ═════════════════════════════════════════════════════════════════
#  QUERY COMMANDS (filter / search)
# ═════════════════════════════════════════════════════════════════

class TestFilterCommand:

    def test_filter_produces_subgraph(self, stub_graph):
        cmd = FilterCommand("Age >= 30")
        r = cmd.execute(stub_graph)
        assert r.success is True
        assert r.graph.get_number_of_nodes() < stub_graph.get_number_of_nodes()

    def test_filter_invalid_query(self, stub_graph):
        cmd = FilterCommand("%%%invalid%%%")
        r = cmd.execute(stub_graph)
        assert r.success is False
        assert "error" in r.message.lower()


class TestSearchCommand:

    def test_search_by_name(self, stub_graph):
        cmd = SearchCommand("Age")
        r = cmd.execute(stub_graph)
        assert r.success is True
        # All nodes have Age
        assert r.graph.get_number_of_nodes() == 15

    def test_search_by_value(self, stub_graph):
        cmd = SearchCommand("Name=Alice")
        r = cmd.execute(stub_graph)
        assert r.success is True
        assert r.graph.get_number_of_nodes() == 1

    def test_search_no_match(self, stub_graph):
        cmd = SearchCommand("Name=ZZZZZ")
        r = cmd.execute(stub_graph)
        assert r.success is True
        assert r.graph.get_number_of_nodes() == 0


# ═════════════════════════════════════════════════════════════════
#  GRAPH-LEVEL COMMANDS
# ═════════════════════════════════════════════════════════════════

class TestClearCommand:

    def test_clear_empties_graph(self):
        g = _small_graph()
        cmd = ClearCommand()
        r = cmd.execute(g)
        assert r.success is True
        assert g.get_number_of_nodes() == 0
        assert g.get_number_of_edges() == 0

    def test_clear_on_empty_graph(self):
        g = _empty_graph()
        r = ClearCommand().execute(g)
        assert r.success is True

    def test_clear_undo_restores(self):
        g = _small_graph()
        cmd = ClearCommand()
        cmd.execute(g)
        r = cmd.undo(g)
        assert r.success is True
        assert r.graph.get_number_of_nodes() == 3
        assert r.graph.get_number_of_edges() == 2

    def test_clear_supports_undo(self):
        assert ClearCommand().supports_undo is True


class TestUndoCommand:

    def test_undo_delegates(self):
        g = _empty_graph()
        r = UndoCommand().execute(g)
        assert r.success is True

    def test_undo_does_not_support_undo(self):
        assert UndoCommand().supports_undo is False


class TestResetCommand:

    def test_reset_delegates(self):
        g = _empty_graph()
        r = ResetCommand().execute(g)
        assert r.success is True

    def test_reset_does_not_support_undo(self):
        assert ResetCommand().supports_undo is False


# ═════════════════════════════════════════════════════════════════
#  INFORMATIONAL COMMANDS
# ═════════════════════════════════════════════════════════════════

class TestInfoCommand:

    def test_info_graph_summary(self):
        g = _small_graph()
        r = InfoCommand().execute(g)
        assert r.success is True
        assert "3 node(s)" in r.message
        assert "2 edge(s)" in r.message

    def test_info_node(self):
        g = _small_graph()
        r = InfoCommand("node", "A").execute(g)
        assert r.success is True
        assert "Alice" in r.message

    def test_info_node_not_found(self):
        g = _small_graph()
        r = InfoCommand("node", "ZZZ").execute(g)
        assert r.success is False

    def test_info_edge(self):
        g = _small_graph()
        r = InfoCommand("edge", "e1").execute(g)
        assert r.success is True
        assert "A" in r.message and "B" in r.message

    def test_info_edge_not_found(self):
        g = _small_graph()
        r = InfoCommand("edge", "ZZZ").execute(g)
        assert r.success is False

    def test_info_edge_shows_direction_arrow(self):
        g = _small_graph()
        r = InfoCommand("edge", "e1").execute(g)
        assert "->" in r.message  # e1 is directed

    def test_info_edge_undirected(self):
        g = _small_graph()
        r = InfoCommand("edge", "e2").execute(g)
        assert "--" in r.message  # e2 is undirected

    def test_info_node_no_attributes(self):
        g = _empty_graph()
        CreateNodeCommand("n1").execute(g)
        r = InfoCommand("node", "n1").execute(g)
        assert r.success is True
        assert "no attributes" in r.message

    def test_info_unknown_target_type(self):
        g = _empty_graph()
        r = InfoCommand("banana", "x").execute(g)
        assert r.success is False


class TestListCommand:

    def test_list_both(self):
        g = _small_graph()
        r = ListCommand().execute(g)
        assert r.success is True
        assert "Nodes (3)" in r.message
        assert "Edges (2)" in r.message

    def test_list_nodes_only(self):
        g = _small_graph()
        r = ListCommand("nodes").execute(g)
        assert "Nodes" in r.message
        assert "Edges" not in r.message

    def test_list_edges_only(self):
        g = _small_graph()
        r = ListCommand("edges").execute(g)
        assert "Edges" in r.message
        assert "Nodes" not in r.message

    def test_list_empty_graph(self):
        g = _empty_graph()
        r = ListCommand().execute(g)
        assert r.success is True
        # Should still show headers with 0 counts
        assert "Nodes (0)" in r.message


class TestHelpCommand:

    def test_help_returns_text(self):
        g = _empty_graph()
        r = HelpCommand().execute(g)
        assert r.success is True
        assert "create node" in r.message
        assert "delete edge" in r.message
        assert "filter" in r.message
        assert "search" in r.message
        assert "undo" in r.message
        assert "help" in r.message


# ═════════════════════════════════════════════════════════════════
#  COMMAND PROCESSOR — parsing
# ═════════════════════════════════════════════════════════════════

class TestProcessorParsing:

    @pytest.fixture
    def proc(self):
        return CommandProcessor()

    @pytest.fixture
    def graph(self):
        return _small_graph()

    # ── Empty / whitespace ────────────────────────────────────────

    def test_empty_string(self, proc, graph):
        r = proc.process("", graph)
        assert r.success is False
        assert "Empty" in r.message

    def test_whitespace_only(self, proc, graph):
        r = proc.process("   ", graph)
        assert r.success is False

    # ── Unknown command ───────────────────────────────────────────

    def test_unknown_command(self, proc, graph):
        r = proc.process("foobar", graph)
        assert r.success is False
        assert "Unknown command" in r.message

    # ── Single-word commands ──────────────────────────────────────

    def test_help(self, proc, graph):
        r = proc.process("help", graph)
        assert r.success is True
        assert "Available commands" in r.message

    def test_help_case_insensitive(self, proc, graph):
        r = proc.process("HELP", graph)
        assert r.success is True

    def test_undo_empty_stack(self, proc, graph):
        r = proc.process("undo", graph)
        assert r.success is False
        assert "Nothing to undo" in r.message

    def test_reset_returns_sentinel(self, proc, graph):
        r = proc.process("reset", graph)
        assert r.success is True
        assert r.data.get("action") == "reset"

    def test_clear(self, proc, graph):
        r = proc.process("clear", graph)
        assert r.success is True
        assert graph.get_number_of_nodes() == 0

    # ── create node ───────────────────────────────────────────────

    def test_create_node_basic(self, proc, graph):
        r = proc.process("create node --id=X", graph)
        assert r.success is True
        assert graph.get_node("X") is not None

    def test_create_node_with_properties(self, proc, graph):
        r = proc.process("create node --id=X --property Name=Dave --property Age=20", graph)
        assert r.success is True
        assert graph.get_node("X").get_attribute("Name") == "Dave"

    def test_create_node_id_space_form(self, proc, graph):
        r = proc.process("create node --id X", graph)
        assert r.success is True
        assert graph.get_node("X") is not None

    def test_create_node_missing_id(self, proc, graph):
        r = proc.process("create node --property Name=X", graph)
        assert r.success is False
        assert "Missing" in r.message or "id" in r.message.lower()

    # ── create edge ───────────────────────────────────────────────

    def test_create_edge_directed(self, proc, graph):
        r = proc.process("create edge --id=e99 A C", graph)
        assert r.success is True
        assert graph.get_edge("e99") is not None

    def test_create_edge_undirected(self, proc, graph):
        r = proc.process("create edge --id=e99 --undirected A C", graph)
        assert r.success is True
        assert not graph.get_edge("e99").is_directed()

    def test_create_edge_with_properties(self, proc, graph):
        r = proc.process("create edge --id=e99 --property Weight=5 A C", graph)
        assert r.success is True

    def test_create_edge_missing_positional(self, proc, graph):
        r = proc.process("create edge --id=e99 A", graph)
        assert r.success is False

    def test_create_edge_missing_id(self, proc, graph):
        r = proc.process("create edge A B", graph)
        assert r.success is False

    # ── edit node ─────────────────────────────────────────────────

    def test_edit_node(self, proc, graph):
        r = proc.process("edit node --id=A --property Name=Alicia", graph)
        assert r.success is True
        assert graph.get_node("A").get_attribute("Name") == "Alicia"

    def test_edit_node_no_properties_fails(self, proc, graph):
        r = proc.process("edit node --id=A", graph)
        assert r.success is False
        assert "property" in r.message.lower()

    def test_edit_node_not_found(self, proc, graph):
        r = proc.process("edit node --id=ZZZ --property X=1", graph)
        assert r.success is False

    # ── edit edge ─────────────────────────────────────────────────

    def test_edit_edge(self, proc, graph):
        r = proc.process("edit edge --id=e1 --property Relation=enemy", graph)
        assert r.success is True

    def test_edit_edge_no_properties_fails(self, proc, graph):
        r = proc.process("edit edge --id=e1", graph)
        assert r.success is False

    # ── delete node ───────────────────────────────────────────────

    def test_delete_node_with_edges_fails(self, proc, graph):
        r = proc.process("delete node --id=A", graph)
        assert r.success is False

    def test_delete_isolated_node(self, proc):
        g = _empty_graph()
        proc2 = CommandProcessor()
        proc2.process("create node --id=X", g)
        r = proc2.process("delete node --id=X", g)
        assert r.success is True
        assert g.get_node("X") is None

    # ── delete edge ───────────────────────────────────────────────

    def test_delete_edge(self, proc, graph):
        r = proc.process("delete edge --id=e1", graph)
        assert r.success is True
        assert graph.get_edge("e1") is None

    def test_delete_edge_not_found(self, proc, graph):
        r = proc.process("delete edge --id=ZZZ", graph)
        assert r.success is False

    # ── filter ────────────────────────────────────────────────────

    def test_filter_via_processor(self, proc, graph):
        r = proc.process("filter Age >= 30", graph)
        assert r.success is True
        assert r.graph.get_number_of_nodes() == 2  # Alice(30), Carol(35)

    def test_filter_quoted(self, proc, graph):
        r = proc.process("filter 'Age >= 30'", graph)
        assert r.success is True

    def test_filter_double_quoted(self, proc, graph):
        r = proc.process('filter "Age >= 30"', graph)
        assert r.success is True

    # ── search ────────────────────────────────────────────────────

    def test_search_by_attr_name(self, proc, graph):
        r = proc.process("search Name", graph)
        assert r.success is True
        assert r.graph.get_number_of_nodes() == 3

    def test_search_by_value(self, proc, graph):
        r = proc.process("search Name=Alice", graph)
        assert r.success is True
        assert r.graph.get_number_of_nodes() == 1

    # ── list ──────────────────────────────────────────────────────

    def test_list_all(self, proc, graph):
        r = proc.process("list", graph)
        assert r.success is True

    def test_list_nodes(self, proc, graph):
        r = proc.process("list nodes", graph)
        assert r.success is True
        assert "Nodes" in r.message

    def test_list_edges(self, proc, graph):
        r = proc.process("list edges", graph)
        assert r.success is True
        assert "Edges" in r.message

    def test_list_invalid_target(self, proc, graph):
        r = proc.process("list bananas", graph)
        assert r.success is False

    # ── info ──────────────────────────────────────────────────────

    def test_info_graph(self, proc, graph):
        r = proc.process("info", graph)
        assert r.success is True

    def test_info_node(self, proc, graph):
        r = proc.process("info node A", graph)
        assert r.success is True

    def test_info_edge(self, proc, graph):
        r = proc.process("info edge e1", graph)
        assert r.success is True

    def test_info_invalid_type(self, proc, graph):
        r = proc.process("info banana x", graph)
        assert r.success is False

    def test_info_node_missing_id(self, proc, graph):
        r = proc.process("info node", graph)
        assert r.success is False

    # ── Unknown entity ────────────────────────────────────────────

    def test_create_unknown_entity(self, proc, graph):
        r = proc.process("create banana --id=1", graph)
        assert r.success is False
        assert "Unknown entity" in r.message

    def test_create_missing_entity(self, proc, graph):
        r = proc.process("create", graph)
        assert r.success is False

    # ── Property format edge cases ────────────────────────────────

    def test_property_equals_format(self, proc, graph):
        r = proc.process("create node --id=P1 --property=Color=red", graph)
        assert r.success is True
        assert graph.get_node("P1").get_attribute("Color") == "red"

    def test_property_missing_value(self, proc, graph):
        r = proc.process("create node --id=P2 --property NoEquals", graph)
        assert r.success is False
        assert "Key=Value" in r.message


# ═════════════════════════════════════════════════════════════════
#  COMMAND PROCESSOR — undo stack
# ═════════════════════════════════════════════════════════════════

class TestProcessorUndo:

    def test_undo_create_node(self):
        proc = CommandProcessor()
        g = _empty_graph()
        proc.process("create node --id=X --property Name=Test", g)
        assert g.get_node("X") is not None
        assert proc.get_undo_depth() == 1

        r = proc.process("undo", g)
        assert r.success is True
        # Undo restores old graph snapshot (without the node)
        assert r.graph.get_node("X") is None
        assert proc.get_undo_depth() == 0

    def test_undo_multiple(self):
        proc = CommandProcessor()
        g = _empty_graph()
        proc.process("create node --id=A", g)
        proc.process("create node --id=B", g)
        assert proc.get_undo_depth() == 2
        proc.process("undo", g)
        assert proc.get_undo_depth() == 1
        proc.process("undo", g)
        assert proc.get_undo_depth() == 0

    def test_undo_nothing(self):
        proc = CommandProcessor()
        g = _empty_graph()
        r = proc.process("undo", g)
        assert r.success is False
        assert "Nothing" in r.message

    def test_undo_stack_limit(self):
        proc = CommandProcessor()
        g = _empty_graph()
        # Create 55 nodes — stack max is 50
        for i in range(55):
            proc.process(f"create node --id=n{i}", g)
        assert proc.get_undo_depth() == 50

    def test_undo_after_clear(self):
        proc = CommandProcessor()
        g = _small_graph()
        proc.process("clear", g)
        assert g.get_number_of_nodes() == 0
        r = proc.process("undo", g)
        assert r.success is True
        assert r.graph.get_number_of_nodes() == 3

    def test_undo_after_filter(self):
        proc = CommandProcessor()
        g = _small_graph()
        proc.process("filter Age >= 30", g)
        assert proc.get_undo_depth() == 1
        r = proc.process("undo", g)
        assert r.success is True
        assert r.graph.get_number_of_nodes() == 3

    def test_undo_after_search(self):
        proc = CommandProcessor()
        g = _small_graph()
        proc.process("search Name=Alice", g)
        assert proc.get_undo_depth() == 1

    def test_help_does_not_push_undo(self):
        proc = CommandProcessor()
        g = _empty_graph()
        proc.process("help", g)
        assert proc.get_undo_depth() == 0

    def test_info_does_not_push_undo(self):
        proc = CommandProcessor()
        g = _small_graph()
        proc.process("info", g)
        assert proc.get_undo_depth() == 0

    def test_list_does_not_push_undo(self):
        proc = CommandProcessor()
        g = _small_graph()
        proc.process("list", g)
        assert proc.get_undo_depth() == 0

    def test_failed_command_does_not_push_undo(self):
        proc = CommandProcessor()
        g = _empty_graph()
        proc.process("delete node --id=nonexistent", g)
        assert proc.get_undo_depth() == 0

    def test_reset_does_not_push_undo(self):
        proc = CommandProcessor()
        g = _empty_graph()
        proc.process("reset", g)
        assert proc.get_undo_depth() == 0


# ═════════════════════════════════════════════════════════════════
#  EDGE CASES & INTEGRATION
# ═════════════════════════════════════════════════════════════════

class TestEdgeCases:

    def test_create_then_delete_then_undo_sequence(self):
        proc = CommandProcessor()
        g = _empty_graph()
        proc.process("create node --id=X --property Name=Alice", g)
        proc.process("delete node --id=X", g)
        assert g.get_node("X") is None
        r = proc.process("undo", g)
        assert r.success is True
        # After undo of delete, node should be back
        assert r.graph.get_node("X") is not None

    def test_multiple_properties(self):
        proc = CommandProcessor()
        g = _empty_graph()
        r = proc.process(
            "create node --id=X --property Name=Alice --property Age=30 --property City=Paris",
            g,
        )
        assert r.success is True
        node = g.get_node("X")
        assert node.get_attribute("Name") == "Alice"
        assert node.get_attribute("City") == "Paris"

    def test_quoted_filter_with_spaces(self):
        proc = CommandProcessor()
        g = _small_graph()
        r = proc.process("filter 'Age >= 30'", g)
        assert r.success is True

    def test_command_with_leading_trailing_spaces(self):
        proc = CommandProcessor()
        g = _empty_graph()
        r = proc.process("   create node --id=X   ", g)
        assert r.success is True

    def test_create_edit_delete_full_lifecycle(self):
        proc = CommandProcessor()
        g = _empty_graph()

        # Create two nodes
        proc.process("create node --id=A --property Name=Alice", g)
        proc.process("create node --id=B --property Name=Bob", g)
        assert g.get_number_of_nodes() == 2

        # Create edge
        proc.process("create edge --id=e1 A B", g)
        assert g.get_number_of_edges() == 1

        # Edit node
        proc.process("edit node --id=A --property Name=Alicia", g)
        assert g.get_node("A").get_attribute("Name") == "Alicia"

        # Edit edge
        proc.process("edit edge --id=e1 --property Weight=10", g)

        # Delete edge then node
        proc.process("delete edge --id=e1", g)
        assert g.get_number_of_edges() == 0
        proc.process("delete node --id=A", g)
        assert g.get_number_of_nodes() == 1

    def test_base_command_undo_not_supported(self):
        """Command base class undo returns failure."""
        g = _empty_graph()
        r = HelpCommand().undo(g)
        assert r.success is False
        assert "not supported" in r.message.lower()

    def test_processor_is_independent_per_instance(self):
        p1 = CommandProcessor()
        p2 = CommandProcessor()
        g = _empty_graph()
        p1.process("create node --id=A", g)
        assert p1.get_undo_depth() == 1
        assert p2.get_undo_depth() == 0
