"""
Tests for RAGCoderAgent.
"""
import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from agent.team.enhanced_agents import RAGCoderAgent
from agent.team.core import Task, AgentResult
from agent.team.rag_system import RAGKnowledgeBase


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