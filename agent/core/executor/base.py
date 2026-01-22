"""Executor shared primitives.

This file provides a stable compatibility surface for the existing executor
subsystem (dispatch/orchestrator/formatters) while the refactor proceeds.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List

from .types import ExecutionResult, ToolSchema
from .tools import get_tool_schemas


# ---------------------------------------------------------------------------
# Compatibility types expected by legacy executor modules
# ---------------------------------------------------------------------------

@dataclass
class ExecSummary:
    """Summary returned by the tool-loop executor."""

    steps: int
    last: str


def get_tool_schema() -> list[dict[str, Any]]:
    """Return tool schema objects used by formatters/backends."""

    return get_tool_schemas()


# ---------------------------------------------------------------------------
# Security helpers expected by dispatch.py
# ---------------------------------------------------------------------------

def sanitize_path(path: str) -> str:
    """Validate/sanitize a filesystem path.

    Notes:
        This is intentionally conservative. It rejects path traversal and
        absolute paths to keep tool calls scoped to the repo/workdir.
    """

    if not isinstance(path, str) or not path.strip():
        raise ValueError("Invalid path")

    p = path.strip().replace("\\x00", "")

    # Disallow traversal/absolute paths.
    if p.startswith(("/", "\\")):
        raise ValueError("Absolute paths are not allowed")
    if ".." in p.split("/"):
        raise ValueError("Path traversal is not allowed")

    return p


def sanitize_command(cmd: str) -> str:
    """Validate/sanitize a shell command.

    This blocks common shell metacharacters used for chaining/redirection.
    """

    if not isinstance(cmd, str) or not cmd.strip():
        raise ValueError("Invalid command")

    c = cmd.strip().replace("\x00", "")

    banned = [";", "&&", "||", "|", "`", "$(", ">", "<"]
    if any(tok in c for tok in banned):
        raise ValueError("Command contains disallowed shell operators")

    return c


# ---------------------------------------------------------------------------
# New-style executor interface (refactor)
# ---------------------------------------------------------------------------

class BaseExecutor(ABC):
    """Abstract base class for all executors."""

    @abstractmethod
    def execute(self, tool_name: str, args: Dict[str, Any]) -> ExecutionResult:
        """Execute a tool with given arguments."""

    @abstractmethod
    def get_available_tools(self) -> List[ToolSchema]:
        """Return list of available tools."""
