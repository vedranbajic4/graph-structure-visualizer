"""
    GraphPlatform — the central orchestrator of the application.

    Design Patterns applied
    ───────────────────────
    • Singleton          – one platform instance per process
                           (via ``GraphPlatform.get_instance()``).
    • Strategy           – pluggable data sources and visualizers.
    • Repository         – ``_workspaces`` dict hides storage details.
    • Facade             – single entry-point for the web layer;
                           hides plugin loading, workspace management,
                           filter/search delegation, and serialization.
    • Observer (hooks)   – ``_listeners`` dict for future view-sync
                           notifications (Main View ↔ Tree View ↔ Bird View).

    Genericity (Genericnost)
    ────────────────────────
    • Uses ``PluginLoader[TPlugin]`` for type-safe plugin discovery.
    • Uses ``GraphQueryService[TQuery]`` in services.
    • ``GraphSerializer`` accepts any ``SerializationConfig`` strategy.
"""
import logging
from typing import Dict, List, Optional, Callable, Any

from api.api.models.graph import Graph
from api.api.plugins.base import DataSourcePlugin, VisualizerPlugin

from .config import PlatformConfig, SerializationConfig
from .workspace import Workspace
from .plugin_loader import (
    PluginLoader,
    create_data_source_loader,
    create_visualizer_loader,
)

logger = logging.getLogger(__name__)


# ── Observer event types ─────────────────────────────────────────
EVENT_WORKSPACE_CREATED = "workspace_created"
EVENT_WORKSPACE_SWITCHED = "workspace_switched"
EVENT_WORKSPACE_REMOVED = "workspace_removed"
EVENT_GRAPH_UPDATED = "graph_updated"
EVENT_NODE_SELECTED = "node_selected"


class GraphPlatform:
    """
    Central orchestrator — Facade for the entire platform.

    Manages:
        • Plugin discovery and loading.
        • Workspace lifecycle (create, switch, remove, list).
        • Graph loading, visualization, filter, search.
        • Serialization / deserialization with configurable fields.
        • Observer hooks for view synchronization.
    """

    _instance: Optional['GraphPlatform'] = None

    # ── Singleton ────────────────────────────────────────────────

    @classmethod
    def get_instance(cls, config: Optional[PlatformConfig] = None) -> 'GraphPlatform':
        """
        Return the singleton platform instance, creating it on first call.

        Args:
            config: Optional custom config (only used on first call).
        """
        if cls._instance is None:
            cls._instance = cls(config or PlatformConfig())
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Destroy the singleton (useful for testing)."""
        cls._instance = None

    # ── Constructor ──────────────────────────────────────────────

    def __init__(self, config: Optional[PlatformConfig] = None):
        """
        Initialize the platform.  Prefer ``get_instance()`` for singleton access.

        Args:
            config: Platform configuration (serialization, defaults, etc.).
        """
        self._config: PlatformConfig = config or PlatformConfig()

        # Plugin loaders (generic)
        self._ds_loader: PluginLoader[DataSourcePlugin] = create_data_source_loader()
        self._vis_loader: PluginLoader[VisualizerPlugin] = create_visualizer_loader()

        # Workspace repository
        self._workspaces: Dict[str, Workspace] = {}
        self._active_workspace_id: Optional[str] = None

        # Services (imported here to avoid circular imports)
        from core.services.filter_service import FilterService
        from core.services.search_service import SearchService
        from core.services.serialization_service import GraphSerializer

        self._filter_service = FilterService()
        self._search_service = SearchService()
        self._serializer = GraphSerializer(self._config.serialization)

        # Observer listeners: event_name → [callback, ...]
        self._listeners: Dict[str, List[Callable[..., Any]]] = {}

        logger.info("GraphPlatform initialized.")

    # ── Configuration ────────────────────────────────────────────

    @property
    def config(self) -> PlatformConfig:
        return self._config

    @config.setter
    def config(self, value: PlatformConfig) -> None:
        self._config = value
        if hasattr(self, '_serializer'):
            self._serializer.config = value.serialization

    @property
    def serialization_config(self) -> SerializationConfig:
        return self._config.serialization

    @serialization_config.setter
    def serialization_config(self, value: SerializationConfig) -> None:
        self._config.serialization = value
        self._serializer.config = value

    # ── Plugin discovery ─────────────────────────────────────────

    def get_data_source_plugins(self) -> Dict[str, DataSourcePlugin]:
        """Return all discovered data-source plugins {name: instance}."""
        return self._ds_loader.load_all()

    def get_visualizer_plugins(self) -> Dict[str, VisualizerPlugin]:
        """Return all discovered visualizer plugins {name: instance}."""
        return self._vis_loader.load_all()

    def get_data_source_names(self) -> List[str]:
        """Sorted list of installed data-source plugin names."""
        return self._ds_loader.get_names()

    def get_visualizer_names(self) -> List[str]:
        """Sorted list of installed visualizer plugin names."""
        return self._vis_loader.get_names()

    def get_data_source(self, name: str) -> Optional[DataSourcePlugin]:
        """Get a specific data-source plugin by name."""
        return self._ds_loader.get(name)

    def get_visualizer(self, name: str) -> Optional[VisualizerPlugin]:
        """Get a specific visualizer plugin by name."""
        return self._vis_loader.get(name)

    def reload_plugins(self) -> None:
        """Force re-discovery of all plugins."""
        self._ds_loader.reload()
        self._vis_loader.reload()
        logger.info("Plugins reloaded: %d data sources, %d visualizers",
                     len(self._ds_loader), len(self._vis_loader))

    # ── Graph loading ────────────────────────────────────────────

    def load_graph(self, plugin_name: str, file_path: str,
                   workspace_name: Optional[str] = None) -> Workspace:
        """
        Load a graph from a data source and create a new workspace.

        Args:
            plugin_name:    Entry-point name of the data-source plugin.
            file_path:      Path / URI to load.
            workspace_name: Optional human-readable workspace name.

        Returns:
            The newly created Workspace.

        Raises:
            ValueError: If the plugin is not found.
        """
        plugin = self._ds_loader.get(plugin_name)
        if plugin is None:
            raise ValueError(
                f"Data source plugin '{plugin_name}' not found. "
                f"Available: {self._ds_loader.get_names()}"
            )

        graph = plugin.parse(file_path)
        ws = self.create_workspace(
            graph,
            data_source=plugin_name,
            file_path=file_path,
            name=workspace_name,
        )
        logger.info("Graph loaded via '%s' from '%s' → workspace %s",
                     plugin_name, file_path, ws.workspace_id[:8])
        return ws

    # ── Workspace management ─────────────────────────────────────

    def create_workspace(
        self,
        graph: Graph,
        data_source: str = "",
        file_path: str = "",
        name: Optional[str] = None,
    ) -> Workspace:
        """
        Create a workspace from an already-constructed graph.

        Args:
            graph:       Populated Graph instance.
            data_source: Plugin name that produced the graph.
            file_path:   Data file path.
            name:        Human-readable label.

        Returns:
            The newly created and activated Workspace.
        """
        ws = Workspace(
            graph,
            data_source=data_source,
            file_path=file_path,
            name=name,
            max_history=self._config.max_history_depth,
        )
        self._workspaces[ws.workspace_id] = ws
        self._active_workspace_id = ws.workspace_id
        self._notify(EVENT_WORKSPACE_CREATED, workspace=ws)
        return ws

    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        """Get a workspace by its ID."""
        return self._workspaces.get(workspace_id)

    def get_active_workspace(self) -> Optional[Workspace]:
        """Get the currently active workspace."""
        if self._active_workspace_id is None:
            return None
        return self._workspaces.get(self._active_workspace_id)

    def set_active_workspace(self, workspace_id: str) -> Workspace:
        """
        Switch the active workspace.

        Raises:
            ValueError: If the workspace ID does not exist.
        """
        if workspace_id not in self._workspaces:
            raise ValueError(f"Workspace '{workspace_id}' not found.")
        self._active_workspace_id = workspace_id
        ws = self._workspaces[workspace_id]
        self._notify(EVENT_WORKSPACE_SWITCHED, workspace=ws)
        return ws

    def remove_workspace(self, workspace_id: str) -> None:
        """Remove a workspace by its ID."""
        if workspace_id not in self._workspaces:
            return
        del self._workspaces[workspace_id]
        if self._active_workspace_id == workspace_id:
            # Activate the next available or set None
            if self._workspaces:
                self._active_workspace_id = next(iter(self._workspaces))
            else:
                self._active_workspace_id = None
        self._notify(EVENT_WORKSPACE_REMOVED, workspace_id=workspace_id)

    def list_workspaces(self) -> List[dict]:
        """Return metadata dicts for all workspaces."""
        return [ws.to_dict() for ws in self._workspaces.values()]

    # ── Graph operations on active workspace ─────────────────────

    def filter_graph(self, query: str,
                     workspace_id: Optional[str] = None) -> Graph:
        """
        Apply a filter on the (active or specified) workspace.

        Returns:
            The resulting subgraph.

        Raises:
            RuntimeError: If no workspace is active / found.
        """
        ws = self._resolve_workspace(workspace_id)
        result = ws.apply_filter(query)
        self._notify(EVENT_GRAPH_UPDATED, workspace=ws, graph=result)
        return result

    def search_graph(self, query: str,
                     workspace_id: Optional[str] = None) -> Graph:
        """
        Apply a search on the (active or specified) workspace.

        Returns:
            The resulting subgraph.
        """
        ws = self._resolve_workspace(workspace_id)
        result = ws.apply_search(query)
        self._notify(EVENT_GRAPH_UPDATED, workspace=ws, graph=result)
        return result

    def undo(self, workspace_id: Optional[str] = None) -> Optional[Graph]:
        """Undo the last filter / search operation."""
        ws = self._resolve_workspace(workspace_id)
        result = ws.undo()
        if result is not None:
            self._notify(EVENT_GRAPH_UPDATED, workspace=ws, graph=result)
        return result

    def reset_workspace(self, workspace_id: Optional[str] = None) -> Graph:
        """Reset workspace to the original graph."""
        ws = self._resolve_workspace(workspace_id)
        result = ws.reset()
        self._notify(EVENT_GRAPH_UPDATED, workspace=ws, graph=result)
        return result

    # ── Visualization ────────────────────────────────────────────

    def visualize(self, visualizer_name: Optional[str] = None,
                  workspace_id: Optional[str] = None) -> str:
        """
        Generate an HTML representation of the current graph
        using the specified (or default) visualizer plugin.

        Args:
            visualizer_name: Entry-point name (e.g. 'simple', 'block').
                             If None, uses ``config.default_visualizer``.
            workspace_id:    Workspace to visualize (defaults to active).

        Returns:
            HTML string generated by the visualizer plugin.

        Raises:
            ValueError:  If no visualizer is found.
            RuntimeError: If no workspace is active.
        """
        ws = self._resolve_workspace(workspace_id)
        name = visualizer_name or self._config.default_visualizer

        if name is None:
            # Pick the first available visualizer
            names = self._vis_loader.get_names()
            if not names:
                raise ValueError("No visualizer plugins installed.")
            name = names[0]

        plugin = self._vis_loader.get(name)
        if plugin is None:
            raise ValueError(
                f"Visualizer plugin '{name}' not found. "
                f"Available: {self._vis_loader.get_names()}"
            )

        return plugin.visualize(ws.current_graph)

    # ── Serialization ────────────────────────────────────────────

    @property
    def serializer(self):
        """Access the graph serializer (configurable via ``serialization_config``)."""
        return self._serializer

    def serialize_graph(self, workspace_id: Optional[str] = None) -> dict:
        """Serialize the current graph of a workspace to a dict."""
        ws = self._resolve_workspace(workspace_id)
        return self._serializer.serialize(ws.current_graph)

    def serialize_graph_json(self, workspace_id: Optional[str] = None) -> str:
        """Serialize the current graph of a workspace to a JSON string."""
        ws = self._resolve_workspace(workspace_id)
        return self._serializer.to_json(ws.current_graph)

    def deserialize_graph(self, data: dict) -> Graph:
        """Deserialize a graph from a dict."""
        return self._serializer.deserialize(data)

    def deserialize_graph_json(self, json_str: str) -> Graph:
        """Deserialize a graph from a JSON string."""
        return self._serializer.from_json(json_str)

    # ── Observer pattern ─────────────────────────────────────────

    def subscribe(self, event: str, callback: Callable[..., Any]) -> None:
        """
        Register a callback for a platform event.

        Events:
            - workspace_created
            - workspace_switched
            - workspace_removed
            - graph_updated
            - node_selected
        """
        self._listeners.setdefault(event, []).append(callback)

    def unsubscribe(self, event: str, callback: Callable[..., Any]) -> None:
        """Remove a previously registered callback."""
        listeners = self._listeners.get(event, [])
        if callback in listeners:
            listeners.remove(callback)

    def _notify(self, event: str, **kwargs: Any) -> None:
        """Fire all callbacks registered for the given event."""
        for cb in self._listeners.get(event, []):
            try:
                cb(**kwargs)
            except Exception as exc:
                logger.error("Observer callback failed for '%s': %s", event, exc)

    # ── Node selection (cross-view sync) ─────────────────────────

    def select_node(self, node_id: str,
                    workspace_id: Optional[str] = None) -> None:
        """
        Signal that a node has been selected in any view.
        Notifies all subscribers so that Main View, Tree View,
        and Bird View can synchronize focus.
        """
        ws = self._resolve_workspace(workspace_id)
        node = ws.current_graph.get_node(node_id)
        if node is not None:
            self._notify(EVENT_NODE_SELECTED,
                         workspace=ws, node_id=node_id, node=node)

    # ── Internal helpers ─────────────────────────────────────────

    def _resolve_workspace(self, workspace_id: Optional[str] = None) -> Workspace:
        """
        Return the requested workspace or the active one.

        Raises:
            RuntimeError: If no workspace can be resolved.
        """
        wid = workspace_id or self._active_workspace_id
        if wid is None:
            raise RuntimeError("No active workspace. Load a graph first.")
        ws = self._workspaces.get(wid)
        if ws is None:
            raise RuntimeError(f"Workspace '{wid}' not found.")
        return ws

    # ── Dunder ───────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"GraphPlatform(workspaces={len(self._workspaces)}, "
            f"data_sources={len(self._ds_loader)}, "
            f"visualizers={len(self._vis_loader)})"
        )
