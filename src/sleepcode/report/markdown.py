# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from sleepcode.config import get_config_dir
from sleepcode.queue.db import get_db_connection
from sleepcode.queue.repository import TaskRepository
from sleepcode.secrets import redact_secrets


def get_reports_dir() -> Path:
    """Return reports directory path, respecting SLEEPCODE_HOME."""
    config_dir = get_config_dir()
    reports_dir = config_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    return reports_dir


def truncate_excerpt(text: Optional[str], max_len: int = 500) -> str:
    """Truncate text excerpt to max_len chars and redact secrets."""
    if not text:
        return "None"
    redacted = redact_secrets(text)
    if len(redacted) > max_len:
        return redacted[:max_len] + "... (truncated)"
    return redacted


def generate_morning_report(
    date_str: Optional[str] = None,
    window_str: str = "23:00-07:00",
    night_budget_usd: float = 5.00,
) -> tuple[Path, str]:
    """Generate Markdown report for date and save to ~/.sleepcode/reports/YYYY-MM-DD.md."""
    if not date_str:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    conn = get_db_connection()
    repo = TaskRepository(conn)
    all_tasks = repo.list_tasks()

    total_spent = 0.0
    task_sections: List[str] = []
    skipped_sections: List[str] = []

    processed_count = 0

    for task in all_tasks:
        runs = repo.list_runs_for_task(task.id)
        if not runs:
            if task.status == "queued":
                skipped_sections.append(
                    f"- **Task #{task.id}**: {redact_secrets(task.task_text)}\n"
                    "  - Reason: Not started (queued)"
                )
            continue

        latest_run = runs[-1]
        cost = latest_run.cost_usd or 0.0
        total_spent += cost
        processed_count += 1

        status_label = "Done"
        next_action = f"Review branch `{task.branch_name}` and merge if it looks right."
        if task.status == "needs_review":
            status_label = "Needs review"
            next_action = f"Review test failures on branch `{task.branch_name}` and fix issues."
        elif task.status == "failed":
            status_label = "Failed"
            next_action = f"Check run log for task #{task.id} and resolve error."

        files_str = latest_run.files_changed
        try:
            files_list = json.loads(files_str)
            files_display = ", ".join(files_list) if files_list else "None"
        except Exception:
            files_display = files_str

        tests_str = "Not run"
        if latest_run.tests_passed is True:
            tests_str = "Passed"
        elif latest_run.tests_passed is False:
            tests_str = "Failed"

        notes_excerpt = truncate_excerpt(latest_run.notes, 500)

        web_tier_val = getattr(latest_run, "web_tier", None) or "off"
        web_str = f"Web access: {web_tier_val}"

        section = (
            f"### Task #{task.id}: {redact_secrets(task.task_text)}\n"
            f"- **Status:** {status_label}\n"
            f"- **Branch:** `{task.branch_name or 'None'}`\n"
            f"- **Files Changed:** {files_display}\n"
            f"- **Tests:** {tests_str}\n"
            f"- **{web_str}**\n"
            f"- **Cost:** ${cost:.4f}\n"
            f"- **Notes:** {notes_excerpt}\n"
            f"- **What to do next:** {next_action}\n"
        )
        task_sections.append(section)

    summary_header = (
        f"# SleepCode Morning Report ({date_str})\n\n"
        f"- **Window:** {window_str}\n"
        f"- **Total Spend:** ${total_spent:.4f} / ${night_budget_usd:.2f}\n"
        f"- **Tasks Processed:** {processed_count}\n\n"
    )

    content = summary_header + "## Processed Tasks\n\n"
    if task_sections:
        content += "\n".join(task_sections) + "\n"
    else:
        content += "No tasks were processed.\n\n"

    if skipped_sections:
        content += "## Skipped Tasks\n\n" + "\n".join(skipped_sections) + "\n"

    report_path = get_reports_dir() / f"{date_str}.md"
    report_path.write_text(content, encoding="utf-8")

    summary_line = (
        f"SleepCode Morning Report ({date_str}): {processed_count} task(s) processed, "
        f"spent ${total_spent:.2f}/${night_budget_usd:.2f}."
    )

    return report_path, summary_line
