from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

from .config import Settings, load_settings
from .enhancement import AutoEnhancementSystem


@dataclass
class Plan:
    plan: list[str]
    coder_prompt: str
    tests: list[str]


SYSTEM_PLANNER = (
    "You are Turbo, a planning-only assistant. You MUST return ONLY valid JSON with exactly these keys:\n"
    "- plan: array of 3-7 string steps (each step is a separate array element)\n"
    "- coder_prompt: string with detailed instructions for the Coder\n" 
    "- tests: array of pytest-style test strings\n\n"
    "IMPORTANT: Do NOT use any tools or function calls. Return ONLY raw JSON text in your response.\n\n"
    "Example format:\n"
    '{"plan": ["Step 1 description", "Step 2 description"], "coder_prompt": "Detailed instructions...", "tests": ["test code 1", "test code 2"]}\n\n'
    "Return ONLY the JSON object, no other text, no tool calls."
)


def _strip_code_fences(text: str) -> str:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info(f"Stripping code fences from text: {text[:60]}...")
    
    # Remove code fences
    pat = re.compile(r'^```(?:json)?\s*|\s*```$', re.MULTILINE)
    result = pat.sub("", text).strip()
    
    # Remove any trailing model tokens like <|constrain|>json
    result = re.sub(r'\s*<\|[^|]*\|>[^}]*$', '', result)
    
    # Find the JSON object (should start with { and end with })
    json_match = re.search(r'\{.*\}', result, re.DOTALL)
    if json_match:
        result = json_match.group(0)
    
    logger.info(f"Result after stripping: {result[:60]}...")
    return result


def get_plan(task: str, s: Settings | None = None, enhance: bool = True, force_local: bool = True) -> Plan:
    """Get a plan from the planner model.
    
    Args:
        task: The task description
        s: Settings object (will load from env if None)
        enhance: Whether to use task enhancement
        force_local: If True, uses local_host instead of turbo_host (default: True)
    """
    s = s or load_settings()
    
    # Apply auto-enhancement if requested
    enhanced_task = task
    task_analysis = None
    if enhance:
        try:
            enhancement_system = AutoEnhancementSystem()
            if enhancement_system.should_use_enhancement(task):
                enhanced_task, task_analysis = enhancement_system.enhance_task(task)
                print(f"[ENHANCED] Task enhanced (complexity: {task_analysis.complexity.value}, type: {task_analysis.task_type.value})")
        except Exception as e:
            print(f"[WARN] Enhancement failed, using original task: {e}")
            enhanced_task = task
    
    headers = {
        "Authorization": f"Bearer {s.api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": s.planner_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PLANNER},
            {"role": "user", "content": enhanced_task},
        ],
        "stream": False,
        "tools": [],  # Explicitly disable tools for planner
    }
    
    # Use local_host by default for local-only operation
    api_host = s.local_host if force_local else s.turbo_host
    url = f"{api_host}/api/chat"
    
    print(f"[DEBUG] Calling planner at: {url}")
    print(f"[DEBUG] Using model: {s.planner_model}")
    
    with httpx.Client(timeout=s.request_timeout_s) as cli:
        try:
            resp = cli.post(url, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            print(f"[ERROR] HTTP request failed: {e}")
            print(f"[ERROR] URL: {url}")
            print(f"[ERROR] Status code: {getattr(e.response, 'status_code', 'N/A')}")
            if hasattr(e, 'response') and e.response:
                print(f"[ERROR] Response: {e.response.text[:500]}")
            raise

    content = data.get("message", {}).get("content", "")
    
    # Handle case where model returns tool calls instead of content
    if not content and "tool_calls" in data.get("message", {}):
        raise ValueError(
            f"planner returned tool calls instead of JSON content. "
            f"Tool calls: {data.get('message', {}).get('tool_calls', [])}\n"
            f"Make sure the planner model is configured to return JSON only, not tool calls."
        )
    
    if not content:
        print(f"[ERROR] Empty content from model. Full response: {data}")
        raise ValueError(f"planner returned empty content. Response: {data}")
    
    content = _strip_code_fences(content)
    try:
        parsed: dict[str, Any] = json.loads(content)
    except json.JSONDecodeError as exc:
        print(f"[ERROR] Failed to parse JSON. Content: {content[:500]}")
        raise ValueError(f"planner returned non-JSON: {exc}\n{content}") from exc

    plan = parsed.get("plan") or []
    coder_prompt = parsed.get("coder_prompt") or ""
    tests = parsed.get("tests") or []

    # Handle case where plan is a string instead of list
    if isinstance(plan, str):
        # Try to split the string into steps
        plan = [line.strip() for line in plan.split('\n') if line.strip()]
    
    if not isinstance(plan, list):
        raise ValueError(f"plan must be a list, got {type(plan)}: {plan}")
    if not isinstance(coder_prompt, str):
        raise ValueError(f"coder_prompt must be a string, got {type(coder_prompt)}: {coder_prompt}")
    if not isinstance(tests, list):
        tests = [str(tests)] if tests else []

    return Plan(
        plan=[str(x) for x in plan],
        coder_prompt=str(coder_prompt),
        tests=[str(x) for x in tests],
    )
