"""
Secure Executor Module

Splits monolithic executor into modular components.
"""
from .types import ExecSummary, ExecutionResult
from .runner import Executor

__all__ = ["Executor", "ExecSummary", "ExecutionResult"]
