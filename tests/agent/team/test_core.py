"""
Tests for agent/team/core.py
"""
import pytest
from unittest.mock import Mock
from agent.team.core import (
    TaskStatus, Message, Task, AgentResult, Agent, TeamOrchestrator
)


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_task_status_values(self):
        """Test that TaskStatus has the expected values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"


class TestMessage:
    """Tests for Message dataclass."""

    def test_message_creation(self):
        """Test creating a Message instance."""
        message = Message(
            sender="agent1",
            recipient="agent2",
            content="Hello",
            message_type="test",
            correlation_id="123"
        )

        assert message.sender == "agent1"
        assert message.recipient == "agent2"
        assert message.content == "Hello"
        assert message.message_type == "test"
        assert message.correlation_id == "123"


class TestTask:
    """Tests for Task dataclass."""

    def test_task_creation(self):
        """Test creating a Task instance."""
        task = Task(
            description="Test task",
            requirements={"key": "value"},
            status=TaskStatus.IN_PROGRESS,
            assignee="agent1"
        )

        assert task.description == "Test task"
        assert task.requirements == {"key": "value"}
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.assignee == "agent1"


class TestAgentResult:
    """Tests for AgentResult dataclass."""

    def test_agent_result_creation(self):
        """Test creating an AgentResult instance."""
        result = AgentResult(
            agent_name="agent1",
            task_id="task123",
            success=True,
            output="result",
            error="some error",
            processing_time=1.5
        )

        assert result.agent_name == "agent1"
        assert result.task_id == "task123"
        assert result.success is True
        assert result.output == "result"


class MockAgent(Agent):
    """Mock concrete agent for testing."""
    def process_task(self, task):
        return AgentResult(self.name, task.id, True, "mock result")


class TestAgent:
    """Tests for Agent abstract base class."""

    def test_agent_creation(self):
        """Test creating an Agent instance."""
        agent = MockAgent("test_agent", "tester")

        assert agent.name == "test_agent"
        assert agent.role == "tester"
        assert agent.inbox == []
        assert agent.is_busy is False

    def test_receive_message(self):
        """Test receiving messages."""
        agent = MockAgent("test_agent", "tester")

        message1 = Message(sender="other", recipient="test_agent", content="msg1")
        message2 = Message(sender="other", recipient="all", content="msg2")

        agent.receive_message(message1)
        agent.receive_message(message2)

        assert len(agent.inbox) == 2

    def test_send_message(self):
        """Test sending messages."""
        agent = MockAgent("test_agent", "tester")

        message = agent.send_message("recipient", "content", "type", "corr_id")

        assert message.sender == "test_agent"
        assert message.recipient == "recipient"
        assert message.content == "content"


class TestTeamOrchestrator:
    """Tests for TeamOrchestrator class."""

    def test_orchestrator_creation(self):
        """Test creating a TeamOrchestrator instance."""
        orchestrator = TeamOrchestrator()

        assert orchestrator.agents == {}
        assert orchestrator.message_queue == []
        assert orchestrator.tasks == {}
        assert orchestrator.task_results == {}

    def test_register_agent(self):
        """Test registering agents."""
        orchestrator = TeamOrchestrator()
        agent = MockAgent("agent1", "role1")

        orchestrator.register_agent(agent)

        assert "agent1" in orchestrator.agents
        assert orchestrator.agents["agent1"] == agent

    def test_get_agent(self):
        """Test getting agents by name."""
        orchestrator = TeamOrchestrator()
        agent = MockAgent("agent1", "role1")
        orchestrator.register_agent(agent)

        assert orchestrator.get_agent("agent1") == agent
        assert orchestrator.get_agent("nonexistent") is None

    def test_submit_task(self):
        """Test submitting tasks."""
        orchestrator = TeamOrchestrator()
        task = Task(description="test task")

        task_id = orchestrator.submit_task(task)

        assert task_id == task.id
        assert task_id in orchestrator.tasks
        assert task_id in orchestrator.task_results

    def test_assign_task_success(self):
        """Test successful task assignment."""
        orchestrator = TeamOrchestrator()
        agent = MockAgent("agent1", "role1")
        orchestrator.register_agent(agent)

        task = Task(description="test task")
        task_id = orchestrator.submit_task(task)

        result = orchestrator.assign_task(task_id, "agent1")

        assert result is True
        assert task.assignee == "agent1"
        assert task.status == TaskStatus.COMPLETED
        assert task.result == "mock result"