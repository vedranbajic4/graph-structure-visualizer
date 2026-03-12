"""
    Abstract base classes for plugins.
    Defines the "Contract" that all plugins must follow.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List
from ..models.graph import Graph


@dataclass
class ParameterDef:
    """
    Describes a single required input parameter for a DataSourcePlugin.

    The web layer calls ``plugin.get_parameters()`` to build the input
    form dynamically — so plugins with a file path, an API key, a URL,
    etc. all work without any changes to the platform or web layer.

    Attributes:
        name:        Internal key used in ``parse(**kwargs)``.
        label:       Human-readable field label for the UI.
        description: Optional hint shown below the field.
        required:    Whether the field must be non-empty.
        default:     Optional default value.
    """
    name: str
    label: str
    description: str = ""
    required: bool = True
    default: Any = None


class DataSourcePlugin(ABC):
    """
    Abstract base class for Data Source plugins.
    Pattern: Strategy (for data loading).
    """

    @abstractmethod
    def get_plugin_name(self) -> str:
        """
        Returns the unique name of the plugin.
        Example: "JSON Parser"
        """
        pass

    @abstractmethod
    def get_parameters(self) -> List[ParameterDef]:
        """
        Return the list of input parameters this plugin requires.

        The web layer renders a form from this list, then passes the
        submitted values as keyword arguments to ``parse()``.

        Example (file-based plugin)::

            return [ParameterDef(name="file_path", label="File Path")]

        Example (API-based plugin)::

            return [
                ParameterDef(name="api_url",  label="API URL"),
                ParameterDef(name="api_key",  label="API Key", description="Twitter Bearer Token"),
            ]
        """
        pass

    @abstractmethod
    def parse(self, **kwargs) -> Graph:
        """
        Parse the data source and return a Graph.

        Keyword arguments correspond to the parameter names declared in
        ``get_parameters()``.  For example, a file-based plugin receives
        ``file_path=...``; an API-based plugin receives ``api_url=...``
        and ``api_key=...``.

        Returns:
            Graph: Graph instance populated with nodes and edges.
        """
        pass


class VisualizerPlugin(ABC):
    """
    Abstract base class for Visualizer plugins.
    Pattern: Strategy (for visualization).
    """

    @abstractmethod
    def get_plugin_name(self) -> str:
        """
        Returns the unique name of the visualizer.
        Example: "Simple Visualizer"
        """
        pass

    @abstractmethod
    def visualize(self, graph: Graph) -> str:
        """
        Convert a graph into an HTML representation.

        NOTE: The core has already loaded the D3.js library.
        This method should return HTML/JS code that uses data from the graph
        to draw it in a <div id="graph-container"> or similar.

        Args:
            graph: Graph data model.

        Returns:
            str: HTML string (may contain <script> tags).
        """
        pass
