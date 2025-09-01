# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

This is a **Turbo Local Coder Agent** - a two-stage AI coding system that combines remote planning with local execution:

1. **Planner** (remote): Uses a cloud model (gpt-oss:120b) to create detailed step-by-step plans
2. **Executor** (local): Uses a local model (qwen2.5-coder) to execute the plan using tool calls

### Core Components

- **agent/core/orchestrator.py**: Main CLI entry point with typer interface
- **agent/core/planner.py**: Handles plan generation via remote API calls 
- **agent/core/executor.py**: Executes plans locally using tool-calling models
- **agent/core/config.py**: Configuration management from .env files
- **agent/tools/**: Tool implementations (file system, shell, Python execution)

### Data Flow

1. User provides high-level task via CLI
2. Planner creates structured plan (JSON: plan steps, coder_prompt, tests)
3. Executor receives coder_prompt and executes using available tools
4. Tools include: fs_read/write/list, shell_run, python_run (pytest/snippet modes)

## Common Commands

### Running the Agent
```bash
# Dry run (planning only)
python3 -m agent.core.orchestrator "your coding task"

# Execute changes
python3 -m agent.core.orchestrator "your coding task" --apply

# Override models
python3 -m agent.core.orchestrator "task" --planner-model "different-model" --coder-model "local-model"

# Limit execution steps
python3 -m agent.core.orchestrator "task" --max-steps 10
```

### Testing
```bash
# Run all tests
python3 -m pytest -q

# Tests are also executable via python_run tool in executor
```

## Configuration

Settings loaded from `.env` file with these key variables:
- `OLLAMA_API_KEY`: API key for remote planner
- `TURBO_HOST`: Remote planner endpoint (default: https://ollama.com)
- `PLANNER_MODEL`: Remote model for planning (default: gpt-oss:120b)  
- `CODER_MODEL`: Local model for execution (default: qwen2.5-coder:latest)
- `OLLAMA_LOCAL`: Local model endpoint (default: http://127.0.0.1:11434)
- `MAX_STEPS`: Maximum tool execution steps (default: 25)

## Tool System

The executor provides these tools to the local model:
- **fs_read**: Read UTF-8 text files
- **fs_write**: Write/overwrite UTF-8 text files  
- **fs_list**: List directory contents
- **shell_run**: Execute safe shell commands in CWD
- **python_run**: Run pytest tests or code snippets

Tools are designed with safety restrictions and return structured results with ok/error status.