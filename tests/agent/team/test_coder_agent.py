"""
Tests for CoderAgent.
"""
import pytest
from unittest.mock import Mock, patch
from agent.team.specialized_agents import CoderAgent
from agent.team.core import Task, AgentResult


class TestCoderAgent:
    """Tests for CoderAgent."""

    @pytest.fixture
    def agent(self):
        """Create a CoderAgent."""
        return CoderAgent("test-coder")

    @patch('agent.team.specialized_agents.execute')
    @patch('agent.team.specialized_agents.os.listdir')
    @patch('agent.tools.fs.fs_read')
    def test_process_task_success(self, mock_fs_read, mock_listdir, mock_execute, agent):
        """Test successful code generation."""
        # Mock execution
        mock_summary = Mock()
        mock_summary.steps = 5
        mock_summary.last = "Code generated successfully"
        mock_execute.return_value = mock_summary

        # Mock file collection
        mock_listdir.return_value = ["test.py", "__pycache__"]
        mock_result = Mock()
        mock_result.ok = True
        mock_result.detail = "print('hello')"
        mock_fs_read.return_value = mock_result

        task = Task(id="test-1", description="Write a function")
        result = agent.process_task(task)

        assert result.success is True
        assert "execution_summary" in result.output
        assert "generated_files" in result.output
        assert "code_metrics" in result.output

    @patch('agent.team.specialized_agents.execute')
    def test_process_task_with_plan(self, mock_execute, agent):
        """Test code generation with plan in requirements."""
        mock_summary = Mock()
        mock_summary.steps = 3
        mock_summary.last = "Done"
        mock_execute.return_value = mock_summary

        agent._collect_generated_files = Mock(return_value={})
        agent._analyze_code = Mock(return_value={})

        plan_data = {"detailed_instructions": "Write a class"}
        task = Task(id="test-1", description="Code task", requirements={"plan": plan_data})
        result = agent.process_task(task)

        mock_execute.assert_called_once_with(plan_data["detailed_instructions"], agent.settings)
        assert result.success is True

    @patch('agent.team.specialized_agents.execute')
    def test_process_task_failure(self, mock_execute, agent):
        """Test code generation failure."""
        mock_execute.side_effect = Exception("Execution failed")

        task = Task(id="test-1", description="Write code")
        result = agent.process_task(task)

        assert result.success is False
        assert "Execution failed" in result.error

    @patch('agent.team.specialized_agents.os.listdir')
    @patch('agent.team.specialized_agents.fs_read')
    def test_collect_generated_files(self, mock_fs_read, mock_listdir, agent):
        """Test collection of generated files."""
        mock_listdir.return_value = ["test.py", "__pycache__", "data.txt", "utils.py"]
        mock_result = Mock()
        mock_result.ok = True
        mock_result.detail = "print('hello')"
        mock_fs_read.return_value = mock_result

        result = agent._collect_generated_files()

        assert "test.py" in result
        assert "utils.py" in result
        assert "data.txt" not in result  # Not .py
        assert "__pycache__" not in result  # Starts with __

    @patch('os.listdir')
    @patch('agent.tools.fs.fs_read')
    def test_collect_generated_files_fs_error(self, mock_fs_read, mock_listdir, agent):
        """Test file collection with FS errors."""
        mock_listdir.return_value = ["test.py"]
        mock_result = Mock()
        mock_result.ok = False
        mock_fs_read.return_value = mock_result

        result = agent._collect_generated_files()

        assert result == {}

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

    def test_analyze_code_empty(self, agent):
        """Test code analysis with empty files."""
        result = agent._analyze_code({})

        assert result["total_lines"] == 0
        assert result["total_functions"] == 0
        assert result["total_classes"] == 0
        assert result["files_count"] == 0