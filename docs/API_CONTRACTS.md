# API Contracts and Interfaces

## Core System APIs

### Agent Orchestrator API

```python
from typing import Protocol, Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class TaskResult:
    """Standardized task execution result."""
    task_id: str
    status: TaskStatus
    output: str
    metadata: Dict[str, Any]
    execution_time_ms: int
    error_details: Optional[str] = None

class AgentProtocol(Protocol):
    """Standard interface all agents must implement."""
    
    def execute_task(self, task: str, context: Dict[str, Any]) -> TaskResult:
        """Execute a task with given context."""
        ...
    
    def get_capabilities(self) -> List[str]:
        """Return list of agent capabilities."""
        ...
    
    def validate_task(self, task: str) -> bool:
        """Validate if agent can handle the task."""
        ...

class OrchestratorAPI:
    """Main orchestrator interface for coordinating agents."""
    
    def submit_task(self, task: str, agent_type: str, priority: int = 0) -> str:
        """Submit task to appropriate agent queue."""
        
    def get_task_status(self, task_id: str) -> TaskStatus:
        """Get current status of a task."""
        
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or in-progress task."""
        
    def get_results(self, task_id: str) -> Optional[TaskResult]:
        """Retrieve results for completed task."""
```

### Tool System API

```python
from abc import ABC, abstractmethod
from typing import Union, Any

@dataclass
class ToolResult:
    """Standardized tool execution result."""
    success: bool
    data: Any
    error_message: Optional[str] = None
    execution_time_ms: int = 0

class BaseTool(ABC):
    """Abstract base class for all tools."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool identifier."""
        
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable tool description."""
        
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        
    @abstractmethod
    def validate_params(self, **kwargs) -> bool:
        """Validate parameters before execution."""

class FileSystemTool(BaseTool):
    """File system operations interface."""
    
    def read_file(self, path: str, encoding: str = "utf-8") -> ToolResult:
        """Read file contents."""
        
    def write_file(self, path: str, content: str, encoding: str = "utf-8") -> ToolResult:
        """Write content to file."""
        
    def list_directory(self, path: str, recursive: bool = False) -> ToolResult:
        """List directory contents."""
        
    def create_directory(self, path: str, parents: bool = True) -> ToolResult:
        """Create directory structure."""

class ShellTool(BaseTool):
    """Safe shell command execution interface."""
    
    def execute_command(self, command: str, timeout_s: int = 30) -> ToolResult:
        """Execute whitelisted shell command."""
        
    def get_allowed_commands(self) -> List[str]:
        """Return list of allowed commands."""
        
    def validate_command(self, command: str) -> bool:
        """Check if command is allowed."""
```

### RAG System API

```python
@dataclass
class Document:
    """Knowledge base document."""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    created_at: str = ""
    updated_at: str = ""

@dataclass
class SearchResult:
    """Search result with relevance score."""
    document: Document
    relevance_score: float
    matched_snippets: List[str]

class RAGSystemAPI:
    """Retrieval-Augmented Generation system interface."""
    
    def add_document(self, content: str, metadata: Dict[str, Any]) -> str:
        """Add document to knowledge base."""
        
    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """Search knowledge base for relevant documents."""
        
    def update_document(self, doc_id: str, content: str, metadata: Dict[str, Any]) -> bool:
        """Update existing document."""
        
    def delete_document(self, doc_id: str) -> bool:
        """Remove document from knowledge base."""
        
    def get_document(self, doc_id: str) -> Optional[Document]:
        """Retrieve document by ID."""
        
    def bulk_import(self, documents: List[Dict[str, Any]]) -> List[str]:
        """Import multiple documents at once."""
```

### Model Integration API

```python
@dataclass
class ModelConfig:
    """LLM configuration parameters."""
    name: str
    endpoint: str
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout_s: int = 30

@dataclass
class ChatMessage:
    """Standardized chat message format."""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None

class ModelAPI:
    """Language model integration interface."""
    
    def chat_completion(self, 
                       messages: List[ChatMessage],
                       tools: Optional[List[Dict[str, Any]]] = None,
                       stream: bool = False) -> Union[str, Iterator[str]]:
        """Generate chat completion response."""
        
    def embedding(self, text: str) -> List[float]:
        """Generate text embedding vector."""
        
    def health_check(self) -> bool:
        """Check if model endpoint is available."""
        
    def get_model_info(self) -> Dict[str, Any]:
        """Retrieve model metadata and capabilities."""
```

## Web Interface APIs

### WebSocket API

```python
from enum import Enum

class MessageType(Enum):
    TASK_SUBMIT = "task_submit"
    TASK_UPDATE = "task_update" 
    TASK_RESULT = "task_result"
    AGENT_STATUS = "agent_status"
    SYSTEM_HEALTH = "system_health"
    ERROR = "error"

@dataclass
class WebSocketMessage:
    """WebSocket message format."""
    type: MessageType
    data: Dict[str, Any]
    timestamp: str
    session_id: str

class WebSocketHandler:
    """WebSocket connection management."""
    
    async def on_connect(self, websocket) -> None:
        """Handle new WebSocket connection."""
        
    async def on_message(self, websocket, message: WebSocketMessage) -> None:
        """Process incoming WebSocket message."""
        
    async def on_disconnect(self, websocket) -> None:
        """Handle WebSocket disconnection."""
        
    async def broadcast_status(self, message: WebSocketMessage) -> None:
        """Broadcast status to all connected clients."""
```

### REST API Endpoints

```python
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

class TaskRequest(BaseModel):
    """Task submission request."""
    description: str
    agent_type: str
    priority: int = 0
    context: Dict[str, Any] = {}

class TaskResponse(BaseModel):
    """Task submission response."""
    task_id: str
    status: TaskStatus
    estimated_completion_time: Optional[int] = None

class HealthResponse(BaseModel):
    """System health status."""
    status: str  # "healthy", "degraded", "unhealthy"
    agents: Dict[str, str]  # agent_name -> status
    uptime_seconds: int
    total_tasks_processed: int

# REST API Routes
router = APIRouter()

@router.post("/tasks", response_model=TaskResponse)
async def submit_task(request: TaskRequest):
    """Submit new task for processing."""
    
@router.get("/tasks/{task_id}", response_model=TaskResult)
async def get_task_result(task_id: str):
    """Retrieve task result by ID."""
    
@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """Cancel pending task."""
    
@router.get("/health", response_model=HealthResponse)
async def get_health():
    """Get system health status."""
    
@router.get("/agents")
async def list_agents():
    """List available agents and their capabilities."""
```

## Configuration API

```python
@dataclass
class SystemConfig:
    """System-wide configuration."""
    # Model settings
    planner_model: ModelConfig
    coder_model: ModelConfig
    reviewer_model: ModelConfig
    
    # Agent settings
    max_concurrent_tasks: int = 10
    task_timeout_s: int = 300
    retry_attempts: int = 3
    
    # Security settings
    allowed_file_extensions: List[str]
    blocked_directories: List[str]
    max_file_size_mb: int = 10
    
    # RAG settings
    knowledge_base_path: str
    embedding_model: str
    max_context_length: int = 8192

class ConfigAPI:
    """Configuration management interface."""
    
    def load_config(self, config_path: str) -> SystemConfig:
        """Load configuration from file."""
        
    def save_config(self, config: SystemConfig, config_path: str) -> bool:
        """Save configuration to file."""
        
    def validate_config(self, config: SystemConfig) -> List[str]:
        """Validate configuration and return errors."""
        
    def get_default_config(self) -> SystemConfig:
        """Get default configuration values."""
```

## Error Handling

```python
class TurboCoderException(Exception):
    """Base exception for Turbo Coder system."""
    
    def __init__(self, message: str, error_code: str = "UNKNOWN"):
        self.message = message
        self.error_code = error_code
        super().__init__(message)

class AgentExecutionError(TurboCoderException):
    """Agent execution failure."""
    pass

class ToolExecutionError(TurboCoderException):
    """Tool execution failure."""
    pass

class ConfigurationError(TurboCoderException):
    """Configuration validation failure."""
    pass

class SecurityViolationError(TurboCoderException):
    """Security policy violation."""
    pass

# Error response format
@dataclass
class ErrorResponse:
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: str = ""
    trace_id: str = ""
```

## Version Compatibility

```python
class APIVersion:
    """API version management."""
    CURRENT = "1.0.0"
    SUPPORTED = ["1.0.0"]
    
    @classmethod
    def is_compatible(cls, version: str) -> bool:
        """Check if API version is supported."""
        return version in cls.SUPPORTED
    
    @classmethod
    def get_deprecation_info(cls, version: str) -> Optional[Dict[str, str]]:
        """Get deprecation information for version."""
        # Return deprecation timeline and migration guide
        pass
```