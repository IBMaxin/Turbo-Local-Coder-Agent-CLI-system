# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

The Turbo Local Coder Agent is an intelligent hybrid AI coding system that combines remote planning with local execution. It uses **DeepSeek v3.1:671b** (671B parameters) for high-level planning and QWen2.5-Coder for secure local code execution.

### 🚀 **Enhanced Features (v2024+)**
- **Smart Configuration**: Auto-detects project complexity and optimal settings
- **Super-RAG Knowledge System**: Permanent learning with 671B parameter intelligence
- **Robust Error Handling**: Centralized error recovery with detailed diagnostics
- **Task Complexity Detection**: Automatically adjusts execution strategy
- **Zero-Config Experience**: Works out-of-the-box for 80% of use cases

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

## 🧠 Super-RAG Intelligence System

The **Super-RAG Knowledge Infrastructure** transforms the system into a learning, permanent intelligence that dramatically enhances local model capabilities using DeepSeek v3.1's 671B reasoning power.

### Architecture

**DeepSeek v3.1 (671B)** → **Knowledge Extraction & Analysis** → **Permanent Knowledge Base** → **Enhanced Local Execution**

- **Knowledge Extractor**: Uses DeepSeek v3.1 to analyze codebases, extract patterns, and generate architectural insights
- **Semantic Storage**: Vector database with intelligent pattern matching and relationship mapping
- **Intelligence Engine**: Dynamic context assembly and pattern recognition system  
- **Enhanced Executor**: Local model enhanced with perfect context and learned intelligence

### Key Benefits

🎯 **Dramatic Performance Improvement**: Local 7B model performs like a much larger model
🧠 **Permanent Learning**: Knowledge compounds over time, surviving model transitions  
📚 **Intelligent Context**: Perfect context assembly for any coding task
🔍 **Pattern Recognition**: Automatic identification and application of successful patterns
📈 **Self-Improving**: Gets smarter with every execution through continuous learning

### Super-RAG Workflow

1. **Knowledge Extraction**: DeepSeek v3.1 analyzes your codebase and extracts reusable patterns
2. **Task Analysis**: Deep analysis of coding requests with complexity prediction  
3. **Context Assembly**: Dynamic assembly of optimal context from knowledge base
4. **Enhanced Execution**: Local model receives perfect context and executes with higher success rates
5. **Learning Loop**: Results are analyzed and fed back into knowledge base for continuous improvement

## Development Commands

### Running the Agent

**🎯 Smart Execution (Recommended):**
The system now auto-detects optimal settings based on task complexity:

```bash
# Simple tasks - auto-configured for fast execution (10 steps, basic mode)
python3 -m agent.core.orchestrator run "fix typo in readme" --apply

# Complex tasks - auto-enables enhanced mode with more steps (50+ steps)
python3 -m agent.core.orchestrator run "refactor architecture for microservices" --apply

# Force enhanced mode with Super-RAG intelligence
python3 -m agent.core.orchestrator run "create authentication system" --apply --enhanced
```

**Legacy Usage:**
```bash
# Dry run (planning only)
python3 -m agent.core.orchestrator run "Create a Python calculator"

# Execute changes
python3 -m agent.core.orchestrator run "Create a Python calculator" --apply
```

**🚀 Super-RAG Enhanced Execution:**
```bash
# Use DeepSeek v3.1 intelligence with local qwen2.5-coder
python3 -m agent.core.orchestrator "Create a complex web API" --apply --enhanced

# Extract knowledge from codebase first, then execute with intelligence
python3 -m agent.core.orchestrator "Refactor authentication system" --apply --enhanced --extract

# Knowledge management commands
python3 -m agent.core.orchestrator knowledge extract    # Extract patterns from codebase
python3 -m agent.core.orchestrator knowledge analyze    # Analyze execution performance
python3 -m agent.core.orchestrator knowledge stats      # View knowledge statistics
```

**Legacy Unified Interface:**
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
- `PLANNER_MODEL` - Remote planning model (default: **deepseek-v3.1:671b**)
- `CODER_MODEL` - Local execution model (default: qwen2.5-coder:latest)
- `OLLAMA_LOCAL` - Local Ollama endpoint (default: http://127.0.0.1:11434)
- `MAX_STEPS` - Maximum execution steps (auto-detected based on task complexity)

### 🧠 **Smart Configuration Features**
- **Auto-Detection**: Automatically detects project type, complexity, and optimal settings
- **Task Analysis**: Analyzes task description to determine complexity (simple/medium/complex/enterprise)
- **Project Context**: Scans codebase to understand languages, frameworks, and architecture
- **Intelligent Defaults**: Zero configuration needed for most common use cases
- **Error Recovery**: Robust error handling with automatic recovery strategies

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