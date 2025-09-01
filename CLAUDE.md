# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

The Turbo Local Coder Agent is a hybrid AI coding system that combines remote planning with local execution. It uses a remote cloud model (like `gpt-oss:120b`) for high-level planning and a local model (like `qwen2.5-coder`) for secure code execution.

## Architecture

The system operates in two main phases:

1. **Planning Phase**: Remote model analyzes the coding request and creates a detailed step-by-step plan
2. **Execution Phase**: Local model executes the plan using sandboxed tools (file system, shell, Python execution)

### Core Components

- `agent/core/orchestrator.py` - Main CLI interface and workflow orchestration
- `agent/main.py` - Unified entry point with progressive enhancement flags
- `agent/core/planner.py` - Remote planning logic
- `agent/core/executor.py` - Local execution engine with tool calling
- `agent/tools/` - Sandboxed tools (fs.py, shell.py, python_exec.py)
- `agent/team/` - Multi-agent collaboration system for complex tasks

### Tool System

The executor provides these sandboxed tools:
- `fs_read(path)`, `fs_write(path, content)`, `fs_list(path)` - File system operations
- `shell_run(cmd)` - Filtered shell command execution
- `python_run(mode, code=None)` - Python execution (pytest or snippets)

All operations are restricted to the current working directory for security.

## Development Commands

### Running the Agent

Basic usage (dry run by default):
```bash
python3 -m agent.core.orchestrator "Create a Python calculator"
```

Execute changes:
```bash
python3 -m agent.core.orchestrator "Create a Python calculator" --apply
```

Using the unified interface:
```bash
python3 -m agent.main "fix typo in readme"                    # Simple task
python3 -m agent.main "add authentication" --review --test    # Enhanced workflow
python3 -m agent.main "refactor architecture" --team          # Full multi-agent
```

### Development Setup

Set up virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Testing

Run tests:
```bash
python3 -m pytest
```

Run specific tests:
```bash
python3 -m pytest tests/test_specific.py
```

The system uses pytest for testing and includes a built-in `python_run("pytest")` tool.

### Configuration

Environment variables (set in `.env` file):
- `OLLAMA_API_KEY` - API key for remote planner (required)
- `TURBO_HOST` - Remote planner endpoint (default: https://ollama.com)
- `PLANNER_MODEL` - Remote planning model (default: gpt-oss:20b)
- `CODER_MODEL` - Local execution model (default: qwen2.5-coder:latest)
- `OLLAMA_LOCAL` - Local Ollama endpoint (default: http://127.0.0.1:11434)
- `MAX_STEPS` - Maximum execution steps (default: 25)

### VS Code Tasks

The project includes VS Code tasks in `.vscode/tasks.json` for:
- Testing Ollama connection
- Running full agent pipeline
- Manual planning and execution steps

Use `Ctrl+Shift+P` → "Tasks: Run Task" to access them.

### Package Installation

Install as CLI tool:
```bash
pip install -e .
turbo-coder "your task here" --apply
```

## Key Patterns

- The system separates planning (remote) from execution (local) for security and performance
- All file operations are sandboxed to the current working directory
- The planner creates structured plans with specific steps and a coder prompt
- The executor uses function calling to interact with tools
- Progressive enhancement allows simple tasks to use single-agent workflow while complex tasks can use multi-agent collaboration