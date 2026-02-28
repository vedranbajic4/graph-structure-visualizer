"""
    Generic plugin discovery and loading via entry_points.

    Design Pattern: Service Locator / Registry
    ────────────────────────────────────────────
    Discovers all installed plugins at runtime by scanning Python
    package entry_points.  Each plugin type (data source, visualizer)
    uses a distinct entry-point group.

    Genericity (Genericnost):
    ─────────────────────────
    PluginLoader[TPlugin] is generic over the plugin base class so the
    same loader works for DataSourcePlugin and VisualizerPlugin without
    code duplication.
"""
import importlib.metadata
import logging
from typing import TypeVar, Generic, Type, Dict, List, Optional

from api.api.plugins.base import DataSourcePlugin, VisualizerPlugin

logger = logging.getLogger(__name__)

# Generic type variable bounded to plugin ABCs
TPlugin = TypeVar('TPlugin')

# Entry-point group names (must match setup.py / pyproject.toml)
DATA_SOURCE_EP_GROUP = 'graph_visualizer.data_source'
VISUALIZER_EP_GROUP = 'graph_visualizer.visualizer'


class PluginLoader(Generic[TPlugin]):
    """
    Generic loader that discovers all installed plugins of a given type
    from a specific entry-point group.

    Usage:
        loader = PluginLoader(DataSourcePlugin, 'graph_visualizer.data_source')
        plugins = loader.load_all()          # Dict[str, DataSourcePlugin]
        json_plugin = loader.get('json')     # Optional[DataSourcePlugin]
    """

    def __init__(self, plugin_base_class: Type[TPlugin], group: str):
        """
        Args:
            plugin_base_class: The ABC that every discovered plugin must subclass.
            group:             The entry-point group to scan
                               (e.g. 'graph_visualizer.data_source').
        """
        self._base_class = plugin_base_class
        self._group = group
        self._plugins: Dict[str, TPlugin] = {}
        self._loaded = False

    def load_all(self) -> Dict[str, TPlugin]:
        """
        Discover and instantiate every plugin registered under the group.

        Returns:
            Dict mapping entry-point name → plugin instance.
        """
        if self._loaded:
            return self._plugins

        try:
            entry_points = importlib.metadata.entry_points()

            # Python 3.12+ returns a SelectableGroups; older returns dict
            if hasattr(entry_points, 'select'):
                eps = entry_points.select(group=self._group)
            elif isinstance(entry_points, dict):
                eps = entry_points.get(self._group, [])
            else:
                eps = [ep for ep in entry_points if ep.group == self._group]

            for ep in eps:
                try:
                    plugin_cls = ep.load()
                    if not issubclass(plugin_cls, self._base_class):
                        logger.warning(
                            "Plugin '%s' does not subclass %s — skipped.",
                            ep.name, self._base_class.__name__
                        )
                        continue
                    instance = plugin_cls()
                    self._plugins[ep.name] = instance
                    logger.info("Loaded plugin: %s (%s)", ep.name, plugin_cls.__name__)
                except Exception as exc:
                    logger.error("Failed to load plugin '%s': %s", ep.name, exc)

        except Exception as exc:
            logger.error("Entry-point discovery failed: %s", exc)

        self._loaded = True
        return self._plugins

    def get(self, name: str) -> Optional[TPlugin]:
        """
        Get a specific plugin by its entry-point name.

        Args:
            name: Entry-point name (e.g. 'json', 'simple').

        Returns:
            Plugin instance, or None if not found.
        """
        if not self._loaded:
            self.load_all()
        return self._plugins.get(name)

    def get_names(self) -> List[str]:
        """Return sorted list of all discovered plugin names."""
        if not self._loaded:
            self.load_all()
        return sorted(self._plugins.keys())

    def reload(self) -> Dict[str, TPlugin]:
        """Force re-discovery of plugins (useful after hot-install)."""
        self._plugins.clear()
        self._loaded = False
        return self.load_all()

    def __len__(self) -> int:
        if not self._loaded:
            self.load_all()
        return len(self._plugins)

    def __contains__(self, name: str) -> bool:
        if not self._loaded:
            self.load_all()
        return name in self._plugins

    def __repr__(self) -> str:
        return (
            f"PluginLoader(base={self._base_class.__name__}, "
            f"group='{self._group}', loaded={len(self._plugins)})"
        )


# ── Convenience factory functions ────────────────────────────────

def create_data_source_loader() -> PluginLoader[DataSourcePlugin]:
    """Create a loader for Data Source plugins."""
    return PluginLoader(DataSourcePlugin, DATA_SOURCE_EP_GROUP)


def create_visualizer_loader() -> PluginLoader[VisualizerPlugin]:
    """Create a loader for Visualizer plugins."""
    return PluginLoader(VisualizerPlugin, VISUALIZER_EP_GROUP)
