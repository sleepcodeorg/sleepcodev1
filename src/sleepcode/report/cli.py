# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime, timezone
from typing import Optional

import typer
from rich.console import Console

from sleepcode.report.markdown import generate_morning_report, get_reports_dir

report_app = typer.Typer(help="Manage SleepCode morning reports.")
console = Console()


@report_app.command("show")
def report_show(
    latest: bool = typer.Option(False, "--latest", help="Show latest report summary"),
    date_str: Optional[str] = typer.Option(None, "--date", help="Report date YYYY-MM-DD"),
) -> None:
    """Show morning report."""
    target_date = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report_path = get_reports_dir() / f"{target_date}.md"

    if not report_path.exists() or latest:
        report_path, summary_line = generate_morning_report(date_str=target_date)

    content = report_path.read_text(encoding="utf-8")
    console.print(f"[bold cyan]Report File:[/bold cyan] {report_path}\n")
    console.print(content)
