"""Model-specific tool formatters with security."""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any

from .base import ToolCall, ToolSchema


class ModelToolFormatter(ABC):
    """Abstract base for model-specific tool formatting."""

    @abstractmethod
    def format_tools(self, tools: list[ToolSchema]) -> str:
        """Format tools for model consumption.
        
        Args:
            tools: List of tool schemas
            
        Returns:
            Formatted tool description string
        """
        ...

    @abstractmethod
    def extract_calls(self, content: str) -> list[ToolCall]:
        """Extract tool calls from model output.
        
        Args:
            content: Model output text
            
        Returns:
            List of extracted tool calls
        """
        ...

    @abstractmethod
    def get_system_prompt(self, tools_description: str) -> str:
        """Get model-specific system prompt.
        
        Args:
            tools_description: Formatted tools description
            
        Returns:
            System prompt string
        """
        ...


class Qwen3Formatter(ModelToolFormatter):
    """Qwen3 XML-based tool formatter."""

    def format_tools(self, tools: list[ToolSchema]) -> str:
        """Format tools in Qwen3's XML format."""
        tools_json = json.dumps(tools, indent=2)
        return f"<tools>\n{tools_json}\n</tools>"

    def extract_calls(self, content: str) -> list[ToolCall]:
        """Extract tool calls from Qwen3's <tool_call> tags."""
        tool_calls: list[ToolCall] = []
        pattern = r"<tool_call>\s*({.*?})\s*</tool_call>"
        matches = re.findall(pattern, content, re.DOTALL)

        for match in matches:
            try:
                tool_data = json.loads(match)
                tool_calls.append({
                    "function": {
                        "name": tool_data.get("name", ""),
                        "arguments": tool_data.get("arguments", {}),
                    }
                })
            except json.JSONDecodeError:
                continue

        return tool_calls

    def get_system_prompt(self, tools_description: str) -> str:
        """Get Qwen3-specific system prompt."""
        return (
            "You are the Coder. Your job is to implement requested changes by calling tools.\n\n"
            "AVAILABLE TOOLS:\n"
            f"{tools_description}\n\n"
            "To call a tool, use this format:\n"
            "<tool_call>\n"
            '{"name": "tool_name", "arguments": {"param": "value"}}\n'
            "</tool_call>\n\n"
            "RULES:\n"
            "1. ALWAYS use tool_call tags to make changes\n"
            "2. For file modifications: fs_read first, then fs_write\n"
            "3. Each tool call must be valid JSON inside <tool_call> tags\n"
            "4. Continue until task is fully complete"
        )


class Phi4Formatter(ModelToolFormatter):
    """Phi-4-mini tool formatter."""

    def format_tools(self, tools: list[ToolSchema]) -> str:
        """Format tools in Phi-4's simplified format."""
        simplified = [
            {
                "name": t["function"]["name"],
                "description": t["function"]["description"],
                "parameters": t["function"]["parameters"],
            }
            for t in tools
        ]
        tools_json = json.dumps(simplified, indent=2)
        return f"<|tool|>\n{tools_json}\n<|/tool|>"

    def extract_calls(self, content: str) -> list[ToolCall]:
        """Extract tool calls from Phi-4's <|tool_call|> format."""
        tool_calls: list[ToolCall] = []
        pattern = r"<\|tool_call\|>@?\s*\[\s*({.*?})\s*\]"
        matches = re.findall(pattern, content, re.DOTALL)

        for match in matches:
            try:
                tool_data = json.loads(match)
                if "function" in tool_data:
                    tool_calls.append(tool_data)
                else:
                    tool_calls.append({
                        "function": {
                            "name": tool_data.get("name", ""),
                            "arguments": tool_data.get("arguments", {}),
                        }
                    })
            except json.JSONDecodeError:
                continue

        return tool_calls

    def get_system_prompt(self, tools_description: str) -> str:
        """Get Phi-4-specific system prompt."""
        return (
            "You are the Coder. Your job is to implement requested changes by calling tools.\n\n"
            "AVAILABLE TOOLS:\n"
            f"{tools_description}\n\n"
            "To call a tool, output:\n"
            '<|tool_call|>[ {"type": "function", "function": {"name": "tool_name", "arguments": {...}}} ]\n\n'
            "RULES:\n"
            "1. ALWAYS output tool calls using <|tool_call|> tags\n"
            "2. For file modifications: fs_read first, then fs_write\n"
            "3. JSON must be valid and properly escaped\n"
            "4. Continue until task is fully complete"
        )


class Granite4Formatter(ModelToolFormatter):
    """Granite4 IBM bracket notation formatter."""

    def format_tools(self, tools: list[ToolSchema]) -> str:
        """Format tools in Granite4's bracket notation style."""
        tool_desc = []
        for t in tools:
            name = t["function"]["name"]
            desc = t["function"]["description"]
            params = t["function"]["parameters"]["properties"]
            param_list = ", ".join(f"{k}=<{v['type']}>" for k, v in params.items())
            tool_desc.append(f"- {name}({param_list}): {desc}")

        return "\n".join(tool_desc)

    def extract_calls(self, content: str) -> list[ToolCall]:
        """Extract tool calls from Granite4's bracket notation."""
        tool_calls: list[ToolCall] = []
        pattern = r'\[(\w+)\((.*?)\)\]'
        matches = re.findall(pattern, content)

        for func_name, args_str in matches:
            try:
                arguments: dict[str, Any] = {}
                if args_str.strip():
                    # Handle quoted parameters correctly
                    arg_pattern = r'(\w+)\s*=\s*(?:"([^"\\]*(?:\\.[^"\\]*)*)"|\'([^\'\\]*(?:\\.[^\'\\]*)*)\'|([^\s,]+))'
                    arg_matches = re.findall(arg_pattern, args_str.strip())
                    for param, quoted_value1, quoted_value2, unquoted_value in arg_matches:
                        value = quoted_value1 or quoted_value2 or unquoted_value
                        # Strip any remaining quotes
                        value = value.strip('\'"')
                        arguments[param] = value

                tool_calls.append({
                    "function": {
                        "name": func_name,
                        "arguments": arguments,
                    }
                })
            except Exception as e:
                continue

        return tool_calls

    def get_system_prompt(self, tools_description: str) -> str:
        """Get Granite4-specific system prompt."""
        return (
            "You are the Coder. Your job is to implement requested changes by calling tools.\n\n"
            "AVAILABLE TOOLS:\n"
            f"{tools_description}\n\n"
            "To call a tool, use IBM bracket notation:\n"
            '[function_name(param1="value1", param2="value2")]\n\n'
            "RULES:\n"
            "1. ALWAYS use bracket notation [func(...)] to make changes\n"
            "2. For file modifications: fs_read first, then fs_write\n"
            "3. Quote all string parameters\n"
            "4. Continue until task is fully complete"
        )


class StandardFormatter(ModelToolFormatter):
    """Standard OpenAI-compatible tool formatter."""

    def format_tools(self, tools: list[ToolSchema]) -> str:
        """Format tools in standard OpenAI format."""
        return json.dumps(tools, indent=2)

    def extract_calls(self, content: str) -> list[ToolCall]:
        """Extract JSON tool calls from content."""
        tool_calls: list[ToolCall] = []
        json_content = content.strip()

        # Remove markdown code fences
        if json_content.startswith("```json"):
            json_content = json_content[7:]
        elif json_content.startswith("```"):
            json_content = json_content[3:]
        if json_content.endswith("```"):
            json_content = json_content[:-3]
        json_content = json_content.strip()

        if json_content.startswith('{"name":'):
            brace_count = 0
            for i, char in enumerate(json_content):
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        json_obj = json_content[: i + 1]
                        try:
                            tool_data = json.loads(json_obj)
                            if "name" in tool_data and "arguments" in tool_data:
                                tool_calls.append({
                                    "function": {
                                        "name": tool_data["name"],
                        "arguments": tool_data["arguments"],
                                    }
                                })
                        except json.JSONDecodeError:
                            pass
                        break

        return tool_calls

    def get_system_prompt(self, tools_description: str) -> str:
        """Get standard system prompt."""
        return (
            "You are the Coder. Your job is to implement requested changes by calling tools.\n\n"
            "RULES:\n"
            "1. ALWAYS call tools to make actual changes\n"
            "2. For file modifications: fs_read first, then fs_write\n"
            "3. For new files: directly use fs_write\n"
            "4. Continue until task is fully complete"
        )


def get_formatter(model_name: str) -> ModelToolFormatter:
    """Get appropriate formatter for model.
    
    Args:
        model_name: Name of the model
        
    Returns:
        Appropriate ModelToolFormatter instance
    """
    model_lower = model_name.lower()
    
    if "qwen3" in model_lower or "qwen-3" in model_lower:
        return Qwen3Formatter()
    elif "phi4" in model_lower or "phi-4" in model_lower:
        return Phi4Formatter()
    elif "granite4" in model_lower or "granite-4" in model_lower:
        return Granite4Formatter()
    else:
        return StandardFormatter()
