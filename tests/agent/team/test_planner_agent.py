"""
Tests for PlannerAgent.
"""
import pytest
from unittest.mock import Mock, patch
from agent.team.specialized_agents import PlannerAgent
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