# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import sqlite3
from pathlib import Path

from sleepcode.config import get_config_dir

CURRENT_SCHEMA_VERSION = 2


def get_db_path() -> Path:
    """Return path to SQLite database, respecting SLEEPCODE_HOME."""
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "sleepcode.db"


def get_db_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Get SQLite connection and ensure schema is up to date."""
    target_path = db_path or get_db_path()
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    migrate_db(conn)
    return conn


def migrate_db(conn: sqlite3.Connection) -> None:
    """Run migrations to bring SQLite DB schema to CURRENT_SCHEMA_VERSION."""
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY
            );
            """
        )
        cur = conn.execute("SELECT version FROM schema_version LIMIT 1;")
        row = cur.fetchone()
        current_ver = row["version"] if row else 0

        if current_ver < 1:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS tasks (
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

                CREATE TABLE IF NOT EXISTS runs (
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

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    step INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    tool_name TEXT,
                    arguments_json TEXT,
                    result_summary TEXT,
                    tokens INTEGER NOT NULL DEFAULT 0,
                    cost_usd REAL,
                    FOREIGN KEY (run_id) REFERENCES runs(id)
                );

                DELETE FROM schema_version;
                INSERT INTO schema_version (version) VALUES (1);
                """
            )
            current_ver = 1

        if current_ver < 2:
            conn.executescript(
                """
                ALTER TABLE runs ADD COLUMN web_tier TEXT;

                DELETE FROM schema_version;
                INSERT INTO schema_version (version) VALUES (2);
                """
            )
