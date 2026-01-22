"""
Comprehensive tests for specialized agents.
"""
import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from agent.team.specialized_agents import PlannerAgent, CoderAgent, ReviewerAgent, TesterAgent
from agent.team.core import Task, AgentResult


class TestPlannerAgent:
    """Tests for PlannerAgent."""

    @pytest.fixture
    def agent(self):
        """Create a PlannerAgent."""
        return PlannerAgent("test-planner")

    @patch('agent.team.specialized_agents.get_plan')
    def test_process_task_success(self, mock_get_plan, agent):
        """Test successful task planning."""
        # Mock the plan
        mock_plan = Mock()
        mock_plan.plan = ["Step 1", "Step 2"]
        mock_plan.coder_prompt = "Write code for..."
        mock_plan.tests = ["test1", "test2"]
        mock_get_plan.return_value = mock_plan

        task = Task(id="test-1", description="Create a function")
        result = agent.process_task(task)

        assert result.success is True
        assert result.agent_name == "test-planner"
        assert result.task_id == "test-1"
        assert "plan_steps" in result.output
        assert "detailed_instructions" in result.output
        assert "suggested_tests" in result.output
        assert result.processing_time >= 0

    @patch('agent.team.specialized_agents.get_plan')
    def test_process_task_failure(self, mock_get_plan, agent):
        """Test planning failure."""
        mock_get_plan.side_effect = Exception("Planning failed")

        task = Task(id="test-1", description="Create a function")
        result = agent.process_task(task)

        assert result.success is False
        assert result.error == "Planning failed"
        assert result.output is None

    def test_break_down_task_simple(self, agent):
        """Test task breakdown for simple tasks."""
        result = agent._break_down_task("print hello world")

        assert result["complexity"] == "low"
        assert result["estimated_files"] == 1
        assert result["requires_testing"] is False

    def test_break_down_task_complex(self, agent):
        """Test task breakdown for complex tasks."""
        result = agent._break_down_task("Create a web API with database integration")

        assert result["complexity"] == "high"
        assert result["estimated_files"] == 3
        assert "requests" in result["dependencies"]
        assert "fastapi" in result["dependencies"]
        assert result["requires_testing"] is True


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


class TestReviewerAgent:
    """Tests for ReviewerAgent."""

    @pytest.fixture
    def agent(self):
        """Create a ReviewerAgent."""
        return ReviewerAgent("test-reviewer")

    def test_process_task_success(self, agent):
        """Test successful code review."""
        code_files = {
            "test.py": '''
def hello(name):
    """Say hello."""
    return f"Hello {name}"
'''
        }

        task = Task(id="test-1", description="Review code", requirements={"generated_files": code_files})
        result = agent.process_task(task)

        assert result.success is True
        assert "overall_score" in result.output
        assert "file_reviews" in result.output
        assert "recommendations" in result.output
        assert result.output["approved"] is True  # Good code should be approved

    def test_process_task_no_files(self, agent):
        """Test review with no code files."""
        task = Task(id="test-1", description="Review code")
        result = agent.process_task(task)

        assert result.success is False
        assert "No code files provided" in result.error

    def test_process_task_failure(self, agent):
        """Test review failure."""
        # Pass invalid code_files type
        task = Task(id="test-1", description="Review", requirements={"generated_files": "not_a_dict"})
        result = agent.process_task(task)

        assert result.success is False

    def test_review_file_good_code(self, agent):
        """Test review of good code."""
        content = '''
"""Module docstring."""
def func(name: str) -> str:
    """Function docstring."""
    try:
        return f"Hello {name}"
    except Exception as e:
        return str(e)
'''

        result = agent._review_file("test.py", content)

        assert result["score"] > 8.0
        assert len(result["issues"]) == 0
        assert result["complexity"] == "low"

    def test_review_file_issues(self, agent):
        """Test review finding issues."""
        content = '''
def func():  # No docstring, no type hints, long line
    x = "this is a very long line that exceeds the recommended length of 100 characters and should be flagged"
    risky = open('file.txt')  # Risky without try
    localhost = "127.0.0.1"  # Hardcoded
    return risky.read()
'''

        result = agent._review_file("test.py", content)

        assert result["score"] < 7.0
        assert len(result["issues"]) > 0
        assert any("docstrings" in issue for issue in result["issues"])
        assert any("long" in issue for issue in result["issues"])
        assert any("error handling" in issue for issue in result["issues"])
        assert any("hardcoded" in issue.lower() for issue in result["issues"])

    def test_generate_recommendations_good(self, agent):
        """Test recommendations for good code."""
        reviews = {
            "file1.py": {"score": 9.0, "issues": []},
            "file2.py": {"score": 8.5, "issues": []}
        }

        result = agent._generate_recommendations(reviews)

        assert isinstance(result, list)
        # Should not have major recommendations for good code

    def test_generate_recommendations_issues(self, agent):
        """Test recommendations for code with issues."""
        reviews = {
            "file1.py": {"score": 5.0, "issues": ["issue1", "issue2", "issue3", "issue4", "issue5", "issue6"]},
            "file2.py": {"score": 4.0, "issues": ["long lines"]}
        }

        result = agent._generate_recommendations(reviews)

        assert "improvement" in " ".join(result).lower()
        assert "refactoring" in " ".join(result).lower()


class TestTesterAgent:
    """Tests for TesterAgent."""

    @pytest.fixture
    def agent(self):
        """Create a TesterAgent."""
        return TesterAgent("test-tester")

    @patch('agent.team.specialized_agents.python_run')
    def test_process_task_success(self, mock_python_run, agent):
        """Test successful testing."""
        # Mock python_run for syntax check
        mock_result = Mock()
        mock_result.ok = True
        mock_result.stdout = "success"
        mock_result.stderr = ""
        mock_python_run.return_value = mock_result

        code_files = {"test.py": "print('hello')"}
        suggested_tests = ["assert True"]

        task = Task(id="test-1", description="Test code",
                   requirements={"generated_files": code_files, "suggested_tests": suggested_tests})
        result = agent.process_task(task)

        assert result.success is True
        assert result.output["overall_success"] is True
        assert "syntax_check" in result.output["test_results"]
        assert "execution_test" in result.output["test_results"]

    def test_process_task_no_files(self, agent):
        """Test testing with no code files."""
        task = Task(id="test-1", description="Test code")
        result = agent.process_task(task)

        assert result.success is False
        assert "No code files provided" in result.error

    @patch('builtins.compile')
    def test_check_syntax_success(self, mock_compile, agent):
        """Test syntax checking success."""
        mock_compile.return_value = None  # Success

        code_files = {"test.py": "print('hello')"}
        result = agent._check_syntax(code_files)

        assert result["passed"] is True
        assert len(result["errors"]) == 0

    @patch('builtins.compile')
    def test_check_syntax_failure(self, mock_compile, agent):
        """Test syntax checking failure."""
        mock_compile.side_effect = SyntaxError("Invalid syntax")

        code_files = {"test.py": "print('hello'"}  # Missing closing paren
        result = agent._check_syntax(code_files)

        assert result["passed"] is False
        assert len(result["errors"]) == 1
        assert "test.py" in result["errors"][0]

    @patch('agent.team.specialized_agents.python_run')
    def test_test_execution_success(self, mock_python_run, agent):
        """Test execution testing success."""
        mock_result = Mock()
        mock_result.ok = True
        mock_result.stdout = "Hello"
        mock_result.stderr = ""
        mock_python_run.return_value = mock_result

        code_files = {"test.py": "print('Hello')"}
        result = agent._test_execution(code_files)

        assert result["passed"] is True
        assert "test.py" in result["outputs"]
        assert result["outputs"]["test.py"]["success"] is True

    @patch('agent.team.specialized_agents.python_run')
    def test_test_execution_failure(self, mock_python_run, agent):
        """Test execution testing failure."""
        mock_result = Mock()
        mock_result.ok = False
        mock_result.stdout = ""
        mock_result.stderr = "NameError: name 'undefined' is not defined"
        mock_python_run.return_value = mock_result

        code_files = {"test.py": "print(undefined)"}
        result = agent._test_execution(code_files)

        assert result["passed"] is False
        assert len(result["errors"]) == 1
        assert "test.py" in result["errors"][0]

    @patch('agent.team.specialized_agents.python_run')
    def test_run_pytest_success(self, mock_python_run, agent):
        """Test pytest execution success."""
        mock_result = Mock()
        mock_result.ok = True
        mock_result.stdout = "2 passed"
        mock_result.stderr = ""
        mock_python_run.return_value = mock_result

        result = agent._run_pytest()

        assert result["executed"] is True
        assert result["success"] is True
        assert "2 passed" in result["output"]

    @patch('agent.team.specialized_agents.python_run')
    def test_run_pytest_failure(self, mock_python_run, agent):
        """Test pytest execution failure."""
        mock_result = Mock()
        mock_result.ok = False
        mock_result.stdout = ""
        mock_result.stderr = "FAILED"
        mock_python_run.return_value = mock_result

        result = agent._run_pytest()

        assert result["executed"] is True
        assert result["success"] is False
        assert "FAILED" in result["errors"]

    @patch('agent.team.specialized_agents.python_run')
    def test_run_pytest_exception(self, mock_python_run, agent):
        """Test pytest execution with exception."""
        mock_python_run.side_effect = Exception("pytest not found")

        result = agent._run_pytest()

        assert result["executed"] is False
        assert "pytest not found" in result["error"]

    @patch('agent.team.specialized_agents.python_run')
    def test_run_unit_tests_success(self, mock_python_run, agent):
        """Test unit test execution success."""
        mock_result = Mock()
        mock_result.ok = True
        mock_result.stdout = "passed"
        mock_result.stderr = ""
        mock_python_run.return_value = mock_result

        suggested_tests = ["assert 1 + 1 == 2", "assert len([1,2,3]) == 3"]
        result = agent._run_unit_tests(suggested_tests)

        assert result["executed"] is True
        assert result["passed"] == 2
        assert result["failed"] == 0
        assert len(result["test_results"]) == 2

    @patch('agent.team.specialized_agents.python_run')
    def test_run_unit_tests_failure(self, mock_python_run, agent):
        """Test unit test execution with failures."""
        def mock_run(mode, code):
            result = Mock()
            if "failing" in code:
                result.ok = False
                result.stdout = ""
                result.stderr = "AssertionError"
            else:
                result.ok = True
                result.stdout = "passed"
                result.stderr = ""
            return result

        mock_python_run.side_effect = mock_run

        suggested_tests = ["assert 1 + 1 == 2", "assert 1 + 1 == 3  # failing"]
        result = agent._run_unit_tests(suggested_tests)

        assert result["executed"] is True
        assert result["passed"] == 1
        assert result["failed"] == 1

    def test_estimate_coverage_with_tests(self, agent):
        """Test coverage estimation with tests."""
        code_files = {
            "test.py": "def func():\n    pass\n\nclass MyClass:\n    pass\n"
        }
        tests = ["test1", "test2", "test3"]

        result = agent._estimate_coverage(code_files, tests)

        assert "coverage" in result
        assert "testable_units" in result
        assert result["testable_units"] == 2  # 1 function + 1 class
        assert result["test_count"] == 3

    def test_estimate_coverage_no_tests(self, agent):
        """Test coverage estimation without tests."""
        code_files = {"test.py": "print('hello')"}

        result = agent._estimate_coverage(code_files, [])

        assert result["coverage"] == 0
        assert "No tests available" in result["reason"]

    def test_estimate_coverage_no_testable_units(self, agent):
        """Test coverage estimation with no testable units."""
        code_files = {"test.py": "print('hello')"}  # No functions or classes

        result = agent._estimate_coverage(code_files, [])

        assert result["coverage"] == 100  # Special case
        assert "No testable units found" in result["reason"]

    def test_generate_test_recommendations_all_good(self, agent):
        """Test test recommendations when all tests pass."""
        test_results = {
            "syntax_check": {"passed": True},
            "execution_test": {"passed": True},
            "unit_tests": {"failed": 0},
            "pytest_results": {"executed": True, "success": True},
            "coverage_estimate": {"coverage": 85}
        }

        result = agent._generate_test_recommendations(test_results)

        assert isinstance(result, list)
        # Should have minimal recommendations

    def test_generate_test_recommendations_issues(self, agent):
        """Test test recommendations with issues."""
        test_results = {
            "syntax_check": {"passed": False},
            "execution_test": {"passed": False},
            "unit_tests": {"failed": 2},
            "pytest_results": {"executed": True, "success": False},
            "coverage_estimate": {"coverage": 25}
        }

        result = agent._generate_test_recommendations(test_results)

        assert len(result) > 0
        assert any("syntax" in rec.lower() for rec in result)
        assert any("runtime" in rec.lower() or "error" in rec.lower() for rec in result)
        assert any("failing" in rec.lower() for rec in result)
        assert any("coverage" in rec.lower() for rec in result)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])