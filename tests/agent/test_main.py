"""
Tests for agent/main.py
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from agent.main import execute_standard_workflow, execute_enhanced_workflow
from agent.core.config import Settings


class TestExecuteStandardWorkflow:
    """Tests for execute_standard_workflow function."""

    @patch('agent.main.get_plan')
    @patch('agent.main.execute')
    @patch('agent.core.config.Settings._validate_settings')
    def test_execute_standard_workflow_success(self, mock_validate, mock_execute, mock_get_plan):
        """Test successful execution of standard workflow."""
        # Setup mocks
        mock_validate.return_value = None  # Skip validation
        mock_reporter = Mock()

        mock_plan = Mock()
        mock_plan.plan = ["step1", "step2"]
        mock_plan.coder_prompt = "test prompt"
        mock_get_plan.return_value = mock_plan

        mock_result = Mock()
        mock_execute.return_value = mock_result

        # Test settings
        settings = Settings(
            turbo_host="http://test.com",
            local_host="http://localhost:8000",
            planner_model="test-model",
            coder_model="test-model",
            api_key="sk-test-key-long-enough-for-validation",
            max_steps=10,
            request_timeout_s=30,
            dry_run=False
        )

        # Execute
        result = execute_standard_workflow("test task", settings, mock_reporter)

        # Verify calls
        mock_reporter.on_planning_start.assert_called_once()
        mock_get_plan.assert_called_once_with("test task", settings, enhance=True)
        mock_reporter.on_plan_created.assert_called_once_with(mock_plan.plan)
        mock_reporter.on_execution_start.assert_called_once()
        mock_reporter.on_step_start.assert_has_calls([
            ((mock_plan.plan[0], 1, 2), {}),
            ((mock_plan.plan[1], 2, 2), {})
        ])
        mock_execute.assert_called_once_with(mock_plan.coder_prompt, settings, mock_reporter)
        assert result == mock_result

    @patch('agent.main.get_plan')
    @patch('agent.core.config.Settings._validate_settings')
    def test_execute_standard_workflow_dry_run(self, mock_validate, mock_get_plan):
        """Test dry run mode."""
        mock_validate.return_value = None  # Skip validation
        mock_reporter = Mock()

        mock_plan = Mock()
        mock_get_plan.return_value = mock_plan

        settings = Settings(
            turbo_host="http://test.com",
            local_host="http://localhost:8000",
            planner_model="test-model",
            coder_model="test-model",
            api_key="sk-test-key-long-enough-for-validation",
            max_steps=10,
            request_timeout_s=30,
            dry_run=True
        )

        result = execute_standard_workflow("test task", settings, mock_reporter)

        # Should return plan without executing
        assert result == mock_plan
        mock_reporter.on_execution_start.assert_not_called()

    @patch('agent.main.get_plan')
    @patch('agent.main.execute')
    @patch('agent.core.config.Settings._validate_settings')
    def test_execute_standard_workflow_no_enhance(self, mock_validate, mock_execute, mock_get_plan):
        """Test workflow without enhancement."""
        mock_validate.return_value = None  # Skip validation
        mock_reporter = Mock()

        mock_plan = Mock()
        mock_plan.plan = ["step1", "step2"]  # Make it iterable
        mock_plan.coder_prompt = "test prompt"
        mock_get_plan.return_value = mock_plan

        mock_result = Mock()
        mock_execute.return_value = mock_result

        settings = Settings(
            turbo_host="http://test.com",
            local_host="http://localhost:8000",
            planner_model="test-model",
            coder_model="test-model",
            api_key="sk-test-key-long-enough-for-validation",
            max_steps=10,
            request_timeout_s=30,
            dry_run=False
        )

        result = execute_standard_workflow("test task", settings, mock_reporter, enhance=False)

        mock_get_plan.assert_called_once_with("test task", settings, enhance=False)
        assert result == mock_result


class TestExecuteEnhancedWorkflow:
    """Tests for execute_enhanced_workflow function."""

    @patch('agent.team.workflow.CodingWorkflow')
    @patch('agent.core.config.Settings._validate_settings')
    def test_execute_enhanced_workflow_success(self, mock_validate, mock_coding_workflow):
        """Test successful execution of enhanced workflow."""
        mock_validate.return_value = None  # Skip validation
        mock_reporter = Mock()

        mock_workflow_instance = Mock()
        mock_workflow_instance.execute_full_workflow.return_value = "success"
        mock_coding_workflow.return_value = mock_workflow_instance

        settings = Settings(
            turbo_host="http://test.com",
            local_host="http://localhost:8000",
            planner_model="test-model",
            coder_model="test-model",
            api_key="sk-test-key-long-enough-for-validation",
            max_steps=10,
            request_timeout_s=30,
            dry_run=False
        )

        result = execute_enhanced_workflow(
            "test task", settings, mock_reporter,
            enable_review=True, enable_testing=True, enable_docs=True, full_team=True
        )

        mock_reporter.on_planning_start.assert_called_once()
        mock_coding_workflow.assert_called_once()
        mock_workflow_instance.execute_full_workflow.assert_called_once_with(
            description="test task",
            skip_review=False,
            skip_testing=False,
            apply_changes=True
        )
        assert result == "success"

    @patch('agent.main.execute_standard_workflow')
    @patch('agent.core.config.Settings._validate_settings')
    def test_execute_enhanced_workflow_fallback(self, mock_validate, mock_standard_workflow):
        """Test fallback to standard workflow when team workflow fails to import."""
        mock_validate.return_value = None  # Skip validation
        mock_reporter = Mock()

        mock_standard_workflow.return_value = "fallback_result"

        settings = Settings(
            turbo_host="http://test.com",
            local_host="http://localhost:8000",
            planner_model="test-model",
            coder_model="test-model",
            api_key="sk-test-key-long-enough-for-validation",
            max_steps=10,
            request_timeout_s=30,
            dry_run=False
        )

        # Mock the import to fail by patching the module before import
        import sys
        original_modules = sys.modules.copy()
        try:
            # Remove the module if it exists
            if 'agent.team.workflow' in sys.modules:
                del sys.modules['agent.team.workflow']
            # Make sure the parent modules exist but workflow doesn't
            sys.modules['agent.team'] = Mock()
            # Now the import will fail
            result = execute_enhanced_workflow("test task", settings, mock_reporter)
        finally:
            sys.modules.update(original_modules)

        mock_standard_workflow.assert_called_once_with("test task", settings, mock_reporter)
        assert result == "fallback_result"