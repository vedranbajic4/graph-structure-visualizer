"""
    Workspace — a data source combined with active filters and searches.

    Design Pattern: Memento (simplified)
    ─────────────────────────────────────
    The Workspace keeps a history stack of graph snapshots so that the
    user can roll back filter / search operations or reset to the
    original graph.

    Each workspace holds:
        • original_graph  – the unmodified graph from the data source
        • current_graph   – the graph after all applied operations
        • history         – stack of intermediate graph snapshots

    Persistence (optional feature)
    ──────────────────────────────
    ``save()`` / ``load()`` enable persistent workspace storage so a
    user can resume a previous session.
"""
import json
import uuid
import logging
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

from api.models.graph import Graph

from services.filter_service import FilterService
from services.search_service import SearchService

logger = logging.getLogger(__name__)


class Workspace:
    """
    Encapsulates one loaded graph and the chain of filter / search
    operations applied to it.

    Attributes:
        workspace_id:   Unique identifier.
        name:           Human-readable label.
        data_source:    Name of the data-source plugin that produced the graph.
        file_path:      Path / URI of the loaded data file.
        original_graph: The graph as initially loaded (never modified).
        current_graph:  The graph after all applied operations.
    """

    def __init__(
        self,
        graph: Graph,
        data_source: str = "",
        file_path: str = "",
        name: Optional[str] = None,
        max_history: int = 50,
    ):
        self.workspace_id: str = str(uuid.uuid4())
        self.name: str = name or f"Workspace-{self.workspace_id[:8]}"
        self.data_source: str = data_source
        self.file_path: str = file_path

        self._original_graph: Graph = deepcopy(graph)
        self._current_graph: Graph = deepcopy(graph)
        self._history: List[Graph] = []
        self._max_history: int = max_history

        # Services (injected by default; can be replaced for testing)
        self._filter_service = FilterService()
        self._search_service = SearchService()

    # ── Properties ───────────────────────────────────────────────

    @property
    def original_graph(self) -> Graph:
        """The graph as originally loaded (read-only deep copy)."""
        return deepcopy(self._original_graph)

    @property
    def current_graph(self) -> Graph:
        """The graph after all applied operations."""
        return self._current_graph

    @property
    def history_depth(self) -> int:
        """Number of snapshots in the undo history."""
        return len(self._history)

    # ── Mutation operations ──────────────────────────────────────

    def apply_filter(self, query: str) -> Graph:
        """
        Apply a filter to the *current* graph and push a snapshot.

        Args:
            query: Filter expression, e.g. ``"Age >= 30"``.

        Returns:
            The resulting subgraph (also stored as ``current_graph``).
        """
        conditions = [c.strip() for c in query.split('&&')]

        # Evaluate all conditions first so a parse/type error does not leave
        # the workspace in a partially-filtered state.
        result_graph = self._current_graph
        for condition in conditions:
            result_graph = self._filter_service.filter(result_graph, condition)

        self._push_snapshot()
        self._current_graph = result_graph
        logger.info("Workspace %s: filter '%s' applied (%d nodes)",
                     self.workspace_id[:8], query,
                     self._current_graph.get_number_of_nodes())
        return self._current_graph

    def apply_search(self, query: str) -> Graph:
        """
        Apply a search to the *current* graph and push a snapshot.

        Args:
            query: Search expression, e.g. ``"Name=Alice"`` or ``"Age"``.

        Returns:
            The resulting subgraph (also stored as ``current_graph``).
        """
        self._push_snapshot()
        self._current_graph = self._search_service.search(
            self._current_graph, query
        )
        logger.info("Workspace %s: search '%s' applied (%d nodes)",
                     self.workspace_id[:8], query,
                     self._current_graph.get_number_of_nodes())
        return self._current_graph

    def undo(self) -> Optional[Graph]:
        """
        Revert to the previous graph snapshot (one step back).

        Returns:
            The restored graph, or ``None`` if history is empty.
        """
        if not self._history:
            logger.warning("Workspace %s: nothing to undo.", self.workspace_id[:8])
            return None

        self._current_graph = self._history.pop()
        logger.info("Workspace %s: undo (%d nodes)",
                     self.workspace_id[:8],
                     self._current_graph.get_number_of_nodes())
        return self._current_graph

    def reset(self) -> Graph:
        """
        Reset the workspace to the original graph, clearing all history.

        Returns:
            A deep copy of the original graph.
        """
        self._history.clear()
        self._current_graph = deepcopy(self._original_graph)
        logger.info("Workspace %s: reset to original (%d nodes)",
                     self.workspace_id[:8],
                     self._current_graph.get_number_of_nodes())
        return self._current_graph

    # ── Snapshot management ──────────────────────────────────────

    def _push_snapshot(self) -> None:
        """Save the current graph state before a mutation."""
        if len(self._history) >= self._max_history:
            self._history.pop(0)  # Drop oldest snapshot
        self._history.append(deepcopy(self._current_graph))

    def _pop_snapshot(self) -> None:
        """Remove the most recent snapshot (rolls back a pre-emptive push on command failure)."""
        if self._history:
            self._history.pop()

    # ── Convenience ──────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialize workspace metadata (not the full graph)."""
        return {
            'workspace_id': self.workspace_id,
            'name': self.name,
            'data_source': self.data_source,
            'file_path': self.file_path,
            'nodes': self._current_graph.get_number_of_nodes(),
            'edges': self._current_graph.get_number_of_edges(),
            'history_depth': self.history_depth,
        }

    # ── Persistence (optional feature) ──────────────────────────────

    def save(self, directory: str) -> str:
        """
        Persist the workspace to disk so the user can resume later.

        Creates a JSON file containing workspace metadata **and** the
        serialized original + current graphs.

        Args:
            directory: Directory to write the workspace file into.

        Returns:
            Absolute path to the saved file.
        """
        from services.serialization_service import GraphSerializer

        serializer = GraphSerializer()
        data: Dict[str, Any] = {
            'workspace_id': self.workspace_id,
            'name': self.name,
            'data_source': self.data_source,
            'file_path': self.file_path,
            'max_history': self._max_history,
            'original_graph': serializer.serialize(self._original_graph),
            'current_graph': serializer.serialize(self._current_graph),
            'history': [serializer.serialize(g) for g in self._history],
        }

        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)
        file_path = dir_path / f"{self.workspace_id}.json"

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)

        logger.info("Workspace %s saved to %s", self.workspace_id[:8], file_path)
        return str(file_path)

    @classmethod
    def load(cls, file_path: str) -> 'Workspace':
        """
        Restore a workspace from a previously saved JSON file.

        Args:
            file_path: Path to the saved workspace JSON file.

        Returns:
            A fully restored Workspace instance with history.
        """
        from services.serialization_service import GraphSerializer

        serializer = GraphSerializer()

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        original_graph = serializer.deserialize(data['original_graph'])
        current_graph = serializer.deserialize(data['current_graph'])

        ws = cls.__new__(cls)
        ws.workspace_id = data['workspace_id']
        ws.name = data['name']
        ws.data_source = data.get('data_source', '')
        ws.file_path = data.get('file_path', '')
        ws._original_graph = original_graph
        ws._current_graph = current_graph
        ws._max_history = data.get('max_history', 50)
        ws._history = [serializer.deserialize(g) for g in data.get('history', [])]
        ws._filter_service = FilterService()
        ws._search_service = SearchService()

        logger.info("Workspace %s loaded from %s", ws.workspace_id[:8], file_path)
        return ws

    def __repr__(self) -> str:
        return (
            f"Workspace(id={self.workspace_id[:8]}, "
            f"name='{self.name}', "
            f"source='{self.data_source}', "
            f"nodes={self._current_graph.get_number_of_nodes()}, "
            f"edges={self._current_graph.get_number_of_edges()})"
        )
