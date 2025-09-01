# API Documentation

## Core Modules

### `agent.core.config`

#### Classes

##### `Settings`
Configuration dataclass containing all system settings.

```python
@dataclass(frozen=True)
class Settings:
    turbo_host: str           # Remote planner endpoint
    local_host: str           # Local executor endpoint  
    planner_model: str        # Remote planning model
    coder_model: str          # Local execution model
    api_key: str              # Authentication key
    max_steps: int            # Maximum execution steps
    request_timeout_s: int    # HTTP timeout in seconds
    dry_run: bool            # Whether to execute changes
```

#### Functions

##### `load_settings() -> Settings`
Load configuration from environment and `.env` file.

**Returns:** Populated `Settings` instance with defaults applied.

**Environment Variables:**
- `TURBO_HOST` (default: "https://ollama.com")
- `OLLAMA_LOCAL` (default: "http://127.0.0.1:11434") 
- `PLANNER_MODEL` (default: "gpt-oss:20b")
- `CODER_MODEL` (default: "qwen2.5-coder")
- `OLLAMA_API_KEY` (required)
- `MAX_STEPS` (default: "25")
- `REQUEST_TIMEOUT_S` (default: "120")
- `DRY_RUN` (default: "0")

##### `compact_json(obj: object) -> str`
Return compact JSON representation for logging.

---

### `agent.core.planner`

#### Classes

##### `Plan`
Data structure containing planning results.

```python
@dataclass
class Plan:
    plan: list[str]      # Step-by-step execution plan
    coder_prompt: str    # Detailed instructions for executor
    tests: list[str]     # Suggested test cases
```

#### Functions

##### `get_plan(task: str, s: Settings | None = None) -> Plan`
Generate execution plan for a given task using remote planner.

**Parameters:**
- `task`: High-level coding request from user
- `s`: Optional settings override (defaults to `load_settings()`)

**Returns:** `Plan` object with structured planning results

**Raises:**
- `ValueError`: If planner returns invalid JSON or structure
- `httpx.HTTPStatusError`: If API request fails

**Implementation Details:**
- Sends request to `{turbo_host}/api/chat` endpoint
- Uses system prompt that enforces JSON response format
- Strips code fences and extracts JSON from response
- Handles string-to-list conversion for malformed plans

---

### `agent.core.executor`

#### Classes

##### `ExecSummary` 
Execution result summary.

```python
@dataclass
class ExecSummary:
    steps: int    # Number of execution steps taken
    last: str     # Last message from executor
```

#### Functions

##### `execute(coder_prompt: str, s: Settings | None = None) -> ExecSummary`
Execute plan using local model with tool calling.

**Parameters:**
- `coder_prompt`: Detailed instructions from planner
- `s`: Optional settings override

**Returns:** `ExecSummary` with execution details

**Process:**
1. Initialize conversation with system prompt and coder instructions
2. Stream responses from local model endpoint
3. Parse and execute tool calls
4. Continue until model stops or max_steps reached

##### `_tool_schema() -> list[dict[str, Any]]`
Return OpenAI-compatible tool schema definitions.

##### `_dispatch_tool(name: str, args: dict[str, Any]) -> str`
Execute tool call and return formatted result.

**Parameters:**
- `name`: Tool function name
- `args`: Tool arguments dictionary

**Returns:** Tool execution result as string

---

### `agent.core.orchestrator`

#### CLI Commands

##### `run`
Main command for executing coding tasks.

**Usage:**
```bash
python3 -m agent.core.orchestrator run [OPTIONS] TASK
```

**Arguments:**
- `TASK`: High-level coding request (required)

**Options:**
- `--apply`: Execute changes (default: dry run)
- `--planner-model TEXT`: Override default planner model
- `--coder-model TEXT`: Override default coder model  
- `--max-steps INTEGER`: Override max execution steps (default: 25)

**Process:**
1. Load and display configuration
2. Generate plan using `get_plan()`
3. Display plan steps to user
4. If `--apply`, execute plan using `execute()`
5. Display execution summary

---

## Tools API

### `agent.tools.fs`

#### Classes

##### `FSResult`
File system operation result.

```python
@dataclass
class FSResult:
    ok: bool      # Success status
    detail: str   # Result message or error details
```

#### Functions

##### `fs_read(path: str) -> FSResult`
Read UTF-8 text file contents.

**Security:** Path is sandboxed to current working directory.

**Returns:**
- Success: `FSResult(True, file_contents)`
- Failure: `FSResult(False, error_message)`

##### `fs_write(path: str, content: str) -> FSResult`
Write UTF-8 text to file (creates parent directories if needed).

**Returns:**
- Success: `FSResult(True, "wrote {path} ({lines} lines, {bytes} bytes)")`
- Failure: `FSResult(False, error_message)`

##### `fs_list(path: str) -> FSResult`
List directory contents (directories have trailing slash).

**Returns:**
- Success: `FSResult(True, "file1\nfile2\ndir/\n...")`
- Failure: `FSResult(False, error_message)`

##### `_safe_path(path: str) -> Path`
Internal function ensuring path stays within CWD sandbox.

**Raises:** `ValueError` if path attempts to escape sandbox.

---

### `agent.tools.shell`

#### Classes

##### `ShellResult`
Shell command execution result.

```python
@dataclass
class ShellResult:
    ok: bool        # Success status (exit code == 0)
    stdout: str     # Standard output
    stderr: str     # Standard error
    code: int       # Exit code
```

#### Functions

##### `shell_run(cmd: str) -> ShellResult`
Execute shell command in current working directory.

**Security Features:**
- Whitelist-based command filtering
- Blocks dangerous commands (rm, dd, format, etc.)
- Prevents path traversal attempts
- Limits to current working directory

**Allowed Commands:**
- File operations: ls, cat, head, tail, find, grep
- Build tools: make, cmake, npm, pip, cargo, go
- Version control: git
- Python: python, python3, pytest
- Text processing: sort, uniq, wc, diff
- And more (see `shell.py` for full list)

---

### `agent.tools.python_exec`

#### Classes

##### `PyRunResult`
Python execution result.

```python
@dataclass
class PyRunResult:
    ok: bool        # Success status
    stdout: str     # Standard output
    stderr: str     # Standard error  
    code: int       # Exit code
```

#### Functions

##### `python_run(mode: str, code: str | None = None) -> PyRunResult`
Execute Python code or run pytest.

**Parameters:**
- `mode`: Execution mode ("pytest" or "snippet")
- `code`: Python code (required for "snippet" mode)

**Modes:**
- `"pytest"`: Run `python -m pytest -q` in current directory
- `"snippet"`: Execute provided code in temporary file

**Returns:** `PyRunResult` with execution details

---

## Error Handling

All tools follow consistent error handling patterns:

1. **Validation Errors**: Invalid parameters return error results
2. **Security Violations**: Path escapes raise `ValueError`
3. **System Errors**: File/network issues return error results
4. **Graceful Degradation**: Partial failures are reported, not raised

### Common Error Types

- **File Not Found**: `FSResult(False, "read: not found: {path}")`
- **Permission Denied**: `FSResult(False, "write: permission denied: {path}")`
- **Command Blocked**: `ShellResult(False, "", "blocked: {command}", 126)`
- **Invalid Mode**: `PyRunResult(False, "", "unknown mode: {mode}", 2)`
- **Path Escape**: `ValueError("path escapes sandbox")`

---

## HTTP API Interactions

### Planner Endpoint

**URL:** `{turbo_host}/api/chat`

**Method:** POST

**Headers:**
```json
{
  "Authorization": "Bearer {api_key}",
  "Content-Type": "application/json"
}
```

**Request Body:**
```json
{
  "model": "gpt-oss:120b",
  "messages": [
    {"role": "system", "content": "...planning prompt..."},
    {"role": "user", "content": "user task"}
  ],
  "stream": false
}
```

**Response:**
```json
{
  "message": {
    "content": "{\"plan\": [...], \"coder_prompt\": \"...\", \"tests\": [...]}"
  }
}
```

### Executor Endpoint

**URL:** `{local_host}/api/chat`

**Method:** POST (streaming)

**Request Body:**
```json
{
  "model": "qwen2.5-coder", 
  "messages": [...],
  "tools": [...tool_schemas...],
  "stream": true
}
```

**Streaming Response:**
```
{"message": {"content": "..."}}
{"message": {"tool_calls": [{"function": {"name": "...", "arguments": "..."}}]}}
{"done": true}
```