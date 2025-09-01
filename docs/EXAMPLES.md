# Usage Examples and Tutorials

## Getting Started

### Example 1: Simple File Creation

**Task:** Create a basic Python script

```bash
python3 -m agent.core.orchestrator "Create a Python script that prints the current date and time" --apply
```

**What the planner creates:**
1. Create a Python file with datetime imports
2. Implement a function to get current time
3. Add proper main guard
4. Test the script execution

**Expected output:**
```
Planner: gpt-oss:120b
Executor: qwen2.5-coder
Apply: True

Plan
1. Create a new Python file named datetime_script.py
2. Import the datetime module to work with date and time
3. Create a function to get and format the current date and time
4. Add a main guard and call the function
5. Test the script execution

Executing…
Done in 2 step(s).
```

**Verification:**
```bash
python3 datetime_script.py
# Output: 2024-08-31 15:30:45.123456
```

### Example 2: Data Processing Script

**Task:** Create a CSV processor

```bash
python3 -m agent.core.orchestrator "Create a Python script that reads a CSV file and calculates summary statistics" --apply
```

**What happens:**
1. Planner creates steps for CSV processing
2. Executor creates script with pandas/csv usage
3. May create sample CSV for testing
4. Tests the functionality

### Example 3: Testing and Validation

**Task:** Create a project with tests

```bash
python3 -m agent.core.orchestrator "Create a calculator module with unit tests using pytest" --apply
```

**Generated structure:**
```
calculator.py       # Main module
test_calculator.py  # Pytest tests
```

**Running tests:**
```bash
python3 -m pytest
```

## Advanced Examples

### Example 4: Multi-file Project

**Task:** Create a web scraper project

```bash
python3 -m agent.core.orchestrator "Create a web scraping project with separate modules for fetching, parsing, and saving data" --apply
```

**Expected plan:**
1. Create main scraper module
2. Create utilities for HTTP requests
3. Create parser for HTML/JSON
4. Create data storage module
5. Create main script to coordinate
6. Add error handling and logging
7. Create requirements file

### Example 5: Configuration Management

**Task:** Create configurable application

```bash
python3 -m agent.core.orchestrator "Create a CLI application that uses environment variables and config files for settings" --apply
```

**What gets created:**
- Main application script
- Configuration loading module
- Example config files
- Environment variable documentation
- CLI argument parsing

### Example 6: API Client

**Task:** Create REST API client

```bash
python3 -m agent.core.orchestrator "Create a Python client for a REST API with authentication and error handling" --apply
```

**Components created:**
- HTTP client class
- Authentication handling
- Error exception classes
- Response parsing utilities
- Usage examples

## Dry Run Examples

Use dry runs to preview what the agent will do:

### Planning a Complex Project

```bash
python3 -m agent.core.orchestrator "Create a complete Flask web application with user authentication, database models, and RESTful API endpoints"
```

**Sample plan output:**
```
Plan
1. Set up Flask application structure with blueprints
2. Create user authentication system with login/logout
3. Set up SQLAlchemy database models for users and data
4. Implement RESTful API endpoints with proper HTTP methods
5. Add input validation and error handling
6. Create basic HTML templates for web interface
7. Add configuration management for different environments
8. Write unit tests for API endpoints and authentication
```

This helps you understand the scope before committing to execution.

## Tool-Specific Examples

### File System Operations

**Reading project files:**
```bash
python3 -m agent.core.orchestrator "Analyze all Python files in the project and create a code quality report" --apply
```

The executor will use:
- `fs_list()` to discover Python files
- `fs_read()` to analyze each file
- `fs_write()` to create the report

### Shell Commands

**Build automation:**
```bash
python3 -m agent.core.orchestrator "Create a build script that runs tests, checks code quality, and packages the application" --apply
```

The executor may use:
- `shell_run("python3 -m pytest")` for testing
- `shell_run("python3 -m pip freeze")` for dependencies
- File operations to create build scripts

### Python Execution

**Testing and validation:**
```bash
python3 -m agent.core.orchestrator "Create mathematical functions with comprehensive test coverage" --apply
```

The executor will:
- Create the functions with `fs_write()`
- Create test files with `fs_write()`
- Run tests with `python_run("pytest")`
- Execute validation with `python_run("snippet", code)`

## Error Handling Examples

### Invalid Requests

**Too vague request:**
```bash
python3 -m agent.core.orchestrator "make it better"
```

The planner will ask for clarification or make assumptions about what to improve.

**Conflicting requirements:**
```bash
python3 -m agent.core.orchestrator "Create a simple script that also has advanced machine learning capabilities"
```

The planner will balance the requirements or ask for prioritization.

### Recovery Scenarios

**Network issues during planning:**
```
Error: Failed to connect to planner endpoint
Solution: Check TURBO_HOST and OLLAMA_API_KEY settings
```

**Local model not available:**
```
Error: Connection refused to http://127.0.0.1:11434
Solution: Start Ollama locally with 'ollama serve'
```

## Best Practices

### 1. Clear, Specific Requests

**Good:**
```bash
"Create a Python function that validates email addresses using regex and returns True/False"
```

**Poor:**
```bash
"make email thing"
```

### 2. Specify Requirements

**Include context:**
```bash
"Create a data analysis script for sales data that handles missing values and generates monthly reports in both CSV and JSON formats"
```

### 3. Use Dry Runs for Exploration

```bash
# First, understand the scope
python3 -m agent.core.orchestrator "Create a machine learning pipeline for text classification"

# Then execute if satisfied
python3 -m agent.core.orchestrator "Create a machine learning pipeline for text classification" --apply
```

### 4. Iterative Development

**Start simple:**
```bash
python3 -m agent.core.orchestrator "Create a basic todo list manager with add/remove functions" --apply
```

**Then enhance:**
```bash
python3 -m agent.core.orchestrator "Add persistence to the todo list manager using JSON files" --apply
```

### 5. Specify Testing Requirements

```bash
python3 -m agent.core.orchestrator "Create a password generator with strength validation and include comprehensive pytest tests" --apply
```

## Troubleshooting Common Issues

### Planning Phase Issues

**Issue:** Planner returns generic plan
**Solution:** Be more specific about requirements, technologies, and constraints

**Issue:** Planning fails with authentication error
**Solution:** Check OLLAMA_API_KEY in .env file

### Execution Phase Issues

**Issue:** Executor creates files but they're incomplete
**Solution:** Check max_steps setting, increase if needed

**Issue:** Tools fail with permission errors
**Solution:** Ensure proper file permissions in working directory

**Issue:** Python execution fails
**Solution:** Check Python environment and required packages

### Model Issues

**Issue:** Local model not responding
**Solution:** Verify Ollama installation and model availability

**Issue:** Different model needed
**Solution:** Use --planner-model or --coder-model flags

## Integration Examples

### With Version Control

```bash
# Create a new feature
python3 -m agent.core.orchestrator "Create a logging module with configurable levels and file rotation" --apply

# Review changes
git diff

# Commit if satisfied
git add .
git commit -m "Add logging module with rotation"
```

### With CI/CD

```bash
# Create build pipeline
python3 -m agent.core.orchestrator "Create GitHub Actions workflow for Python testing and deployment" --apply
```

### With Documentation

```bash
# Generate documentation
python3 -m agent.core.orchestrator "Create comprehensive docstrings for all functions and generate API documentation" --apply
```

## Custom Workflows

### Development Workflow

1. **Planning Phase:**
   ```bash
   python3 -m agent.core.orchestrator "your task here"
   ```

2. **Review and Refine:**
   - Analyze the generated plan
   - Refine the request if needed

3. **Execution:**
   ```bash
   python3 -m agent.core.orchestrator "your refined task" --apply
   ```

4. **Validation:**
   ```bash
   python3 -m pytest  # Or other validation
   ```

5. **Iteration:**
   - Request improvements or additional features
   - Repeat the cycle

### Quality Assurance

```bash
# 1. Create functionality
python3 -m agent.core.orchestrator "Create user authentication system" --apply

# 2. Add tests
python3 -m agent.core.orchestrator "Add comprehensive tests for the authentication system" --apply

# 3. Add documentation  
python3 -m agent.core.orchestrator "Add detailed docstrings and usage examples for authentication" --apply

# 4. Security review
python3 -m agent.core.orchestrator "Review authentication system for security vulnerabilities and add improvements" --apply
```