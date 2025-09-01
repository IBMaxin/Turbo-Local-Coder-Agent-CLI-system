# Installation Guide

## Prerequisites

- **Python 3.8+** (tested with Python 3.8, 3.9, 3.10, 3.11)
- **Ollama** installed locally for model execution
- **Internet connection** for remote planning
- **API key** for the planning service

## Step 1: Install Ollama

### Linux/macOS
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### Windows
Download and run the installer from [ollama.ai](https://ollama.ai)

### Verify Installation
```bash
ollama --version
```

## Step 2: Install Required Models

Start Ollama service:
```bash
ollama serve
```

In another terminal, install the coder model:
```bash
ollama pull qwen2.5-coder:latest
```

Verify model installation:
```bash
ollama list
```

## Step 3: Clone and Setup Project

```bash
git clone <repository-url>
cd turbo_local_coder_agent
```

## Step 4: Configure Environment

Create a `.env` file in the project root:
```bash
cat > .env << EOF
OLLAMA_API_KEY=your_api_key_here
TURBO_HOST=https://ollama.com
PLANNER_MODEL=gpt-oss:120b
CODER_MODEL=qwen2.5-coder:latest
OLLAMA_LOCAL=http://127.0.0.1:11434
MAX_STEPS=25
REQUEST_TIMEOUT_S=120
DRY_RUN=0
EOF
```

**Important:** Replace `your_api_key_here` with your actual API key.

## Step 5: Verify Installation

Run the system validation script:
```bash
python3 validate_system.py
```

You should see:
```
🎉 All systems operational!
The Turbo Local Coder Agent is ready for use.
```

## Step 6: Test Basic Functionality

Try a simple dry run:
```bash
python3 -m agent.core.orchestrator "Create a hello world Python script"
```

If everything works, you should see a plan generated.

Execute the plan:
```bash
python3 -m agent.core.orchestrator "Create a hello world Python script" --apply
```

## Troubleshooting Installation

### Common Issues

**Ollama not found:**
```bash
# Make sure Ollama is in PATH
which ollama
# Add to PATH if needed (example for Linux/macOS)
export PATH=$PATH:/usr/local/bin
```

**Model not available:**
```bash
# Check what models are installed
ollama list
# Pull the required model
ollama pull qwen2.5-coder:latest
```

**API key issues:**
- Ensure API key is valid and has proper permissions
- Check for extra spaces or quotes in `.env` file
- Test API key manually with curl

**Python module import errors:**
```bash
# Make sure you're in the project directory
pwd
ls agent/
# If using virtual environment, activate it
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

### Dependencies

The system uses only Python standard library modules plus:
- `httpx` (installed with Ollama)
- `typer` (for CLI interface)
- `rich` (for pretty output)

If you need to install these manually:
```bash
pip install httpx typer rich
```

### Virtual Environment (Optional)

For isolated dependencies:
```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
pip install httpx typer rich
```

## Verification Checklist

- [ ] Ollama is installed and running (`ollama serve`)
- [ ] Required model is available (`ollama list`)
- [ ] `.env` file is properly configured
- [ ] API key is valid and set
- [ ] Validation script passes all tests
- [ ] Basic functionality test works

## Next Steps

Once installation is complete:

1. Read the [README.md](../README.md) for usage instructions
2. Check out [EXAMPLES.md](EXAMPLES.md) for practical examples
3. Refer to [TROUBLESHOOTING.md](TROUBLESHOOTING.md) if you encounter issues
4. See [API.md](API.md) for technical details

## Uninstallation

To remove the system:
```bash
# Remove project directory
rm -rf turbo_local_coder_agent

# Remove Ollama models (optional)
ollama rm qwen2.5-coder:latest

# Uninstall Ollama (optional)
# Linux/macOS: /usr/local/bin/ollama
# Windows: Use Add/Remove Programs
```