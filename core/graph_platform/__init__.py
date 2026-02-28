"""
Graph Platform — core package.

Public API:
    GraphPlatform       – central orchestrator (Facade / Singleton)
    Workspace           – data source + filter/search state
    PlatformConfig      – top-level configuration
    SerializationConfig – serialization field control
    PluginLoader        – generic plugin discovery
"""
from .core import GraphPlatform
from .workspace import Workspace
from .config import PlatformConfig, SerializationConfig
from .plugin_loader import (
    PluginLoader,
    create_data_source_loader,
    create_visualizer_loader,
)

__all__ = [
    'GraphPlatform',
    'Workspace',
    'PlatformConfig',
    'SerializationConfig',
    'PluginLoader',
    'create_data_source_loader',
    'create_visualizer_loader',
]
