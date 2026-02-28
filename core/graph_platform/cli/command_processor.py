"""
    CommandProcessor — parses raw CLI strings and dispatches commands.

    Design Patterns
    ───────────────
    • Interpreter   – parses the CLI text into structured ``Command`` objects.
    • Invoker       – maintains a command history for undo.
    • Facade        – single ``process(text)`` entry-point hides all parsing.

    The processor is aware of the current graph on the Main View
    (accessed through the Workspace).  Every mutating command is
    recorded in an undo stack so the user can step back.
"""
from __future__ import annotations

import logging
import re
import shlex
from typing import List, Optional, Tuple, Dict, Any

from api.api.models.graph import Graph

from .commands import (
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

logger = logging.getLogger(__name__)


class CommandProcessor:
    """
    Parses raw CLI input, creates ``Command`` objects, executes them
    on the active graph, and maintains an undo history.

    Usage from the web layer:
        processor = CommandProcessor(workspace)
        result = processor.process("create node --id=1 --property Name=Alice")
    """

    def __init__(self):
        """
        Initialize the processor.
        """
        self._undo_stack: List[Tuple[Command, Graph]] = []
        self._max_undo = 50

    # ── Public API ───────────────────────────────────────────────

    def process(self, text: str, graph: Graph) -> CommandResult:
        """
        Parse and execute a single CLI command on the given graph.

        Args:
            text:  Raw command string from the user.
            graph: The current graph on the Main View.

        Returns:
            ``CommandResult`` with success status, message, and
            (possibly new) graph reference.
        """
        text = self._strip_comments(text).strip()
        if not text:
            return CommandResult(False, "Empty command. Type 'help' for usage.", graph)

        try:
            command = self._parse(text)
        except ValueError as e:
            return CommandResult(False, f"Parse error: {e}", graph)

        return self._execute(command, graph)

    def get_undo_depth(self) -> int:
        """Number of commands that can be undone."""
        return len(self._undo_stack)

    # ── Execution engine ─────────────────────────────────────────

    def _execute(self, command: Command, graph: Graph) -> CommandResult:
        """Execute a parsed command and manage the undo stack."""

        # --- Special: undo ---
        if isinstance(command, UndoCommand):
            return self._do_undo(graph)

        # --- Special: reset (needs access to the original, handled externally) ---
        if isinstance(command, ResetCommand):
            return CommandResult(
                True,
                "RESET",  # Sentinel for the platform / web layer
                graph,
                data={"action": "reset"},
            )

        # --- Special: filter / search produce a NEW graph ---
        if isinstance(command, (FilterCommand, SearchCommand)):
            result = command.execute(graph)
            if result.success and result.graph is not None:
                # Push old graph for undo
                self._push_undo(command, graph)
            return result

        # --- Standard mutating commands ---
        from copy import deepcopy
        snapshot = deepcopy(graph) if command.supports_undo else None

        result = command.execute(graph)

        if result.success and command.supports_undo and snapshot is not None:
            self._push_undo(command, snapshot)

        return result

    def _do_undo(self, graph: Graph) -> CommandResult:
        """Pop the last command and restore the previous graph."""
        if not self._undo_stack:
            return CommandResult(False, "Nothing to undo.", graph)

        command, old_graph = self._undo_stack.pop()
        return CommandResult(
            True,
            f"Undo successful (stack depth: {len(self._undo_stack)}).",
            old_graph,
        )

    def _push_undo(self, command: Command, graph_snapshot: Graph) -> None:
        """Save a command + graph snapshot for potential undo."""
        if len(self._undo_stack) >= self._max_undo:
            self._undo_stack.pop(0)
        self._undo_stack.append((command, graph_snapshot))

    # ── Comment handling ────────────────────────────────────────

    @staticmethod
    def _strip_comments(text: str) -> str:
        """
        Strip inline comments — everything after an unquoted ``#``.

        Handles single- and double-quoted strings so that ``#``
        inside quotes is preserved.

        Example:
            >>> CommandProcessor._strip_comments(
            ...     "create edge --id=1 1 2   # a comment")
            'create edge --id=1 1 2'
        """
        in_single = False
        in_double = False
        for i, ch in enumerate(text):
            if ch == "'" and not in_double:
                in_single = not in_single
            elif ch == '"' and not in_single:
                in_double = not in_double
            elif ch == '#' and not in_single and not in_double:
                return text[:i].rstrip()
        return text

    # ── Parser ───────────────────────────────────────────────────

    def _parse(self, text: str) -> Command:
        """
        Parse raw CLI text into a ``Command`` object.

        Raises:
            ValueError: If the text cannot be parsed.
        """
        # Normalize and tokenize using shlex for proper quote handling
        try:
            tokens = shlex.split(text)
        except ValueError:
            # Fallback: simple split if quotes are malformed
            tokens = text.split()

        if not tokens:
            raise ValueError("Empty command.")

        verb = tokens[0].lower()

        # ── Single-word commands ──
        if verb == "help":
            return HelpCommand()
        if verb == "undo":
            return UndoCommand()
        if verb == "reset":
            return ResetCommand()
        if verb == "clear":
            return ClearCommand()

        # ── filter / search ──
        if verb == "filter":
            query = self._extract_query(tokens[1:])
            return FilterCommand(query)
        if verb == "search":
            query = self._extract_query(tokens[1:])
            return SearchCommand(query)

        # ── list ──
        if verb == "list":
            target = tokens[1].lower() if len(tokens) > 1 else None
            if target not in (None, "nodes", "edges"):
                raise ValueError(f"Unknown list target: '{target}'. Use 'nodes' or 'edges'.")
            return ListCommand(target)

        # ── info ──
        if verb == "info":
            if len(tokens) == 1:
                return InfoCommand()
            target_type = tokens[1].lower() if len(tokens) > 1 else None
            target_id = tokens[2] if len(tokens) > 2 else None
            if target_type not in ("node", "edge"):
                raise ValueError("Usage: info [node|edge] <id>")
            if target_id is None:
                raise ValueError(f"Usage: info {target_type} <id>")
            return InfoCommand(target_type, target_id)

        # ── create / edit / delete ──
        if verb in ("create", "edit", "delete"):
            if len(tokens) < 2:
                raise ValueError(f"Usage: {verb} <node|edge> ...")
            entity = tokens[1].lower()
            remaining = tokens[2:]

            if verb == "create" and entity == "node":
                return self._parse_create_node(remaining)
            if verb == "create" and entity == "edge":
                return self._parse_create_edge(remaining)
            if verb == "edit" and entity == "node":
                return self._parse_edit_node(remaining)
            if verb == "edit" and entity == "edge":
                return self._parse_edit_edge(remaining)
            if verb == "delete" and entity == "node":
                return self._parse_delete(remaining, "node")
            if verb == "delete" and entity == "edge":
                return self._parse_delete(remaining, "edge")

            raise ValueError(f"Unknown entity: '{entity}'. Use 'node' or 'edge'.")

        raise ValueError(f"Unknown command: '{verb}'. Type 'help' for usage.")

    # ── Token parsers ────────────────────────────────────────────

    @staticmethod
    def _extract_id(tokens: List[str]) -> Tuple[str, List[str]]:
        """
        Extract --id=<value> from token list.
        Returns (id_value, remaining_tokens).
        """
        remaining = []
        found_id = None
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token.startswith("--id="):
                found_id = token[5:]
            elif token == "--id" and i + 1 < len(tokens):
                found_id = tokens[i + 1]
                i += 1
            else:
                remaining.append(token)
            i += 1

        if found_id is None:
            raise ValueError("Missing required --id=<value>.")
        return found_id, remaining

    @staticmethod
    def _extract_properties(tokens: List[str]) -> Tuple[Dict[str, Any], List[str]]:
        """
        Extract --property Key=Value pairs from token list.
        Returns (properties_dict, remaining_tokens).
        """
        props: Dict[str, Any] = {}
        remaining: List[str] = []
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token == "--property" and i + 1 < len(tokens):
                kv = tokens[i + 1]
                eq_pos = kv.find("=")
                if eq_pos == -1:
                    raise ValueError(f"Invalid property format: '{kv}'. Expected Key=Value.")
                key = kv[:eq_pos]
                value = kv[eq_pos + 1:]
                props[key] = value
                i += 2
                continue
            elif token.startswith("--property="):
                # --property=Key=Value (less common)
                kv = token[11:]
                eq_pos = kv.find("=")
                if eq_pos == -1:
                    raise ValueError(f"Invalid property format: '{kv}'. Expected Key=Value.")
                key = kv[:eq_pos]
                value = kv[eq_pos + 1:]
                props[key] = value
            else:
                remaining.append(token)
            i += 1

        return props, remaining

    @staticmethod
    def _extract_query(tokens: List[str]) -> str:
        """Join remaining tokens into a query string, stripping quotes."""
        raw = " ".join(tokens)
        # Strip surrounding quotes if present
        if len(raw) >= 2 and raw[0] in ("'", '"') and raw[-1] == raw[0]:
            raw = raw[1:-1]
        return raw.strip()

    # ── Compound parsers ─────────────────────────────────────────

    def _parse_create_node(self, tokens: List[str]) -> CreateNodeCommand:
        node_id, remaining = self._extract_id(tokens)
        props, _ = self._extract_properties(remaining)
        return CreateNodeCommand(node_id, props)

    def _parse_create_edge(self, tokens: List[str]) -> CreateEdgeCommand:
        edge_id, remaining = self._extract_id(tokens)
        props, remaining = self._extract_properties(remaining)

        # Check for --directed / --undirected flags
        directed = True  # default
        positional: List[str] = []
        for tok in remaining:
            if tok == "--directed":
                directed = True
            elif tok == "--undirected":
                directed = False
            elif not tok.startswith("--"):
                positional.append(tok)
            # Skip unknown flags for forward-compat

        # Last two positional tokens are source_id and target_id
        if len(positional) < 2:
            raise ValueError(
                "create edge requires <source_id> <target_id> as positional arguments."
            )
        source_id = positional[-2]
        target_id = positional[-1]

        return CreateEdgeCommand(edge_id, source_id, target_id, directed, props)

    def _parse_edit_node(self, tokens: List[str]) -> EditNodeCommand:
        node_id, remaining = self._extract_id(tokens)
        props, _ = self._extract_properties(remaining)
        if not props:
            raise ValueError("edit node requires at least one --property Key=Value.")
        return EditNodeCommand(node_id, props)

    def _parse_edit_edge(self, tokens: List[str]) -> EditEdgeCommand:
        edge_id, remaining = self._extract_id(tokens)
        props, _ = self._extract_properties(remaining)
        if not props:
            raise ValueError("edit edge requires at least one --property Key=Value.")
        return EditEdgeCommand(edge_id, props)

    def _parse_delete(self, tokens: List[str], entity: str) -> Command:
        entity_id, _ = self._extract_id(tokens)
        if entity == "node":
            return DeleteNodeCommand(entity_id)
        return DeleteEdgeCommand(entity_id)
