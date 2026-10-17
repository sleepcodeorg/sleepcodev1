# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from sleepcode.cli import app
from sleepcode.queue.db import CURRENT_SCHEMA_VERSION, get_db_connection
from sleepcode.queue.repository import TaskRepository

runner = CliRunner()


def create_temp_git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "init"], cwd=path, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    (path / "README.md").write_text("# Test Repo\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=path, check=True)
    return path


def test_migration_and_parameterized_queries(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    conn = get_db_connection(db_path)

    cur = conn.execute("SELECT version FROM schema_version LIMIT 1;")
    assert cur.fetchone()["version"] == CURRENT_SCHEMA_VERSION

    repo = TaskRepository(conn)

    injection_text = "'; DROP TABLE tasks; --"
    task = repo.add_task(
        task_text=injection_text,
        repo_path="/fake/repo",
        model="groq/llama-3.3-70b-versatile",
    )

    assert task.task_text == injection_text

    fetched = repo.get_task(task.id)
    assert fetched is not None
    assert fetched.task_text == injection_text


def test_queue_add_dirty_and_non_git_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SLEEPCODE_HOME", str(tmp_path))

    non_git = tmp_path / "non_git_dir"
    non_git.mkdir()
    res1 = runner.invoke(app, ["queue", "add", "my task", "--repo", str(non_git)])
    assert res1.exit_code != 0
    assert "not a git repository" in res1.output

    git_repo = create_temp_git_repo(tmp_path / "git_repo")
    (git_repo / "dirty.txt").write_text("uncommitted changes", encoding="utf-8")

    res2 = runner.invoke(app, ["queue", "add", "my task", "--repo", str(git_repo)])
    assert res2.exit_code != 0
    assert "working tree is not clean" in res2.output
    assert "Commit or stash your changes first" in res2.output


def test_queue_add_cancel_show_retry_flow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLEEPCODE_HOME", str(tmp_path))
    git_repo = create_temp_git_repo(tmp_path / "clean_repo")

    add_res = runner.invoke(app, ["queue", "add", "Fix bug in app", "--repo", str(git_repo)])
    assert add_res.exit_code == 0
    assert "Task #1 queued successfully" in add_res.output

    list_res = runner.invoke(app, ["queue", "list"])
    assert list_res.exit_code == 0
    assert "Fix bug in app" in list_res.output or "Fix bug" in list_res.output

    show_res = runner.invoke(app, ["queue", "show", "1"])
    assert show_res.exit_code == 0
    assert "Task #1" in show_res.output

    cancel_res = runner.invoke(app, ["queue", "cancel", "1"])
    assert cancel_res.exit_code == 0
    assert "Task #1 cancelled." in cancel_res.output

    cancel_res2 = runner.invoke(app, ["queue", "cancel", "1"])
    assert cancel_res2.exit_code != 0
    assert "cannot be cancelled" in cancel_res2.output

    conn = get_db_connection()
    repo = TaskRepository(conn)
    repo.update_task_status(1, "failed")

    retry_res = runner.invoke(app, ["queue", "retry", "1"])
    assert retry_res.exit_code == 0
    assert "Created new task #2 to retry task #1" in retry_res.output
