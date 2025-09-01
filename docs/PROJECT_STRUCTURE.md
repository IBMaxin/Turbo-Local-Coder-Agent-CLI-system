# 📁 Project Structure

## 🏗️ Clean, Organized Architecture

```
turbo_local_coder_agent/
├── agent/                          # Main agent system
│   ├── core/                       # Original Turbo Local Coder Agent
│   │   ├── config.py              # Configuration management
│   │   ├── orchestrator.py        # Main CLI interface
│   │   ├── planner.py             # Remote planning logic
│   │   └── executor.py            # Local execution engine
│   ├── tools/                      # Tool implementations
│   │   ├── fs.py                  # File system operations
│   │   ├── python_exec.py         # Python execution
│   │   └── shell.py               # Shell command execution
│   └── team/                       # Multi-agent system with RAG
│       ├── core.py                # Team orchestration framework
│       ├── specialized_agents.py  # Individual agent classes
│       ├── enhanced_agents.py     # RAG-enhanced versions
│       ├── rag_system.py          # Knowledge base system
│       └── workflow.py            # Complete workflow orchestration
├── docs/                           # Documentation
│   ├── API.md                     # Technical API reference
│   ├── EXAMPLES.md                # Usage examples
│   ├── INSTALLATION.md            # Setup guide
│   └── TROUBLESHOOTING.md         # Problem solving
├── CLAUDE.md                       # Claude Code guidance
├── README.md                       # Main project documentation
├── AGENT_TEAM_GUIDE.md            # Multi-agent system guide
├── HOW_RAG_WORKS.md               # RAG system explanation
├── run_agent_team.py              # Convenient CLI script
├── test_rag_learning.py           # RAG learning demonstration
├── validate_system.py             # System validation
├── .env                           # Environment configuration
└── rag_knowledge.db               # RAG knowledge database
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