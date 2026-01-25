"""
Tests for TesterAgent.
"""
import pytest
from unittest.mock import Mock, patch
from agent.team.specialized_agents import TesterAgent
from agent.team.core import Task, AgentResult


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

        assert result["coverage"] == 0  # No tests available
        assert "No tests available" in result["reason"]

    def test_estimate_coverage_with_tests_no_testable_units(self, agent):
        """Test coverage estimation with tests but no testable units."""
        code_files = {"test.py": "print('hello')"}  # No functions or classes
        tests = ["test_something"]

        result = agent._estimate_coverage(code_files, tests)

        assert result["coverage"] == 100  # No testable units found
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