"""
    Abstract base classes for plugins.
    Defines the "Contract" that all plugins must follow.
"""
from abc import ABC, abstractmethod
from ..models.graph import Graph


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
    def parse(self, file_path: str) -> Graph:
        """
        Main method: Parses a file and returns a Graph object.

        Args:
            file_path: Path to the file to be loaded.

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
        Main method: Converts a graph into an HTML representation.

        NOTE: The platform has already loaded the D3.js library.
        This method should return HTML/JS code that uses data from the graph
        to draw it in a <div id="graph-container"> or similar.

        Args:
            graph: Graph data model.

        Returns:
            str: HTML string (may contain <script> tags).
        """
        pass