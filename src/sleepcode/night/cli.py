# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from typing import Optional

import typer
from rich.console import Console

from sleepcode.night.runner import NightRunner

night_app = typer.Typer(help="Manage SleepCode night execution loop.")
console = Console()


@night_app.command("start")
def night_start(
    window: str = typer.Option("23:00-07:00", "--window", "-w", help="Time window HH:MM-HH:MM"),
    budget_usd: float = typer.Option(5.00, "--budget-usd", "-b", help="Total night budget in USD"),
    allow_shell: bool = typer.Option(False, "--allow-shell", help="Allow shell and git tools"),
    web: Optional[str] = typer.Option(
        None, "--web", help="Web access tier for night run (defaults to 'off')"
    ),
    once: bool = typer.Option(False, "--once", help="Run once immediately without checking window"),
    max_tasks: int = typer.Option(10, "--max-tasks", help="Maximum tasks to run per night"),
) -> None:
    """Start night task execution runner."""
    runner = NightRunner(
        window_str=window,
        night_budget_usd=budget_usd,
        allow_shell=allow_shell,
        web_tier_str=web,
        once=once,
        max_tasks=max_tasks,
    )

    if not once and not runner.window_mgr.is_active():
        open_time = window.split("-")[0]
        msg = f"Current time is outside window '{window}'. Window will open at {open_time}."
        console.print(msg)
        raise typer.Exit(code=0)

    console.print(f"[bold cyan]Starting Night Runner...[/bold cyan] (Budget: ${budget_usd:.2f})")
    processed = runner.run_night_queue()
    count_str = f"Processed {len(processed)} task(s)."
    console.print(f"[bold green]Night run completed.[/bold green] {count_str}")
