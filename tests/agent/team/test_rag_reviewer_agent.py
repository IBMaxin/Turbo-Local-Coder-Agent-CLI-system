"""
Tests for RAGReviewerAgent.
"""
import pytest
import tempfile
import os
from unittest.mock import Mock
from agent.team.enhanced_agents import RAGReviewerAgent
from agent.team.core import Task, AgentResult
from agent.team.rag_system import RAGKnowledgeBase


class TestRAGReviewerAgent:
    """Tests for RAGReviewerAgent."""

    @pytest.fixture
    def agent(self):
        """Create a RAGReviewerAgent with mocked dependencies."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        try:
            kb = RAGKnowledgeBase(db_path)
            agent = RAGReviewerAgent("test-reviewer")
            agent.rag_kb = kb
            yield agent
        finally:
            os.unlink(db_path)

    def test_initialization(self, agent):
        """Test RAGReviewerAgent initializes correctly."""
        assert agent.name == "test-reviewer"
        assert agent.role == "reviewer"
        assert isinstance(agent.rag_kb, RAGKnowledgeBase)

    def test_process_task_success(self, agent):
        """Test successful code review."""
        code_files = {
            "test.py": '''
def hello():
    """Say hello."""
    return "Hello"
'''
        }

        # Mock RAG retrieval
        mock_chunk = Mock()
        mock_chunk.content = "docstring best practice"
        agent.rag_kb.retrieve_relevant = Mock(return_value=[(mock_chunk, 0.8)])

        agent._review_file_with_rag = Mock(return_value={
            "score": 9.0,
            "issues": [],
            "line_count": 5,
            "complexity": "low",
            "rag_suggestions": []
        })
        agent._generate_rag_recommendations = Mock(return_value=["Good job"])

        task = Task(id="test-1", description="Review code", requirements={"generated_files": code_files})
        result = agent.process_task(task)

        assert result.success is True
        assert "overall_score" in result.output
        assert "file_reviews" in result.output
        assert result.output["rag_enhanced_review"] is True

    def test_process_task_no_files(self, agent):
        """Test review with no code files."""
        task = Task(id="test-1", description="Review code")
        result = agent.process_task(task)

        assert result.success is False
        assert "No code files provided" in result.error

    def test_process_task_failure(self, agent):
        """Test review failure."""
        # Force an exception
        agent.rag_kb.retrieve_relevant = Mock(side_effect=Exception("RAG error"))

        code_files = {"test.py": "print('hello')"}
        task = Task(id="test-1", description="Review", requirements={"generated_files": code_files})
        result = agent.process_task(task)

        assert result.success is False
        assert "RAG error" in result.error

    def test_review_file_with_rag_good_file(self, agent):
        """Test file review with good code."""
        content = '''
"""Module docstring."""
def func(name: str) -> str:
    """Function docstring."""
    return f"Hello {name}"
'''

        # Mock RAG knowledge
        mock_chunk = Mock()
        mock_chunk.content = "docstring type hint exception best practice"
        knowledge = [(mock_chunk, 0.9)]

        result = agent._review_file_with_rag("test.py", content, knowledge)

        assert result["score"] > 8.0
        assert len(result["issues"]) == 0
        assert result["complexity"] == "low"

    def test_review_file_with_rag_issues(self, agent):
        """Test file review finding issues."""
        content = '''
def func():  # No docstring, no type hints
    risky = open('file.txt')  # Risky operation without try
    return risky.read()
'''

        # Mock RAG knowledge
        mock_chunk = Mock()
        mock_chunk.content = "docstring type hint exception best practice"
        knowledge = [(mock_chunk, 0.9)]

        result = agent._review_file_with_rag("test.py", content, knowledge)

        assert result["score"] < 8.0
        assert len(result["issues"]) > 0
        assert any("docstrings" in issue for issue in result["issues"])
        assert any("error handling" in issue for issue in result["issues"])

    def test_assess_complexity(self, agent):
        """Test complexity assessment."""
        # Low complexity
        low_code = "def func():\n    return 1\n"
        assert agent._assess_complexity(low_code) == "low"

        # Medium complexity
        med_code = "def func():\n" + "\n".join([f"    x = {i}" for i in range(30)])
        assert agent._assess_complexity(med_code) == "medium"

        # High complexity
        high_code = "def func():\n" + "\n".join([f"    if x == {i}: pass" for i in range(50)])
        assert agent._assess_complexity(high_code) == "high"

    def test_generate_rag_recommendations(self, agent):
        """Test generation of RAG-based recommendations."""
        reviews = {
            "file1.py": {"score": 5.0, "issues": ["issue1", "issue2"]},
            "file2.py": {"score": 9.0, "issues": []}
        }

        # Mock RAG knowledge
        mock_chunk = Mock()
        mock_chunk.content = "best practice pattern"
        knowledge = [(mock_chunk, 0.8)]

        result = agent._generate_rag_recommendations(reviews, knowledge)

        assert isinstance(result, list)
        assert len(result) > 0