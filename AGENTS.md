# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Build/Run Commands

- **Run agent**: `python3 -m agent.core.orchestrator run "task description" --apply`
- **Test**: `python3 -m pytest` (runs via python_run tool)
- **Install**: `pip install -e .`

## Architecture Patterns

- **Two-phase execution**: Remote planning (DeepSeek v3.1:671b) + local execution (QWen2.5-Coder)
- **Smart configuration**: Auto-detects task complexity and optimal settings
- **Super-RAG system**: Knowledge extraction and intelligent context enhancement
- **Sandboxed tools**: File operations, shell commands (whitelist), Python execution

## Critical Patterns

- **Shell command whitelist**: Only `python`, `pytest`, `pip`, `ls`, `cat`, `echo`, `mkdir`, `rm`, `touch`, `git` allowed
- **Configuration validation**: Settings validated on load with detailed error messages
- **Auto-complexity detection**: Tasks categorized as simple/medium/complex/enterprise
- **Enhanced execution**: Requires `--apply --enhanced` for Super-RAG intelligence

## Code Style

- Standard Python practices (no custom linting config)
- Type hints with `from __future__ import annotations`
- Dataclasses for configuration and results
- Rich library for terminal output formatting