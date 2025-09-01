# Turbo Local Coder Agent

A hybrid AI coding system that combines remote planning with local execution, providing the best of both worlds: sophisticated planning from powerful cloud models and secure, private execution on your local machine.

## 🏗️ Architecture

The system operates in two stages:

1. **Planning Stage**: Uses a remote cloud model (`gpt-oss:120b` by default) to analyze your coding request and create a detailed step-by-step plan
2. **Execution Stage**: Uses a local model (`qwen2.5-coder` by default) to execute the plan using function calling with sandboxed tools

```
User Request → Planner (Remote) → Plan → Executor (Local) → Tools → File System
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Access to Ollama API (for remote planning)
- Local Ollama installation (for execution)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd turbo_local_coder_agent
```

2. Set up your environment variables in `.env`:
```bash
OLLAMA_API_KEY=your_api_key_here
TURBO_HOST=https://ollama.com
PLANNER_MODEL=gpt-oss:120b
CODER_MODEL=qwen2.5-coder
OLLAMA_LOCAL=http://127.0.0.1:11434
```

3. Install dependencies (if using a virtual environment):
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate
pip install -r requirements.txt  # If requirements.txt exists
```

### Usage

#### Basic Usage

**Dry Run (Planning Only):**
```bash
python3 -m agent.core.orchestrator "Create a Python calculator with basic operations"
```

**Execute Changes:**
```bash
python3 -m agent.core.orchestrator "Create a Python calculator with basic operations" --apply
```

#### Advanced Options

```bash
# Override models
python3 -m agent.core.orchestrator "your task" --planner-model "different-planner" --coder-model "different-coder"

# Limit execution steps
python3 -m agent.core.orchestrator "your task" --max-steps 10 --apply

# Get help
python3 -m agent.core.orchestrator --help
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_API_KEY` | _(required)_ | API key for remote planner |
| `TURBO_HOST` | `https://ollama.com` | Remote planner endpoint |
| `PLANNER_MODEL` | `gpt-oss:120b` | Model for planning stage |
| `CODER_MODEL` | `qwen2.5-coder` | Model for execution stage |
| `OLLAMA_LOCAL` | `http://127.0.0.1:11434` | Local Ollama endpoint |
| `MAX_STEPS` | `25` | Maximum execution steps |
| `REQUEST_TIMEOUT_S` | `120` | HTTP request timeout |
| `DRY_RUN` | `false` | Default to dry run mode |

### Configuration Loading

The system loads configuration from:
1. Environment variables
2. `.env` file in the project root (if exists)
3. Default values

## 🛠️ Tools

The executor provides these sandboxed tools to the local model:

### File System Tools
- **`fs_read(path)`**: Read UTF-8 text files
- **`fs_write(path, content)`**: Write/overwrite text files
- **`fs_list(path)`**: List directory contents

### Shell Tool
- **`shell_run(cmd)`**: Execute safe shell commands in current working directory
- Commands are filtered for security (see `agent/tools/shell.py`)

### Python Execution Tool
- **`python_run(mode, code=None)`**: 
  - `mode="pytest"`: Run pytest in current directory
  - `mode="snippet"`: Execute provided Python code snippet

### Security Features

- **Path Sandbox**: All file operations are restricted to the current working directory
- **Command Filtering**: Shell commands are filtered to prevent dangerous operations
- **No Network Access**: Tools don't provide network access to the executor

## 📊 Examples

### Example 1: Simple Script Creation

**Command:**
```bash
python3 -m agent.core.orchestrator "Create a Python script that calculates fibonacci numbers" --apply
```

**What happens:**
1. Planner creates a step-by-step plan
2. Executor uses `fs_write` to create the script
3. Executor may use `python_run` to test the script

### Example 2: Project Analysis

**Command:**
```bash
python3 -m agent.core.orchestrator "Analyze the current project structure and create a summary"
```

**What happens:**
1. Planner creates analysis plan
2. Executor uses `fs_list` and `fs_read` to explore files
3. Executor creates summary document

## 🏃‍♂️ Development

### Project Structure

```
turbo_local_coder_agent/
├── agent/
│   ├── __init__.py
│   ├── core/
│   │   ├── config.py          # Configuration management
│   │   ├── orchestrator.py    # Main CLI interface
│   │   ├── planner.py         # Remote planning logic
│   │   └── executor.py        # Local execution engine
│   └── tools/
│       ├── fs.py              # File system operations
│       ├── python_exec.py     # Python execution
│       └── shell.py           # Shell command execution
├── .env                       # Environment configuration
├── CLAUDE.md                  # Claude Code guidance
└── README.md                  # This file
```

### Running Tests

```bash
# Run all tests
python3 -m pytest

# Run specific tests
python3 -m pytest tests/test_specific.py

# Test tools individually
python3 -c "from agent.tools.fs import fs_write; print(fs_write('test.txt', 'hello'))"
```

### Adding New Tools

1. Create tool function in `agent/tools/`
2. Add tool schema to `_tool_schema()` in `executor.py`
3. Add dispatch logic to `_dispatch_tool()` in `executor.py`

## 🔍 Troubleshooting

### Common Issues

**"planner returned non-JSON"**
- Check your API key and network connection
- Verify the planner model is available
- Check logs for detailed error messages

**"no tests ran"**
- This is normal if no test files exist
- Create test files following pytest conventions

**"path escapes sandbox"**
- The security system prevents accessing files outside the project directory
- Use relative paths within the project

**Local model not responding**
- Ensure Ollama is running locally: `ollama serve`
- Check that the specified model is installed: `ollama list`
- Verify the local endpoint URL in configuration

### Debug Mode

Enable detailed logging by modifying the planner:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📚 Documentation

For complete documentation, see the **[docs/](docs/)** folder:

- **[Getting Started](docs/INSTALLATION.md)** - Detailed installation and setup
- **[Examples](docs/EXAMPLES.md)** - Usage examples and tutorials  
- **[Production Roadmap](docs/PRODUCTION_ROADMAP.md)** - 18-month development plan
- **[Technical Specifications](docs/TECHNICAL_SPECIFICATIONS.md)** - System architecture
- **[API Documentation](docs/API.md)** - Complete API reference
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

See [Implementation Guidelines](docs/IMPLEMENTATION_GUIDELINES.md) for coding standards.

## 📄 License

[Add your license information here]

## 🙏 Acknowledgments

Built with:
- [Ollama](https://ollama.ai/) for model serving
- [Typer](https://typer.tiangolo.com/) for CLI interface
- [httpx](https://www.python-httpx.org/) for HTTP requests