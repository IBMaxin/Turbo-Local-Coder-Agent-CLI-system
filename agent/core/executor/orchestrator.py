"""Main orchestrator for tool-based execution loop."""
from __future__ import annotations

import json
from typing import Any

from .base import ExecSummary, get_tool_schema
from .dispatch import ToolDispatcher
from .formatters import get_formatter
from ..config import Settings, load_settings
from ..backend_manager import get_backend

try:
    from ..streaming import StreamingReporter, QuietReporter
except ImportError:
    StreamingReporter = Any  # type: ignore
    QuietReporter = Any  # type: ignore


def execute(
    coder_prompt: str,
    s: Settings | None = None,
    reporter: StreamingReporter | QuietReporter | None = None,
) -> ExecSummary:
    """Execute prompt with tool-calling loop.
    
    Args:
        coder_prompt: User prompt to execute
        s: Optional settings (loads default if None)
        reporter: Optional reporter for streaming updates
        
    Returns:
        ExecSummary with execution results
        
    Raises:
        RuntimeError: If backend fails or execution error occurs
    """
    settings = s or load_settings()
    tools = get_tool_schema()
    formatter = get_formatter(settings.coder_model)
    dispatcher = ToolDispatcher(reporter)
    
    # Format tools and build initial messages
    tools_description = formatter.format_tools(tools)
    system_prompt = formatter.get_system_prompt(tools_description)
    
    # Determine if we need API-level tools or embedded in prompt
    use_api_tools = isinstance(formatter.__class__.__name__, str) and \
                    formatter.__class__.__name__ == "StandardFormatter"
    
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": coder_prompt},
    ]
    
    print(f"[DEBUG] Using backend: {settings.backend}")
    print(f"[DEBUG] Using model: {settings.coder_model}")
    print(f"[DEBUG] Using formatter: {formatter.__class__.__name__}")
    
    backend = get_backend(settings)
    steps = 0
    last_text = ""
    
    while steps < settings.max_steps:
        steps += 1
        
        # Call backend with streaming
        content_chunks: list[str] = []
        tool_calls_from_api: list[Any] = []
        
        try:
            api_tools = tools if use_api_tools else None
            
            for response in backend.chat(
                messages,
                settings.coder_model,
                tools=api_tools,
                stream=True,
            ):
                if response.content:
                    chunk = response.content
                    content_chunks.append(chunk)
                    if reporter:
                        reporter.on_llm_chunk(chunk)
                
                if response.tool_calls:
                    tool_calls_from_api = response.tool_calls
                
                if response.done:
                    break
                    
        except Exception as e:
            print(f"[ERROR] Backend call failed: {e}")
            raise RuntimeError(f"Backend execution failed: {e}") from e
        
        content = "".join(content_chunks)
        last_text = content or last_text
        
        # Extract tool calls from content or use API-provided
        calls = tool_calls_from_api if tool_calls_from_api else formatter.extract_calls(content)
        
        # Exit if no tool calls
        if not calls:
            # Try to encourage tool usage on early steps
            if steps <= 2 and last_text and not _has_tool_results(messages):
                messages.append({
                    "role": "user",
                    "content": "Continue with the implementation. You must call tools to make actual changes.",
                })
                continue
            break
        
        # Execute tool calls
        error_occurred = False
        for call in calls:
            fn_data = call.get("function", {})
            fn_name = fn_data.get("name", "")
            raw_args = fn_data.get("arguments", "{}")
            
            # Parse arguments if string
            try:
                if isinstance(raw_args, dict):
                    args = raw_args
                else:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                args = {}
            
            # Dispatch tool
            result = dispatcher.dispatch(fn_name, args)
            messages.append({"role": "tool", "content": result, "name": fn_name})
            
            # Handle errors with retry logic
            if result.startswith("ERROR:"):
                retry_key = f"step_{steps}_{fn_name}_{json.dumps(args, sort_keys=True)}"
                retry_count = dispatcher._retry_counts.get(retry_key, 0)
                
                if retry_count < 2:
                    dispatcher._retry_counts[retry_key] = retry_count + 1
                    messages.append({
                        "role": "user",
                        "content": f"The tool call failed with error: {result}\nPlease fix the issue and try again.",
                    })
                    error_occurred = True
                    break
        
        if error_occurred:
            continue
    
    return ExecSummary(steps=steps, last=last_text)


def _has_tool_results(messages: list[dict[str, Any]]) -> bool:
    """Check if messages contain tool execution results.
    
    Args:
        messages: Message history
        
    Returns:
        True if tool results found
    """
    for msg in messages[-3:]:
        if msg.get("role") == "tool":
            return True
        content = msg.get("content", "")
        if "wrote " in content or "OK (code" in content:
            return True
    return False
