"""
Real-time streaming feedback for development tasks.
"""

from __future__ import annotations
import sys
import time
from typing import Optional, Dict, Any
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import box

class StreamingReporter:
    """Provides real-time feedback during agent execution."""
    
    def __init__(self, verbose: bool = False):
        self.console = Console()
        self.verbose = verbose
        self.start_time = time.time()
        self.current_step = 0
        self.total_steps = 0
        self.live_display = None
        self.progress = None
        self.main_task = None
        
    def start_session(self, task_description: str):
        """Start a new development session."""
        self.console.print(f"\n[AGENT] [bold blue]Starting Development Task[/bold blue]")
        self.console.print(f"[TASK] {task_description}\n")
        self.start_time = time.time()
        
    def on_planning_start(self):
        """Called when planning phase begins."""
        with self.console.status("[bold green][PLAN] Planning task..."):
            time.sleep(0.1)  # Brief pause for visual effect
            
    def on_plan_created(self, plan: list[str]):
        """Called when plan is ready."""
        self.total_steps = len(plan)
        self.console.print("[PLAN] [bold green]Plan created:[/bold green]")
        
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_column("Step", style="dim")
        table.add_column("Description")
        
        for i, step in enumerate(plan, 1):
            table.add_row(f"{i}.", step)
            
        self.console.print(table)
        self.console.print()
        
    def on_execution_start(self):
        """Called when execution phase begins."""
        self.console.print("[EXEC] [bold green]Starting execution...[/bold green]\n")
        
        # Initialize progress tracking
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        )
        
        self.main_task = self.progress.add_task("Executing...", total=100)
        self.live_display = Live(self.progress, console=self.console, refresh_per_second=10)
        self.live_display.start()
        
    def on_step_start(self, step: str, n: int, total: int):
        """Called when a new step begins."""
        self.current_step = n
        self.total_steps = total
        
        if self.progress and self.main_task is not None:
            progress_percent = (n - 1) / total * 100
            self.progress.update(self.main_task, completed=progress_percent, 
                               description=f"[{n}/{total}] {step}")
            
    def on_tool_call(self, tool: str, args: Dict[str, Any]):
        """Called when a tool is being executed."""
        if self.verbose:
            args_str = ", ".join(f"{k}={v}" for k, v in args.items())
            self.console.print(f"  [TOOL] {tool}({args_str})")
            
    def on_tool_result(self, tool: str, success: bool, result: str = ""):
        """Called when a tool execution completes."""
        icon = "[OK]" if success else "[ERR]"
        if self.verbose or not success:
            self.console.print(f"  {icon} {tool}: {'Success' if success else 'Failed'}")
            if not success and result:
                self.console.print(f"     [red]{result[:200]}...[/red]" if len(result) > 200 else f"     [red]{result}[/red]")
                
    def on_llm_chunk(self, chunk: str):
        """Called when LLM streams a text chunk."""
        if self.verbose:
            print(chunk, end="", flush=True)
            
    def on_thinking(self, thought: str):
        """Called when agent is 'thinking' (processing)."""
        if self.verbose:
            self.console.print(f"[THINK] [italic dim]{thought}[/italic dim]")
            
    def on_file_operation(self, operation: str, filepath: str):
        """Called during file operations."""
        icons = {
            "read": "[READ]",
            "write": "[WRITE]",
            "create": "[CREATE]",
            "delete": "[DELETE]"
        }
        icon = icons.get(operation, "[FILE]")
        self.console.print(f"  {icon} {operation.title()}: [cyan]{filepath}[/cyan]")
        
    def on_test_run(self, test_file: str, result: bool, output: str = ""):
        """Called when tests are run."""
        icon = "[TEST][OK]" if result else "[TEST][FAIL]"
        self.console.print(f"  {icon} Tests: [cyan]{test_file}[/cyan]")
        if not result and output:
            self.console.print(f"     [red]{output[:300]}...[/red]" if len(output) > 300 else f"     [red]{output}[/red]")
            
    def on_step_complete(self, step: str, success: bool):
        """Called when a step completes."""
        if self.progress and self.main_task is not None:
            progress_percent = self.current_step / self.total_steps * 100
            self.progress.update(self.main_task, completed=progress_percent)
            
    def on_session_complete(self, success: bool, summary: str = ""):
        """Called when the entire session completes."""
        if self.live_display:
            self.live_display.stop()
            
        elapsed = time.time() - self.start_time
        minutes, seconds = divmod(elapsed, 60)
        time_str = f"{int(minutes)}m {int(seconds)}s" if minutes > 0 else f"{int(seconds)}s"
        
        if success:
            self.console.print(f"\n[DONE] [bold green]Task completed successfully![/bold green] ({time_str})")
        else:
            self.console.print(f"\n[FAIL] [bold red]Task failed.[/bold red] ({time_str})")
            
        if summary:
            panel = Panel(summary, title="Summary", border_style="green" if success else "red")
            self.console.print(panel)
            
    def on_error(self, error: str, details: str = ""):
        """Called when an error occurs."""
        self.console.print(f"\n[ERR] [bold red]Error:[/bold red] {error}")
        if details and self.verbose:
            self.console.print(f"[dim]{details}[/dim]")


class QuietReporter:
    """Minimal output reporter for quiet mode."""
    
    def __init__(self):
        self.console = Console()
        
    def start_session(self, task_description: str):
        self.console.print(f"[AGENT] {task_description}")
        
    def on_planning_start(self): pass
    def on_plan_created(self, plan: list[str]): pass
    def on_execution_start(self): pass
    def on_step_start(self, step: str, n: int, total: int): pass
    def on_tool_call(self, tool: str, args: Dict[str, Any]): pass
    def on_tool_result(self, tool: str, success: bool, result: str = ""): pass
    def on_llm_chunk(self, chunk: str): pass
    def on_thinking(self, thought: str): pass
    def on_file_operation(self, operation: str, filepath: str): pass
    def on_test_run(self, test_file: str, result: bool, output: str = ""): pass
    def on_step_complete(self, step: str, success: bool): pass
    
    def on_session_complete(self, success: bool, summary: str = ""):
        icon = "[OK]" if success else "[ERR]"
        self.console.print(f"{icon} {'Done' if success else 'Failed'}")
        
    def on_error(self, error: str, details: str = ""):
        self.console.print(f"[ERR] {error}")


def create_reporter(verbose: bool = False, quiet: bool = False) -> StreamingReporter | QuietReporter:
    """Factory function to create appropriate reporter."""
    if quiet:
        return QuietReporter()
    return StreamingReporter(verbose=verbose)