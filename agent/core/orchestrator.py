from __future__ import annotations

from typing import Optional

import typer
from rich import print

from .config import Settings, load_settings
from .planner import get_plan
from .executor import execute

app = typer.Typer(add_completion=False)


@app.command("run")
def run(
    task: str = typer.Argument(..., help="High level coding request."),
    apply: bool = typer.Option(False, "--apply", help="Execute changes."),
    planner_model: Optional[str] = typer.Option(
        None, "--planner-model", help="Override Turbo model."
    ),
    coder_model: Optional[str] = typer.Option(
        None, "--coder-model", help="Override local model."
    ),
    max_steps: int = typer.Option(25, "--max-steps", help="Max tool steps."),
) -> None:
    """Plan with Turbo, then execute locally with tool-calls."""
    s = load_settings()
    if planner_model:
        s = Settings(
            turbo_host=s.turbo_host,
            local_host=s.local_host,
            planner_model=planner_model,
            coder_model=s.coder_model,
            api_key=s.api_key,
            max_steps=s.max_steps,
            request_timeout_s=s.request_timeout_s,
            dry_run=s.dry_run,
        )
    if coder_model:
        s = Settings(
            turbo_host=s.turbo_host,
            local_host=s.local_host,
            planner_model=s.planner_model,
            coder_model=coder_model,
            api_key=s.api_key,
            max_steps=s.max_steps,
            request_timeout_s=s.request_timeout_s,
            dry_run=s.dry_run,
        )
    s = Settings(
        turbo_host=s.turbo_host,
        local_host=s.local_host,
        planner_model=s.planner_model,
        coder_model=s.coder_model,
        api_key=s.api_key,
        max_steps=max_steps,
        request_timeout_s=s.request_timeout_s,
        dry_run=not apply,
    )

    print(f"[bold]Planner:[/bold] {s.planner_model}")
    print(f"[bold]Executor:[/bold] {s.coder_model}")
    print(f"[bold]Apply:[/bold] {apply}")

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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
