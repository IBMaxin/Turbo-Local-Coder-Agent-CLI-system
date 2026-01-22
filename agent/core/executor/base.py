"""Base types and protocols for executor system."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Protocol, TypedDict


class ToolSchema(TypedDict, total=True):
    """Type definition for tool schema."""
    type: str
    function: ToolFunction


class ToolFunction(TypedDict, total=True):
    """Type definition for tool function."""
    name: str
    description: str
    parameters: ToolParameters


class ToolParameters(TypedDict, total=True):
    """Type definition for tool parameters."""
    type: str
    properties: dict[str, Any]
    required: list[str]


class ToolCallFunction(TypedDict, total=False):
    """Type definition for tool call function."""
    name: str
    arguments: dict[str, Any] | str


class ToolCall(TypedDict, total=False):
    """Type definition for tool call."""
    function: ToolCallFunction


@dataclass(frozen=True)
class ExecSummary:
    """Summary of execution run."""
    steps: int
    last: str


class ExecutorProtocol(Protocol):
    """Protocol for executor implementations."""

    def execute(
        self,
        prompt: str,
        settings: Any,
        reporter: Any | None = None,
    ) -> ExecSummary:
        """Execute prompt with tools.
        
        Args:
            prompt: User prompt to execute
            settings: Settings object
            reporter: Optional reporter for streaming
            
        Returns:
            ExecSummary with execution results
        """
        ...


def get_tool_schema() -> list[ToolSchema]:
    """Return standardized tool schema.
    
    Returns:
        List of tool definitions following OpenAI format
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "fs_read",
                "description": "Read a UTF-8 text file.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "fs_write",
                "description": "Write/overwrite a UTF-8 text file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "fs_list",
                "description": "List files in a directory.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "shell_run",
                "description": "Run a safe shell command in CWD.",
                "parameters": {
                    "type": "object",
                    "properties": {"cmd": {"type": "string"}},
                    "required": ["cmd"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "python_run",
                "description": "Run pytest or a small snippet.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "mode": {
                            "type": "string",
                            "enum": ["pytest", "snippet"],
                        },
                        "code": {"type": "string"},
                    },
                    "required": ["mode"],
                },
            },
        },
    ]


def sanitize_path(path: str) -> str:
    """Sanitize file path for security.
    
    Prevents path traversal attacks and validates path format.
    
    Args:
        path: Input path string
        
    Returns:
        Sanitized path
        
    Raises:
        ValueError: If path contains suspicious patterns
    """
    # Security: Prevent path traversal
    if ".." in path or path.startswith("/"):
        raise ValueError(f"Invalid path: {path}")
    
    # Security: Validate path characters
    if not re.match(r"^[\w\-./]+$", path):
        raise ValueError(f"Path contains invalid characters: {path}")
    
    return path


def sanitize_command(cmd: str) -> str:
    """Sanitize shell command for security.
    
    Validates command format and prevents injection attacks.
    
    Args:
        cmd: Input command string
        
    Returns:
        Sanitized command
        
    Raises:
        ValueError: If command contains suspicious patterns
    """
    # Security: Block dangerous patterns
    dangerous_patterns = [
        r"[;&|`$()]",  # Shell metacharacters
        r"rm\s+-rf",  # Dangerous rm commands
        r"eval",  # Code evaluation
        r"exec",  # Code execution
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, cmd):
            raise ValueError(f"Command contains dangerous pattern: {cmd}")
    
    return cmd
