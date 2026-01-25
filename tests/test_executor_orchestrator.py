"""Tests for executor orchestrator."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from agent.core.executor.orchestrator import execute, _has_tool_results
from agent.core.executor.base import ExecSummary


class TestExecuteFunction:
    """Test main execute function."""

    @patch("agent.core.executor.orchestrator.get_backend")
    @patch("agent.core.executor.orchestrator.load_settings")
    def test_basic_execution(self, mock_settings: MagicMock, mock_backend: MagicMock) -> None:
        """Test basic execution flow."""
        # Mock settings
        settings = MagicMock()
        settings.backend = "test"
        settings.coder_model = "test-model"
        settings.max_steps = 3
        mock_settings.return_value = settings
        
        # Mock backend response (no tool calls, immediate exit)
        response = MagicMock(content="Done", tool_calls=[], done=True)
        backend = MagicMock()
        backend.chat.return_value = [response]
        mock_backend.return_value = backend
        
        result = execute("test prompt")
        
        assert isinstance(result, ExecSummary)
        assert result.last == "Done"

    @patch("agent.core.executor.orchestrator.get_backend")
    @patch("agent.core.executor.orchestrator.load_settings")
    def test_with_tool_calls(self, mock_settings: MagicMock, mock_backend: MagicMock) -> None:
        """Test execution with tool calls."""
        settings = MagicMock()
        settings.backend = "test"
        settings.coder_model = "test-model"
        settings.max_steps = 5
        mock_settings.return_value = settings
        
        # First response with tool call
        tool_call = {
            "function": {
                "name": "fs_read",
                "arguments": {"path": "test.py"},
            }
        }
        response1 = MagicMock(content="", tool_calls=[tool_call], done=True)
        
        # Second response without tool calls (exit)
        response2 = MagicMock(content="Completed", tool_calls=[], done=True)
        
        backend = MagicMock()
        backend.chat.side_effect = [[response1], [response2]]
        mock_backend.return_value = backend
        
        with patch("agent.core.executor.orchestrator.ToolDispatcher") as mock_dispatcher_class:
            mock_dispatcher = MagicMock()
            mock_dispatcher.dispatch.return_value = "file content"
            mock_dispatcher._retry_counts = {}
            mock_dispatcher_class.return_value = mock_dispatcher
            
            result = execute("read file")
            
            assert result.steps == 2
            assert result.last == "Completed"
            mock_dispatcher.dispatch.assert_called_once_with("fs_read", {"path": "test.py"})

    @patch("agent.core.executor.orchestrator.get_backend")
    @patch("agent.core.executor.orchestrator.load_settings")
    def test_max_steps_limit(self, mock_settings: MagicMock, mock_backend: MagicMock) -> None:
        """Test execution respects max_steps limit."""
        settings = MagicMock()
        settings.backend = "test"
        settings.coder_model = "test-model"
        settings.max_steps = 2
        mock_settings.return_value = settings
        
        # Always return tool calls to hit max_steps
        tool_call = {"function": {"name": "fs_read", "arguments": {"path": "test.py"}}}
        response = MagicMock(content="", tool_calls=[tool_call], done=True)
        
        backend = MagicMock()
        backend.chat.return_value = [response]
        mock_backend.return_value = backend
        
        with patch("agent.core.executor.orchestrator.ToolDispatcher") as mock_dispatcher_class:
            mock_dispatcher = MagicMock()
            mock_dispatcher.dispatch.return_value = "content"
            mock_dispatcher._retry_counts = {}
            mock_dispatcher_class.return_value = mock_dispatcher
            
            result = execute("test")
            
            assert result.steps == 2  # Hit max_steps

    @patch("agent.core.executor.orchestrator.get_backend")
    @patch("agent.core.executor.orchestrator.load_settings")
    def test_error_retry(self, mock_settings: MagicMock, mock_backend: MagicMock) -> None:
        """Test error retry logic."""
        settings = MagicMock()
        settings.backend = "test"
        settings.coder_model = "test-model"
        settings.max_steps = 5
        mock_settings.return_value = settings
        
        # Tool call that will error
        tool_call = {"function": {"name": "fs_read", "arguments": {"path": "missing.py"}}}
        response1 = MagicMock(content="", tool_calls=[tool_call], done=True)
        response2 = MagicMock(content="Fixed", tool_calls=[], done=True)
        
        backend = MagicMock()
        backend.chat.side_effect = [[response1], [response2]]
        mock_backend.return_value = backend
        
        with patch("agent.core.executor.orchestrator.ToolDispatcher") as mock_dispatcher_class:
            mock_dispatcher = MagicMock()
            mock_dispatcher.dispatch.return_value = "ERROR: file not found"
            mock_dispatcher._retry_counts = {}
            mock_dispatcher_class.return_value = mock_dispatcher
            
            result = execute("read file")
            
            # Should have triggered retry
            assert result.steps >= 2

    @patch("agent.core.executor.orchestrator.get_backend")
    @patch("agent.core.executor.orchestrator.load_settings")
    def test_backend_failure(self, mock_settings: MagicMock, mock_backend: MagicMock) -> None:
        """Test handling of backend failures."""
        settings = MagicMock()
        settings.backend = "test"
        settings.coder_model = "test-model"
        settings.max_steps = 3
        mock_settings.return_value = settings
        
        backend = MagicMock()
        backend.chat.side_effect = Exception("Backend error")
        mock_backend.return_value = backend
        
        with pytest.raises(RuntimeError, match="Backend execution failed"):
            execute("test")

    @patch("agent.core.executor.orchestrator.get_backend")
    @patch("agent.core.executor.orchestrator.load_settings")
    def test_streaming(self, mock_settings: MagicMock, mock_backend: MagicMock) -> None:
        """Test streaming with reporter."""
        settings = MagicMock()
        settings.backend = "test"
        settings.coder_model = "test-model"
        settings.max_steps = 3
        mock_settings.return_value = settings
        
        # Streaming responses
        chunk1 = MagicMock(content="chunk1", tool_calls=[], done=False)
        chunk2 = MagicMock(content="chunk2", tool_calls=[], done=False)
        final = MagicMock(content="", tool_calls=[], done=True)
        
        backend = MagicMock()
        backend.chat.return_value = [chunk1, chunk2, final]
        mock_backend.return_value = backend
        
        reporter = MagicMock()
        result = execute("test", reporter=reporter)
        
        assert result.last == "chunk1chunk2"
        assert reporter.on_llm_chunk.call_count == 2


class TestHasToolResults:
    """Test _has_tool_results helper."""

    def test_no_tool_results(self) -> None:
        """Test messages without tool results."""
        messages = [
            {"role": "user", "content": "test"},
            {"role": "assistant", "content": "response"},
        ]
        assert not _has_tool_results(messages)

    def test_with_tool_role(self) -> None:
        """Test messages with tool role."""
        messages = [
            {"role": "user", "content": "test"},
            {"role": "tool", "content": "result"},
        ]
        assert _has_tool_results(messages)

    def test_with_wrote_message(self) -> None:
        """Test messages with 'wrote' keyword."""
        messages = [
            {"role": "user", "content": "test"},
            {"role": "assistant", "content": "wrote file.py"},
        ]
        assert _has_tool_results(messages)

    def test_with_ok_code(self) -> None:
        """Test messages with 'OK (code' pattern."""
        messages = [
            {"role": "user", "content": "test"},
            {"role": "assistant", "content": "OK (code 0)"},
        ]
        assert _has_tool_results(messages)

    def test_only_checks_last_three(self) -> None:
        """Test only last 3 messages are checked."""
        messages = [
            {"role": "tool", "content": "old result"},
            {"role": "user", "content": "test1"},
            {"role": "user", "content": "test2"},
            {"role": "user", "content": "test3"},
            {"role": "user", "content": "test4"},
        ]
        assert not _has_tool_results(messages)
