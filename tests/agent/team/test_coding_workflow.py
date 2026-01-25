"""
Tests for CodingWorkflow class.
"""
import pytest
from unittest.mock import Mock, patch
from agent.team.workflow import CodingWorkflow, WorkflowResult


class TestCodingWorkflow:
    """Tests for CodingWorkflow class."""

    @patch('agent.team.workflow.PlannerAgent')
    @patch('agent.team.workflow.CoderAgent')
    @patch('agent.team.workflow.ReviewerAgent')
    @patch('agent.team.workflow.TesterAgent')
    def test_initialization(self, mock_tester, mock_reviewer, mock_coder, mock_planner):
        """Test workflow initialization."""
        # Setup mocks
        mock_planner.return_value = Mock()
        mock_coder.return_value = Mock()
        mock_reviewer.return_value = Mock()
        mock_tester.return_value = Mock()

        workflow = CodingWorkflow(min_coverage=80.0)

        assert workflow.min_coverage == 80.0
        assert hasattr(workflow, 'orchestrator')
        assert hasattr(workflow, 'planner')
        assert hasattr(workflow, 'coder')
        assert hasattr(workflow, 'reviewer')
        assert hasattr(workflow, 'tester')

        # Check that agents were registered
        assert mock_planner.called
        assert mock_coder.called
        assert mock_reviewer.called
        assert mock_tester.called

    @patch('agent.team.workflow.PlannerAgent')
    @patch('agent.team.workflow.CoderAgent')
    @patch('agent.team.workflow.ReviewerAgent')
    @patch('agent.team.workflow.TesterAgent')
    @patch('agent.team.workflow.time')
    def test_execute_full_workflow_planning_failure(self, mock_time, mock_tester, mock_reviewer, mock_coder, mock_planner):
        """Test workflow execution when planning fails."""
        # Setup mocks
        mock_time.time.return_value = 100.0

        mock_planner_instance = Mock()
        mock_planner.return_value = mock_planner_instance
        mock_coder.return_value = Mock()
        mock_reviewer.return_value = Mock()
        mock_tester.return_value = Mock()

        workflow = CodingWorkflow(min_coverage=0.0)

        # Mock planning failure
        workflow._execute_planning_phase = Mock(return_value=None)

        result = workflow.execute_full_workflow("test description")

        assert result.success is False
        assert "Planning phase failed" in result.errors
        assert result.total_time == 0.0  # Not set due to early return

    @patch('agent.team.workflow.PlannerAgent')
    @patch('agent.team.workflow.CoderAgent')
    @patch('agent.team.workflow.ReviewerAgent')
    @patch('agent.team.workflow.TesterAgent')
    @patch('agent.team.workflow.time')
    def test_execute_full_workflow_success(self, mock_time, mock_tester, mock_reviewer, mock_coder, mock_planner):
        """Test successful workflow execution."""
        # Setup mocks
        mock_time.time.return_value = 100.0

        mock_planner_instance = Mock()
        mock_planner.return_value = mock_planner_instance
        mock_coder.return_value = Mock()
        mock_reviewer.return_value = Mock()
        mock_tester.return_value = Mock()

        workflow = CodingWorkflow()

        # Mock successful phases
        plan_result = {"task_id": "task123", "steps": ["step1"]}
        workflow._execute_planning_phase = Mock(return_value=plan_result)
        workflow._execute_coding_phase = Mock(return_value={"files": ["file1.py"]})
        workflow._execute_linting_phase = Mock(return_value={"success": True, "output": ""})
        workflow._execute_testing_phase = Mock(return_value={"coverage_estimate": {"coverage": 85.0}, "overall_success": True})
        workflow._execute_review_phase = Mock(return_value={"comments": []})

        result = workflow.execute_full_workflow("test description", skip_review=False, skip_testing=False)

        assert result.success is True
        assert result.task_id == "task123"
        assert result.plan == plan_result
        assert result.code == {"files": ["file1.py"]}
        assert result.tests == {"coverage_estimate": {"coverage": 85.0}, "overall_success": True}
        assert result.review == {"comments": []}

    def test_get_workflow_summary(self):
        """Test workflow summary generation."""
        workflow = CodingWorkflow()

        # Test successful result
        result = WorkflowResult(
            success=True,
            task_id="task123",
            plan={"plan_steps": ["step1", "step2"]},
            code={"generated_files": {"file1.py": "code"}, "code_metrics": {"total_lines": 10}},
            review={"overall_score": 8.5, "total_issues": 2, "approved": True},
            tests={"overall_success": True, "coverage_estimate": {"coverage": 85.0}},
            pr_url="https://github.com/user/repo/pull/1",
            total_time=120.5,
            errors=[]
        )

        summary = workflow.get_workflow_summary(result)
        assert "[OK] SUCCESS" in summary
        assert "120.50 seconds" in summary
        assert "task123" in summary
        assert "2 steps generated" in summary
        assert "1 files, 10 lines" in summary
        assert "8.5/10 score" in summary
        assert "[OK] APPROVED" in summary
        assert "[OK] PASSED" in summary
        assert "85% coverage" in summary
        assert "https://github.com/user/repo/pull/1" in summary

    def test_get_workflow_summary_failed(self):
        """Test workflow summary for failed result."""
        workflow = CodingWorkflow()

        result = WorkflowResult(
            success=False,
            task_id="task123",
            total_time=60.0,
            errors=["Planning failed", "Coding failed"]
        )

        summary = workflow.get_workflow_summary(result)
        assert "[FAIL] FAILED" in summary
        assert "60.00 seconds" in summary
        assert "Planning failed" in summary
        assert "Coding failed" in summary

    @patch('agent.team.workflow.PlannerAgent')
    @patch('agent.team.workflow.CoderAgent')
    @patch('agent.team.workflow.ReviewerAgent')
    @patch('agent.team.workflow.TesterAgent')
    def test_execute_planning_phase_success(self, mock_tester, mock_reviewer, mock_coder, mock_planner):
        """Test successful planning phase execution."""
        mock_planner_instance = Mock()
        mock_planner.return_value = mock_planner_instance
        mock_coder.return_value = Mock()
        mock_reviewer.return_value = Mock()
        mock_tester.return_value = Mock()

        workflow = CodingWorkflow()

        # Mock orchestrator methods
        mock_task = Mock()
        mock_task.id = "task123"
        workflow.orchestrator.submit_task = Mock(return_value="task123")
        workflow.orchestrator.assign_task = Mock(return_value=True)
        mock_result = Mock()
        mock_result.success = True
        mock_result.output = {"plan_steps": ["step1"], "detailed_instructions": "code"}
        workflow.orchestrator.get_task_results = Mock(return_value=[mock_result])

        result = workflow._execute_planning_phase("test description")

        assert result is not None
        assert result["task_id"] == "task123"
        assert result["plan_steps"] == ["step1"]

    @patch('agent.team.workflow.PlannerAgent')
    @patch('agent.team.workflow.CoderAgent')
    @patch('agent.team.workflow.ReviewerAgent')
    @patch('agent.team.workflow.TesterAgent')
    def test_execute_planning_phase_failure(self, mock_tester, mock_reviewer, mock_coder, mock_planner):
        """Test planning phase failure."""
        mock_planner_instance = Mock()
        mock_planner.return_value = mock_planner_instance
        mock_coder.return_value = Mock()
        mock_reviewer.return_value = Mock()
        mock_tester.return_value = Mock()

        workflow = CodingWorkflow()

        # Mock failure
        workflow.orchestrator.submit_task = Mock(return_value="task123")
        workflow.orchestrator.assign_task = Mock(return_value=False)

        result = workflow._execute_planning_phase("test description")

        assert result is None

    @patch('agent.team.workflow.PlannerAgent')
    @patch('agent.team.workflow.CoderAgent')
    @patch('agent.team.workflow.ReviewerAgent')
    @patch('agent.team.workflow.TesterAgent')
    def test_execute_coding_phase_success(self, mock_tester, mock_reviewer, mock_coder, mock_planner):
        """Test successful coding phase execution."""
        mock_planner_instance = Mock()
        mock_planner.return_value = mock_planner_instance
        mock_coder.return_value = Mock()
        mock_reviewer.return_value = Mock()
        mock_tester.return_value = Mock()

        workflow = CodingWorkflow()

        # Mock orchestrator
        workflow.orchestrator.submit_task = Mock(return_value="task456")
        workflow.orchestrator.assign_task = Mock(return_value=True)
        mock_result = Mock()
        mock_result.success = True
        mock_result.output = {"generated_files": {"file1.py": "code"}}
        workflow.orchestrator.get_task_results = Mock(return_value=[mock_result])

        plan_data = {"task_id": "task123"}
        result = workflow._execute_coding_phase(plan_data)

        assert result is not None
        assert result["task_id"] == "task456"
        assert result["generated_files"] == {"file1.py": "code"}

    @patch('agent.team.workflow.PlannerAgent')
    @patch('agent.team.workflow.CoderAgent')
    @patch('agent.team.workflow.ReviewerAgent')
    @patch('agent.team.workflow.TesterAgent')
    def test_execute_linting_phase_success(self, mock_tester, mock_reviewer, mock_coder, mock_planner):
        """Test successful linting phase."""
        mock_planner_instance = Mock()
        mock_planner.return_value = mock_planner_instance
        mock_coder.return_value = Mock()
        mock_reviewer.return_value = Mock()
        mock_tester.return_value = Mock()

        workflow = CodingWorkflow()

        # Mock subprocess for linting
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            result = workflow._execute_linting_phase({"files": ["file1.py"]})

            assert result["success"] is True
            assert "Linting passed" in result["output"]

    @patch('agent.team.workflow.PlannerAgent')
    @patch('agent.team.workflow.CoderAgent')
    @patch('agent.team.workflow.ReviewerAgent')
    @patch('agent.team.workflow.TesterAgent')
    def test_execute_linting_phase_failure(self, mock_tester, mock_reviewer, mock_coder, mock_planner):
        """Test linting phase failure."""
        mock_planner_instance = Mock()
        mock_planner.return_value = mock_planner_instance
        mock_coder.return_value = Mock()
        mock_reviewer.return_value = Mock()
        mock_tester.return_value = Mock()

        workflow = CodingWorkflow()

        # Mock subprocess failure
        with patch('subprocess.run') as mock_run:
            mock_proc = Mock()
            mock_proc.returncode = 1
            mock_proc.stdout = "linting errors"
            mock_run.return_value = mock_proc
            result = workflow._execute_linting_phase({"files": ["file1.py"]})

            assert result["success"] is False