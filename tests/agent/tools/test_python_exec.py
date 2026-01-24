"""
Tests for agent/tools/python_exec.py
"""
import pytest
import sys
from unittest.mock import patch, Mock, ANY
from agent.tools.python_exec import python_run, PyRunResult


class TestPythonRun:
    """Tests for python_run function."""

    @patch('subprocess.run')
    def test_pytest_mode_success(self, mock_run):
        """Test pytest mode with successful run."""
        mock_proc = Mock()
        mock_proc.returncode = 0
        mock_proc.stdout = "test output"
        mock_proc.stderr = "test stderr"
        mock_run.return_value = mock_proc

        result = python_run("pytest")

        assert result.ok is True
        assert result.stdout == "test output"
        assert result.stderr == "test stderr"
        assert result.code == 0
        mock_run.assert_called_once_with(
            [sys.executable, "-m", "pytest", "-q"],
            capture_output=True,
            text=True
        )

    @patch('subprocess.run')
    def test_pytest_mode_failure(self, mock_run):
        """Test pytest mode with failure."""
        mock_proc = Mock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "test failed"
        mock_run.return_value = mock_proc

        result = python_run("pytest")

        assert result.ok is False
        assert result.code == 1

    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    def test_snippet_mode_success(self, mock_tempfile, mock_run):
        """Test snippet mode with successful execution."""
        # Mock tempfile
        mock_file = Mock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=False)
        mock_file.name = "/tmp/test.py"
        mock_tempfile.return_value = mock_file

        # Mock subprocess
        mock_proc = Mock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Hello, World!"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        result = python_run("snippet", "print('Hello, World!')")

        assert result.ok is True
        assert result.stdout == "Hello, World!"
        assert result.code == 0
        mock_file.write.assert_called_with("print('Hello, World!')")
        mock_run.assert_called_once_with(
            [sys.executable, "/tmp/test.py"],
            capture_output=True,
            text=True
        )

    def test_snippet_mode_no_code(self):
        """Test snippet mode with no code provided."""
        result = python_run("snippet", None)

        assert result.ok is False
        assert result.stdout == ""
        assert result.stderr == "no code provided"
        assert result.code == 2

    def test_unknown_mode(self):
        """Test unknown mode."""
        result = python_run("unknown")

        assert result.ok is False
        assert result.stdout == ""
        assert result.stderr == "unknown mode: unknown"
        assert result.code == 2

    @patch('subprocess.run')
    def test_exception_handling(self, mock_run):
        """Test exception handling."""
        mock_run.side_effect = Exception("subprocess error")

        result = python_run("pytest")

        assert result.ok is False
        assert result.stdout == ""
        assert "error: subprocess error" in result.stderr
        assert result.code == 1