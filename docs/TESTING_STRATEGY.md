# Testing and Quality Assurance Strategy

## Testing Framework

### Unit Testing with pytest
```python
# test_agent_core.py
import pytest
from unittest.mock import patch, MagicMock
from agent.core.executor import execute, TaskResult, TaskStatus

@pytest.fixture
def mock_settings():
    """Mock system settings for testing."""
    return Settings(
        local_host="http://test:11434",
        coder_model="test-model",
        max_steps=5,
        request_timeout_s=30
    )

@pytest.fixture 
def mock_llm_response():
    """Mock LLM streaming response."""
    return [
        '{"message": {"content": "I will help you write code"}}',
        '{"message": {"tool_calls": [{"function": {"name": "fs_write", "arguments": "{\\"path\\": \\"test.py\\", \\"content\\": \\"print(\\\\\\"hello\\\\\\")\\"}"}]}}',
        '{"done": true}'
    ]

def test_executor_handles_tool_calls(mock_settings, mock_llm_response):
    """Test executor processes LLM tool calls correctly."""
    with patch('httpx.Client') as mock_client:
        mock_stream = MagicMock()
        mock_stream.__enter__.return_value.iter_lines.return_value = mock_llm_response
        mock_client.return_value.stream.return_value = mock_stream
        
        result = execute("write hello world script", mock_settings)
        
        assert result.steps > 0
        assert "hello" in result.last.lower()
```

### Integration Testing
```python
# test_agent_integration.py
import tempfile
import os
from pathlib import Path

@pytest.fixture
def temp_workspace():
    """Create temporary workspace for integration tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        os.chdir(tmpdir)
        yield Path(tmpdir)
        os.chdir(original_cwd)

def test_full_coding_workflow(temp_workspace):
    """Test complete workflow: plan -> code -> test."""
    # Test with real LLM endpoints (if available)
    task = "Create a simple calculator function with tests"
    
    # Execute planning phase
    plan_result = plan_task(task)
    assert plan_result.success
    
    # Execute coding phase  
    code_result = execute(plan_result.implementation_plan)
    assert code_result.steps > 0
    
    # Verify files were created
    assert (temp_workspace / "calculator.py").exists()
    assert (temp_workspace / "test_calculator.py").exists()
```

### RAG System Testing
```python
# test_rag_system.py
def test_rag_search_relevance():
    """Test RAG system returns relevant results."""
    rag = RAGSystem("test_knowledge.db")
    
    # Add test documents
    rag.add_document("Python functions are defined with def keyword", {"type": "syntax"})
    rag.add_document("FastAPI is a web framework for Python", {"type": "framework"})
    
    # Test search
    results = rag.search("how to define function python", top_k=1)
    
    assert len(results) > 0
    assert "def keyword" in results[0].content
    assert results[0].relevance_score > 0.5

def test_rag_embedding_quality():
    """Test embedding quality for similar concepts."""
    rag = RAGSystem("test_knowledge.db")
    
    # Test semantic similarity
    embedding1 = rag.get_embedding("Python function definition")
    embedding2 = rag.get_embedding("How to define functions in Python")
    
    similarity = cosine_similarity([embedding1], [embedding2])[0][0]
    assert similarity > 0.7  # Should be semantically similar
```

## Performance Testing

### Load Testing
```python
# test_performance.py
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

def test_concurrent_task_execution():
    """Test system handles multiple concurrent tasks."""
    tasks = [
        "write a hello world script",
        "create a simple web server", 
        "implement binary search algorithm"
    ] * 5  # 15 concurrent tasks
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(execute, task) for task in tasks]
        results = [future.result() for future in futures]
    
    execution_time = time.time() - start_time
    
    # Verify all tasks completed
    assert all(result.steps > 0 for result in results)
    # Should complete within reasonable time
    assert execution_time < 300  # 5 minutes max
```

### Memory and Token Usage
```python
def test_memory_usage():
    """Monitor memory usage during execution."""
    import psutil
    
    process = psutil.Process()
    initial_memory = process.memory_info().rss
    
    # Execute memory-intensive task
    result = execute("analyze large codebase and suggest improvements")
    
    final_memory = process.memory_info().rss
    memory_increase = final_memory - initial_memory
    
    # Memory increase should be reasonable
    assert memory_increase < 100 * 1024 * 1024  # 100MB limit

def test_token_efficiency():
    """Test token usage efficiency."""
    task = "write a simple web API"
    
    with patch('agent.core.executor._dispatch_tool') as mock_dispatch:
        mock_dispatch.return_value = "File written successfully"
        
        result = execute(task)
        
        # Count mock calls to estimate token usage
        call_count = mock_dispatch.call_count
        assert call_count < 20  # Efficient tool usage
```

## Quality Gates

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black
        args: [--line-length=88]
        
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: [--profile=black]
        
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=88, --extend-ignore=E203]
        
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
```

### CI/CD Pipeline
```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]
        
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
        
    - name: Install dependencies
      run: |
        pip install -e .
        pip install pytest pytest-cov pytest-mock
        
    - name: Run unit tests
      run: pytest tests/unit/ -v --cov=agent --cov-report=xml
      
    - name: Run integration tests
      run: pytest tests/integration/ -v
      env:
        OLLAMA_LOCAL: ${{ secrets.TEST_OLLAMA_ENDPOINT }}
        
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

## Security Testing

### Input Validation
```python
def test_shell_command_validation():
    """Test shell command whitelist enforcement."""
    from agent.tools.shell import _allowed
    
    # Safe commands
    assert _allowed("python script.py")
    assert _allowed("git status") 
    assert _allowed("ls -la")
    
    # Dangerous commands blocked
    assert not _allowed("rm -rf /")
    assert not _allowed("curl malicious-site.com")
    assert not _allowed("sudo anything")

def test_file_path_validation():
    """Test file path traversal protection."""
    from agent.tools.fs import fs_read
    
    # Normal paths allowed
    result = fs_read("./test_file.py")
    assert result.ok or "not found" in result.detail.lower()
    
    # Path traversal blocked
    result = fs_read("../../../etc/passwd")
    assert not result.ok
    assert "blocked" in result.detail.lower()
```

## Test Data Management

### Fixtures and Mocks
```python
# conftest.py
@pytest.fixture
def sample_codebase():
    """Create sample codebase structure for testing."""
    return {
        "main.py": "def main(): print('hello')",
        "utils.py": "def helper(): return True", 
        "tests/test_main.py": "def test_main(): assert True",
        "requirements.txt": "fastapi==0.100.0\npytest==7.0.0"
    }

@pytest.fixture
def mock_knowledge_base():
    """Mock RAG knowledge base with coding knowledge."""
    return [
        {"content": "FastAPI routing uses @app.get() decorator", "metadata": {"type": "web"}},
        {"content": "pytest fixtures provide reusable test data", "metadata": {"type": "testing"}},
        {"content": "Python dataclasses reduce boilerplate code", "metadata": {"type": "patterns"}}
    ]
```

### Test Execution
```bash
# Run specific test categories
pytest tests/unit/ -v                    # Unit tests only
pytest tests/integration/ -v -s          # Integration tests with output
pytest tests/ -k "rag" -v               # RAG-related tests only
pytest tests/ --cov=agent --cov-report=html  # Coverage report

# Performance testing
pytest tests/performance/ -v --benchmark-only

# Security testing  
pytest tests/security/ -v --strict
```