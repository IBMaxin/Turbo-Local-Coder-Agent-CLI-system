# Implementation Guidelines

## Code Standards

### Python Style
- **PEP 8** compliance with 88-character line limit
- **Type hints** required for all functions
- **Docstrings** for LLM consumption with clear parameter descriptions
- **Dataclasses** over dictionaries for structured data

```python
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

@dataclass
class AgentTask:
    """Task definition for LLM agent execution.
    
    Args:
        description: Clear task description for LLM understanding
        context: Additional context data for task execution
        timeout_s: Maximum execution time in seconds
    """
    description: str
    context: Dict[str, Any]
    timeout_s: int = 300
    priority: int = 0
```

### Error Handling
- **Custom exceptions** with LLM-friendly error messages
- **Graceful degradation** when services unavailable
- **Detailed logging** for debugging LLM interactions

```python
class AgentExecutionError(Exception):
    """LLM agent execution failure with context for recovery."""
    
    def __init__(self, message: str, task_id: str, recovery_suggestions: List[str]):
        self.message = message
        self.task_id = task_id
        self.recovery_suggestions = recovery_suggestions
        super().__init__(message)
```

## Architecture Patterns

### Agent Design
- **Protocol-based interfaces** for LLM integration
- **Function calling schemas** for tool definitions  
- **Context injection** for RAG-enhanced responses

```python
def create_tool_schema(tool_class: BaseTool) -> Dict[str, Any]:
    """Generate OpenAI function calling schema for LLM tools."""
    return {
        "type": "function",
        "function": {
            "name": tool_class.name,
            "description": tool_class.description,
            "parameters": tool_class.get_parameters_schema()
        }
    }
```

### Security Patterns
- **Command whitelisting** for shell tools
- **Path validation** for file operations
- **Input sanitization** for LLM-generated content

```python
ALLOWED_COMMANDS = {"python", "pytest", "git", "ls", "cat", "mkdir"}

def validate_shell_command(command: str) -> bool:
    """Validate command against whitelist for LLM safety."""
    parts = shlex.split(command)
    return bool(parts) and parts[0] in ALLOWED_COMMANDS
```

## Testing Standards

### Unit Tests
- **pytest** framework with fixtures
- **Mock external services** (LLM endpoints, file system)
- **Test LLM tool schemas** and function calling

```python
@pytest.fixture
def mock_llm_client():
    """Mock LLM client for agent testing."""
    with patch('httpx.Client') as mock:
        mock.return_value.stream.return_value.__enter__.return_value.iter_lines.return_value = [
            '{"message": {"content": "test response"}}'
        ]
        yield mock

def test_agent_tool_execution(mock_llm_client):
    """Test agent executes tools correctly."""
    agent = CoderAgent()
    result = agent.execute_task("write hello.py", {})
    assert result.status == TaskStatus.COMPLETED
```

### Integration Tests
- **End-to-end workflows** with real LLM interactions
- **RAG system accuracy** testing
- **Performance benchmarks** for token usage

## Deployment Standards

### Configuration
- **Environment variables** for all external dependencies
- **Validation schemas** for configuration
- **Default fallbacks** for missing values

```python
@dataclass
class SystemConfig:
    """System configuration with LLM endpoint settings."""
    planner_model: str = "gpt-oss:20b"
    coder_model: str = "qwen2.5-coder:latest"
    max_tokens: int = 2048
    temperature: float = 0.7
    
    @classmethod
    def from_env(cls) -> 'SystemConfig':
        """Load configuration from environment variables."""
        return cls(
            planner_model=os.getenv("PLANNER_MODEL", cls.planner_model),
            coder_model=os.getenv("CODER_MODEL", cls.coder_model)
        )
```

### Monitoring
- **Structured logging** with correlation IDs
- **Metrics collection** for LLM usage and performance
- **Health checks** for all services

```python
import structlog

logger = structlog.get_logger()

def log_llm_interaction(task_id: str, model: str, tokens_used: int):
    """Log LLM interaction for monitoring and cost tracking."""
    logger.info(
        "llm_interaction",
        task_id=task_id,
        model=model,
        tokens_used=tokens_used,
        timestamp=datetime.utcnow().isoformat()
    )
```

## LLM Integration Best Practices

### Prompt Engineering
- **System prompts** with clear role definitions
- **Context injection** from RAG search results
- **Tool descriptions** optimized for function calling

```python
SYSTEM_PROMPT = """You are the Coder agent in a multi-agent system.
Your role is to execute code changes using the provided tools.
Always validate inputs and provide detailed error information.
Use incremental changes and test after each modification."""

def build_context_prompt(search_results: List[SearchResult]) -> str:
    """Build context prompt from RAG search results."""
    if not search_results:
        return ""
    
    context_parts = []
    for result in search_results[:3]:  # Limit for token efficiency
        context_parts.append(f"Context: {result.content[:200]}...")
    
    return "\n".join(context_parts)
```

### Token Optimization
- **Truncate long outputs** while preserving key information
- **Batch similar operations** to reduce API calls
- **Cache embeddings** for frequently accessed documents

```python
def truncate_for_llm(text: str, max_tokens: int = 1000) -> str:
    """Truncate text while preserving structure for LLM consumption."""
    if len(text) <= max_tokens * 4:  # Rough token estimation
        return text
    
    # Keep beginning and end, truncate middle
    half = (max_tokens * 2) // 2
    return f"{text[:half]}...\n[TRUNCATED]\n...{text[-half:]}"
```