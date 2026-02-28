"""
    CLI Commands — concrete command implementations.

    Design Pattern: Command
    ───────────────────────
    Each command encapsulates a graph-manipulation action as an object.
    Every command has:
        • ``execute(graph) → CommandResult``  — perform the action
        • ``undo(graph) → CommandResult``     — reverse the action (where applicable)

    This enables:
        • Decoupling the invoker (CommandProcessor) from the receiver (Graph).
        • Full undo / redo stack.
        • Logging / auditing of every mutation.

    Supported commands (per README §2.1.5):
    ────────────────────────────────────────
        create node --id=<id> --property <Key>=<Value> ...
        create edge --id=<id> --property <Key>=<Value> <source_id> <target_id>
        edit   node --id=<id> --property <Key>=<Value> ...
        edit   edge --id=<id> --property <Key>=<Value> ...
        delete node --id=<id>
        delete edge --id=<id>
        filter '<query>'
        search '<query>'
        clear
        undo
        reset
        info   [node|edge] <id>
        list   [nodes|edges]
        help
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from api.api.models.graph import Graph
from api.api.models.node import Node
from api.api.models.edge import Edge, EdgeDirection


# ── Concrete Node for CLI-created nodes ──────────────────────────

class _CLINode(Node):
    """Minimal concrete Node subclass for CLI-created nodes."""
    pass


# ── Result wrapper ───────────────────────────────────────────────

@dataclass
class CommandResult:
    """
    Value object returned by every command execution.

    Attributes:
        success:  Whether the command completed without error.
        message:  Human-readable output.
        graph:    The (possibly modified) graph after the command.
        data:     Optional structured data for programmatic consumers.
    """
    success: bool
    message: str
    graph: Optional[Graph] = None
    data: Optional[Dict[str, Any]] = field(default_factory=dict)


# ── Abstract base ────────────────────────────────────────────────

class Command(ABC):
    """
    Abstract base for all CLI commands.

    Design Pattern: Command
    """

    @abstractmethod
    def execute(self, graph: Graph) -> CommandResult:
        """Execute the command on the given graph."""
        ...

    def undo(self, graph: Graph) -> CommandResult:
        """
        Reverse the command.  Override in concrete commands
        that support undo.
        """
        return CommandResult(
            success=False,
            message="Undo is not supported for this command.",
            graph=graph,
        )

    @property
    def supports_undo(self) -> bool:
        """Whether this command can be undone."""
        return False


# ═════════════════════════════════════════════════════════════════
#  NODE COMMANDS
# ═════════════════════════════════════════════════════════════════

class CreateNodeCommand(Command):
    """
    Create a new node.

    Syntax:
        create node --id=<id> --property Name=Alice --property Age=25
    """

    def __init__(self, node_id: str, properties: Optional[Dict[str, Any]] = None):
        self._node_id = str(node_id)
        self._properties = properties or {}

    def execute(self, graph: Graph) -> CommandResult:
        if graph.get_node(self._node_id) is not None:
            return CommandResult(
                success=False,
                message=f"Node '{self._node_id}' already exists.",
                graph=graph,
            )

        node = _CLINode(self._node_id, **self._properties)
        graph.add_node(node)
        return CommandResult(
            success=True,
            message=f"Node '{self._node_id}' created with {len(self._properties)} attribute(s).",
            graph=graph,
        )

    def undo(self, graph: Graph) -> CommandResult:
        node = graph.get_node(self._node_id)
        if node is None:
            return CommandResult(False, f"Node '{self._node_id}' not found for undo.", graph)

        # Check if node has edges (per spec: can't delete node with edges)
        edges = graph._adjacency_list.get(self._node_id, [])
        if edges:
            # Force-remove edges first (since we're undoing a create, they shouldn't exist)
            for edge in list(edges):
                graph.remove_edge(edge.edge_id)

        graph.remove_node(self._node_id)
        return CommandResult(True, f"Undo: node '{self._node_id}' removed.", graph)

    @property
    def supports_undo(self) -> bool:
        return True


class EditNodeCommand(Command):
    """
    Edit attributes of an existing node.

    Syntax:
        edit node --id=<id> --property Age=40
    """

    def __init__(self, node_id: str, properties: Dict[str, Any]):
        self._node_id = str(node_id)
        self._new_properties = properties
        self._old_properties: Dict[str, Any] = {}

    def execute(self, graph: Graph) -> CommandResult:
        node = graph.get_node(self._node_id)
        if node is None:
            return CommandResult(False, f"Node '{self._node_id}' not found.", graph)

        # Save old values for undo
        for key in self._new_properties:
            self._old_properties[key] = node.get_attribute(key)

        # Apply new values
        for key, value in self._new_properties.items():
            node.set_attribute(key, value)

        return CommandResult(
            True,
            f"Node '{self._node_id}' updated: {list(self._new_properties.keys())}.",
            graph,
        )

    def undo(self, graph: Graph) -> CommandResult:
        node = graph.get_node(self._node_id)
        if node is None:
            return CommandResult(False, f"Node '{self._node_id}' not found for undo.", graph)

        for key, old_value in self._old_properties.items():
            if old_value is None:
                node.delete_attribute(key)
            else:
                node.set_attribute(key, old_value)

        return CommandResult(True, f"Undo: node '{self._node_id}' attributes restored.", graph)

    @property
    def supports_undo(self) -> bool:
        return True


class DeleteNodeCommand(Command):
    """
    Delete a node.  Fails if the node has connected edges
    (per spec §2.1.5: edges must be removed first).

    Syntax:
        delete node --id=<id>
    """

    def __init__(self, node_id: str):
        self._node_id = str(node_id)
        self._deleted_node_attrs: Dict[str, Any] = {}

    def execute(self, graph: Graph) -> CommandResult:
        node = graph.get_node(self._node_id)
        if node is None:
            return CommandResult(False, f"Node '{self._node_id}' not found.", graph)

        # Check edges — per spec, node can only be deleted if no edges connect to it
        connected_edges = graph._adjacency_list.get(self._node_id, [])
        if connected_edges:
            edge_ids = [e.edge_id for e in connected_edges]
            return CommandResult(
                False,
                f"Cannot delete node '{self._node_id}': "
                f"it has {len(connected_edges)} connected edge(s): {edge_ids}. "
                f"Remove edges first.",
                graph,
            )

        # Save state for undo
        self._deleted_node_attrs = node.get_all_attributes()

        graph.remove_node(self._node_id)
        return CommandResult(True, f"Node '{self._node_id}' deleted.", graph)

    def undo(self, graph: Graph) -> CommandResult:
        if graph.get_node(self._node_id) is not None:
            return CommandResult(False, f"Node '{self._node_id}' already exists.", graph)

        node = _CLINode(self._node_id, **self._deleted_node_attrs)
        graph.add_node(node)
        return CommandResult(True, f"Undo: node '{self._node_id}' restored.", graph)

    @property
    def supports_undo(self) -> bool:
        return True


# ═════════════════════════════════════════════════════════════════
#  EDGE COMMANDS
# ═════════════════════════════════════════════════════════════════

class CreateEdgeCommand(Command):
    """
    Create a new edge between two existing nodes.

    Syntax:
        create edge --id=<id> --property Name=Siblings <source_id> <target_id>
        create edge --id=<id> --directed --property Weight=0.8 <src> <tgt>
    """

    def __init__(self, edge_id: str, source_id: str, target_id: str,
                 directed: bool = True,
                 properties: Optional[Dict[str, Any]] = None):
        self._edge_id = str(edge_id)
        self._source_id = str(source_id)
        self._target_id = str(target_id)
        self._directed = directed
        self._properties = properties or {}

    def execute(self, graph: Graph) -> CommandResult:
        source = graph.get_node(self._source_id)
        if source is None:
            return CommandResult(False, f"Source node '{self._source_id}' not found.", graph)

        target = graph.get_node(self._target_id)
        if target is None:
            return CommandResult(False, f"Target node '{self._target_id}' not found.", graph)

        if graph.get_edge(self._edge_id) is not None:
            return CommandResult(False, f"Edge '{self._edge_id}' already exists.", graph)

        direction = EdgeDirection.DIRECTED if self._directed else EdgeDirection.UNDIRECTED
        edge = Edge(self._edge_id, source, target, direction, **self._properties)
        graph.add_edge(edge)

        arrow = "->" if self._directed else "--"
        return CommandResult(
            True,
            f"Edge '{self._edge_id}' created: {self._source_id} {arrow} {self._target_id}.",
            graph,
        )

    def undo(self, graph: Graph) -> CommandResult:
        if graph.get_edge(self._edge_id) is None:
            return CommandResult(False, f"Edge '{self._edge_id}' not found for undo.", graph)

        graph.remove_edge(self._edge_id)
        return CommandResult(True, f"Undo: edge '{self._edge_id}' removed.", graph)

    @property
    def supports_undo(self) -> bool:
        return True


class EditEdgeCommand(Command):
    """
    Edit attributes of an existing edge.

    Syntax:
        edit edge --id=<id> --property Weight=1.0
    """

    def __init__(self, edge_id: str, properties: Dict[str, Any]):
        self._edge_id = str(edge_id)
        self._new_properties = properties
        self._old_properties: Dict[str, Any] = {}

    def execute(self, graph: Graph) -> CommandResult:
        edge = graph.get_edge(self._edge_id)
        if edge is None:
            return CommandResult(False, f"Edge '{self._edge_id}' not found.", graph)

        # Save old values for undo
        for key in self._new_properties:
            self._old_properties[key] = edge.get_attribute(key)

        # Apply new values
        for key, value in self._new_properties.items():
            edge.set_attribute(key, value)

        return CommandResult(
            True,
            f"Edge '{self._edge_id}' updated: {list(self._new_properties.keys())}.",
            graph,
        )

    def undo(self, graph: Graph) -> CommandResult:
        edge = graph.get_edge(self._edge_id)
        if edge is None:
            return CommandResult(False, f"Edge '{self._edge_id}' not found for undo.", graph)

        for key, old_value in self._old_properties.items():
            if old_value is None:
                edge.delete_attribute(key)
            else:
                edge.set_attribute(key, old_value)

        return CommandResult(True, f"Undo: edge '{self._edge_id}' attributes restored.", graph)

    @property
    def supports_undo(self) -> bool:
        return True


class DeleteEdgeCommand(Command):
    """
    Delete an existing edge.

    Syntax:
        delete edge --id=<id>
    """

    def __init__(self, edge_id: str):
        self._edge_id = str(edge_id)
        # Saved state for undo
        self._source_id: Optional[str] = None
        self._target_id: Optional[str] = None
        self._directed: bool = True
        self._attrs: Dict[str, Any] = {}

    def execute(self, graph: Graph) -> CommandResult:
        edge = graph.get_edge(self._edge_id)
        if edge is None:
            return CommandResult(False, f"Edge '{self._edge_id}' not found.", graph)

        # Save for undo
        self._source_id = edge.source_node.node_id
        self._target_id = edge.target_node.node_id
        self._directed = edge.is_directed()
        self._attrs = edge.get_all_attributes()

        graph.remove_edge(self._edge_id)
        return CommandResult(True, f"Edge '{self._edge_id}' deleted.", graph)

    def undo(self, graph: Graph) -> CommandResult:
        if graph.get_edge(self._edge_id) is not None:
            return CommandResult(False, f"Edge '{self._edge_id}' already exists.", graph)

        source = graph.get_node(self._source_id)
        target = graph.get_node(self._target_id)

        if source is None or target is None:
            return CommandResult(
                False,
                f"Cannot undo: endpoint nodes no longer exist.",
                graph,
            )

        direction = EdgeDirection.DIRECTED if self._directed else EdgeDirection.UNDIRECTED
        edge = Edge(self._edge_id, source, target, direction, **self._attrs)
        graph.add_edge(edge)
        return CommandResult(True, f"Undo: edge '{self._edge_id}' restored.", graph)

    @property
    def supports_undo(self) -> bool:
        return True


# ═════════════════════════════════════════════════════════════════
#  QUERY COMMANDS (filter / search)
# ═════════════════════════════════════════════════════════════════

class FilterCommand(Command):
    """
    Apply a filter to the current graph.

    Syntax:
        filter 'Age>30 && Height>=150'
        filter Age >= 30
    """

    def __init__(self, query: str):
        self._query = query

    def execute(self, graph: Graph) -> CommandResult:
        from core.services.filter_service import FilterService
        try:
            svc = FilterService()
            result_graph = svc.filter(graph, self._query)
            return CommandResult(
                True,
                f"Filter '{self._query}' applied: "
                f"{result_graph.get_number_of_nodes()} node(s), "
                f"{result_graph.get_number_of_edges()} edge(s) remaining.",
                result_graph,
            )
        except Exception as e:
            return CommandResult(False, f"Filter error: {e}", graph)


class SearchCommand(Command):
    """
    Apply a search to the current graph.

    Syntax:
        search 'Name=Tom'
        search Age
    """

    def __init__(self, query: str):
        self._query = query

    def execute(self, graph: Graph) -> CommandResult:
        from core.services.search_service import SearchService
        try:
            svc = SearchService()
            result_graph = svc.search(graph, self._query)
            return CommandResult(
                True,
                f"Search '{self._query}': "
                f"{result_graph.get_number_of_nodes()} node(s), "
                f"{result_graph.get_number_of_edges()} edge(s) found.",
                result_graph,
            )
        except Exception as e:
            return CommandResult(False, f"Search error: {e}", graph)


# ═════════════════════════════════════════════════════════════════
#  GRAPH-LEVEL COMMANDS
# ═════════════════════════════════════════════════════════════════

class ClearCommand(Command):
    """
    Clear the entire graph (remove all nodes and edges).

    Syntax:
        clear
    """

    def __init__(self):
        self._backup: Optional[Graph] = None

    def execute(self, graph: Graph) -> CommandResult:
        self._backup = deepcopy(graph)
        # Remove all edges first, then all nodes
        for edge_id in list(graph.edges.keys()):
            graph.remove_edge(edge_id)
        for node_id in list(graph.nodes.keys()):
            graph.remove_node(node_id)

        return CommandResult(
            True,
            "Graph cleared.",
            graph,
        )

    def undo(self, graph: Graph) -> CommandResult:
        if self._backup is None:
            return CommandResult(False, "No backup available for undo.", graph)
        return CommandResult(True, "Undo: graph restored.", self._backup)

    @property
    def supports_undo(self) -> bool:
        return True


class UndoCommand(Command):
    """
    Undo the last command.  Handled specially by ``CommandProcessor``.

    Syntax:
        undo
    """

    def execute(self, graph: Graph) -> CommandResult:
        # The actual undo logic is in CommandProcessor
        return CommandResult(True, "Undo delegated to processor.", graph)


class ResetCommand(Command):
    """
    Reset the graph to its original state (from the workspace).

    Syntax:
        reset
    """

    def execute(self, graph: Graph) -> CommandResult:
        # Actual reset is handled by CommandProcessor (needs workspace access)
        return CommandResult(True, "Reset delegated to processor.", graph)


# ═════════════════════════════════════════════════════════════════
#  INFORMATIONAL COMMANDS (no graph mutation)
# ═════════════════════════════════════════════════════════════════

class InfoCommand(Command):
    """
    Display details about a node or edge.

    Syntax:
        info node <id>
        info edge <id>
        info   (shows graph summary)
    """

    def __init__(self, target_type: Optional[str] = None,
                 target_id: Optional[str] = None):
        self._target_type = target_type      # "node", "edge", or None
        self._target_id = target_id

    def execute(self, graph: Graph) -> CommandResult:
        if self._target_type is None:
            # Graph summary
            msg = (
                f"Graph '{graph.graph_id}': "
                f"{graph.get_number_of_nodes()} node(s), "
                f"{graph.get_number_of_edges()} edge(s), "
                f"has_cycle={graph.has_cycle()}"
            )
            return CommandResult(True, msg, graph)

        if self._target_type == "node":
            node = graph.get_node(self._target_id)
            if node is None:
                return CommandResult(False, f"Node '{self._target_id}' not found.", graph)
            attrs_str = "\n".join(
                f"  {k} = {v} ({node.attribute_types.get(k, '?').value if hasattr(node.attribute_types.get(k, '?'), 'value') else '?'})"
                for k, v in node.attributes.items()
            )
            msg = f"Node '{self._target_id}':\n{attrs_str}" if attrs_str else f"Node '{self._target_id}': (no attributes)"
            return CommandResult(True, msg, graph)

        if self._target_type == "edge":
            edge = graph.get_edge(self._target_id)
            if edge is None:
                return CommandResult(False, f"Edge '{self._target_id}' not found.", graph)
            arrow = "->" if edge.is_directed() else "--"
            attrs_str = "\n".join(
                f"  {k} = {v}" for k, v in edge.attributes.items()
            )
            msg = (
                f"Edge '{self._target_id}': "
                f"{edge.source_node.node_id} {arrow} {edge.target_node.node_id}"
            )
            if attrs_str:
                msg += f"\n{attrs_str}"
            return CommandResult(True, msg, graph)

        return CommandResult(False, f"Unknown target type: '{self._target_type}'.", graph)


class ListCommand(Command):
    """
    List all nodes or edges in the graph.

    Syntax:
        list nodes
        list edges
        list   (lists both)
    """

    def __init__(self, target: Optional[str] = None):
        self._target = target  # "nodes", "edges", or None

    def execute(self, graph: Graph) -> CommandResult:
        lines: List[str] = []

        if self._target in (None, "nodes"):
            lines.append(f"── Nodes ({graph.get_number_of_nodes()}) ──")
            for node in graph.get_all_nodes():
                attr_summary = ", ".join(f"{k}={v}" for k, v in node.attributes.items())
                lines.append(f"  [{node.node_id}] {attr_summary}")

        if self._target in (None, "edges"):
            lines.append(f"── Edges ({graph.get_number_of_edges()}) ──")
            for edge in graph.get_all_edges():
                arrow = "->" if edge.is_directed() else "--"
                attr_summary = ", ".join(f"{k}={v}" for k, v in edge.attributes.items())
                line = f"  [{edge.edge_id}] {edge.source_node.node_id} {arrow} {edge.target_node.node_id}"
                if attr_summary:
                    line += f"  ({attr_summary})"
                lines.append(line)

        msg = "\n".join(lines) if lines else "Graph is empty."
        return CommandResult(True, msg, graph)


class HelpCommand(Command):
    """
    Display available CLI commands.

    Syntax:
        help
    """

    def execute(self, graph: Graph) -> CommandResult:
        help_text = """
Available commands:
───────────────────────────────────────────────────────
  create node --id=<id> [--property Key=Value ...]
      Create a new node with optional attributes.

  create edge --id=<id> [--directed|--undirected]
               [--property Key=Value ...] <source_id> <target_id>
      Create a new edge between two nodes.

  edit node --id=<id> --property Key=Value [...]
      Update attributes of an existing node.

  edit edge --id=<id> --property Key=Value [...]
      Update attributes of an existing edge.

  delete node --id=<id>
      Delete a node (must have no connected edges).

  delete edge --id=<id>
      Delete an edge.

  filter '<attribute> <operator> <value>'
      Filter graph nodes. Operators: ==, !=, >, >=, <, <=
      Example: filter Age >= 30

  search '<query>'
      Search by attribute name or value.
      Example: search Name=Alice   |   search Age

  clear
      Remove all nodes and edges from the graph.

  undo
      Undo the last command.

  reset
      Reset graph to its original state.

  info [node|edge] [<id>]
      Show details about a node, edge, or the whole graph.

  list [nodes|edges]
      List all nodes, edges, or both.

  help
      Show this help text.
───────────────────────────────────────────────────────
""".strip()
        return CommandResult(True, help_text, graph)
