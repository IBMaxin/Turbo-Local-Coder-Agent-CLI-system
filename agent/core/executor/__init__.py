"""
Secure Executor Module

Splits monolithic executor into modular components.

This package also re-exports the legacy `execute()` entrypoint used by
`agent/core/orchestrator.py` for CLI compatibility.
"""

from .types import ExecutionResult
from .runner import Executor

# Compatibility surface (used by agent/core/executor/orchestrator.py)
from .base import ExecSummary, get_tool_schema, sanitize_command, sanitize_path
from .orchestrator import execute

__all__ = [
    "Executor",
    "ExecSummary",
    "ExecutionResult",
    "execute",
    "get_tool_schema",
    "sanitize_command",
    "sanitize_path",
]
