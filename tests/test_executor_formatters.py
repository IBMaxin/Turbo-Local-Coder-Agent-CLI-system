"""Tests for model-specific formatters."""
from __future__ import annotations

import json
import pytest

from agent.core.executor.formatters import (
    Qwen3Formatter,
    Phi4Formatter,
    Granite4Formatter,
    StandardFormatter,
    get_formatter,
)
from agent.core.executor.base import get_tool_schema


class TestQwen3Formatter:
    """Test Qwen3 XML formatter."""

    def test_format_tools(self) -> None:
        """Test Qwen3 tool formatting."""
        formatter = Qwen3Formatter()
        tools = get_tool_schema()
        result = formatter.format_tools(tools)
        
        assert "<tools>" in result
        assert "</tools>" in result
        assert "fs_read" in result

    def test_extract_calls(self) -> None:
        """Test Qwen3 tool call extraction."""
        formatter = Qwen3Formatter()
        content = '<tool_call>\n{"name": "fs_read", "arguments": {"path": "test.py"}}\n</tool_call>'
        
        calls = formatter.extract_calls(content)
        assert len(calls) == 1
        assert calls[0]["function"]["name"] == "fs_read"
        assert calls[0]["function"]["arguments"] == {"path": "test.py"}

    def test_extract_multiple_calls(self) -> None:
        """Test extracting multiple Qwen3 calls."""
        formatter = Qwen3Formatter()
        content = (
            '<tool_call>{"name": "fs_read", "arguments": {"path": "a.py"}}</tool_call>\n'
            '<tool_call>{"name": "fs_write", "arguments": {"path": "b.py", "content": "x"}}</tool_call>'
        )
        
        calls = formatter.extract_calls(content)
        assert len(calls) == 2

    def test_extract_invalid_json(self) -> None:
        """Test handling invalid JSON in Qwen3 format."""
        formatter = Qwen3Formatter()
        content = '<tool_call>{invalid json}</tool_call>'
        
        calls = formatter.extract_calls(content)
        assert len(calls) == 0

    def test_system_prompt(self) -> None:
        """Test Qwen3 system prompt generation."""
        formatter = Qwen3Formatter()
        prompt = formatter.get_system_prompt("<tools>...</tools>")
        
        assert "Coder" in prompt
        assert "<tool_call>" in prompt
        assert "RULES" in prompt


class TestPhi4Formatter:
    """Test Phi-4-mini formatter."""

    def test_format_tools(self) -> None:
        """Test Phi-4 tool formatting."""
        formatter = Phi4Formatter()
        tools = get_tool_schema()
        result = formatter.format_tools(tools)
        
        assert "<|tool|>" in result
        assert "<|/tool|>" in result
        assert "fs_read" in result

    def test_extract_calls(self) -> None:
        """Test Phi-4 tool call extraction."""
        formatter = Phi4Formatter()
        content = '<|tool_call|>[ {"type": "function", "function": {"name": "fs_read", "arguments": {"path": "test.py"}}} ]'
        
        calls = formatter.extract_calls(content)
        assert len(calls) == 1
        assert calls[0]["function"]["name"] == "fs_read"

    def test_system_prompt(self) -> None:
        """Test Phi-4 system prompt generation."""
        formatter = Phi4Formatter()
        prompt = formatter.get_system_prompt("<|tool|>...</|tool|>")
        
        assert "Coder" in prompt
        assert "<|tool_call|>" in prompt


class TestGranite4Formatter:
    """Test Granite4 IBM formatter."""

    def test_format_tools(self) -> None:
        """Test Granite4 tool formatting."""
        formatter = Granite4Formatter()
        tools = get_tool_schema()
        result = formatter.format_tools(tools)
        
        assert "fs_read" in result
        assert "path=<string>" in result

    def test_extract_calls(self) -> None:
        """Test Granite4 tool call extraction."""
        formatter = Granite4Formatter()
        content = '[fs_read(path="test.py")]'
        
        calls = formatter.extract_calls(content)
        assert len(calls) == 1
        assert calls[0]["function"]["name"] == "fs_read"
        assert calls[0]["function"]["arguments"]["path"] == "test.py"

    def test_extract_multiple_params(self) -> None:
        """Test Granite4 with multiple parameters."""
        formatter = Granite4Formatter()
        content = '[fs_write(path="test.py", content="print(42)")]'
        
        calls = formatter.extract_calls(content)
        assert len(calls) == 1
        assert calls[0]["function"]["arguments"]["path"] == "test.py"
        assert calls[0]["function"]["arguments"]["content"] == "print(42)"

    def test_system_prompt(self) -> None:
        """Test Granite4 system prompt generation."""
        formatter = Granite4Formatter()
        prompt = formatter.get_system_prompt("tools")
        
        assert "bracket notation" in prompt
        assert "[function_name" in prompt


class TestStandardFormatter:
    """Test standard OpenAI formatter."""

    def test_format_tools(self) -> None:
        """Test standard tool formatting."""
        formatter = StandardFormatter()
        tools = get_tool_schema()
        result = formatter.format_tools(tools)
        
        parsed = json.loads(result)
        assert len(parsed) == 5

    def test_extract_calls(self) -> None:
        """Test standard JSON extraction."""
        formatter = StandardFormatter()
        content = '{"name": "fs_read", "arguments": {"path": "test.py"}}'
        
        calls = formatter.extract_calls(content)
        assert len(calls) == 1
        assert calls[0]["function"]["name"] == "fs_read"

    def test_extract_with_markdown(self) -> None:
        """Test extraction with markdown code fence."""
        formatter = StandardFormatter()
        content = '```json\n{"name": "fs_read", "arguments": {"path": "test.py"}}\n```'
        
        calls = formatter.extract_calls(content)
        assert len(calls) == 1

    def test_system_prompt(self) -> None:
        """Test standard system prompt generation."""
        formatter = StandardFormatter()
        prompt = formatter.get_system_prompt("tools")
        
        assert "Coder" in prompt
        assert "RULES" in prompt


class TestGetFormatter:
    """Test formatter selection."""

    def test_qwen3_detection(self) -> None:
        """Test Qwen3 model detection."""
        formatter = get_formatter("qwen3-7b")
        assert isinstance(formatter, Qwen3Formatter)

    def test_phi4_detection(self) -> None:
        """Test Phi-4 model detection."""
        formatter = get_formatter("phi4-mini")
        assert isinstance(formatter, Phi4Formatter)

    def test_granite4_detection(self) -> None:
        """Test Granite4 model detection."""
        formatter = get_formatter("granite4-8b")
        assert isinstance(formatter, Granite4Formatter)

    def test_standard_fallback(self) -> None:
        """Test fallback to standard formatter."""
        formatter = get_formatter("gpt-4")
        assert isinstance(formatter, StandardFormatter)

    def test_case_insensitive(self) -> None:
        """Test case-insensitive model detection."""
        formatter = get_formatter("QWEN3-7B")
        assert isinstance(formatter, Qwen3Formatter)
