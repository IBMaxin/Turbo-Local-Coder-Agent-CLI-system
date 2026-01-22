"""Base classes for executor system."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from .types import ExecutionResult, ToolSchema

class BaseExecutor(ABC):
    """Abstract base class for all executors."""
    
    @abstractmethod
    def execute(self, tool_name: str, args: Dict[str, Any]) -> ExecutionResult:
        """Execute a tool with given arguments."""
        pass

    @abstractmethod
    def get_available_tools(self) -> List[ToolSchema]:
        """Return list of available tools."""
        pass
