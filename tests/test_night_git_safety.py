# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import subprocess
from pathlib import Path

from sleepcode.night.git_ops import (
    commit_task_changes,
    create_task_branch,
    find_staged_secret_files,
    get_current_branch,
    restore_branch,
)


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


def test_branch_creation_and_restoration(tmp_path: Path) -> None:
    repo = create_temp_git_repo(tmp_path / "repo")
    orig_branch = get_current_branch(repo)

    task_branch = create_task_branch(repo, "Fix security bug in auth module")
    assert task_branch.startswith("sleepcode/fix-security-bug-in")
    assert get_current_branch(repo) == task_branch

    (repo / "fix.py").write_text("print('fixed')", encoding="utf-8")
    ok, msg = commit_task_changes(repo, "Fix security bug")
    assert ok is True

    restore_branch(repo, orig_branch)
    assert get_current_branch(repo) == orig_branch


def test_secret_path_check_refuses_commit(tmp_path: Path) -> None:
    repo = create_temp_git_repo(tmp_path / "repo")
    create_task_branch(repo, "Add secret configuration")

    (repo / ".env").write_text("SECRET_KEY=123", encoding="utf-8")
    (repo / "secrets.key").write_text("key_data", encoding="utf-8")

    staged_secrets = find_staged_secret_files(repo)
    assert ".env" in staged_secrets
    assert "secrets.key" in staged_secrets

    ok, msg = commit_task_changes(repo, "Add secret configuration")
    assert ok is False
    assert "Refused commit due to secret path check" in msg
    assert ".env" in msg
    assert "secrets.key" in msg
    assert "SECRET_KEY=123" not in msg
    assert "key_data" not in msg
