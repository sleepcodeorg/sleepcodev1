# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from sleepcode.night.runner import NightRunner, set_test_night_provider_override
from sleepcode.providers.base import ProviderResponse, ToolCall
from sleepcode.providers.fake_provider import FakeProvider
from sleepcode.queue.db import get_db_connection
from sleepcode.queue.repository import TaskRepository


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


def test_night_runner_executes_task_and_restores_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SLEEPCODE_HOME", str(tmp_path))
    repo = create_temp_git_repo(tmp_path / "app_repo")

    conn = get_db_connection()
    repo_db = TaskRepository(conn)
    task = repo_db.add_task(
        task_text="Add helper module",
        repo_path=str(repo),
        model="groq/llama-3.3-70b-versatile",
    )

    resp1 = ProviderResponse(
        text="Writing helper file",
        tool_calls=[
            ToolCall(
                id="tc1",
                name="write_file",
                arguments={"path": "helper.py", "content": "def help_me(): pass"},
            )
        ],
    )
    resp2 = ProviderResponse(text="Done adding helper module", tool_calls=[])

    fake_provider = FakeProvider([resp1, resp2])
    set_test_night_provider_override(fake_provider)

    runner = NightRunner(once=True, allow_shell=True)
    processed = runner.run_night_queue()

    assert len(processed) == 1
    updated_task = repo_db.get_task(task.id)
    assert updated_task is not None
    assert updated_task.status == "succeeded"

    res_log = subprocess.run(
        ["git", "log", "-n", "1", "--oneline", updated_task.branch_name],
        cwd=repo,
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    )
    assert "sleepcode: Add helper module" in res_log.stdout

    main_log = subprocess.run(
        ["git", "log", "-n", "1", "--oneline", "master"],
        cwd=repo,
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    )
    assert "Initial commit" in main_log.stdout
    assert "sleepcode" not in main_log.stdout


def test_night_runner_allow_shell_schema_presence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SLEEPCODE_HOME", str(tmp_path))
    repo = create_temp_git_repo(tmp_path / "shell_repo")

    conn = get_db_connection()
    repo_db = TaskRepository(conn)
    repo_db.add_task(
        task_text="Run shell task",
        repo_path=str(repo),
        model="groq/llama-3.3-70b-versatile",
    )

    fake_provider1 = FakeProvider([ProviderResponse(text="Done", tool_calls=[])])
    set_test_night_provider_override(fake_provider1)

    runner_no_shell = NightRunner(once=True, allow_shell=False)
    runner_no_shell.run_night_queue()

    tools_sent_no_shell = fake_provider1.calls[0]["tools"]
    tool_names_no_shell = [t["function"]["name"] for t in tools_sent_no_shell]
    assert "run_shell" not in tool_names_no_shell
    assert "git_status" not in tool_names_no_shell

    repo_db.add_task(
        task_text="Run shell task 2",
        repo_path=str(repo),
        model="groq/llama-3.3-70b-versatile",
    )

    fake_provider2 = FakeProvider([ProviderResponse(text="Done", tool_calls=[])])
    set_test_night_provider_override(fake_provider2)

    runner_with_shell = NightRunner(once=True, allow_shell=True)
    runner_with_shell.run_night_queue()

    tools_sent_with_shell = fake_provider2.calls[0]["tools"]
    tool_names_with_shell = [t["function"]["name"] for t in tools_sent_with_shell]
    assert "run_shell" in tool_names_with_shell
    assert "git_status" in tool_names_with_shell


def test_core_offline_demo_integration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Core demo offline test.

    Sets up a git repo, adds two tasks with scripted fake responses (one succeeds, one fails due
    to forbidden secret file), runs 'sleepcode night start --once', and asserts:
    - Task 1 succeeds and creates a commit on its task branch.
    - Task 2 fails and records status 'failed' with reason.
    - 'main' (or 'master') remains unchanged.
    - Original branch is restored.
    - Morning report file is created.
    """
    monkeypatch.setenv("SLEEPCODE_HOME", str(tmp_path))
    repo = create_temp_git_repo(tmp_path / "demo_repo")

    conn = get_db_connection()
    repo_db = TaskRepository(conn)

    # Task 1: succeeds without test_cmd
    t1 = repo_db.add_task(
        task_text="Successful feature task",
        repo_path=str(repo),
        model="groq/llama-3.3-70b-versatile",
    )

    # Task 2: fails due to secret path check (.env file)
    t2 = repo_db.add_task(
        task_text="Task with forbidden secret file",
        repo_path=str(repo),
        model="groq/llama-3.3-70b-versatile",
    )

    resp1_1 = ProviderResponse(
        text="Adding feature",
        tool_calls=[
            ToolCall(
                id="tc1",
                name="write_file",
                arguments={"path": "feature.py", "content": "print('feature')"},
            )
        ],
    )
    resp1_2 = ProviderResponse(text="Done feature", tool_calls=[])

    resp2_1 = ProviderResponse(
        text="Adding secret file",
        tool_calls=[
            ToolCall(
                id="tc2",
                name="write_file",
                arguments={"path": ".env", "content": "SECRET_KEY=123"},
            )
        ],
    )
    resp2_2 = ProviderResponse(text="Done secret file", tool_calls=[])

    fake_provider = FakeProvider([resp1_1, resp1_2, resp2_1, resp2_2])
    set_test_night_provider_override(fake_provider)

    runner = NightRunner(once=True, allow_shell=True)
    processed = runner.run_night_queue()

    assert len(processed) == 2

    # Check Task 1
    task1_updated = repo_db.get_task(t1.id)
    assert task1_updated is not None
    assert task1_updated.status == "succeeded"
    assert task1_updated.branch_name is not None
    assert task1_updated.branch_name.startswith("sleepcode/successful-feature-task")

    log_t1 = subprocess.run(
        ["git", "log", "-n", "1", "--oneline", task1_updated.branch_name],
        cwd=repo,
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    )
    assert "sleepcode: Successful feature task" in log_t1.stdout

    # Check Task 2 (failed due to secret path check)
    task2_updated = repo_db.get_task(t2.id)
    assert task2_updated is not None
    assert task2_updated.status == "failed"

    # Check master branch unchanged
    master_log = subprocess.run(
        ["git", "log", "-n", "1", "--oneline", "master"],
        cwd=repo,
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    )
    assert "Initial commit" in master_log.stdout
    assert "sleepcode" not in master_log.stdout

    # Check original branch restored
    current_branch = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=repo,
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    ).stdout.strip()
    assert current_branch in ("master", "main")

    # Check Morning Report created today
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report_file = tmp_path / "reports" / f"{today_str}.md"
    assert report_file.exists()
    report_text = report_file.read_text(encoding="utf-8")
    assert "SleepCode Morning Report" in report_text
    assert "Successful feature task" in report_text
    assert "Task with forbidden secret file" in report_text
