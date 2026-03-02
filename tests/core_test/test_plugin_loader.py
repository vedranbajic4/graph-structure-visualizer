# tests/core_test/test_plugin_loader.py
"""
Tests for PluginLoader — generic plugin discovery via entry_points.

Covers:
    • load_all discovers and instantiates plugins
    • get by name
    • get_names returns sorted list
    • reload clears cache and re-discovers
    • __contains__ / __len__
    • Invalid plugin (wrong base class) is skipped
    • Failed plugin load is logged and skipped
    • Empty entry_points (no plugins installed)
    • Generic type safety (same loader works for different plugin types)
"""
import pytest
from unittest.mock import patch, MagicMock

from api.plugins.base import DataSourcePlugin, VisualizerPlugin
from api.models.graph import Graph

from graph_platform.plugin_loader import (
    PluginLoader,
    create_data_source_loader,
    create_visualizer_loader,
    DATA_SOURCE_EP_GROUP,
    VISUALIZER_EP_GROUP,
)


# ── Mock plugin classes ──────────────────────────────────────────

class MockDataSourcePlugin(DataSourcePlugin):
    def get_plugin_name(self) -> str:
        return "mock_ds"

    def parse(self, file_path: str) -> Graph:
        return Graph("mock")


class MockVisualizerPlugin(VisualizerPlugin):
    def get_plugin_name(self) -> str:
        return "mock_vis"

    def visualize(self, graph: Graph) -> str:
        return "<div>mock</div>"


class NotAPlugin:
    """Class that does NOT subclass any plugin ABC."""
    pass


# ── Helper to create mock entry points ───────────────────────────

def _make_ep(name: str, cls, group: str):
    """Create a mock entry point that returns cls on load()."""
    ep = MagicMock()
    ep.name = name
    ep.group = group
    ep.load.return_value = cls
    return ep


def _mock_entry_points_factory(eps_list):
    """Create a side_effect for importlib.metadata.entry_points
    that returns a mock with .select() method."""
    def _entry_points():
        mock_result = MagicMock()
        mock_result.select = lambda group: [ep for ep in eps_list if ep.group == group]
        mock_result.__iter__ = lambda self: iter(eps_list)
        return mock_result
    return _entry_points


# ═════════════════════════════════════════════════════════════════
#  BASIC OPERATIONS
# ═════════════════════════════════════════════════════════════════

class TestBasicOperations:

    def test_load_all_discovers_plugins(self):
        eps = [_make_ep("mock", MockDataSourcePlugin, DATA_SOURCE_EP_GROUP)]
        with patch("importlib.metadata.entry_points", _mock_entry_points_factory(eps)):
            loader = PluginLoader(DataSourcePlugin, DATA_SOURCE_EP_GROUP)
            plugins = loader.load_all()
            assert "mock" in plugins
            assert isinstance(plugins["mock"], MockDataSourcePlugin)

    def test_load_all_caches_result(self):
        eps = [_make_ep("mock", MockDataSourcePlugin, DATA_SOURCE_EP_GROUP)]
        with patch("importlib.metadata.entry_points", _mock_entry_points_factory(eps)):
            loader = PluginLoader(DataSourcePlugin, DATA_SOURCE_EP_GROUP)
            p1 = loader.load_all()
            p2 = loader.load_all()
            assert p1 is p2  # Same dict object, cached

    def test_get_by_name(self):
        eps = [_make_ep("json", MockDataSourcePlugin, DATA_SOURCE_EP_GROUP)]
        with patch("importlib.metadata.entry_points", _mock_entry_points_factory(eps)):
            loader = PluginLoader(DataSourcePlugin, DATA_SOURCE_EP_GROUP)
            plugin = loader.get("json")
            assert plugin is not None
            assert isinstance(plugin, MockDataSourcePlugin)

    def test_get_returns_none_for_unknown(self):
        with patch("importlib.metadata.entry_points", _mock_entry_points_factory([])):
            loader = PluginLoader(DataSourcePlugin, DATA_SOURCE_EP_GROUP)
            assert loader.get("nonexistent") is None

    def test_get_names_sorted(self):
        eps = [
            _make_ep("xml", MockDataSourcePlugin, DATA_SOURCE_EP_GROUP),
            _make_ep("json", MockDataSourcePlugin, DATA_SOURCE_EP_GROUP),
            _make_ep("csv", MockDataSourcePlugin, DATA_SOURCE_EP_GROUP),
        ]
        with patch("importlib.metadata.entry_points", _mock_entry_points_factory(eps)):
            loader = PluginLoader(DataSourcePlugin, DATA_SOURCE_EP_GROUP)
            names = loader.get_names()
            assert names == ["csv", "json", "xml"]


# ═════════════════════════════════════════════════════════════════
#  RELOAD
# ═════════════════════════════════════════════════════════════════

class TestReload:

    def test_reload_clears_cache(self):
        eps = [_make_ep("mock", MockDataSourcePlugin, DATA_SOURCE_EP_GROUP)]
        with patch("importlib.metadata.entry_points", _mock_entry_points_factory(eps)):
            loader = PluginLoader(DataSourcePlugin, DATA_SOURCE_EP_GROUP)
            p1 = loader.load_all()
            old_instance = p1["mock"]
            p2 = loader.reload()
            # After reload, the dict is repopulated with fresh instances
            assert "mock" in p2
            assert p2["mock"] is not old_instance

    def test_reload_picks_up_new_plugins(self):
        eps1 = [_make_ep("old", MockDataSourcePlugin, DATA_SOURCE_EP_GROUP)]
        eps2 = [
            _make_ep("old", MockDataSourcePlugin, DATA_SOURCE_EP_GROUP),
            _make_ep("new", MockDataSourcePlugin, DATA_SOURCE_EP_GROUP),
        ]
        with patch("importlib.metadata.entry_points", _mock_entry_points_factory(eps1)):
            loader = PluginLoader(DataSourcePlugin, DATA_SOURCE_EP_GROUP)
            loader.load_all()
            assert len(loader) == 1

        with patch("importlib.metadata.entry_points", _mock_entry_points_factory(eps2)):
            loader.reload()
            assert len(loader) == 2


# ═════════════════════════════════════════════════════════════════
#  DUNDER METHODS
# ═════════════════════════════════════════════════════════════════

class TestDunderMethods:

    def test_len(self):
        eps = [
            _make_ep("a", MockDataSourcePlugin, DATA_SOURCE_EP_GROUP),
            _make_ep("b", MockDataSourcePlugin, DATA_SOURCE_EP_GROUP),
        ]
        with patch("importlib.metadata.entry_points", _mock_entry_points_factory(eps)):
            loader = PluginLoader(DataSourcePlugin, DATA_SOURCE_EP_GROUP)
            assert len(loader) == 2

    def test_contains(self):
        eps = [_make_ep("json", MockDataSourcePlugin, DATA_SOURCE_EP_GROUP)]
        with patch("importlib.metadata.entry_points", _mock_entry_points_factory(eps)):
            loader = PluginLoader(DataSourcePlugin, DATA_SOURCE_EP_GROUP)
            assert "json" in loader
            assert "xml" not in loader

    def test_repr(self):
        eps = [_make_ep("json", MockDataSourcePlugin, DATA_SOURCE_EP_GROUP)]
        with patch("importlib.metadata.entry_points", _mock_entry_points_factory(eps)):
            loader = PluginLoader(DataSourcePlugin, DATA_SOURCE_EP_GROUP)
            loader.load_all()
            r = repr(loader)
            assert "DataSourcePlugin" in r
            assert "loaded=1" in r

    def test_len_triggers_load(self):
        """__len__ should auto-load if not yet loaded."""
        eps = [_make_ep("x", MockDataSourcePlugin, DATA_SOURCE_EP_GROUP)]
        with patch("importlib.metadata.entry_points", _mock_entry_points_factory(eps)):
            loader = PluginLoader(DataSourcePlugin, DATA_SOURCE_EP_GROUP)
            assert len(loader) == 1  # triggers load_all internally


# ═════════════════════════════════════════════════════════════════
#  ERROR HANDLING
# ═════════════════════════════════════════════════════════════════

class TestErrorHandling:

    def test_wrong_base_class_is_skipped(self):
        """Plugin that doesn't subclass the expected ABC is skipped."""
        eps = [_make_ep("bad", NotAPlugin, DATA_SOURCE_EP_GROUP)]
        with patch("importlib.metadata.entry_points", _mock_entry_points_factory(eps)):
            loader = PluginLoader(DataSourcePlugin, DATA_SOURCE_EP_GROUP)
            plugins = loader.load_all()
            assert "bad" not in plugins
            assert len(plugins) == 0

    def test_failed_load_is_skipped(self):
        """Plugin that raises on load is skipped."""
        ep = MagicMock()
        ep.name = "broken"
        ep.group = DATA_SOURCE_EP_GROUP
        ep.load.side_effect = ImportError("broken dependency")
        with patch("importlib.metadata.entry_points", _mock_entry_points_factory([ep])):
            loader = PluginLoader(DataSourcePlugin, DATA_SOURCE_EP_GROUP)
            plugins = loader.load_all()
            assert "broken" not in plugins

    def test_empty_entry_points(self):
        with patch("importlib.metadata.entry_points", _mock_entry_points_factory([])):
            loader = PluginLoader(DataSourcePlugin, DATA_SOURCE_EP_GROUP)
            plugins = loader.load_all()
            assert plugins == {}

    def test_plugin_init_failure_is_skipped(self):
        """Plugin class that raises in __init__ is skipped."""
        class FailingPlugin(DataSourcePlugin):
            def __init__(self):
                raise RuntimeError("init failed")
            def get_plugin_name(self): return "fail"
            def parse(self, fp): return Graph("x")

        eps = [_make_ep("fail", FailingPlugin, DATA_SOURCE_EP_GROUP)]
        with patch("importlib.metadata.entry_points", _mock_entry_points_factory(eps)):
            loader = PluginLoader(DataSourcePlugin, DATA_SOURCE_EP_GROUP)
            plugins = loader.load_all()
            assert "fail" not in plugins


# ═════════════════════════════════════════════════════════════════
#  GENERIC TYPE SAFETY
# ═════════════════════════════════════════════════════════════════

class TestGenericTypeSafety:

    def test_data_source_loader_only_accepts_data_source(self):
        """A visualizer plugin in the data-source group should be rejected."""
        eps = [_make_ep("wrong", MockVisualizerPlugin, DATA_SOURCE_EP_GROUP)]
        with patch("importlib.metadata.entry_points", _mock_entry_points_factory(eps)):
            loader = PluginLoader(DataSourcePlugin, DATA_SOURCE_EP_GROUP)
            plugins = loader.load_all()
            assert "wrong" not in plugins

    def test_visualizer_loader_only_accepts_visualizer(self):
        """A data-source plugin in the visualizer group should be rejected."""
        eps = [_make_ep("wrong", MockDataSourcePlugin, VISUALIZER_EP_GROUP)]
        with patch("importlib.metadata.entry_points", _mock_entry_points_factory(eps)):
            loader = PluginLoader(VisualizerPlugin, VISUALIZER_EP_GROUP)
            plugins = loader.load_all()
            assert "wrong" not in plugins

    def test_visualizer_loader_accepts_visualizer(self):
        eps = [_make_ep("simple", MockVisualizerPlugin, VISUALIZER_EP_GROUP)]
        with patch("importlib.metadata.entry_points", _mock_entry_points_factory(eps)):
            loader = PluginLoader(VisualizerPlugin, VISUALIZER_EP_GROUP)
            plugins = loader.load_all()
            assert "simple" in plugins
            assert isinstance(plugins["simple"], MockVisualizerPlugin)


# ═════════════════════════════════════════════════════════════════
#  FACTORY FUNCTIONS
# ═════════════════════════════════════════════════════════════════

class TestFactoryFunctions:

    def test_create_data_source_loader(self):
        loader = create_data_source_loader()
        assert loader._base_class is DataSourcePlugin
        assert loader._group == DATA_SOURCE_EP_GROUP

    def test_create_visualizer_loader(self):
        loader = create_visualizer_loader()
        assert loader._base_class is VisualizerPlugin
        assert loader._group == VISUALIZER_EP_GROUP