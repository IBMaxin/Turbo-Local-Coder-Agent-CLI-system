"""Type definitions for executor."""
from dataclasses import dataclass
from typing import TypedDict, Any, Dict, Optional

@dataclass
class ExecSummary:
    steps: int
    last_output: str

@dataclass
class ExecutionResult:
    success: bool
    output: str
    error: Optional[str] = None

class ToolSchema(TypedDict):
    name: str
    description: str
    parameters: Dict[str, Any]
