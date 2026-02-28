"""MemX Integration Layer — hook abstractions and manager.

Public API:
    BaseHook, PreInferenceHook, PostActionHook, SessionEndHook,
    ContextInjection, ToolEvent, IntegrationManager,
    CLIPreInferenceHook, CLIPostActionHook, CLISessionEndHook,
    setup_signal_handlers
"""

from memx.integration.cli_hooks import (
    CLIPostActionHook,
    CLIPreInferenceHook,
    CLISessionEndHook,
    setup_signal_handlers,
)
from memx.integration.hooks import (
    BaseHook,
    ContextInjection,
    PostActionHook,
    PreInferenceHook,
    SessionEndHook,
    ToolEvent,
)
from memx.integration.manager import IntegrationManager

__all__ = [
    "BaseHook",
    "CLIPostActionHook",
    "CLIPreInferenceHook",
    "CLISessionEndHook",
    "ContextInjection",
    "IntegrationManager",
    "PostActionHook",
    "PreInferenceHook",
    "SessionEndHook",
    "ToolEvent",
    "setup_signal_handlers",
]
