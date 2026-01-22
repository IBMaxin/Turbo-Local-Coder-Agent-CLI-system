"""Main execution runner."""
from typing import Dict, Any, List, Optional

from ...tools.fs import fs_read, fs_write, fs_list
from ...tools.shell import shell_run
from ...tools.python_exec import python_run

from .base import BaseExecutor
from .types import ExecutionResult, ExecSummary, ToolSchema
from .sandbox import SandboxEnvironment
from .tools import get_tool_schemas

class Executor(BaseExecutor):
    """Main executor implementation."""
    
    def __init__(self, sandbox: bool = True):
        self.sandbox = SandboxEnvironment() if sandbox else None

    def execute(self, tool_name: str, args: Dict[str, Any]) -> ExecutionResult:
        """Execute tool safely."""
        if self.sandbox:
            # In a real impl, sandbox would validate before execution
            # For now, we dispatch directly after 'check'
            pass

        try:
            if tool_name == "fs_read":
                r = fs_read(args["path"])
                return self._map_result(r)
            
            elif tool_name == "fs_write":
                r = fs_write(args["path"], args["content"])
                return self._map_result(r)
            
            elif tool_name == "fs_list":
                r = fs_list(args["path"])
                return self._map_result(r)
            
            elif tool_name == "shell_run":
                r = shell_run(args["cmd"])
                # Shell result has stdout/stderr/code
                output = f"STDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
                return ExecutionResult(
                    success=r.ok,
                    output=output,
                    error=None if r.ok else f"Exit code {r.code}"
                )
            
            elif tool_name == "python_run":
                r = python_run(args["mode"], args.get("code"))
                output = f"STDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
                return ExecutionResult(
                    success=r.ok,
                    output=output,
                    error=None if r.ok else f"Exit code {r.code}"
                )
                
            return ExecutionResult(success=False, output="", error=f"Unknown tool: {tool_name}")
            
        except Exception as e:
            return ExecutionResult(success=False, output="", error=str(e))

    def get_available_tools(self) -> List[ToolSchema]:
        return get_tool_schemas()

    def _map_result(self, r: Any) -> ExecutionResult:
        """Map legacy tool result to ExecutionResult."""
        # Assumes r has .ok and .detail attributes
        return ExecutionResult(
            success=r.ok,
            output=r.detail if r.ok else "",
            error=r.detail if not r.ok else None
        )
