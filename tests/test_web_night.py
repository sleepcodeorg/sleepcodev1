# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import sqlite3

from sleepcode.queue.db import CURRENT_SCHEMA_VERSION, migrate_db


def test_schema_migration_v1_to_v2(tmp_path):
    db_file = tmp_path / "test_migration.db"
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row

    conn.executescript(
        """
        CREATE TABLE schema_version (version INTEGER PRIMARY KEY);
        INSERT INTO schema_version (version) VALUES (1);

        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_text TEXT NOT NULL,
            repo_path TEXT NOT NULL,
            model TEXT NOT NULL,
            priority INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'queued',
            branch_name TEXT,
            budget_usd REAL NOT NULL DEFAULT 1.00,
            test_cmd TEXT,
            created_at TEXT NOT NULL,
            started_at TEXT,
            finished_at TEXT
        );

        CREATE TABLE runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            status TEXT NOT NULL,
            cost_usd REAL,
            tokens INTEGER NOT NULL DEFAULT 0,
            files_changed TEXT NOT NULL DEFAULT '[]',
            tests_passed INTEGER,
            notes TEXT,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        );

        INSERT INTO tasks (task_text, repo_path, model, created_at)
        VALUES ('Task 1', '/tmp/repo', 'openai/gpt-4o-mini', '2026-01-01T00:00:00Z');

        INSERT INTO runs (task_id, started_at, status)
        VALUES (1, '2026-01-01T00:00:00Z', 'succeeded');
        """
    )
    conn.commit()

    cur = conn.execute("SELECT version FROM schema_version LIMIT 1;")
    assert cur.fetchone()["version"] == 1

    migrate_db(conn)

    cur = conn.execute("SELECT version FROM schema_version LIMIT 1;")
    assert cur.fetchone()["version"] == 2
    assert CURRENT_SCHEMA_VERSION == 2

    cur = conn.execute("SELECT id, status, web_tier FROM runs WHERE id = 1;")
    row = cur.fetchone()
    assert row["status"] == "succeeded"
    assert row["web_tier"] is None
