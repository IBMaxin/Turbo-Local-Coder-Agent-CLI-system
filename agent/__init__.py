"""
Turbo Local Coder Agent

A smart development assistant that combines remote planning with local execution.

Notes:
    Importing the CLI at module import time breaks test collection when the
    dependency graph is mid-refactor. Export `cli` lazily instead.
"""

from __future__ import annotations

__version__ = "1.0.0"
__all__ = ["cli"]


def __getattr__(name: str):
    if name == "cli":
        from .main import cli

        return cli
    raise AttributeError(name)
