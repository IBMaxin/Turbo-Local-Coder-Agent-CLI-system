"""
Comprehensive tests for RAG-enhanced agents.
"""
import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from agent.team.enhanced_agents import RAGPlannerAgent, RAGCoderAgent, RAGReviewerAgent
from agent.team.core import Task, AgentResult
from agent.team.rag_system import RAGKnowledgeBase


class TestRAGPlannerAgent:
    """Tests for RAGPlannerAgent."""

    @pytest.fixture
    def agent(self):
        """Create a RAGPlannerAgent with mocked RAG KB."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        try:
            kb = RAGKnowledgeBase(db_path)
            agent = RAGPlannerAgent("test-planner")
            agent.rag_kb = kb  # Override with our KB
            yield agent
        finally:
            os.unlink(db_path)

    def test_initialization(self, agent):
        """Test RAGPlannerAgent initializes correctly."""
        assert agent.name == "test-planner"
        assert agent.role == "planner"
        assert isinstance(agent.rag_kb, RAGKnowledgeBase)
        assert hasattr(agent, 'settings')

    @patch('agent.team.enhanced_agents.get_plan')
    def test_process_task_success(self, mock_get_plan, agent):
        """Test successful task processing."""
        # Mock the plan
        mock_plan = Mock()
        mock_plan.plan = ["Step 1", "Step 2"]
        mock_plan.coder_prompt = "Write code for..."
        mock_plan.tests = ["test1", "test2"]
        mock_get_plan.return_value = mock_plan

        # Mock RAG methods
        agent.rag_kb.get_context_for_query = Mock(return_value="context")
        agent.enhance_prompt = Mock(return_value="enhanced prompt")
        agent._analyze_task_with_rag = Mock(return_value={"complexity": "medium"})

        task = Task(id="test-1", description="Create a function")
        result = agent.process_task(task)

        assert result.success is True
        assert result.agent_name == "test-planner"
        assert result.task_id == "test-1"
        assert "plan_steps" in result.output
        assert "detailed_instructions" in result.output
        assert "suggested_tests" in result.output
        assert result.processing_time >= 0

    @patch('agent.team.enhanced_agents.get_plan')
    def test_process_task_failure(self, mock_get_plan, agent):
        """Test task processing failure."""
        mock_get_plan.side_effect = Exception("Planning failed")

        task = Task(id="test-1", description="Create a function")
        result = agent.process_task(task)

        assert result.success is False
        assert result.error == "Planning failed"
        assert result.output is None

    def test_analyze_task_with_rag_simple(self, agent):
        """Test task analysis for simple tasks."""
        # Mock RAG retrieval
        mock_chunk = Mock()
        mock_chunk.chunk_type = "pattern"
        mock_chunk.content = "simple pattern"
        agent.rag_kb.retrieve_relevant = Mock(return_value=[(mock_chunk, 0.8)])

        result = agent._analyze_task_with_rag("print hello")

        assert result["complexity"] == "low"
        assert result["requires_testing"] is False
        assert "rag_insights" in result

    def test_analyze_task_with_rag_complex(self, agent):
        """Test task analysis for complex tasks."""
        # Mock RAG retrieval with complex indicators
        mock_chunk = Mock()
        mock_chunk.chunk_type = "documentation"
        mock_chunk.content = "complex advanced api web server database"
        agent.rag_kb.retrieve_relevant = Mock(return_value=[(mock_chunk, 0.9)])

        result = agent._analyze_task_with_rag("Create a web API with database")

        assert result["complexity"] == "high"
        assert result["estimated_files"] == 3
        assert result["requires_testing"] is True


class TestRAGCoderAgent:
    """Tests for RAGCoderAgent."""

    @pytest.fixture
    def agent(self):
        """Create a RAGCoderAgent with mocked dependencies."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        try:
            kb = RAGKnowledgeBase(db_path)
            agent = RAGCoderAgent("test-coder")
            agent.rag_kb = kb
            yield agent
        finally:
            os.unlink(db_path)

    def test_initialization(self, agent):
        """Test RAGCoderAgent initializes correctly."""
        assert agent.name == "test-coder"
        assert agent.role == "coder"
        assert isinstance(agent.rag_kb, RAGKnowledgeBase)

    @patch('agent.team.enhanced_agents.execute')
    def test_process_task_success(self, mock_execute, agent):
        """Test successful code generation."""
        # Mock execution result
        mock_summary = Mock()
        mock_summary.steps = 5
        mock_summary.last = "Code generated successfully"
        mock_execute.return_value = mock_summary

        # Mock other methods
        agent.enhance_prompt = Mock(return_value="enhanced prompt")
        agent._collect_generated_files = Mock(return_value={"test.py": "print('hello')"})
        agent._analyze_code_quality_with_rag = Mock(return_value={"quality_score": 8.0})
        agent._identify_applied_knowledge = Mock(return_value=["error handling"])
        agent._analyze_code = Mock(return_value={"total_lines": 10})
        agent.add_experience = Mock()

        task = Task(id="test-1", description="Write a function")
        result = agent.process_task(task)

        assert result.success is True
        assert "execution_summary" in result.output
        assert "generated_files" in result.output
        assert "code_metrics" in result.output
        assert result.output["rag_enhanced"] is True

    @patch('agent.team.enhanced_agents.execute')
    def test_process_task_with_plan(self, mock_execute, agent):
        """Test code generation with plan in requirements."""
        mock_summary = Mock()
        mock_summary.steps = 3
        mock_summary.last = "Done"
        mock_execute.return_value = mock_summary

        agent.enhance_prompt = Mock(return_value="enhanced")
        agent._collect_generated_files = Mock(return_value={})
        agent._analyze_code_quality_with_rag = Mock(return_value={})
        agent._identify_applied_knowledge = Mock(return_value=[])
        agent._analyze_code = Mock(return_value={})

        plan_data = {"detailed_instructions": "Write a class"}
        task = Task(id="test-1", description="Code task", requirements={"plan": plan_data})
        result = agent.process_task(task)

        mock_execute.assert_called_once()
        assert result.success is True

    @patch('agent.team.enhanced_agents.execute')
    def test_process_task_failure(self, mock_execute, agent):
        """Test code generation failure."""
        mock_execute.side_effect = Exception("Execution failed")

        task = Task(id="test-1", description="Write code")
        result = agent.process_task(task)

        assert result.success is False
        assert "Execution failed" in result.error

    def test_analyze_code_quality_with_rag_good_code(self, agent):
        """Test code quality analysis for good code."""
        files = {
            "test.py": '''
"""Module docstring."""
def hello(name: str) -> str:
    """Function docstring."""
    try:
        return f"Hello {name}"
    except Exception as e:
        return str(e)
'''
        }

        # Mock RAG retrieval
        mock_chunk = Mock()
        mock_chunk.content = "best practices documentation type hints"
        agent.rag_kb.retrieve_relevant = Mock(return_value=[(mock_chunk, 0.8)])

        result = agent._analyze_code_quality_with_rag(files)

        assert result["quality_score"] > 5
        assert "Has docstrings" in result["good_practices"]
        assert "Uses type hints" in result["good_practices"]
        assert "Includes error handling" in result["good_practices"]

    def test_analyze_code_quality_no_files(self, agent):
        """Test code quality analysis with no files."""
        result = agent._analyze_code_quality_with_rag({})

        assert result["analysis"] == "No files to analyze"

    def test_identify_applied_knowledge(self, agent):
        """Test identification of applied RAG knowledge."""
        files = {
            "test.py": '''
try:
    def func():
        """Docstring."""
        pass
except:
    pass

class MyClass:
    pass
'''
        }

        result = agent._identify_applied_knowledge(files)

        assert "Error handling patterns" in result
        assert "Documentation practices" in result
        assert "Object-oriented patterns" in result

    @patch('os.listdir')
    @patch('agent.tools.fs.fs_read')
    def test_collect_generated_files(self, mock_fs_read, mock_listdir, agent):
        """Test collection of generated files."""
        mock_listdir.return_value = ["test.py", "__pycache__", "data.txt"]
        mock_result = Mock()
        mock_result.ok = True
        mock_result.detail = "print('hello')"
        mock_fs_read.return_value = mock_result

        result = agent._collect_generated_files()

        assert "test.py" in result
        assert result["test.py"] == "print('hello')"
        assert "data.txt" not in result  # Not .py

    def test_analyze_code(self, agent):
        """Test basic code analysis."""
        files = {
            "file1.py": "def func():\n    pass\n\nclass MyClass:\n    pass\n",
            "file2.py": "print('hello')\n# comment\n"
        }

        result = agent._analyze_code(files)

        assert result["total_lines"] == 7  # Non-empty lines
        assert result["total_functions"] == 1
        assert result["total_classes"] == 1
        assert result["files_count"] == 2


class TestRAGReviewerAgent:
    """Tests for RAGReviewerAgent."""

    @pytest.fixture
    def agent(self):
        """Create a RAGReviewerAgent with mocked dependencies."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        try:
            kb = RAGKnowledgeBase(db_path)
            agent = RAGReviewerAgent("test-reviewer")
            agent.rag_kb = kb
            yield agent
        finally:
            os.unlink(db_path)

    def test_initialization(self, agent):
        """Test RAGReviewerAgent initializes correctly."""
        assert agent.name == "test-reviewer"
        assert agent.role == "reviewer"
        assert isinstance(agent.rag_kb, RAGKnowledgeBase)

    def test_process_task_success(self, agent):
        """Test successful code review."""
        code_files = {
            "test.py": '''
def hello():
    """Say hello."""
    return "Hello"
'''
        }

        # Mock RAG retrieval
        mock_chunk = Mock()
        mock_chunk.content = "docstring best practice"
        agent.rag_kb.retrieve_relevant = Mock(return_value=[(mock_chunk, 0.8)])

        agent._review_file_with_rag = Mock(return_value={
            "score": 9.0,
            "issues": [],
            "line_count": 5,
            "complexity": "low",
            "rag_suggestions": []
        })
        agent._generate_rag_recommendations = Mock(return_value=["Good job"])

        task = Task(id="test-1", description="Review code", requirements={"generated_files": code_files})
        result = agent.process_task(task)

        assert result.success is True
        assert "overall_score" in result.output
        assert "file_reviews" in result.output
        assert result.output["rag_enhanced_review"] is True

    def test_process_task_no_files(self, agent):
        """Test review with no code files."""
        task = Task(id="test-1", description="Review code")
        result = agent.process_task(task)

        assert result.success is False
        assert "No code files provided" in result.error

    def test_process_task_failure(self, agent):
        """Test review failure."""
        # Force an exception
        agent.rag_kb.retrieve_relevant = Mock(side_effect=Exception("RAG error"))

        code_files = {"test.py": "print('hello')"}
        task = Task(id="test-1", description="Review", requirements={"generated_files": code_files})
        result = agent.process_task(task)

        assert result.success is False
        assert "RAG error" in result.error

    def test_review_file_with_rag_good_file(self, agent):
        """Test file review with good code."""
        content = '''
"""Module docstring."""
def func(name: str) -> str:
    """Function docstring."""
    return f"Hello {name}"
'''

        # Mock RAG knowledge
        mock_chunk = Mock()
        mock_chunk.content = "docstring type hint exception best practice"
        knowledge = [(mock_chunk, 0.9)]

        result = agent._review_file_with_rag("test.py", content, knowledge)

        assert result["score"] > 8.0
        assert len(result["issues"]) == 0
        assert result["complexity"] == "low"

    def test_review_file_with_rag_issues(self, agent):
        """Test file review finding issues."""
        content = '''
def func():  # No docstring, no type hints
    risky = open('file.txt')  # Risky operation without try
    return risky.read()
'''

        # Mock RAG knowledge
        mock_chunk = Mock()
        mock_chunk.content = "docstring type hint exception best practice"
        knowledge = [(mock_chunk, 0.9)]

        result = agent._review_file_with_rag("test.py", content, knowledge)

        assert result["score"] < 8.0
        assert len(result["issues"]) > 0
        assert any("docstrings" in issue for issue in result["issues"])
        assert any("error handling" in issue for issue in result["issues"])

    def test_assess_complexity(self, agent):
        """Test complexity assessment."""
        # Low complexity
        low_code = "def func():\n    return 1\n"
        assert agent._assess_complexity(low_code) == "low"

        # Medium complexity
        med_code = "def func():\n" + "\n".join([f"    x = {i}" for i in range(30)])
        assert agent._assess_complexity(med_code) == "medium"

        # High complexity
        high_code = "def func():\n" + "\n".join([f"    if x == {i}: pass" for i in range(50)])
        assert agent._assess_complexity(high_code) == "high"

    def test_generate_rag_recommendations(self, agent):
        """Test generation of RAG-based recommendations."""
        reviews = {
            "file1.py": {"score": 5.0, "issues": ["issue1", "issue2"]},
            "file2.py": {"score": 9.0, "issues": []}
        }

        # Mock RAG knowledge
        mock_chunk = Mock()
        mock_chunk.content = "best practice pattern"
        knowledge = [(mock_chunk, 0.8)]

        result = agent._generate_rag_recommendations(reviews, knowledge)

        assert isinstance(result, list)
        assert len(result) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])