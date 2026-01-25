"""
Tests for ReviewerAgent.
"""
import pytest
from agent.team.specialized_agents import ReviewerAgent
from agent.team.core import Task, AgentResult


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