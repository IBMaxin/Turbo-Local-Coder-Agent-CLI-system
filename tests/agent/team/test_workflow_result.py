"""
Tests for WorkflowResult dataclass.
"""
import pytest
from agent.team.workflow import WorkflowResult


class TestWorkflowResult:
    """Tests for WorkflowResult dataclass."""

    def test_workflow_result_creation(self):
        """Test creating a WorkflowResult instance."""
        result = WorkflowResult(
            success=True,
            task_id="task123",
            plan={"steps": ["step1"]},
            code={"files": ["file1.py"]},
            review={"comments": []},
            tests={"coverage": 85.0},
            pr_url="https://github.com/user/repo/pull/1",
            total_time=120.5,
            errors=["error1", "error2"]
        )

        assert result.success is True
        assert result.task_id == "task123"
        assert result.plan == {"steps": ["step1"]}
        assert result.code == {"files": ["file1.py"]}
        assert result.review == {"comments": []}
        assert result.tests == {"coverage": 85.0}
        assert result.pr_url == "https://github.com/user/repo/pull/1"
        assert result.total_time == 120.5
        assert result.errors == ["error1", "error2"]

    def test_workflow_result_defaults(self):
        """Test WorkflowResult default values."""
        result = WorkflowResult(success=False, task_id="task123")

        assert result.success is False
        assert result.task_id == "task123"
        assert result.plan is None
        assert result.code is None
        assert result.review is None
        assert result.tests is None
        assert result.pr_url is None
        assert result.total_time == 0.0
        assert result.errors == []