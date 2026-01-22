"""Executor shared primitives.

This file provides a stable compatibility surface for the existing executor
subsystem (dispatch/orchestrator/formatters) while the refactor proceeds.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, TypedDict

try:
    # Python 3.11+
    from typing import NotRequired
except ImportError:  # pragma: no cover
    from typing_extensions import NotRequired  # type: ignore

from .types import ExecutionResult


# ---------------------------------------------------------------------------
# Public tool schema / call typing (used by formatters + orchestrator)
# ---------------------------------------------------------------------------

class ToolFunctionCall(TypedDict):
    name: str
    arguments: dict[str, Any]


class ToolCall(TypedDict):
    function: ToolFunctionCall
    type: NotRequired[Literal["function"]]


class ToolFunctionSchema(TypedDict):
    name: str
    description: str
    parameters: dict[str, Any]


class ToolSchema(TypedDict):
    type: Literal["function"]
    function: ToolFunctionSchema


# ---------------------------------------------------------------------------
# Compatibility types expected by legacy executor modules
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExecSummary:
    """Summary returned by the tool-loop executor."""

    steps: int
    last: str


def get_tool_schema() -> list[ToolSchema]:
    """Return tool schema objects used by formatters/backends."""

    # Local import to avoid circular dependency (tools imports ToolSchema).
    from .tools import get_tool_schemas

    return get_tool_schemas()


# ---------------------------------------------------------------------------
# Security helpers expected by dispatch.py
# ---------------------------------------------------------------------------

def sanitize_path(path: str) -> str:
    """Validate/sanitize a filesystem path.

    Intentionally conservative: rejects traversal and absolute paths.
    """

    if not isinstance(path, str) or not path.strip():
        raise ValueError("Invalid path")

    p = path.strip().replace("\x00", "")

    if p.startswith(("/", "\\")):
        raise ValueError("Invalid path")
    if ".." in p.split("/") or ".." in p.split("\\"):
        raise ValueError("Invalid path")
    
    # Check for invalid characters
    invalid_chars = [";", "|", "&", "$", "`", "<", ">"]
    if any(char in p for char in invalid_chars):
        raise ValueError("invalid characters")

    return p


def sanitize_command(cmd: str) -> str:
    """Validate/sanitize a shell command.

    Blocks common shell metacharacters used for chaining/redirection.
    """

    if not isinstance(cmd, str) or not cmd.strip():
        raise ValueError("Invalid command")

    c = cmd.strip().replace("\x00", "")

    banned = [";", "&&", "||", "|", "`", "$(", ">", "<"]
    if any(tok in c for tok in banned):
        raise ValueError("dangerous pattern")
    
    # Check for dangerous commands
    dangerous_cmds = ["rm -rf", "eval ", "exec "]
    if any(cmd in c.lower() for cmd in dangerous_cmds):
        raise ValueError("dangerous pattern")

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
