#!/usr/bin/env python3
"""
Unified Turbo Local Coder Agent

A smart development assistant that adapts complexity based on your needs:
- Simple tasks: Fast single-agent execution
- Complex tasks: Multi-agent collaboration with quality gates
- Real-time streaming feedback
- Progressive enhancement flags
"""

from __future__ import annotations
import sys
from typing import Optional

import typer
from rich import print

from .core.config import Settings, load_settings
from .core.planner import get_plan
from .core.executor import execute
from .core.streaming import create_reporter

app = typer.Typer(add_completion=False, help="Turbo Local Coder Agent - Intelligent code development assistant")


@app.command()
def main(
    task: str = typer.Argument(..., help="Description of the development task"),
    
    # Execution control
    apply: bool = typer.Option(False, "--apply", help="Execute changes (default: dry run)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Plan only, don't execute"),
    max_steps: int = typer.Option(25, "--max-steps", help="Maximum execution steps"),
    
    # Model overrides
    planner_model: Optional[str] = typer.Option(None, "--planner-model", help="Override planner model"),
    coder_model: Optional[str] = typer.Option(None, "--coder-model", help="Override coder model"),
    
    # Progressive enhancement flags
    review: bool = typer.Option(False, "--review", help="Add code review phase"),
    test: bool = typer.Option(False, "--test", help="Add comprehensive testing"),
    docs: bool = typer.Option(False, "--docs", help="Generate documentation"),
    team: bool = typer.Option(False, "--team", help="Use full multi-agent workflow"),
    
    # Output control
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Show detailed progress"),
    quiet: bool = typer.Option(False, "-q", "--quiet", help="Minimal output"),
    
    # Enhancement control
    no_enhance: bool = typer.Option(False, "--no-enhance", help="Disable auto-enhancement system"),
    
) -> None:
    """
    Intelligent development assistant that adapts to task complexity.
    
    Examples:
        agent "fix typo in readme"                    # Simple single-agent
        agent "add authentication" --review --test    # Enhanced with quality gates  
        agent "refactor architecture" --team          # Full multi-agent workflow
    """
    
    # Load and configure settings
    settings = load_settings()
    
    if planner_model:
        settings = Settings(
            turbo_host=settings.turbo_host,
            local_host=settings.local_host,
            planner_model=planner_model,
            coder_model=settings.coder_model,
            api_key=settings.api_key,
            max_steps=settings.max_steps,
            request_timeout_s=settings.request_timeout_s,
            dry_run=settings.dry_run,
        )
        
    if coder_model:
        settings = Settings(
            turbo_host=settings.turbo_host,
            local_host=settings.local_host,
            planner_model=settings.planner_model,
            coder_model=coder_model,
            api_key=settings.api_key,
            max_steps=settings.max_steps,
            request_timeout_s=settings.request_timeout_s,
            dry_run=settings.dry_run,
        )
    
    # Apply execution settings
    settings = Settings(
        turbo_host=settings.turbo_host,
        local_host=settings.local_host,
        planner_model=settings.planner_model,
        coder_model=settings.coder_model,
        api_key=settings.api_key,
        max_steps=max_steps,
        request_timeout_s=settings.request_timeout_s,
        dry_run=dry_run or not apply,
    )
    
    # Create streaming reporter
    reporter = create_reporter(verbose=verbose, quiet=quiet)
    
    # Start session
    reporter.start_session(task)
    
    try:
        # Check if we should use multi-agent workflow
        if team or any([review, test, docs]):
            # Enhanced/multi-agent workflow
            result = execute_enhanced_workflow(
                task=task,
                settings=settings,
                reporter=reporter,
                enable_review=review,
                enable_testing=test,
                enable_docs=docs,
                full_team=team
            )
        else:
            # Standard single-agent workflow
            result = execute_standard_workflow(
                task=task,
                settings=settings,
                reporter=reporter,
                enhance=not no_enhance
            )
            
        # Report completion
        reporter.on_session_complete(
            success=True,
            summary=result.last if hasattr(result, 'last') else "Task completed successfully"
        )
        
    except Exception as e:
        reporter.on_error(str(e))
        reporter.on_session_complete(success=False)
        raise typer.Exit(1)


def execute_standard_workflow(task: str, settings: Settings, reporter, enhance: bool = True) -> any:
    """Execute standard single-agent workflow."""
    
    # Planning phase
    reporter.on_planning_start()
    plan = get_plan(task, settings, enhance=enhance)
    reporter.on_plan_created(plan.plan)
    
    if settings.dry_run:
        print("\n[yellow]Dry run mode. Re-run with [bold]--apply[/bold] to execute.[/yellow]")
        return plan
    
    # Execution phase
    reporter.on_execution_start()
    
    # Simulate step progression for the reporter
    for i, step in enumerate(plan.plan, 1):
        reporter.on_step_start(step, i, len(plan.plan))
        
    # Execute with streaming
    result = execute(plan.coder_prompt, settings, reporter)
    
    return result


def execute_enhanced_workflow(task: str, settings: Settings, reporter, 
                             enable_review: bool = False,
                             enable_testing: bool = False, 
                             enable_docs: bool = False,
                             full_team: bool = False) -> any:
    """Execute enhanced multi-agent workflow with quality gates."""
    
    # For now, delegate to the team system if it exists
    try:
        from .team.workflow import CodingWorkflow
        workflow = CodingWorkflow()
        
        reporter.on_planning_start()
        
        # Execute with team workflow
        result = workflow.execute_full_workflow(
            description=task,
            skip_review=not enable_review,
            skip_testing=not enable_testing,
            apply_changes=not settings.dry_run
        )
        
        return result
        
    except ImportError:
        # Fallback to standard workflow with warnings
        print("[yellow]⚠️  Team workflow not available, falling back to standard workflow[/yellow]")
        return execute_standard_workflow(task, settings, reporter)


def cli():
    """CLI entry point."""
    app()


if __name__ == "__main__":
    cli()