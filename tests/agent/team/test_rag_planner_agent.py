"""
Tests for RAGPlannerAgent.
"""
import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from agent.team.enhanced_agents import RAGPlannerAgent
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