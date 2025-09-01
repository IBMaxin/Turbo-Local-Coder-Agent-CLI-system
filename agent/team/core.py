"""
Core components for the multi-agent system.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Type
from enum import Enum
import uuid


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Message:
    """Inter-agent communication message."""
    sender: str
    recipient: str
    content: str
    message_type: str = "general"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None


@dataclass 
class Task:
    """Represents a unit of work for agents."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    requirements: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    assignee: Optional[str] = None
    result: Optional[Any] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AgentResult:
    """Result from an agent operation."""
    agent_name: str
    task_id: str
    success: bool
    output: Any
    error: Optional[str] = None
    processing_time: Optional[float] = None


class Agent(ABC):
    """Base class for all agents in the system."""
    
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        self.inbox: List[Message] = []
        self.is_busy = False
        
    def receive_message(self, message: Message) -> None:
        """Receive a message from another agent."""
        if message.recipient == self.name or message.recipient == "all":
            self.inbox.append(message)
    
    def send_message(self, recipient: str, content: str, 
                    message_type: str = "general", 
                    correlation_id: Optional[str] = None) -> Message:
        """Create a message to send to another agent."""
        return Message(
            sender=self.name,
            recipient=recipient,
            content=content,
            message_type=message_type,
            correlation_id=correlation_id
        )
    
    @abstractmethod
    def process_task(self, task: Task) -> AgentResult:
        """Process a task and return result."""
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', role='{self.role}')"


class TeamOrchestrator:
    """Orchestrates tasks between multiple agents."""
    
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.message_queue: List[Message] = []
        self.tasks: Dict[str, Task] = {}
        self.task_results: Dict[str, List[AgentResult]] = {}
        
    def register_agent(self, agent: Agent) -> None:
        """Register an agent with the orchestrator."""
        self.agents[agent.name] = agent
        
    def get_agent(self, name: str) -> Optional[Agent]:
        """Get agent by name."""
        return self.agents.get(name)
        
    def get_agents_by_role(self, role: str) -> List[Agent]:
        """Get all agents with a specific role."""
        return [agent for agent in self.agents.values() if agent.role == role]
    
    def send_message(self, message: Message) -> None:
        """Send a message through the system."""
        self.message_queue.append(message)
        
    def process_messages(self) -> None:
        """Process all pending messages."""
        while self.message_queue:
            message = self.message_queue.pop(0)
            if message.recipient == "all":
                for agent in self.agents.values():
                    agent.receive_message(message)
            elif message.recipient in self.agents:
                self.agents[message.recipient].receive_message(message)
    
    def submit_task(self, task: Task) -> str:
        """Submit a task for processing."""
        self.tasks[task.id] = task
        self.task_results[task.id] = []
        return task.id
    
    def assign_task(self, task_id: str, agent_name: str) -> bool:
        """Assign a task to a specific agent."""
        if task_id not in self.tasks or agent_name not in self.agents:
            return False
            
        task = self.tasks[task_id]
        agent = self.agents[agent_name]
        
        if agent.is_busy:
            return False
            
        task.assignee = agent_name
        task.status = TaskStatus.IN_PROGRESS
        agent.is_busy = True
        
        # Process task
        try:
            result = agent.process_task(task)
            self.task_results[task_id].append(result)
            
            if result.success:
                task.status = TaskStatus.COMPLETED
                task.result = result.output
            else:
                task.status = TaskStatus.FAILED
                
        except Exception as e:
            result = AgentResult(
                agent_name=agent_name,
                task_id=task_id,
                success=False,
                output=None,
                error=str(e)
            )
            self.task_results[task_id].append(result)
            task.status = TaskStatus.FAILED
            
        finally:
            agent.is_busy = False
            
        return True
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get status of a task."""
        task = self.tasks.get(task_id)
        return task.status if task else None
    
    def get_task_results(self, task_id: str) -> List[AgentResult]:
        """Get all results for a task."""
        return self.task_results.get(task_id, [])