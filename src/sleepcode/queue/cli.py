# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from sleepcode.config import load_config
from sleepcode.queue.db import get_db_connection
from sleepcode.queue.repository import TaskRepository
from sleepcode.safety.commands import validate_command
from sleepcode.workspace import Workspace

queue_app = typer.Typer(help="Manage SleepCode task queue.")
console = Console()


def validate_repo_clean(repo_path: Path) -> None:
    """Ensure repository exists, is a git repo, and has a clean working tree."""
    if not repo_path.exists() or not repo_path.is_dir():
        msg = (
            f"[bold red]Error: Repository path '{repo_path}' "
            "does not exist or is not a directory.[/bold red]"
        )
        console.print(msg)
        raise typer.Exit(code=1)

    git_dir = repo_path / ".git"
    if not git_dir.exists():
        console.print(f"[bold red]Error: Path '{repo_path}' is not a git repository.[/bold red]")
        raise typer.Exit(code=1)

    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        if res.stdout.strip():
            msg = (
                "[bold red]Refused to add task:[/bold red] Repository working tree is not clean.\n"
                "Commit or stash your changes first, so the agent's work is easy to review."
            )
            console.print(msg)
            raise typer.Exit(code=1)
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Git error checking working tree: {e.stderr.strip()}[/bold red]")
        raise typer.Exit(code=1) from e


@queue_app.command("add")
def queue_add(
    task: str = typer.Argument(..., help="Task text description"),
    repo: Path = typer.Option(..., "--repo", "-r", help="Path to git repository"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model identifier override"),
    priority: int = typer.Option(0, "--priority", "-p", help="Task priority (higher runs first)"),
    budget_usd: float = typer.Option(1.00, "--budget-usd", "-b", help="Per-task budget in USD"),
    test_cmd: Optional[str] = typer.Option(None, "--test-cmd", "-t", help="Optional test command"),
) -> None:
    """Add a new task to the queue."""
    repo_path = repo.expanduser().resolve()
    validate_repo_clean(repo_path)

    config = load_config()
    chosen_model = model or config.default_model or "groq/llama-3.3-70b-versatile"

    if test_cmd:
        try:
            ws = Workspace(repo_path)
            validate_command(test_cmd, ws)
        except Exception as e:
            console.print(f"[bold red]Invalid test command: {str(e)}[/bold red]")
            raise typer.Exit(code=1) from e

    conn = get_db_connection()
    repo_obj = TaskRepository(conn)
    task_item = repo_obj.add_task(
        task_text=task,
        repo_path=str(repo_path),
        model=chosen_model,
        priority=priority,
        budget_usd=budget_usd,
        test_cmd=test_cmd,
    )

    msg = (
        f"[bold green]Task #{task_item.id} queued successfully.[/bold green] "
        f"(Priority: {task_item.priority}, Model: {task_item.model}, "
        f"Budget: ${task_item.budget_usd:.2f})"
    )
    console.print(msg)


@queue_app.command("list")
def queue_list(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
) -> None:
    """List queued and historical tasks."""
    conn = get_db_connection()
    repo_obj = TaskRepository(conn)
    tasks = repo_obj.list_tasks(status=status)

    if not tasks:
        console.print("[dim]No tasks found.[/dim]")
        return

    table = Table(title="SleepCode Task Queue")
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Priority", justify="right")
    table.add_column("Status", style="bold")
    table.add_column("Task Text")
    table.add_column("Repo Path")
    table.add_column("Model")
    table.add_column("Budget ($)")

    for t in tasks:
        status_color = "yellow"
        if t.status == "succeeded":
            status_color = "green"
        elif t.status in ("failed", "cancelled"):
            status_color = "red"
        elif t.status == "needs_review":
            status_color = "magenta"
        elif t.status == "running":
            status_color = "blue"

        table.add_row(
            str(t.id),
            str(t.priority),
            f"[{status_color}]{t.status}[/{status_color}]",
            t.task_text[:50] + ("..." if len(t.task_text) > 50 else ""),
            t.repo_path,
            t.model,
            f"{t.budget_usd:.2f}",
        )

    console.print(table)


@queue_app.command("show")
def queue_show(
    task_id: int = typer.Argument(..., help="Task ID"),
) -> None:
    """Show details and run history for a task."""
    conn = get_db_connection()
    repo_obj = TaskRepository(conn)
    task = repo_obj.get_task(task_id)

    if not task:
        console.print(f"[bold red]Task #{task_id} not found.[/bold red]")
        raise typer.Exit(code=1)

    console.print(f"[bold cyan]Task #{task.id}[/bold cyan]")
    console.print(f"  [bold]Text:[/bold] {task.task_text}")
    console.print(f"  [bold]Repo Path:[/bold] {task.repo_path}")
    console.print(f"  [bold]Status:[/bold] {task.status}")
    console.print(f"  [bold]Priority:[/bold] {task.priority}")
    console.print(f"  [bold]Model:[/bold] {task.model}")
    console.print(f"  [bold]Budget:[/bold] ${task.budget_usd:.2f}")
    console.print(f"  [bold]Test Cmd:[/bold] {task.test_cmd or 'None'}")
    console.print(f"  [bold]Branch:[/bold] {task.branch_name or 'None'}")
    console.print(f"  [bold]Created At:[/bold] {task.created_at}")
    console.print(f"  [bold]Started At:[/bold] {task.started_at or 'N/A'}")
    console.print(f"  [bold]Finished At:[/bold] {task.finished_at or 'N/A'}\n")

    runs = repo_obj.list_runs_for_task(task.id)
    if not runs:
        console.print("[dim]No runs recorded for this task yet.[/dim]")
        return

    console.print("[bold]Run History:[/bold]")
    for r in runs:
        cost_str = f"${r.cost_usd:.4f}" if r.cost_usd is not None else "Unknown"
        console.print(
            f"  Run #{r.id} | Status: {r.status} | Cost: {cost_str} | "
            f"Tokens: {r.tokens} | Tests Passed: {r.tests_passed}"
        )
        if r.notes:
            console.print(f"    Notes: {r.notes}")


@queue_app.command("cancel")
def queue_cancel(
    task_id: int = typer.Argument(..., help="Task ID to cancel"),
) -> None:
    """Cancel a queued task."""
    conn = get_db_connection()
    repo_obj = TaskRepository(conn)
    success, msg = repo_obj.cancel_task(task_id)
    if success:
        console.print(f"[bold green]{msg}[/bold green]")
    else:
        console.print(f"[bold red]{msg}[/bold red]")
        raise typer.Exit(code=1)


@queue_app.command("retry")
def queue_retry(
    task_id: int = typer.Argument(..., help="Task ID to retry"),
) -> None:
    """Retry a failed or needs_review task by creating a new run task."""
    conn = get_db_connection()
    repo_obj = TaskRepository(conn)
    new_task, msg = repo_obj.retry_task(task_id)
    if new_task:
        console.print(f"[bold green]{msg}[/bold green]")
    else:
        console.print(f"[bold red]{msg}[/bold red]")
        raise typer.Exit(code=1)
