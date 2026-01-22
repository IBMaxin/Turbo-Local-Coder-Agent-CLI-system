"""Secure modular executor system with type safety."""
from __future__ import annotations

from .base import ExecSummary, ExecutorProtocol
from .dispatch import ToolDispatcher
from .formatters import (
    ModelToolFormatter,
    Qwen3Formatter,
    Phi4Formatter,
    Granite4Formatter,
    StandardFormatter,
)
from .orchestrator import execute

__all__ = [
    "ExecSummary",
    "ExecutorProtocol",
    "ToolDispatcher",
    "ModelToolFormatter",
    "Qwen3Formatter",
    "Phi4Formatter",
    "Granite4Formatter",
    "StandardFormatter",
    "execute",
]
