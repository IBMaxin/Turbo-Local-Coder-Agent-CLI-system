"""Type definitions for executor.

Keep this module minimal to avoid circular imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ExecutionResult:
    success: bool
    output: str
    error: Optional[str] = None
