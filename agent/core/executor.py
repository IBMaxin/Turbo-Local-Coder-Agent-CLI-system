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

# Import RAG system for success tracking
try:
    from ..team.rag_system import RAGKnowledgeBase, KnowledgeChunk
    _rag_kb = RAGKnowledgeBase()
except ImportError:
    _rag_kb = None


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


def _add_success_to_rag(original_prompt: str, tool_name: str, args: dict, result: str):
    """Add successful tool execution to RAG knowledge base."""
    if not _rag_kb:
        return
    
    try:
        import hashlib
        import time
        
        # Create a knowledge chunk from the successful execution pattern
        task_type = _classify_task_type(original_prompt)
        file_ext = _extract_file_extension(args.get('path', ''))
        
        content = f"""SUCCESSFUL PATTERN:
Task Type: {task_type}
File Type: {file_ext}
Original Request: {original_prompt}

Execution Pattern:
Tool: {tool_name}
Arguments: {json.dumps(args, indent=2)}
Result: {result}

This pattern worked for: {task_type} tasks involving {file_ext} files."""

        chunk_id = f"pattern_{hashlib.md5(f'{task_type}_{tool_name}_{file_ext}'.encode()).hexdigest()[:12]}"
        
        chunk = KnowledgeChunk(
            id=chunk_id,
            content=content,
            source="execution_pattern",
            chunk_type="pattern",
            keywords=_extract_task_keywords(original_prompt) + [task_type, file_ext, tool_name],
            created_at=time.time()
        )
        
        _rag_kb.add_knowledge(chunk)
    except Exception:
        # Don't fail execution if RAG tracking fails
        pass


def _classify_task_type(prompt: str) -> str:
    """Classify the type of coding task."""
    prompt_lower = prompt.lower()
    
    if any(word in prompt_lower for word in ['create', 'make', 'new']):
        return 'creation'
    elif any(word in prompt_lower for word in ['fix', 'debug', 'error', 'bug']):
        return 'debugging'
    elif any(word in prompt_lower for word in ['add', 'implement', 'extend']):
        return 'enhancement'
    elif any(word in prompt_lower for word in ['refactor', 'improve', 'optimize']):
        return 'refactoring'
    else:
        return 'modification'


def _extract_file_extension(path: str) -> str:
    """Extract file extension from path."""
    if not path:
        return 'unknown'
    ext = path.split('.')[-1] if '.' in path else 'no_extension'
    return ext.lower()


def _extract_task_keywords(text: str) -> list[str]:
    """Extract keywords from task description."""
    import re
    words = re.findall(r'\b\w+\b', text.lower())
    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "create", "add", "make", "write"}
    return list(set(w for w in words if len(w) > 2 and w not in stop_words))


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
                "You are the Coder. Your job is to implement requested changes by calling tools.\n\n"
                "EXAMPLE WORKFLOW:\n"
                "User: Create a simple math.py file with add function\n"
                "Assistant: {\"name\": \"fs_write\", \"arguments\": {\"path\": \"math.py\", \"content\": \"def add(a, b):\\n    return a + b\"}}\n"
                "Tool result: wrote math.py (2 lines, 25 bytes)\n"
                "Assistant: I've created math.py with an add function that takes two parameters and returns their sum.\n\n"
                
                "User: Add error handling to existing config.py\n"
                "Assistant: {\"name\": \"fs_read\", \"arguments\": {\"path\": \"config.py\"}}\n"
                "Tool result: def load_config(): return {...}\n"
                "Assistant: {\"name\": \"fs_write\", \"arguments\": {\"path\": \"config.py\", \"content\": \"def load_config():\\n    try:\\n        return {...}\\n    except Exception as e:\\n        print(f'Error: {e}')\\n        return None\"}}\n"
                "Tool result: wrote config.py (5 lines, 120 bytes)\n"
                "Assistant: I've added try-catch error handling to the load_config function.\n\n"
                
                "RULES:\n"
                "1. ALWAYS call tools to make actual changes - descriptions don't count\n"
                "2. For file modifications: fs_read first, then fs_write with complete content\n"
                "3. For new files: directly use fs_write\n"
                "4. Each tool call must be valid JSON on its own line\n"
                "5. After successful tool calls, briefly confirm what was done\n"
                "6. Continue until task is fully complete\n\n"
                
                "Remember: You must EXECUTE changes with tools, not just analyze or describe them."
            ),
        },
        {"role": "user", "content": coder_prompt},
    ]

    url = f"{s.local_host}/api/chat"
    steps = 0
    last_text = ""

    print(f"[DEBUG] Executor calling: {url}")
    print(f"[DEBUG] Using model: {s.coder_model}")

    with httpx.Client(timeout=s.request_timeout_s) as cli:
        while steps < s.max_steps:
            steps += 1
            
            # Build payload compatible with Ollama API
            payload = {
                "model": s.coder_model,
                "messages": messages,
                "tools": tools,
                "stream": True,
            }
            
            # Only add options if they're supported (remove problematic ones)
            # Ollama supports: temperature, top_p, top_k, repeat_penalty
            # But NOT in an "options" wrapper for /api/chat
            
            content_chunks = []
            tool_calls = []
            done = False
            
            try:
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
            except httpx.HTTPStatusError as e:
                print(f"[ERROR] HTTP {e.response.status_code}: {e.response.text[:200]}")
                # Try without tools if it failed
                if tools and "tools" in str(e.response.text).lower():
                    print("[WARN] Model doesn't support tools, retrying without them")
                    payload.pop("tools", None)
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
                            if data.get("done", False):
                                done = True
                                break
                else:
                    raise
                    
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
                    except json.JSONDecodeError:
                        pass
            
            # Exit if no tool calls were found
            if not calls:
                # If no tool calls but we haven't made progress, prompt to continue
                if steps <= 2 and last_text and not any("wrote " in msg.get("content", "") for msg in messages[-3:]):
                    continue_prompt = "Continue with the implementation. You must call tools to make actual changes."
                    messages.append({"role": "user", "content": continue_prompt})
                    continue
                break
            
            error_occurred = False
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
                
                # Check for errors and auto-retry
                if result.startswith("ERROR:") or "failed" in result.lower():
                    # Track retry attempts per step/call combination
                    retry_key = f"step_{steps}_{fn}_{json.dumps(args, sort_keys=True)}"
                    if not hasattr(execute, '_retry_counts'):
                        execute._retry_counts = {}
                    
                    retry_count = execute._retry_counts.get(retry_key, 0)
                    if retry_count < 2:
                        execute._retry_counts[retry_key] = retry_count + 1
                        error_fix_prompt = f"The tool call failed with error: {result}\nPlease fix the issue and try again. Focus on correcting the specific error mentioned."
                        messages.append({"role": "user", "content": error_fix_prompt})
                        error_occurred = True
                        break  # Break out of tool loop to retry
                
                # Track successful operations for RAG learning
                if "wrote " in result and result.startswith("wrote "):
                    _add_success_to_rag(coder_prompt, fn, args, result)
            
            # If error occurred, continue to next step to allow retry
            if error_occurred:
                continue

    return ExecSummary(steps=steps, last=last_text)
