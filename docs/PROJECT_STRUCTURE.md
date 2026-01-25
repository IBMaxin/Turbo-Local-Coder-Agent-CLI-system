# 📁 Project Structure

## 🏗️ Clean, Organized Architecture

```
Turbo-Local-Coder-Agent-CLI-system/
├── agent/                          # Main agent system
│   ├── __init__.py
│   ├── main.py
│   ├── core/                       # Core system components
│   │   ├── auto_config.py          # Automatic configuration detection
│   │   ├── backend_manager.py      # Backend model management
│   │   ├── config.py               # Configuration management
│   │   ├── enhancement.py          # System enhancements
│   │   ├── errors.py               # Error handling
│   │   ├── llamacpp_server.py     # LlamaCPP server integration
│   │   ├── orchestrator.py         # Main orchestration logic
│   │   ├── planner.py              # Remote planning logic
│   │   ├── streaming.py            # Streaming responses
│   │   └── executor/               # Execution engine (modular)
│   │       ├── __init__.py
│   │       ├── base.py             # Base execution classes
│   │       ├── dispatch.py         # Tool dispatching
│   │       ├── formatters.py       # Output formatting
│   │       ├── orchestrator.py     # Execution orchestration
│   │       ├── runner.py           # Execution runner
│   │       ├── sandbox.py          # Sandboxing utilities
│   │       ├── tools.py            # Tool definitions
│   │       └── types.py            # Type definitions
│   ├── team/                       # Multi-agent system with RAG
│   │   ├── __init__.py
│   │   ├── core.py                 # Team orchestration framework
│   │   ├── enhanced_agents.py      # RAG-enhanced agents
│   │   ├── rag_system.py           # Knowledge base system
│   │   ├── specialized_agents.py   # Individual agent classes
│   │   └── workflow.py             # Complete workflow orchestration
│   └── tools/                      # Tool implementations
│       ├── fs.py                   # File system operations
│       ├── python_exec.py          # Python execution
│       └── shell.py                # Shell command execution
├── docs/                           # Comprehensive documentation
│   ├── AGENT_TEAM_GUIDE.md         # Multi-agent system guide
│   ├── API_CONTRACTS.md            # API contracts
│   ├── API.md                      # Technical API reference
│   ├── CLAUDE.md                   # Claude Code guidance
│   ├── DEPLOYMENT_MAINTENANCE.md   # Deployment and maintenance
│   ├── EXAMPLES.md                 # Usage examples
│   ├── HOW_RAG_WORKS.md            # RAG system explanation
│   ├── IMPLEMENTATION_GUIDELINES.md # Coding standards
│   ├── INSTALLATION.md             # Setup guide
│   ├── LLAMACPP_SETUP.md           # LlamaCPP setup guide
│   ├── OPTIMIZATIONS.md            # Performance optimizations
│   ├── PERFORMANCE.md              # Performance documentation
│   ├── PRODUCTION_ROADMAP.md       # Development roadmap
│   ├── PROJECT_STRUCTURE.md        # This file
│   ├── README.md                   # Docs overview
│   ├── REPORT.md                   # Project reports
│   ├── TECHNICAL_SPECIFICATIONS.md # System architecture
│   ├── TESTING_STRATEGY.md         # Testing approach
│   ├── TROUBLESHOOTING.md          # Problem solving
│   ├── VERIFICATION.md             # Verification procedures
│   └── updates.md                  # Update logs
├── examples/                       # Example code and configurations
│   ├── .env.llamacpp-example       # Example env for LlamaCPP
│   ├── .env.ollama-backup          # Backup env for Ollama
│   ├── code_file.txt               # Example code file
│   ├── fibonacci_iterative.py      # Example Fibonacci script
│   └── fibonacci_recursive.py      # Example recursive Fibonacci
├── patches/                        # Git patches for changes
├── scripts/                        # Utility scripts
│   ├── __init__.py
│   ├── auto_pr.sh                  # Auto PR script
│   └── validate_system.py          # System validation
├── tests/                          # Test suite
│   ├── __init__.py
│   ├── conftest.py                 # Pytest configuration
│   ├── test_executor_base.py
│   ├── test_executor_dispatch.py
│   ├── test_executor_formatters.py
│   ├── test_executor_orchestrator.py
│   ├── test_executor.py
│   ├── agent/
│   │   └── test_main.py
│   ├── agent/core/
│   ├── agent/team/
│   │   ├── test_core.py
│   │   ├── test_enhanced_agents_new.py
│   │   ├── test_enhanced_agents.py
│   │   ├── test_rag_system.py
│   │   ├── test_specialized_agents.py
│   │   └── test_workflow.py
│   └── agent/tools/
├── .bandit                         # Bandit security config
├── .claude/                        # Claude-specific files
├── .gitignore                      # Git ignore rules
├── .github/                        # GitHub configuration
├── .roo/                           # Roo-specific files
├── AGENTS.md                       # Agent rules and guidelines
├── CLAUDE.md                       # Claude Code guidance
├── README.md                       # Main project documentation
├── agent_cli.py                    # CLI script
├── mypy.ini                        # MyPy configuration
├── pyproject.toml                  # Python project config
├── pytest.ini                      # Pytest configuration
├── requirements-dev.txt            # Development dependencies
├── requirements.txt                # Production dependencies
├── run_agent_team.py               # Team agent runner
├── setup.py                        # Setup script
├── turbo_local_coder_agent.code-workspace # VSCode workspace
└── updates.md                      # Update logs
```

## 🔧 What Each Component Does

### 📦 `agent/core/` - Original System
- **`orchestrator.py`**: Main CLI with typer interface
- **`planner.py`**: Generates plans using remote cloud model
- **`executor.py`**: Executes plans using local model with tools
- **`config.py`**: Manages settings from environment and .env

### 🛠️ `agent/tools/` - Tool Implementations
- **`fs.py`**: Sandboxed file operations (read/write/list)
- **`shell.py`**: Safe shell command execution
- **`python_exec.py`**: Python code and pytest execution

### 👥 `agent/team/` - Multi-Agent System
- **`core.py`**: Base classes (Agent, Task, TeamOrchestrator)
- **`specialized_agents.py`**: Individual agents (Planner, Coder, Reviewer, Tester)
- **`enhanced_agents.py`**: RAG-enhanced versions of specialized agents
- **`rag_system.py`**: Knowledge base with retrieval and learning
- **`workflow.py`**: Complete multi-phase workflow orchestration

## 🎯 Usage Patterns

### Single Agent (Original)
```python
# Direct usage
python3 -m agent.core.orchestrator "Create a function" --apply

# Programmatic
from agent.core.planner import get_plan
from agent.core.executor import execute
```

### Multi-Agent Team
```python
# Simple workflow
from agent.team.workflow import CodingWorkflow
workflow = CodingWorkflow()
result = workflow.execute_full_workflow("Complex project")

# Individual agents
from agent.team.enhanced_agents import RAGCoderAgent
agent = RAGCoderAgent()
```

### RAG Knowledge System
```python
# Access knowledge base
from agent.team.rag_system import RAGKnowledgeBase
rag_kb = RAGKnowledgeBase()
relevant = rag_kb.retrieve_relevant("query")

# Add custom knowledge
from agent.team.rag_system import KnowledgeChunk
chunk = KnowledgeChunk(id="custom", content="...", ...)
rag_kb.add_knowledge(chunk)
```

## ✨ Key Benefits of This Structure

1. **🧹 Clean Separation**: Original single-agent vs multi-agent systems
2. **🔄 Backwards Compatible**: Original workflows still work unchanged
3. **📈 Progressive Enhancement**: Use original system or upgrade to team
4. **🎯 Focused Modules**: Each file has a clear, single responsibility
5. **🔍 Easy Navigation**: Logical hierarchy makes finding code simple
6. **🧪 Testable**: Components can be tested independently
7. **📚 Well Documented**: Each major component explained

This structure eliminates the previous duplication between `agent/` and `agent_team/` folders while maintaining all functionality and providing a clear upgrade path from single-agent to multi-agent workflows! 🚀