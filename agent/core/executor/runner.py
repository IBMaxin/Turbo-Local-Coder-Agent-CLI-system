"""Main execution runner."""

from __future__ import annotations

from typing import Any, Dict, List

from ...tools.fs import fs_list, fs_read, fs_write
from ...tools.python_exec import python_run
from ...tools.shell import shell_run

from .base import BaseExecutor, ToolSchema
from .sandbox import SandboxEnvironment
from .tools import get_tool_schemas
from .types import ExecutionResult


class Executor(BaseExecutor):
    """Main executor implementation."""

    def __init__(self, sandbox: bool = True):
        self.sandbox = SandboxEnvironment() if sandbox else None

    def execute(self, tool_name: str, args: Dict[str, Any]) -> ExecutionResult:
        """Execute tool safely."""

        if self.sandbox:
            # Placeholder: sandbox should validate before execution.
            pass

        try:
            if tool_name == "fs_read":
                r = fs_read(args["path"])
                return self._map_result(r)

            if tool_name == "fs_write":
                r = fs_write(args["path"], args["content"])
                return self._map_result(r)

            if tool_name == "fs_list":
                r = fs_list(args["path"])
                return self._map_result(r)

            if tool_name == "shell_run":
                r = shell_run(args["cmd"])
                output = f"STDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
                return ExecutionResult(
                    success=r.ok,
                    output=output,
                    error=None if r.ok else f"Exit code {r.code}",
                )

            if tool_name == "python_run":
                r = python_run(args["mode"], args.get("code"))
                output = f"STDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
                return ExecutionResult(
                    success=r.ok,
                    output=output,
                    error=None if r.ok else f"Exit code {r.code}",
                )

            return ExecutionResult(success=False, output="", error=f"Unknown tool: {tool_name}")

        except Exception as e:
            return ExecutionResult(success=False, output="", error=str(e))

    def get_available_tools(self) -> List[ToolSchema]:
        return get_tool_schemas()

    def _map_result(self, r: Any) -> ExecutionResult:
        """Map legacy tool result to ExecutionResult."""

        return ExecutionResult(
            success=r.ok,
            output=r.detail if r.ok else "",
            error=r.detail if not r.ok else None,
        )
