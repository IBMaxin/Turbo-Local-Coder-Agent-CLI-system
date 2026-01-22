"""Pytest configuration and fixtures."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_reporter() -> MagicMock:
    """Create a mock reporter for testing."""
    reporter = MagicMock()
    reporter.on_tool_call = MagicMock()
    reporter.on_tool_result = MagicMock()
    reporter.on_file_operation = MagicMock()
    reporter.on_test_run = MagicMock()
    reporter.on_llm_chunk = MagicMock()
    return reporter


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings for testing."""
    settings = MagicMock()
    settings.backend = "test"
    settings.coder_model = "test-model"
    settings.max_steps = 10
    return settings
