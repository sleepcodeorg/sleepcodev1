# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import sqlite3
from pathlib import Path

from sleepcode.queue.db import CURRENT_SCHEMA_VERSION, get_db_connection, migrate_db
from sleepcode.queue.repository import TaskRepository


def test_migration_from_empty_db_to_version_1(tmp_path: Path) -> None:
    db_path = tmp_path / "empty.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Initially empty DB
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables_before = [r[0] for r in cur.fetchall()]
    assert "tasks" not in tables_before
    assert "schema_version" not in tables_before

    # Run migration
    migrate_db(conn)

    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables_after = [r[0] for r in cur.fetchall()]
    assert "tasks" in tables_after
    assert "runs" in tables_after
    assert "events" in tables_after
    assert "schema_version" in tables_after

    cur = conn.execute("SELECT version FROM schema_version LIMIT 1;")
    assert cur.fetchone()["version"] == CURRENT_SCHEMA_VERSION
    conn.close()


def test_parameterized_sql_injection_resilience(tmp_path: Path) -> None:
    db_path = tmp_path / "injection.db"
    conn = get_db_connection(db_path)
    repo = TaskRepository(conn)

    injection_text = "'; DROP TABLE tasks; SELECT * FROM tasks WHERE 'a'='a"
    task = repo.add_task(
        task_text=injection_text,
        repo_path="/tmp/repo",
        model="groq/llama-3.3-70b-versatile",
    )

    # Verify task text stored verbatim
    assert task.task_text == injection_text

    # Verify table survived
    cur = conn.execute("SELECT COUNT(*) FROM tasks;")
    count = cur.fetchone()[0]
    assert count == 1

    fetched = repo.get_task(task.id)
    assert fetched is not None
    assert fetched.task_text == injection_text
    conn.close()
