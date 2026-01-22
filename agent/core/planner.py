from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from .config import Settings, load_settings
from .enhancement import AutoEnhancementSystem
from .backend_manager import get_backend


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
    
    messages = [
        {"role": "system", "content": SYSTEM_PLANNER},
        {"role": "user", "content": enhanced_task},
    ]
    
    print(f"[DEBUG] Calling planner with backend: {s.backend}")
    print(f"[DEBUG] Using model: {s.planner_model}")
    print(f"[DEBUG] Local mode: {force_local}")
    
    # Get backend and make request
    backend = get_backend(s)
    
    try:
        # For non-streaming, we should get one complete response
        # But iterate through all responses to handle both cases
        final_content = ""
        for response in backend.chat(messages, s.planner_model, tools=None, stream=False):
            if response.content:
                # For non-streaming, the last response with done=True has full content
                if response.done:
                    final_content = response.content
                    break
                else:
                    # Shouldn't happen with stream=False, but handle it
                    final_content += response.content
        
        content = final_content
        
        if not content:
            raise ValueError("planner returned empty content")
        
    except Exception as e:
        print(f"[ERROR] Backend request failed: {e}")
        raise
    
    print(f"[DEBUG] Received content length: {len(content)} chars")
    print(f"[DEBUG] Content preview: {content[:100]}...{content[-100:] if len(content) > 200 else ''}")
    
    content = _strip_code_fences(content)
    
    # Validate JSON is complete before parsing
    if not content.strip().endswith('}'):
        print(f"[WARN] JSON appears incomplete (doesn't end with }}). Content: {content[-200:]}")
    
    try:
        parsed: dict[str, Any] = json.loads(content)
    except json.JSONDecodeError as exc:
        print(f"[ERROR] Failed to parse JSON. Content length: {len(content)}")
        print(f"[ERROR] Content start: {content[:200]}")
        print(f"[ERROR] Content end: {content[-200:]}")
        print(f"[ERROR] Parse error: {exc}")
        raise ValueError(f"planner returned non-JSON: {exc}\n{content[:500]}") from exc

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
