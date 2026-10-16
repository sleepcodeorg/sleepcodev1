# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import subprocess

from sleepcode.tools.git import (
    GitCommitTool,
    GitCreateBranchTool,
    GitDiffTool,
    GitStatusTool,
    generate_branch_name,
    is_valid_branch_name,
)
from sleepcode.tools.registry import ToolRegistry
from sleepcode.workspace import Workspace


def test_slug_generation_and_regex():
    branch = generate_branch_name("Fix Bug #123 in User Auth!!")
    assert is_valid_branch_name(branch)

    assert not is_valid_branch_name("feature/my-branch")
    assert not is_valid_branch_name("sleepcode/invalid")


def test_git_commit_refuses_on_main_and_master(tmp_path):
    ws = Workspace(tmp_path)
    subprocess.run(["git", "init"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(tmp_path), check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=str(tmp_path), check=True
    )
    subprocess.run(["git", "checkout", "-b", "main"], cwd=str(tmp_path), check=True)

    # Initial commit so HEAD is valid
    (tmp_path / "init.txt").write_text("init")
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=str(tmp_path), check=True)

    # Create dummy file to commit
    (tmp_path / "hello.txt").write_text("hello")

    commit_tool = GitCommitTool(ws)
    res = commit_tool.run({"message": "test commit"})
    assert not res.ok
    assert "Refusing to commit on branch 'main'" in res.output


def test_git_tools_absence_in_registry_without_allow_shell(tmp_path):
    registry = ToolRegistry()
    schemas = registry.get_schemas()
    tool_names = [s["function"]["name"] for s in schemas]
    for git_tool in ["git_status", "git_diff", "git_create_branch", "git_commit"]:
        assert git_tool not in tool_names


def test_no_forbidden_git_tools_registered():
    ws_dummy = Workspace(".")
    forbidden_tools = ["git_push", "git_remote", "git_reset", "git_clean"]
    registry = ToolRegistry()
    registry.register(GitStatusTool(ws_dummy))
    registry.register(GitDiffTool(ws_dummy))
    registry.register(GitCreateBranchTool(ws_dummy))
    registry.register(GitCommitTool(ws_dummy))

    schemas = registry.get_schemas()
    registered_names = [s["function"]["name"] for s in schemas]

    for tool in forbidden_tools:
        assert tool not in registered_names
