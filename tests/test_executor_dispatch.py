"""Tests for tool dispatcher."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from agent.core.executor.dispatch import ToolDispatcher


class TestToolDispatcher:
    """Test ToolDispatcher class."""

    def test_init(self) -> None:
        """Test dispatcher initialization."""
        dispatcher = ToolDispatcher()
        assert dispatcher.reporter is None
        assert dispatcher._retry_counts == {}

    def test_init_with_reporter(self) -> None:
        """Test dispatcher initialization with reporter."""
        reporter = MagicMock()
        dispatcher = ToolDispatcher(reporter)
        assert dispatcher.reporter is reporter

    def test_invalid_tool(self) -> None:
        """Test dispatching invalid tool name."""
        dispatcher = ToolDispatcher()
        result = dispatcher.dispatch("invalid_tool", {})
        assert result.startswith("ERROR:")
        assert "unknown tool" in result

    @patch("agent.core.executor.dispatch.fs_read")
    def test_fs_read_success(self, mock_read: MagicMock) -> None:
        """Test successful file read."""
        mock_result = MagicMock(ok=True, detail="file content")
        mock_read.return_value = mock_result
        
        dispatcher = ToolDispatcher()
        result = dispatcher.dispatch("fs_read", {"path": "test.py"})
        
        assert result == "file content"
        mock_read.assert_called_once_with("test.py")

    @patch("agent.core.executor.dispatch.fs_read")
    def test_fs_read_failure(self, mock_read: MagicMock) -> None:
        """Test failed file read."""
        mock_result = MagicMock(ok=False, detail="file not found")
        mock_read.return_value = mock_result
        
        dispatcher = ToolDispatcher()
        result = dispatcher.dispatch("fs_read", {"path": "missing.py"})
        
        assert result.startswith("ERROR:")
        assert "file not found" in result

    @patch("agent.core.executor.dispatch.fs_write")
    def test_fs_write_success(self, mock_write: MagicMock) -> None:
        """Test successful file write."""
        mock_result = MagicMock(ok=True, detail="wrote test.py")
        mock_write.return_value = mock_result
        
        dispatcher = ToolDispatcher()
        result = dispatcher.dispatch("fs_write", {"path": "test.py", "content": "print('hi')"})
        
        assert result == "wrote test.py"
        mock_write.assert_called_once_with("test.py", "print('hi')")

    @patch("agent.core.executor.dispatch.fs_list")
    def test_fs_list_success(self, mock_list: MagicMock) -> None:
        """Test successful directory listing."""
        mock_result = MagicMock(ok=True, detail="file1.py\nfile2.py")
        mock_list.return_value = mock_result
        
        dispatcher = ToolDispatcher()
        result = dispatcher.dispatch("fs_list", {"path": "."})
        
        assert "file1.py" in result
        assert "file2.py" in result

    @patch("agent.core.executor.dispatch.shell_run")
    def test_shell_run_success(self, mock_run: MagicMock) -> None:
        """Test successful shell command."""
        mock_result = MagicMock(ok=True, code=0, stdout="output", stderr="")
        mock_run.return_value = mock_result
        
        dispatcher = ToolDispatcher()
        result = dispatcher.dispatch("shell_run", {"cmd": "pytest"})
        
        assert "OK (code 0)" in result
        assert "output" in result

    @patch("agent.core.executor.dispatch.shell_run")
    def test_shell_run_failure(self, mock_run: MagicMock) -> None:
        """Test failed shell command."""
        mock_result = MagicMock(ok=False, code=1, stdout="", stderr="error")
        mock_run.return_value = mock_result
        
        dispatcher = ToolDispatcher()
        result = dispatcher.dispatch("shell_run", {"cmd": "pytest"})
        
        assert "ERROR (code 1)" in result
        assert "error" in result

    @patch("agent.core.executor.dispatch.python_run")
    def test_python_run_pytest(self, mock_run: MagicMock) -> None:
        """Test pytest execution."""
        mock_result = MagicMock(ok=True, code=0, stdout="test passed", stderr="")
        mock_run.return_value = mock_result
        
        dispatcher = ToolDispatcher()
        result = dispatcher.dispatch("python_run", {"mode": "pytest"})
        
        assert "OK (code 0)" in result
        assert "test passed" in result

    @patch("agent.core.executor.dispatch.python_run")
    def test_python_run_snippet(self, mock_run: MagicMock) -> None:
        """Test Python snippet execution."""
        mock_result = MagicMock(ok=True, code=0, stdout="42", stderr="")
        mock_run.return_value = mock_result
        
        dispatcher = ToolDispatcher()
        result = dispatcher.dispatch("python_run", {"mode": "snippet", "code": "print(42)"})
        
        assert "OK (code 0)" in result
        assert "42" in result

    def test_python_run_invalid_mode(self) -> None:
        """Test invalid Python mode."""
        dispatcher = ToolDispatcher()
        result = dispatcher.dispatch("python_run", {"mode": "invalid"})
        
        assert result.startswith("ERROR:")
        assert "Invalid mode" in result

    def test_path_sanitization(self) -> None:
        """Test path traversal is blocked."""
        dispatcher = ToolDispatcher()
        result = dispatcher.dispatch("fs_read", {"path": "../etc/passwd"})
        
        assert result.startswith("ERROR:")
        assert "Invalid path" in result

    def test_command_sanitization(self) -> None:
        """Test dangerous commands are blocked."""
        dispatcher = ToolDispatcher()
        result = dispatcher.dispatch("shell_run", {"cmd": "rm -rf /"})
        
        assert result.startswith("ERROR:")
        assert "dangerous pattern" in result

    @patch("agent.core.executor.dispatch.fs_read")
    def test_reporter_callbacks(self, mock_read: MagicMock) -> None:
        """Test reporter receives callbacks."""
        mock_result = MagicMock(ok=True, detail="content")
        mock_read.return_value = mock_result
        reporter = MagicMock()
        
        dispatcher = ToolDispatcher(reporter)
        dispatcher.dispatch("fs_read", {"path": "test.py"})
        
        reporter.on_tool_call.assert_called_once()
        reporter.on_file_operation.assert_called_once()
        reporter.on_tool_result.assert_called_once()
