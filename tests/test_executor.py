"""Tests for Executor module."""
import pytest
from agent.core.executor import Executor

def test_executor_init():
    """Test executor initialization."""
    ex = Executor()
    assert ex.sandbox is not None

def test_executor_sandbox_disabled():
    """Test executor with sandbox disabled."""
    ex = Executor(sandbox=False)
    assert ex.sandbox is None
