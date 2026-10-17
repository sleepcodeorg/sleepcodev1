# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import json
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

from sleepcode.queue.models import Event, Run, Task


class TaskRepository:
    """Repository for managing Task, Run, and Event persistence with parameterized SQL."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def add_task(
        self,
        task_text: str,
        repo_path: str,
        model: str,
        priority: int = 0,
        budget_usd: float = 1.00,
        test_cmd: Optional[str] = None,
    ) -> Task:
        now_str = datetime.now(timezone.utc).isoformat()
        with self.conn:
            cur = self.conn.execute(
                """
                INSERT INTO tasks (
                    task_text, repo_path, model, priority, status, budget_usd, test_cmd, created_at
                ) VALUES (?, ?, ?, ?, 'queued', ?, ?, ?)
                """,
                (task_text, repo_path, model, priority, budget_usd, test_cmd, now_str),
            )
            task_id = cur.lastrowid
            assert task_id is not None

        return self.get_task(task_id)  # type: ignore[return-value]

    def get_task(self, task_id: int) -> Optional[Task]:
        cur = self.conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cur.fetchone()
        if not row:
            return None
        return Task(
            id=row["id"],
            task_text=row["task_text"],
            repo_path=row["repo_path"],
            model=row["model"],
            priority=row["priority"],
            status=row["status"],
            branch_name=row["branch_name"],
            budget_usd=row["budget_usd"],
            test_cmd=row["test_cmd"],
            created_at=row["created_at"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
        )

    def list_tasks(self, status: Optional[str] = None) -> List[Task]:
        if status:
            cur = self.conn.execute(
                "SELECT * FROM tasks WHERE status = ? ORDER BY priority DESC, created_at ASC",
                (status,),
            )
        else:
            cur = self.conn.execute("SELECT * FROM tasks ORDER BY priority DESC, created_at ASC")

        tasks = []
        for row in cur.fetchall():
            tasks.append(
                Task(
                    id=row["id"],
                    task_text=row["task_text"],
                    repo_path=row["repo_path"],
                    model=row["model"],
                    priority=row["priority"],
                    status=row["status"],
                    branch_name=row["branch_name"],
                    budget_usd=row["budget_usd"],
                    test_cmd=row["test_cmd"],
                    created_at=row["created_at"],
                    started_at=row["started_at"],
                    finished_at=row["finished_at"],
                )
            )
        return tasks

    def cancel_task(self, task_id: int) -> tuple[bool, str]:
        task = self.get_task(task_id)
        if not task:
            return False, f"Task #{task_id} does not exist."
        if task.status == "running":
            msg = f"Task #{task_id} is currently running and cannot be cancelled from the queue."
            return False, msg
        if task.status != "queued":
            return False, f"Task #{task_id} is in '{task.status}' state and cannot be cancelled."

        with self.conn:
            self.conn.execute("UPDATE tasks SET status = 'cancelled' WHERE id = ?", (task_id,))
        return True, f"Task #{task_id} cancelled."

    def retry_task(self, task_id: int) -> tuple[Optional[Task], str]:
        task = self.get_task(task_id)
        if not task:
            return None, f"Task #{task_id} does not exist."
        if task.status not in ("failed", "needs_review"):
            msg = (
                f"Task #{task_id} is in '{task.status}' status. "
                "Only 'failed' or 'needs_review' tasks can be retried."
            )
            return None, msg

        new_task = self.add_task(
            task_text=task.task_text,
            repo_path=task.repo_path,
            model=task.model,
            priority=task.priority,
            budget_usd=task.budget_usd,
            test_cmd=task.test_cmd,
        )
        return new_task, f"Created new task #{new_task.id} to retry task #{task_id}."

    def take_next_queued_task(self) -> Optional[Task]:
        """Atomically find and lock the highest priority queued task."""
        with self.conn:
            cur = self.conn.execute(
                """
                SELECT id FROM tasks
                WHERE status = 'queued'
                ORDER BY priority DESC, created_at ASC
                LIMIT 1
                """
            )
            row = cur.fetchone()
            if not row:
                return None
            task_id = row["id"]
            now_str = datetime.now(timezone.utc).isoformat()
            cur_update = self.conn.execute(
                """
                UPDATE tasks
                SET status = 'running', started_at = ?
                WHERE id = ? AND status = 'queued'
                """,
                (now_str, task_id),
            )
            if cur_update.rowcount == 0:
                return None

        return self.get_task(task_id)

    def update_task_status(
        self,
        task_id: int,
        status: str,
        branch_name: Optional[str] = None,
        finished_at: Optional[str] = None,
    ) -> None:
        if not finished_at and status in ("succeeded", "failed", "needs_review", "cancelled"):
            finished_at = datetime.now(timezone.utc).isoformat()

        with self.conn:
            self.conn.execute(
                """
                UPDATE tasks
                SET status = ?,
                    branch_name = COALESCE(?, branch_name),
                    finished_at = COALESCE(?, finished_at)
                WHERE id = ?
                """,
                (status, branch_name, finished_at, task_id),
            )

    def add_run(
        self,
        task_id: int,
        status: str = "running",
        cost_usd: Optional[float] = None,
        tokens: int = 0,
        files_changed: List[str] | str = "[]",
        tests_passed: Optional[bool] = None,
        notes: Optional[str] = None,
    ) -> Run:
        now_str = datetime.now(timezone.utc).isoformat()
        files_json = json.dumps(files_changed) if isinstance(files_changed, list) else files_changed
        tests_val = 1 if tests_passed is True else (0 if tests_passed is False else None)

        with self.conn:
            cur = self.conn.execute(
                """
                INSERT INTO runs (
                    task_id, started_at, status, cost_usd, tokens,
                    files_changed, tests_passed, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (task_id, now_str, status, cost_usd, tokens, files_json, tests_val, notes),
            )
            run_id = cur.lastrowid
            assert run_id is not None

        return Run(
            id=run_id,
            task_id=task_id,
            started_at=now_str,
            status=status,
            cost_usd=cost_usd,
            tokens=tokens,
            files_changed=files_json,
            tests_passed=tests_passed,
            notes=notes,
        )

    def update_run(
        self,
        run_id: int,
        status: str,
        cost_usd: Optional[float] = None,
        tokens: int = 0,
        files_changed: Optional[List[str]] = None,
        tests_passed: Optional[bool] = None,
        notes: Optional[str] = None,
        finished_at: Optional[str] = None,
    ) -> None:
        if not finished_at:
            finished_at = datetime.now(timezone.utc).isoformat()
        files_json = json.dumps(files_changed) if files_changed is not None else None
        tests_val = 1 if tests_passed is True else (0 if tests_passed is False else None)

        with self.conn:
            self.conn.execute(
                """
                UPDATE runs
                SET status = ?,
                    cost_usd = COALESCE(?, cost_usd),
                    tokens = COALESCE(?, tokens),
                    files_changed = COALESCE(?, files_changed),
                    tests_passed = COALESCE(?, tests_passed),
                    notes = COALESCE(?, notes),
                    finished_at = ?
                WHERE id = ?
                """,
                (status, cost_usd, tokens, files_json, tests_val, notes, finished_at, run_id),
            )

    def list_runs_for_task(self, task_id: int) -> List[Run]:
        cur = self.conn.execute(
            "SELECT * FROM runs WHERE task_id = ? ORDER BY started_at ASC", (task_id,)
        )
        runs = []
        for row in cur.fetchall():
            tp = True if row["tests_passed"] == 1 else (False if row["tests_passed"] == 0 else None)
            runs.append(
                Run(
                    id=row["id"],
                    task_id=row["task_id"],
                    started_at=row["started_at"],
                    finished_at=row["finished_at"],
                    status=row["status"],
                    cost_usd=row["cost_usd"],
                    tokens=row["tokens"],
                    files_changed=row["files_changed"],
                    tests_passed=tp,
                    notes=row["notes"],
                )
            )
        return runs

    def add_event(
        self,
        run_id: int,
        step: int,
        role: str,
        tool_name: Optional[str] = None,
        arguments_json: Optional[str] = None,
        result_summary: Optional[str] = None,
        tokens: int = 0,
        cost_usd: Optional[float] = None,
    ) -> Event:
        now_str = datetime.now(timezone.utc).isoformat()
        with self.conn:
            cur = self.conn.execute(
                """
                INSERT INTO events (
                    run_id, timestamp, step, role, tool_name,
                    arguments_json, result_summary, tokens, cost_usd
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    now_str,
                    step,
                    role,
                    tool_name,
                    arguments_json,
                    result_summary,
                    tokens,
                    cost_usd,
                ),
            )
            event_id = cur.lastrowid
            assert event_id is not None

        return Event(
            id=event_id,
            run_id=run_id,
            timestamp=now_str,
            step=step,
            role=role,
            tool_name=tool_name,
            arguments_json=arguments_json,
            result_summary=result_summary,
            tokens=tokens,
            cost_usd=cost_usd,
        )
