from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx

from .config import Settings, load_settings
from .streaming import StreamingReporter, QuietReporter
from .enhancement import AutoEnhancementSystem
from ..tools.fs import fs_read, fs_write, fs_list
from ..tools.shell import shell_run
from ..tools.python_exec import python_run


@dataclass
class ExecSummary:
    steps: int
    last: str


def _tool_schema() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "fs_read",
                "description": "Read a UTF-8 text file.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "fs_write",
                "description": "Write/overwrite a UTF-8 text file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "fs_list",
                "description": "List files in a directory.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "shell_run",
                "description": "Run a safe shell command in CWD.",
                "parameters": {
                    "type": "object",
                    "properties": {"cmd": {"type": "string"}},
                    "required": ["cmd"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "python_run",
                "description": "Run pytest or a small snippet.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "mode": {
                            "type": "string",
                            "enum": ["pytest", "snippet"],
                        },
                        "code": {"type": "string"},
                    },
                    "required": ["mode"],
                },
            },
        },
    ]


def _dispatch_tool(name: str, args: dict[str, Any], reporter: StreamingReporter | QuietReporter = None) -> str:
    if reporter:
        reporter.on_tool_call(name, args)
        
    if name == "fs_read":
        if reporter:
            reporter.on_file_operation("read", args["path"])
        r = fs_read(args["path"])
        if reporter:
            reporter.on_tool_result(name, r.ok, r.detail if not r.ok else "")
        return r.detail if r.ok else f"ERROR: {r.detail}"
        
    if name == "fs_write":
        if reporter:
            reporter.on_file_operation("write", args["path"])
        r = fs_write(args["path"], args["content"])
        if reporter:
            reporter.on_tool_result(name, r.ok, r.detail if not r.ok else "")
        return r.detail if r.ok else f"ERROR: {r.detail}"
        
    if name == "fs_list":
        r = fs_list(args["path"])
        if reporter:
            reporter.on_tool_result(name, r.ok, r.detail if not r.ok else "")
        return r.detail if r.ok else f"ERROR: {r.detail}"
        
    if name == "shell_run":
        r = shell_run(args["cmd"])
        status = "OK" if r.ok else "ERROR"
        result = f"{status} (code {r.code})\nSTDOUT:\n{r.stdout}\n" \
               f"STDERR:\n{r.stderr}"
        if reporter:
            reporter.on_tool_result(name, r.ok, r.stderr if not r.ok else "")
        return result
        
    if name == "python_run":
        # Special handling for pytest
        if args.get("mode") == "pytest":
            if reporter:
                reporter.on_test_run("pytest", False, "")  # Will update after execution
        
        r = python_run(args["mode"], args.get("code"))
        status = "OK" if r.ok else "ERROR"
        result = f"{status} (code {r.code})\nSTDOUT:\n{r.stdout}\n" \
               f"STDERR:\n{r.stderr}"
               
        # Update test result
        if args.get("mode") == "pytest" and reporter:
            reporter.on_test_run("pytest", r.ok, r.stderr if not r.ok else r.stdout)
        elif reporter:
            reporter.on_tool_result(name, r.ok, r.stderr if not r.ok else "")
            
        return result
        
    return f"ERROR: unknown tool {name}"


def execute(coder_prompt: str,
            s: Settings | None = None,
            reporter: StreamingReporter | QuietReporter = None) -> ExecSummary:
    """Drive tool-calls until the model stops requesting them."""
    s = s or load_settings()
    tools = _tool_schema()
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "You are the Coder. Use ONLY tools to read/write files and "
                "run tests. Prefer incremental edits. Stop and summarize "
                "when work is complete or tests pass."
            ),
        },
        {"role": "user", "content": coder_prompt},
    ]

    url = f"{s.local_host}/api/chat"
    steps = 0
    last_text = ""


    with httpx.Client(timeout=s.request_timeout_s) as cli:
        while steps < s.max_steps:
            steps += 1
            payload = {
                "model": s.coder_model,
                "messages": messages,
                "tools": tools,
                "stream": True,
            }
            content_chunks = []
            tool_calls = []
            done = False
            # Stream response from Ollama
            with cli.stream("POST", url, json=payload) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except Exception:
                        continue
                    msg = data.get("message", {}) or {}
                    chunk = msg.get("content") or ""
                    if chunk:
                        content_chunks.append(chunk)
                        if reporter:
                            reporter.on_llm_chunk(chunk)
                    calls = msg.get("tool_calls") or []
                    if calls:
                        tool_calls = calls
                    if data.get("done", False):
                        done = True
                        break
            content = "".join(content_chunks)
            last_text = content or last_text
            calls = tool_calls
            # If no proper tool_calls but content looks like a tool call, parse it
            if not calls and content:
                json_content = content.strip()
                
                # Remove markdown code fences
                if json_content.startswith('```json'):
                    json_content = json_content[7:]
                elif json_content.startswith('```'):
                    json_content = json_content[3:]
                if json_content.endswith('```'):
                    json_content = json_content[:-3]
                json_content = json_content.strip()
                
                # Extract just the JSON object - find balanced braces
                import re
                if json_content.startswith('{"name":'):
                    # Find the matching closing brace
                    brace_count = 0
                    start_pos = 0
                    json_obj = json_content
                    for i, char in enumerate(json_content):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_obj = json_content[start_pos:i+1]
                                break
                    
                    try:
                        tool_data = json.loads(json_obj)
                        if "name" in tool_data and "arguments" in tool_data:
                            calls = [{
                                "function": {
                                    "name": tool_data["name"],
                                    "arguments": tool_data["arguments"]
                                }
                            }]
                            if reporter and hasattr(reporter, 'verbose') and reporter.verbose:
                                print(f"DEBUG: Parsed tool call from content: {calls[0]}")
                    except json.JSONDecodeError as e:
                        if reporter and hasattr(reporter, 'verbose') and reporter.verbose:
                            print(f"DEBUG: Failed to parse JSON: {e}")
                            print(f"DEBUG: Content was: {json_obj[:200]}")
                            print(f"DEBUG: Full content was: {json_content[:500]}")
            if not calls:
                break
            for call in calls:
                fn = (call.get("function") or {}).get("name", "")
                raw = (call.get("function") or {}).get("arguments", "{}")
                try:
                    # If it's already a dict (from our JSON parsing), use it directly
                    # Otherwise parse it as JSON string (from proper tool calls)
                    if isinstance(raw, dict):
                        args = raw
                    else:
                        args = json.loads(raw) if isinstance(raw, str) else raw
                except json.JSONDecodeError:
                    args = {}
                result = _dispatch_tool(fn, args, reporter)
                messages.append({"role": "tool", "content": result, "name": fn})

    return ExecSummary(steps=steps, last=last_text)
