from __future__ import annotations

import json
import re
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


def _format_tools_for_qwen3(tools: list[dict]) -> str:
    """Format tools in Qwen3's expected XML format."""
    tools_json = json.dumps(tools, indent=2)
    return f"<tools>\n{tools_json}\n</tools>"


def _format_tools_for_phi4(tools: list[dict]) -> str:
    """Format tools in Phi-4-mini's expected format per official HF docs."""
    # Phi-4 wants simpler format
    simplified = [{"name": t["function"]["name"], 
                   "description": t["function"]["description"],
                   "parameters": t["function"]["parameters"]} 
                  for t in tools]
    tools_json = json.dumps(simplified, indent=2)
    return f"<|tool|>\n{tools_json}\n<|/tool|>"


def _format_tools_for_granite4(tools: list[dict]) -> str:
    """Format tools for Granite4 using IBM's bracket notation style."""
    tool_desc = []
    for t in tools:
        name = t["function"]["name"]
        desc = t["function"]["description"]
        params = t["function"]["parameters"]["properties"]
        param_list = ", ".join(f"{k}=<{v['type']}>" for k, v in params.items())
        tool_desc.append(f"- {name}({param_list}): {desc}")
    
    return "\n".join(tool_desc)


def _extract_qwen3_tool_calls(content: str) -> list[dict]:
    """Extract tool calls from Qwen3's XML format: <tool_call>{...}</tool_call>"""
    tool_calls = []
    
    # Pattern to match <tool_call>...</tool_call>
    pattern = r'<tool_call>\s*({.*?})\s*</tool_call>'
    matches = re.findall(pattern, content, re.DOTALL)
    
    for match in matches:
        try:
            tool_data = json.loads(match)
            # Convert to standard format
            tool_calls.append({
                "function": {
                    "name": tool_data.get("name", ""),
                    "arguments": tool_data.get("arguments", {})
                }
            })
        except json.JSONDecodeError:
            continue
    
    return tool_calls


def _extract_phi4_tool_calls(content: str) -> list[dict]:
    """Extract tool calls from Phi-4-mini format: <|tool_call|>@[ {...} ]"""
    tool_calls = []
    
    # Pattern to match <|tool_call|>@[ ... ]
    pattern = r'<\|tool_call\|>@?\s*\[\s*({.*?})\s*\]'
    matches = re.findall(pattern, content, re.DOTALL)
    
    for match in matches:
        try:
            tool_data = json.loads(match)
            # Phi-4 format: {"type":"function","function":{"name":"...","arguments":{...}}}
            if "function" in tool_data:
                tool_calls.append(tool_data)
            else:
                # Fallback for simpler format
                tool_calls.append({
                    "function": {
                        "name": tool_data.get("name", ""),
                        "arguments": tool_data.get("arguments", {})
                    }
                })
        except json.JSONDecodeError:
            continue
    
    return tool_calls


def _extract_granite4_tool_calls(content: str) -> list[dict]:
    """Extract tool calls from Granite4's bracket notation: [func_name(param="value")]"""
    tool_calls = []
    
    # Pattern to match [function_name(param1="val1", param2="val2")]
    pattern = r'\[(\w+)\((.*?)\)\]'
    matches = re.findall(pattern, content)
    
    for func_name, args_str in matches:
        try:
            # Parse arguments
            arguments = {}
            if args_str.strip():
                # Split by comma but respect quotes
                arg_pattern = r'(\w+)\s*=\s*(["\'](.*?)\2|[^,]+)'
                arg_matches = re.findall(arg_pattern, args_str)
                for param, _, value in arg_matches:
                    arguments[param] = value
            
            tool_calls.append({
                "function": {
                    "name": func_name,
                    "arguments": arguments
                }
            })
        except Exception:
            continue
    
    return tool_calls


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
        pass


def _classify_task_type(prompt: str) -> str:
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
    if not path:
        return 'unknown'
    ext = path.split('.')[-1] if '.' in path else 'no_extension'
    return ext.lower()


def _extract_task_keywords(text: str) -> list[str]:
    import re
    words = re.findall(r'\b\w+\b', text.lower())
    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "create", "add", "make", "write"}
    return list(set(w for w in words if len(w) > 2 and w not in stop_words))


def _is_qwen3_model(model_name: str) -> bool:
    """Check if model is Qwen3 (needs XML tool format)."""
    return 'qwen3' in model_name.lower() or 'qwen-3' in model_name.lower()


def _is_phi4_model(model_name: str) -> bool:
    """Check if model is Phi-4-mini (needs special tool format)."""
    return 'phi4' in model_name.lower() or 'phi-4' in model_name.lower()


def _is_granite4_model(model_name: str) -> bool:
    """Check if model is Granite4 (needs IBM bracket notation)."""
    return 'granite4' in model_name.lower() or 'granite-4' in model_name.lower()


def execute(coder_prompt: str,
            s: Settings | None = None,
            reporter: StreamingReporter | QuietReporter = None) -> ExecSummary:
    """Drive tool-calls until the model stops requesting them."""
    s = s or load_settings()
    tools = _tool_schema()
    
    # Detect model type and format tools accordingly
    use_qwen3_format = _is_qwen3_model(s.coder_model)
    use_phi4_format = _is_phi4_model(s.coder_model)
    use_granite4_format = _is_granite4_model(s.coder_model)
    
    if use_qwen3_format:
        print(f"[DEBUG] Using Qwen3 XML tool format for model: {s.coder_model}")
        tools_description = _format_tools_for_qwen3(tools)
        
        system_content = (
            "You are the Coder. Your job is to implement requested changes by calling tools.\n\n"
            "AVAILABLE TOOLS:\n"
            f"{tools_description}\n\n"
            "To call a tool, use this format:\n"
            '<tool_call>\n'
            '{"name": "tool_name", "arguments": {"param": "value"}}\n'
            '</tool_call>\n\n'
            "RULES:\n"
            "1. ALWAYS use tool_call tags to make changes\n"
            "2. For file modifications: fs_read first, then fs_write\n"
            "3. Each tool call must be valid JSON inside <tool_call> tags\n"
            "4. Continue until task is fully complete"
        )
    elif use_phi4_format:
        print(f"[DEBUG] Using Phi-4-mini tool format for model: {s.coder_model}")
        tools_description = _format_tools_for_phi4(tools)
        
        system_content = (
            "You are the Coder. Your job is to implement requested changes by calling tools.\n\n"
            "AVAILABLE TOOLS:\n"
            f"{tools_description}\n\n"
            "To call a tool, output:\n"
            '<|tool_call|>[ {"type": "function", "function": {"name": "tool_name", "arguments": {...}}} ]\n\n'
            "EXAMPLE:\n"
            "User: Create hello.py with hello world\n"
            'Assistant: <|tool_call|>[ {"type": "function", "function": {"name": "fs_write", "arguments": {"path": "hello.py", "content": "print(\'Hello, World!\')"}}} ]\n\n'
            "RULES:\n"
            "1. ALWAYS output tool calls using <|tool_call|> tags\n"
            "2. For file modifications: fs_read first, then fs_write\n"
            "3. JSON must be valid and properly escaped\n"
            "4. Continue until task is fully complete"
        )
    elif use_granite4_format:
        print(f"[DEBUG] Using Granite4 IBM bracket notation for model: {s.coder_model}")
        tools_description = _format_tools_for_granite4(tools)
        
        system_content = (
            "You are the Coder. Your job is to implement requested changes by calling tools.\n\n"
            "AVAILABLE TOOLS:\n"
            f"{tools_description}\n\n"
            "To call a tool, use IBM bracket notation:\n"
            '[function_name(param1="value1", param2="value2")]\n\n'
            "EXAMPLE:\n"
            'User: Create hello.py with hello world\n'
            'Assistant: [fs_write(path="hello.py", content="print(\'Hello, World!\')")]<|endoftext|>\n\n'
            "RULES:\n"
            "1. ALWAYS use bracket notation [func(...)] to make changes\n"
            "2. For file modifications: fs_read first, then fs_write\n"
            "3. Quote all string parameters\n"
            "4. Continue until task is fully complete"
        )
    else:
        print(f"[DEBUG] Using standard OpenAI tool format for model: {s.coder_model}")
        system_content = (
            "You are the Coder. Your job is to implement requested changes by calling tools.\n\n"
            "RULES:\n"
            "1. ALWAYS call tools to make actual changes\n"
            "2. For file modifications: fs_read first, then fs_write\n"
            "3. For new files: directly use fs_write\n"
            "4. Continue until task is fully complete"
        )
    
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_content},
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
            
            # Build payload - for custom formats, don't send tools in API
            payload = {
                "model": s.coder_model,
                "messages": messages,
                "stream": True,
            }
            
            # Only add tools parameter for standard OpenAI models
            if not (use_qwen3_format or use_phi4_format or use_granite4_format):
                payload["tools"] = tools
            
            content_chunks = []
            tool_calls = []
            done = False
            
            try:
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
                        
                        # Standard tool calls from API
                        calls = msg.get("tool_calls") or []
                        if calls:
                            tool_calls = calls
                        
                        if data.get("done", False):
                            done = True
                            break
                            
            except httpx.HTTPStatusError as e:
                print(f"[ERROR] HTTP {e.response.status_code}: {e.response.text[:200]}")
                raise
                    
            content = "".join(content_chunks)
            last_text = content or last_text
            calls = tool_calls
            
            # Extract tool calls based on model format
            if use_qwen3_format and content:
                qwen3_calls = _extract_qwen3_tool_calls(content)
                if qwen3_calls:
                    calls = qwen3_calls
            elif use_phi4_format and content:
                phi4_calls = _extract_phi4_tool_calls(content)
                if phi4_calls:
                    calls = phi4_calls
            elif use_granite4_format and content:
                granite4_calls = _extract_granite4_tool_calls(content)
                if granite4_calls:
                    calls = granite4_calls
            
            # Fallback: parse JSON tool calls from content
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
                
                if json_content.startswith('{"name":'):
                    # Find balanced braces
                    brace_count = 0
                    for i, char in enumerate(json_content):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_obj = json_content[:i+1]
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
                                break
            
            # Exit if no tool calls were found
            if not calls:
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
                    retry_key = f"step_{steps}_{fn}_{json.dumps(args, sort_keys=True)}"
                    if not hasattr(execute, '_retry_counts'):
                        execute._retry_counts = {}
                    
                    retry_count = execute._retry_counts.get(retry_key, 0)
                    if retry_count < 2:
                        execute._retry_counts[retry_key] = retry_count + 1
                        error_fix_prompt = f"The tool call failed with error: {result}\nPlease fix the issue and try again."
                        messages.append({"role": "user", "content": error_fix_prompt})
                        error_occurred = True
                        break
                
                # Track successful operations
                if "wrote " in result and result.startswith("wrote "):
                    _add_success_to_rag(coder_prompt, fn, args, result)
            
            if error_occurred:
                continue

    return ExecSummary(steps=steps, last=last_text)
