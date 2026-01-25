"""
Tests for agent/tools/fs.py
"""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch
from agent.tools.fs import fs_read, fs_write, fs_list, FSResult, _safe_path


class TestSafePath:
    """Tests for _safe_path function."""

    def test_safe_path_relative(self):
        """Test safe path with relative path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('pathlib.Path.cwd', return_value=Path(tmpdir)):
                path = _safe_path("test.txt")
                assert path == Path(tmpdir) / "test.txt"

    def test_safe_path_absolute(self):
        """Test safe path with absolute path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            abs_path = Path(tmpdir) / "test.txt"
            with patch('pathlib.Path.cwd', return_value=Path(tmpdir)):
                path = _safe_path(str(abs_path))
                assert path == abs_path

    def test_safe_path_escape_sandbox(self):
        """Test that paths escaping sandbox raise ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('pathlib.Path.cwd', return_value=Path(tmpdir)):
                with pytest.raises(ValueError, match="path escapes sandbox"):
                    _safe_path("../outside.txt")


class TestFSRead:
    """Tests for fs_read function."""

    def test_read_existing_file(self):
        """Test reading an existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Hello, world!")
            with patch('pathlib.Path.cwd', return_value=Path(tmpdir)):
                result = fs_read(str(test_file))
                assert result.ok is True
                assert result.detail == "Hello, world!"

    def test_read_nonexistent_file(self):
        """Test reading a nonexistent file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('pathlib.Path.cwd', return_value=Path(tmpdir)):
                result = fs_read("nonexistent.txt")
                assert result.ok is False
                assert "not found" in result.detail


class TestFSWrite:
    """Tests for fs_write function."""

    def test_write_file(self):
        """Test writing to a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            content = "Line 1\nLine 2\nLine 3"
            with patch('pathlib.Path.cwd', return_value=Path(tmpdir)):
                result = fs_write(str(test_file), content)
                assert result.ok is True
                assert "3 lines" in result.detail
                assert "wrote" in result.detail

            # Verify content
            assert test_file.read_text() == content

    def test_write_file_creates_directory(self):
        """Test writing to a file creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir_file = Path(tmpdir) / "subdir" / "test.txt"
            with patch('pathlib.Path.cwd', return_value=Path(tmpdir)):
                result = fs_write(str(subdir_file), "content")
                assert result.ok is True
                assert subdir_file.exists()
                assert subdir_file.read_text() == "content"


class TestFSList:
    """Tests for fs_list function."""

    def test_list_directory(self):
        """Test listing a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some files and dirs
            Path(tmpdir, "file1.txt").touch()
            Path(tmpdir, "file2.py").touch()
            Path(tmpdir, "subdir").mkdir()

            with patch('pathlib.Path.cwd', return_value=Path(tmpdir)):
                result = fs_list(tmpdir)
                assert result.ok is True
                items = result.detail.split('\n')
                assert "file1.txt" in items
                assert "file2.py" in items
                assert "subdir/" in items

    def test_list_nonexistent_directory(self):
        """Test listing a nonexistent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('pathlib.Path.cwd', return_value=Path(tmpdir)):
                result = fs_list("nonexistent_dir")
                assert result.ok is False
                assert "not found" in result.detail

    def test_list_file_as_directory(self):
        """Test listing a file (should fail)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file within the temp directory
            test_file = Path(tmpdir) / "testfile.txt"
            test_file.touch()
            with patch('pathlib.Path.cwd', return_value=Path(tmpdir)):
                result = fs_list(str(test_file))
                assert result.ok is False
                assert "not a directory" in result.detail