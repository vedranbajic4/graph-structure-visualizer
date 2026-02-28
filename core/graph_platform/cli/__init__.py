"""
CLI package — Command-Line Interface for graph manipulation.

Design Patterns
───────────────
• Command       – each CLI operation is a ``Command`` object with
                  ``execute()`` and ``undo()`` methods.
• Chain of Responsibility – ``CommandParser`` delegates to registered
                            command factories.
• Interpreter   – parsing the CLI syntax into structured command objects.
"""
from .command_processor import CommandProcessor
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

__all__ = [
    'CommandProcessor',
    'Command',
    'CommandResult',
    'CreateNodeCommand',
    'EditNodeCommand',
    'DeleteNodeCommand',
    'CreateEdgeCommand',
    'EditEdgeCommand',
    'DeleteEdgeCommand',
    'FilterCommand',
    'SearchCommand',
    'ClearCommand',
    'UndoCommand',
    'ResetCommand',
    'InfoCommand',
    'HelpCommand',
    'ListCommand',
]
