from __future__ import annotations

from typing import Optional

import typer
from rich import print

from .config import Settings, load_settings, ConfigurationError
from .auto_config import create_smart_settings, detect_task_complexity


def _detect_task_type(task: str) -> str:
    """Detect the type of task for display purposes."""
    task_lower = task.lower()
    if any(word in task_lower for word in ["create", "build", "generate", "make"]):
        return "creation"
    elif any(word in task_lower for word in ["fix", "debug", "solve", "resolve"]):
        return "debugging"
    elif any(word in task_lower for word in ["refactor", "restructure", "optimize"]):
        return "refactoring"
    elif any(word in task_lower for word in ["test", "verify", "validate"]):
        return "testing"
    elif any(word in task_lower for word in ["update", "modify", "change", "edit"]):
        return "modification"
    elif any(word in task_lower for word in ["analyze", "review", "examine"]):
        return "analysis"
    else:
        return "general"
from .planner import get_plan
from .executor import execute

app = typer.Typer(add_completion=False)


@app.command("run")
def run(
    task: str = typer.Argument(..., help="High level coding request."),
    apply: bool = typer.Option(False, "--apply", help="Execute changes."),
    enhanced: bool = typer.Option(False, "--enhanced", help="Use Super-RAG intelligence."),
    extract_knowledge: bool = typer.Option(False, "--extract", help="Extract knowledge from codebase first."),
    planner_model: Optional[str] = typer.Option(
        None, "--planner-model", help="Override Turbo model."
    ),
    coder_model: Optional[str] = typer.Option(
        None, "--coder-model", help="Override local model."
    ),
    max_steps: int = typer.Option(25, "--max-steps", help="Max tool steps."),
) -> None:
    """Plan with Turbo, then execute locally with tool-calls."""
    try:
        # Use smart configuration that auto-detects optimal settings
        user_overrides = {
            "planner_model": planner_model,
            "coder_model": coder_model,
            "max_steps": max_steps,
            "dry_run": not apply
        }
        s = create_smart_settings(task, user_overrides)
        
        # Detect and show task complexity
        complexity = detect_task_complexity(task)
        print(f"[bold]🧠 Task enhanced (complexity: {complexity.value}, type: {_detect_task_type(task)})[/bold]")
        
    except ConfigurationError as e:
        print(f"[red]Configuration Error:[/red] {e}")
        print("[yellow]Please check your .env file and environment variables[/yellow]")
        raise typer.Exit(1)

    print(f"[bold]Planner:[/bold] {s.planner_model}")
    print(f"[bold]Executor:[/bold] {s.coder_model}")
    print(f"[bold]Apply:[/bold] {apply}")
    print(f"[bold]Enhanced:[/bold] {enhanced}")
    
    # Knowledge extraction phase
    if extract_knowledge:
        print("\n[bold]🔍 Extracting Knowledge from Codebase...[/bold]")
        from ..knowledge.enhanced_executor import EnhancedExecutor
        enhanced_executor = EnhancedExecutor(s)
        extraction_result = enhanced_executor.batch_knowledge_extraction(".")
        print(f"✅ Extracted {extraction_result['patterns_extracted']} patterns")
        print(f"💾 Stored {extraction_result['patterns_stored']} patterns in knowledge base")

    # Enhanced execution path
    if enhanced:
        print("\n[bold]🧠 Using Super-RAG Intelligence...[/bold]")
        
        if not apply:
            print("Enhanced mode requires --apply. Re-run with [bold]--apply --enhanced[/bold]")
            return
            
        from ..knowledge.enhanced_executor import EnhancedExecutor
        enhanced_executor = EnhancedExecutor(s)
        
        result = enhanced_executor.execute_with_intelligence(task, ".")
        
        # Display comprehensive results
        print(f"\n[bold]🎯 Analysis Results:[/bold]")
        analysis = result["analysis"]
        print(f"Task Type: {analysis['characteristics'].get('task_type', 'unknown')}")
        print(f"Predicted Success: {analysis.get('success_probability', 0):.1%}")
        print(f"Complexity: {analysis['complexity'].get('level', 'unknown')}")
        
        print(f"\n[bold]📚 Context Enhancement:[/bold]")
        print(f"Similar Executions: {len(analysis.get('similar_executions', []))}")
        print(f"Relevant Patterns: {len(analysis.get('relevant_patterns', []))}")
        
        summary = result["summary"]
        quality = result["quality_metrics"]
        print(f"\n[bold]✅ Execution Complete:[/bold]")
        print(f"Steps: {summary.steps}")
        print(f"Quality Score: {quality.overall_quality:.2f}")
        print(f"Success: {'Yes' if result['execution_result'].success else 'No'}")
        
        print(f"\n[bold]Last message:[/bold]\n{summary.last}")
        
        # Display insights
        insights = result["intelligence_insights"]
        if insights.get("recommendations"):
            print(f"\n[bold]💡 AI Recommendations:[/bold]")
            for rec in insights["recommendations"]:
                print(f"• {rec}")
    
    else:
        # Original execution path
        plan = get_plan(task, s)
        print("\n[bold]Plan[/bold]")
        for i, step in enumerate(plan.plan, start=1):
            print(f"{i}. {step}")

        if not apply:
            print("\nDry run. Re-run with [bold]--apply[/bold] to execute.")
            return

        print("\n[bold]Executing…[/bold]")
        summary = execute(plan.coder_prompt, s)
        print(
            f"\n[bold]Done[/bold] in {summary.steps} step(s).\n"
            f"[bold]Last message:[/bold]\n{summary.last}"
        )


@app.command("knowledge")
def knowledge_cmd(
    action: str = typer.Argument(..., help="Action: extract, analyze, stats"),
    path: str = typer.Option(".", "--path", help="Codebase path for analysis")
) -> None:
    """Manage the Super-RAG knowledge system."""
    
    from ..knowledge.enhanced_executor import EnhancedExecutor
    
    s = load_settings()
    enhanced_executor = EnhancedExecutor(s)
    
    if action == "extract":
        print(f"[bold]🔍 Extracting knowledge from {path}...[/bold]")
        result = enhanced_executor.batch_knowledge_extraction(path)
        
        print(f"\n[bold]📊 Extraction Results:[/bold]")
        print(f"Patterns Extracted: {result['patterns_extracted']}")
        print(f"Patterns Stored: {result['patterns_stored']}")
        print(f"Architecture Insights: {len(result.get('architecture_insights', {}))}")
        print(f"Knowledge Chunks: {result['knowledge_chunks_created']}")
        
    elif action == "analyze":
        print(f"[bold]📈 Analyzing execution performance...[/bold]")
        performance = enhanced_executor.analyze_execution_performance()
        
        if "message" in performance:
            print(performance["message"])
        else:
            print(f"\n[bold]Performance Summary:[/bold]")
            print(f"Total Executions: {performance['total_executions']}")
            print(f"Success Rate: {performance['success_rate']:.1%}")
            print(f"Avg Execution Time: {performance['average_execution_time']:.1f}s")
            print(f"Avg Quality Score: {performance['average_quality_score']:.2f}")
            
            if performance.get('improvement_opportunities'):
                print(f"\n[bold]💡 Improvement Opportunities:[/bold]")
                for opp in performance['improvement_opportunities'][:3]:
                    print(f"• {opp.get('area', 'Unknown')}: {opp.get('improvement_potential', 'N/A')}")
    
    elif action == "stats":
        print("[bold]📊 Knowledge System Statistics[/bold]")
        print("Feature implemented - detailed stats coming soon!")
        
    else:
        print(f"[red]Unknown action: {action}[/red]")
        print("Available actions: extract, analyze, stats")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
