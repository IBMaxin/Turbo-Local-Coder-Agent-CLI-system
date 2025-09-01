# Troubleshooting Guide

## Common Issues and Solutions

### Configuration Issues

#### API Key Problems

**Issue:** `HTTP 401 Unauthorized` or `Invalid API key`
```
Error: HTTP 401 - Authentication failed
```

**Solutions:**
1. Check your `.env` file contains valid `OLLAMA_API_KEY`
2. Verify the API key format (should be like `xxxxx.xxxxxx`)
3. Ensure no extra spaces or quotes in the `.env` file
4. Test API key manually:
   ```bash
   curl -H "Authorization: Bearer YOUR_KEY" https://ollama.com/api/models
   ```

#### Model Not Found

**Issue:** `Model not available` or `404 Not Found`
```
Error: Model 'gpt-oss:120b' not found
```

**Solutions:**
1. Check available models on your planner endpoint
2. Update `PLANNER_MODEL` in `.env` to an available model
3. Use model override: `--planner-model "available-model"`

#### Local Model Issues

**Issue:** `Connection refused` to local Ollama
```
Error: Connection refused to http://127.0.0.1:11434
```

**Solutions:**
1. Start Ollama locally: `ollama serve`
2. Check Ollama is running: `curl http://127.0.0.1:11434/api/tags`
3. Install required model: `ollama pull qwen2.5-coder`
4. Verify `OLLAMA_LOCAL` setting in `.env`

### Planning Phase Issues

#### Invalid JSON Response

**Issue:** `planner returned non-JSON`
```
Error: planner returned non-JSON: Expecting property name enclosed in double quotes
```

**Debugging Steps:**
1. Enable debug logging:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```
2. Check the raw planner response in logs
3. Try a simpler request to test connectivity
4. Verify planner model supports JSON output

#### Generic or Poor Plans

**Issue:** Planner creates vague, generic plans

**Solutions:**
1. **Be more specific in requests:**
   ```bash
   # Poor
   python3 -m agent.core.orchestrator "create a web app"
   
   # Better  
   python3 -m agent.core.orchestrator "create a Flask web app with user login, SQLite database, and REST API for managing todo items"
   ```

2. **Include constraints and requirements:**
   ```bash
   python3 -m agent.core.orchestrator "create a CLI tool using argparse that processes CSV files, handles missing data, and outputs summary statistics in JSON format"
   ```

3. **Specify technologies:**
   ```bash
   python3 -m agent.core.orchestrator "create a FastAPI web service with Pydantic models, SQLAlchemy ORM, and pytest tests"
   ```

### Execution Phase Issues

#### Incomplete Execution

**Issue:** Executor stops before completing all tasks

**Debugging:**
1. Check if max_steps was reached:
   ```
   Done in 25 step(s).  # Hit the limit
   ```

2. Increase step limit:
   ```bash
   python3 -m agent.core.orchestrator "task" --max-steps 50 --apply
   ```

3. Look for tool errors in the output

#### Tool Execution Failures

**Issue:** `fs_write` or other tools fail

**File System Errors:**
```
ERROR: fs_write: permission denied: /etc/config.txt
```

**Solutions:**
- Ensure write permissions in current directory
- Don't try to write outside project directory
- Check disk space: `df -h`

**Shell Command Blocked:**
```
ERROR: blocked: rm -rf /
```

**Solutions:**
- This is security working correctly
- Use allowed commands only (see shell.py)
- For dangerous operations, explain what you need

#### Model Response Issues

**Issue:** Local model produces invalid tool calls

**Symptoms:**
- JSON parsing errors in tool calls
- Malformed function arguments
- Model doesn't stop after task completion

**Solutions:**
1. Try a different coder model:
   ```bash
   python3 -m agent.core.orchestrator "task" --coder-model "codestral" --apply
   ```

2. Simplify the task:
   ```bash
   # Instead of complex multi-file project, start with single file
   python3 -m agent.core.orchestrator "create a simple calculator function" --apply
   ```

3. Check model is properly installed:
   ```bash
   ollama list | grep qwen2.5-coder
   ```

### Network and Connectivity Issues

#### Timeout Errors

**Issue:** `Request timeout` or `Connection timeout`
```
Error: Read timeout (120 seconds)
```

**Solutions:**
1. Increase timeout in `.env`:
   ```
   REQUEST_TIMEOUT_S=300
   ```

2. Check network connectivity:
   ```bash
   ping ollama.com
   curl -I https://ollama.com
   ```

3. Try during off-peak hours if using shared service

#### SSL/TLS Issues

**Issue:** SSL certificate problems
```
Error: SSL: CERTIFICATE_VERIFY_FAILED
```

**Solutions:**
1. Update certificates: `pip install --upgrade certifi`
2. Check system time is correct
3. For development, temporarily use HTTP (not recommended for production)

### Performance Issues

#### Slow Planning

**Issue:** Planning takes very long time

**Solutions:**
1. Use smaller, faster planner model
2. Reduce request complexity
3. Check planner service status

#### Slow Execution

**Issue:** Local execution is very slow

**Solutions:**
1. Use faster local model:
   ```bash
   python3 -m agent.core.orchestrator "task" --coder-model "codellama:7b" --apply
   ```

2. Reduce task complexity
3. Check system resources: `top`, `htop`
4. Ensure no other heavy processes running

### File and Directory Issues

#### Path Sandbox Violations

**Issue:** `path escapes sandbox` error
```
ValueError: path escapes sandbox
```

**Explanation:** This is security working correctly. The system prevents accessing files outside the current project directory.

**Solutions:**
- Use relative paths within the project
- Copy needed files into project directory
- Don't use `../` to access parent directories

#### Missing Dependencies

**Issue:** Python imports fail in generated code
```
ModuleNotFoundError: No module named 'requests'
```

**Solutions:**
1. Install dependencies:
   ```bash
   pip install requests
   ```

2. Ask agent to create requirements.txt:
   ```bash
   python3 -m agent.core.orchestrator "create requirements.txt with all needed dependencies" --apply
   ```

3. Use virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

## Debugging Techniques

### Enable Verbose Logging

Modify the planner to see detailed output:

```python
# In agent/core/planner.py, add at the top:
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
```

### Test Components Individually

**Test configuration:**
```python
python3 -c "from agent.core.config import load_settings; print(load_settings())"
```

**Test planner:**
```python
python3 -c "from agent.core.planner import get_plan; print(get_plan('test task'))"
```

**Test tools:**
```python
python3 -c "from agent.tools.fs import fs_write; print(fs_write('test.txt', 'hello'))"
```

### Check Logs and Output

**Monitor system resources:**
```bash
# CPU and memory
top
htop

# Disk space
df -h

# Network connections
netstat -an | grep 11434
```

**Check Ollama logs:**
```bash
# If running as service
journalctl -u ollama -f

# If running manually, check terminal output
```

### Test with Minimal Examples

**Start with simplest possible task:**
```bash
python3 -m agent.core.orchestrator "print hello world" --apply
```

**Gradually increase complexity:**
```bash
python3 -m agent.core.orchestrator "create a function that adds two numbers" --apply
```

## Error Recovery

### Partial Execution Recovery

If execution fails partway through:

1. **Check what was created:**
   ```bash
   ls -la
   git status  # if using git
   ```

2. **Continue with remaining tasks:**
   ```bash
   python3 -m agent.core.orchestrator "complete the remaining tasks: [list what's missing]" --apply
   ```

3. **Clean up and restart:**
   ```bash
   # Remove partial files if needed
   rm incomplete_file.py
   python3 -m agent.core.orchestrator "original task" --apply
   ```

### Configuration Reset

If configuration becomes corrupted:

1. **Backup current config:**
   ```bash
   cp .env .env.backup
   ```

2. **Reset to defaults:**
   ```bash
   cat > .env << EOF
   OLLAMA_API_KEY=your_key_here
   TURBO_HOST=https://ollama.com
   PLANNER_MODEL=gpt-oss:20b
   CODER_MODEL=qwen2.5-coder
   OLLAMA_LOCAL=http://127.0.0.1:11434
   EOF
   ```

3. **Test basic functionality:**
   ```bash
   python3 -m agent.core.orchestrator "create hello world script"
   ```

## Getting Help

### Diagnostic Information

When reporting issues, include:

1. **System Information:**
   ```bash
   python3 --version
   ollama --version
   uname -a  # On Linux/Mac
   ```

2. **Configuration:**
   ```bash
   # Sanitize API keys before sharing
   cat .env | sed 's/OLLAMA_API_KEY=.*/OLLAMA_API_KEY=***/'
   ```

3. **Error Messages:**
   - Full error output
   - Steps to reproduce
   - Expected vs actual behavior

4. **Model Information:**
   ```bash
   ollama list
   curl http://127.0.0.1:11434/api/tags
   ```

### Community Resources

- Check project issues on GitHub
- Look for similar problems in documentation
- Test with different models to isolate issues

### Self-Diagnosis Checklist

Before reporting issues:

- [ ] API key is valid and properly set
- [ ] Local Ollama is running and accessible
- [ ] Required models are installed
- [ ] Network connectivity is working
- [ ] Sufficient disk space and memory
- [ ] Permissions allow file creation in project directory
- [ ] Task request is clear and specific
- [ ] Tried with simpler test case first