"""Tests for executor base types and utilities."""
from __future__ import annotations

import pytest

from agent.core.executor.base import (
    ExecSummary,
    get_tool_schema,
    sanitize_path,
    sanitize_command,
)


class TestExecSummary:
    """Test ExecSummary dataclass."""

    def test_creation(self) -> None:
        """Test creating ExecSummary."""
        summary = ExecSummary(steps=5, last="done")
        assert summary.steps == 5
        assert summary.last == "done"

    def test_frozen(self) -> None:
        """Test ExecSummary is immutable."""
        summary = ExecSummary(steps=5, last="done")
        with pytest.raises(AttributeError):
            summary.steps = 10  # type: ignore


class TestToolSchema:
    """Test tool schema generation."""

    def test_get_tool_schema(self) -> None:
        """Test getting tool schema."""
        tools = get_tool_schema()
        assert len(tools) == 5
        assert all("type" in t for t in tools)
        assert all("function" in t for t in tools)

    def test_tool_names(self) -> None:
        """Test tool names are correct."""
        tools = get_tool_schema()
        names = {t["function"]["name"] for t in tools}
        expected = {"fs_read", "fs_write", "fs_list", "shell_run", "python_run"}
        assert names == expected

    def test_tool_parameters(self) -> None:
        """Test tool parameters are defined."""
        tools = get_tool_schema()
        for tool in tools:
            func = tool["function"]
            assert "parameters" in func
            assert "properties" in func["parameters"]
            assert "required" in func["parameters"]


class TestSanitizePath:
    """Test path sanitization for security."""

    def test_valid_paths(self) -> None:
        """Test valid paths pass through."""
        valid = ["file.py", "dir/file.py", "test_file.txt", "path/to/file.json"]
        for path in valid:
            assert sanitize_path(path) == path

    def test_path_traversal_blocked(self) -> None:
        """Test path traversal is blocked."""
        dangerous = ["../etc/passwd", "dir/../../file", "..\\windows\\system32"]
        for path in dangerous:
            with pytest.raises(ValueError, match="Invalid path"):
                sanitize_path(path)

    def test_absolute_paths_blocked(self) -> None:
        """Test absolute paths are blocked."""
        with pytest.raises(ValueError, match="Invalid path"):
            sanitize_path("/etc/passwd")

    def test_invalid_characters(self) -> None:
        """Test invalid characters are blocked."""
        dangerous = ["file;rm -rf", "file|cat", "file&whoami", "file$var"]
        for path in dangerous:
            with pytest.raises(ValueError, match="invalid characters"):
                sanitize_path(path)


class TestSanitizeCommand:
    """Test command sanitization for security."""

    def test_valid_commands(self) -> None:
        """Test valid commands pass through."""
        valid = ["pytest", "python test.py", "ls -la", "grep pattern file"]
        for cmd in valid:
            assert sanitize_command(cmd) == cmd

    def test_shell_metacharacters_blocked(self) -> None:
        """Test shell metacharacters are blocked."""
        dangerous = ["ls; rm -rf /", "cat file | nc", "echo test && whoami", "ls `whoami`"]
        for cmd in dangerous:
            with pytest.raises(ValueError, match="dangerous pattern"):
                sanitize_command(cmd)

    def test_dangerous_rm_blocked(self) -> None:
        """Test dangerous rm commands are blocked."""
        with pytest.raises(ValueError, match="dangerous pattern"):
            sanitize_command("rm -rf /")

    def test_eval_exec_blocked(self) -> None:
        """Test eval/exec are blocked."""
        dangerous = ["eval 'bad code'", "exec python_code"]
        for cmd in dangerous:
            with pytest.raises(ValueError, match="dangerous pattern"):
                sanitize_command(cmd)
