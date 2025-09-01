# Coding Agent Team with RAG System

## 🎯 Overview

Your Turbo Local Coder Agent has been enhanced with a **multi-agent system** and **built-in RAG (Retrieval-Augmented Generation)** capabilities. This creates a powerful coding team that:

- 🧠 **Plans** with enhanced context from knowledge base
- 💻 **Codes** using best practices and patterns  
- 👀 **Reviews** with knowledge-informed criteria
- 🧪 **Tests** with comprehensive validation
- 📚 **Learns** from successful implementations

## 🏗️ System Architecture

```
User Request → RAG Knowledge Base → Enhanced Agents → Coordinated Output

Components:
├── RAG Knowledge Base (Built-in best practices, patterns, examples)
├── Team Orchestrator (Task coordination and workflow)
├── Specialized Agents:
│   ├── RAG Planner Agent (Enhanced planning with context)
│   ├── RAG Coder Agent (Knowledge-informed coding)  
│   ├── RAG Reviewer Agent (Best practice validation)
│   └── RAG Tester Agent (Comprehensive testing)
└── Learning System (Captures successful patterns)
```

## 🚀 Quick Start

### Using the Enhanced Workflow

```python
from agent.team.workflow import CodingWorkflow

# Initialize the enhanced workflow
workflow = CodingWorkflow()

# Execute with RAG enhancement
result = workflow.execute_full_workflow(
    "Create a REST API client with authentication and error handling",
    skip_review=False,
    skip_testing=False
)

# Get detailed summary
print(workflow.get_workflow_summary(result))
```

### Using Individual RAG Agents

```python
from agent.team.enhanced_agents import RAGPlannerAgent, RAGCoderAgent
from agent.team.core import Task

# Create RAG-enhanced agents
planner = RAGPlannerAgent()
coder = RAGCoderAgent()

# Create and process task
task = Task(description="Build a data validation system")
plan_result = planner.process_task(task)

# Use enhanced plan for coding
if plan_result.success:
    coding_task = Task(
        description="Generate code from plan",
        requirements={"plan": plan_result.output}
    )
    code_result = coder.process_task(coding_task)
```

## 📚 RAG Knowledge Base Features

### Built-in Knowledge Includes:
- ✅ Python best practices and PEP guidelines
- ✅ Common design patterns (Singleton, Factory, Decorator)
- ✅ Error handling strategies and exception patterns
- ✅ Testing approaches (unittest, pytest, fixtures)
- ✅ Algorithm implementations and optimization tips

### Dynamic Learning:
- 🧠 Captures successful code implementations
- 🔄 Builds experience base from your projects
- 📈 Improves recommendations over time
- 🎯 Context-aware knowledge retrieval

## 💻 Usage Examples

### Example 1: Simple Function with RAG Enhancement

```bash
# Traditional approach
python3 -m agent.core.orchestrator "Create a function to calculate compound interest" --apply

# RAG-enhanced approach  
python3 -c "
from agent.team.enhanced_agents import RAGCoderAgent
from agent_team.core import Task

agent = RAGCoderAgent()
task = Task(description='Create a function to calculate compound interest with input validation')
result = agent.process_task(task)
print('RAG Knowledge Applied:', result.output.get('knowledge_applied', []))
print('Quality Score:', result.output.get('quality_analysis', {}).get('quality_score'))
"
```

### Example 2: Complete Project Development

```python
from agent.team.workflow import CodingWorkflow

workflow = CodingWorkflow()

# Complex project with full workflow
result = workflow.execute_full_workflow(
    "Create a CLI tool for file organization with configuration support, "
    "logging, error handling, and comprehensive test coverage"
)

if result.success:
    print("📊 Metrics:")
    print(f"  - Files generated: {len(result.code.get('generated_files', {}))}")
    print(f"  - Quality score: {result.review.get('overall_score', 0):.1f}/10")
    print(f"  - Test coverage: {result.tests.get('coverage_estimate', {}).get('coverage', 0):.0f}%")
    print(f"  - Total time: {result.total_time:.2f}s")
```

### Example 3: Learning from Your Codebase

```python
from agent.team.rag_system import RAGKnowledgeBase, KnowledgeChunk

rag_kb = RAGKnowledgeBase()

# Add your successful code patterns
successful_pattern = KnowledgeChunk(
    id="my_api_pattern",
    content="""
    # Successful API client pattern from my project
    class APIClient:
        def __init__(self, base_url, api_key):
            self.base_url = base_url
            self.session = requests.Session()
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})
        
        def _make_request(self, method, endpoint, **kwargs):
            try:
                response = self.session.request(method, f"{self.base_url}{endpoint}", **kwargs)
                response.raise_for_status()
                return response.json()
            except requests.RequestException as e:
                logger.error(f"API request failed: {e}")
                raise
    """,
    source="my_project",
    chunk_type="pattern",
    keywords=["api", "client", "requests", "error", "handling", "session"]
)

rag_kb.add_knowledge(successful_pattern)
print("✅ Added your pattern to knowledge base")
```

## 🔧 Integration with Existing Workflow

### Enhancing Your Current Turbo Agent

```python
# Option 1: Replace existing workflow
from agent.team.workflow import CodingWorkflow

def enhanced_turbo_agent(description, apply=True):
    workflow = CodingWorkflow()
    result = workflow.execute_full_workflow(description, skip_review=not apply)
    return result

# Option 2: Use as a planning enhancement
from agent_team.enhanced_agents import RAGPlannerAgent
from agent.core.executor import execute

def hybrid_approach(description):
    # Enhanced planning with RAG
    planner = RAGPlannerAgent()
    plan_task = Task(description=description)
    plan_result = planner.process_task(plan_task)
    
    # Use original executor with enhanced plan
    if plan_result.success:
        enhanced_prompt = plan_result.output["detailed_instructions"]
        return execute(enhanced_prompt)
```

### CLI Integration

Create a new command that uses the agent team:

```python
# agent/core/team_orchestrator.py
import typer
from agent.team.workflow import CodingWorkflow

team_app = typer.Typer()

@team_app.command("team")
def team_coding(
    task: str = typer.Argument(..., help="Coding task description"),
    apply: bool = typer.Option(True, "--apply", help="Execute the workflow"),
    skip_review: bool = typer.Option(False, "--skip-review", help="Skip code review"),
    skip_testing: bool = typer.Option(False, "--skip-testing", help="Skip testing")
):
    """Execute task using the multi-agent team with RAG enhancement."""
    workflow = CodingWorkflow()
    result = workflow.execute_full_workflow(task, skip_review, skip_testing)
    
    print(workflow.get_workflow_summary(result))
    
    if not result.success:
        raise typer.Exit(1)

if __name__ == "__main__":
    team_app()
```

Usage:
```bash
python3 -m agent.core.team_orchestrator team "Build a web scraper with rate limiting"
```

## 📊 Performance Comparison

| Aspect | Original Turbo Agent | RAG-Enhanced Team |
|--------|---------------------|-------------------|
| **Planning** | Basic step generation | Context-aware planning with best practices |
| **Code Quality** | Variable quality | Consistent high-quality with knowledge application |
| **Error Handling** | Basic implementation | Comprehensive error handling patterns |
| **Testing** | Manual test creation | Automated test generation with coverage analysis |
| **Learning** | No learning capability | Builds experience base over time |
| **Consistency** | Varies by task | Applies consistent best practices |

## 🎛️ Configuration Options

### RAG Knowledge Base Settings

```python
# Custom knowledge base location
rag_kb = RAGKnowledgeBase(db_path="custom_knowledge.db")

# Adjust retrieval parameters
relevant_chunks = rag_kb.retrieve_relevant(
    query="your query",
    chunk_types=["code", "pattern"],  # Filter by type
    limit=5  # Number of chunks to retrieve
)

# Custom context size
context = rag_kb.get_context_for_query("query", max_tokens=1500)
```

### Workflow Customization

```python
class CustomWorkflow(CodingWorkflow):
    def _setup_agents(self):
        """Override to customize agents."""
        self.planner = RAGPlannerAgent("custom-planner")
        self.coder = RAGCoderAgent("custom-coder")  
        # Add specialized reviewer for your domain
        self.reviewer = CustomDomainReviewer("domain-reviewer")
        self.tester = RAGTesterAgent("custom-tester")
        
        # Register with orchestrator
        for agent in [self.planner, self.coder, self.reviewer, self.tester]:
            self.orchestrator.register_agent(agent)
```

## 🚨 Best Practices

### 1. Knowledge Base Management
- **Regular Updates**: Add successful patterns to knowledge base
- **Quality Control**: Review and refine knowledge chunks
- **Domain Specific**: Add domain-specific patterns and practices

### 2. Workflow Optimization
- **Use Appropriate Phases**: Skip review/testing for simple tasks
- **Monitor Performance**: Track quality scores and processing time
- **Iterative Improvement**: Use feedback to enhance the system

### 3. Integration Strategy
- **Start Simple**: Begin with enhanced planning, gradually add more agents
- **Measure Impact**: Compare results with original system
- **Customize**: Adapt agents for your specific coding patterns

## 🔍 Monitoring and Debugging

### Quality Metrics

```python
def analyze_workflow_quality(result):
    metrics = {
        "planning_effectiveness": len(result.plan.get("plan_steps", [])),
        "code_quality_score": result.review.get("overall_score", 0),
        "test_coverage": result.tests.get("coverage_estimate", {}).get("coverage", 0),
        "knowledge_application": len(result.code.get("knowledge_applied", [])),
        "total_issues": result.review.get("total_issues", 0),
        "processing_time": result.total_time
    }
    return metrics
```

### Debugging RAG Retrieval

```python
# Check what knowledge is being retrieved
rag_kb = RAGKnowledgeBase()
query = "your development task"
chunks = rag_kb.retrieve_relevant(query, limit=3)

for chunk, score in chunks:
    print(f"Relevance: {score:.3f}")
    print(f"Type: {chunk.chunk_type}")
    print(f"Content preview: {chunk.content[:100]}...")
    print("-" * 40)
```

## 🎯 Next Steps

1. **Try the Enhanced System**: Start with simple tasks to see RAG benefits
2. **Build Your Knowledge Base**: Add successful patterns from your projects  
3. **Customize Agents**: Adapt agents for your specific development needs
4. **Monitor and Iterate**: Track quality improvements and adjust accordingly
5. **Scale Up**: Use for increasingly complex projects as system improves

The RAG-enhanced agent team transforms your Turbo Local Coder Agent from a simple code generator into an intelligent development assistant that learns, applies best practices, and consistently delivers high-quality results! 🚀