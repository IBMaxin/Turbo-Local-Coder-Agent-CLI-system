"""Secure tool dispatch with validation and tracking."""
from __future__ import annotations

import json
from typing import Any

from .base import sanitize_command, sanitize_path
from ...tools.fs import fs_read, fs_write, fs_list
from ...tools.shell import shell_run
from ...tools.python_exec import python_run

# Type stubs for imports
try:
    from ..streaming import StreamingReporter, QuietReporter
except ImportError:
    StreamingReporter = Any  # type: ignore
    QuietReporter = Any  # type: ignore


class ToolDispatcher:
    """Secure dispatcher for tool execution with validation."""

    def __init__(self, reporter: StreamingReporter | QuietReporter | None = None) -> None:
        """Initialize dispatcher.
        
        Args:
            reporter: Optional reporter for streaming updates
        """
        self.reporter = reporter
        self._retry_counts: dict[str, int] = {}

    def dispatch(
        self,
        name: str,
        args: dict[str, Any],
    ) -> str:
        """Dispatch tool call with security validation.
        
        Args:
            name: Tool name to execute
            args: Tool arguments
            
        Returns:
            Result string from tool execution
            
        Raises:
            ValueError: If tool name is invalid or args are malformed
        """
        # Security: Validate tool name
        valid_tools = {"fs_read", "fs_write", "fs_list", "shell_run", "python_run"}
        if name not in valid_tools:
            return f"ERROR: unknown tool {name}"

        if self.reporter:
            self.reporter.on_tool_call(name, args)

        try:
            if name == "fs_read":
                return self._handle_fs_read(args)
            elif name == "fs_write":
                return self._handle_fs_write(args)
            elif name == "fs_list":
                return self._handle_fs_list(args)
            elif name == "shell_run":
                return self._handle_shell_run(args)
            elif name == "python_run":
                return self._handle_python_run(args)
        except Exception as e:
            error_msg = f"ERROR: {type(e).__name__}: {str(e)}"
            if self.reporter:
                self.reporter.on_tool_result(name, False, error_msg)
            return error_msg

        return f"ERROR: unhandled tool {name}"

    def _handle_fs_read(self, args: dict[str, Any]) -> str:
        """Handle file read with path validation."""
        path = sanitize_path(args["path"])
        if self.reporter:
            self.reporter.on_file_operation("read", path)
        
        result = fs_read(path)
        success = result.ok
        message = result.detail if not success else ""
        
        if self.reporter:
            self.reporter.on_tool_result("fs_read", success, message)
        
        return result.detail if success else f"ERROR: {result.detail}"

    def _handle_fs_write(self, args: dict[str, Any]) -> str:
        """Handle file write with path validation."""
        path = sanitize_path(args["path"])
        content = args["content"]
        
        if self.reporter:
            self.reporter.on_file_operation("write", path)
        
        result = fs_write(path, content)
        success = result.ok
        message = result.detail if not success else ""
        
        if self.reporter:
            self.reporter.on_tool_result("fs_write", success, message)
        
        return result.detail if success else f"ERROR: {result.detail}"

    def _handle_fs_list(self, args: dict[str, Any]) -> str:
        """Handle directory listing with path validation."""
        path = sanitize_path(args["path"])
        result = fs_list(path)
        success = result.ok
        
        if self.reporter:
            self.reporter.on_tool_result("fs_list", success, "" if success else result.detail)
        
        return result.detail if success else f"ERROR: {result.detail}"

    def _handle_shell_run(self, args: dict[str, Any]) -> str:
        """Handle shell command with security validation."""
        cmd = sanitize_command(args["cmd"])
        result = shell_run(cmd)
        success = result.ok
        
        output = (
            f"{'OK' if success else 'ERROR'} (code {result.code})\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )
        
        if self.reporter:
            self.reporter.on_tool_result("shell_run", success, result.stderr if not success else "")
        
        return output

    def _handle_python_run(self, args: dict[str, Any]) -> str:
        """Handle Python execution with mode validation."""
        mode = args.get("mode")
        code = args.get("code")
        
        # Security: Validate mode
        if mode not in ["pytest", "snippet"]:
            return f"ERROR: Invalid mode: {mode}"
        
        if self.reporter and mode == "pytest":
            self.reporter.on_test_run("pytest", False, "")
        
        result = python_run(mode, code)
        success = result.ok
        
        output = (
            f"{'OK' if success else 'ERROR'} (code {result.code})\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )
        
        if mode == "pytest" and self.reporter:
            self.reporter.on_test_run(
                "pytest",
                success,
                result.stderr if not success else result.stdout,
            )
        elif self.reporter:
            self.reporter.on_tool_result("python_run", success, result.stderr if not success else "")
        
        return output
