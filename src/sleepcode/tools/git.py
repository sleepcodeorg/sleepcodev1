# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import re
import shlex
import subprocess
from datetime import datetime
from typing import Any, Dict

from sleepcode.tools.base import Tool, ToolResult
from sleepcode.tools.shell import run_command_in_workspace
from sleepcode.workspace import Workspace

BRANCH_NAME_REGEX = re.compile(r"^sleepcode/[a-z0-9-]+-\d{8}-\d{6}$")


def generate_branch_name(task_slug: str, now: datetime | None = None) -> str:
    """Generate standardized branch name `sleepcode/<slug>-<YYYYMMDD-HHMMSS>`."""
    if now is None:
        now = datetime.now()

    # Lowercase, keep letters, digits, hyphens, replace others with hyphen
    slug = re.sub(r"[^a-z0-9-]+", "-", task_slug.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        slug = "task"
    slug = slug[:40].rstrip("-")

    timestamp = now.strftime("%Y%m%d-%H%M%S")
    return f"sleepcode/{slug}-{timestamp}"


def is_valid_branch_name(branch_name: str) -> bool:
    """Validate branch name against Phase 2 regex pattern."""
    return bool(BRANCH_NAME_REGEX.match(branch_name))


class GitStatusTool(Tool):
    """Tool to view workspace git status."""

    name = "git_status"
    description = "Returns `git status --porcelain` for the workspace repository."
    parameters_schema = {
        "type": "object",
        "properties": {},
    }

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def run(self, arguments: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        if dry_run:
            return ToolResult(ok=True, output="[DRY RUN] git status --porcelain", files_changed=[])
        return run_command_in_workspace("git status --porcelain", self.workspace)


class GitDiffTool(Tool):
    """Tool to view workspace git diff."""

    name = "git_diff"
    description = "Returns `git diff` output, truncated to 20 KB."
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Optional relative file or directory path to diff.",
            }
        },
    }

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def run(self, arguments: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        path = arguments.get("path")
        cmd = f"git diff {shlex.quote(path)}" if path else "git diff"
        if dry_run:
            return ToolResult(ok=True, output=f"[DRY RUN] {cmd}", files_changed=[])
        return run_command_in_workspace(cmd, self.workspace)


class GitCreateBranchTool(Tool):
    """Tool to create and checkout a new branch in workspace."""

    name = "git_create_branch"
    description = (
        "Creates and checks out a new branch matching `sleepcode/<slug>-<YYYYMMDD-HHMMSS>`."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Branch name to create and checkout.",
            }
        },
        "required": ["name"],
    }

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def run(self, arguments: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        name = arguments.get("name", "").strip()
        if not is_valid_branch_name(name):
            return ToolResult(
                ok=False,
                output=(
                    f"Error: Invalid branch name '{name}'. "
                    "Must match regex pattern ^sleepcode/[a-z0-9-]+-\\d{8}-\\d{6}$"
                ),
                files_changed=[],
            )

        cmd = f"git checkout -b {shlex.quote(name)}"
        if dry_run:
            return ToolResult(ok=True, output=f"[DRY RUN] {cmd}", files_changed=[])
        return run_command_in_workspace(cmd, self.workspace)


class GitCommitTool(Tool):
    """Tool to stage all changes and commit in workspace repository."""

    name = "git_commit"
    description = "Stages all workspace changes and commits with the provided message."
    parameters_schema = {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Commit message.",
            }
        },
        "required": ["message"],
    }

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def run(self, arguments: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        message = arguments.get("message", "").strip()
        if not message:
            msg_err = "Error: Commit message cannot be empty."
            return ToolResult(ok=False, output=msg_err, files_changed=[])

        if dry_run:
            return ToolResult(
                ok=True,
                output=f"[DRY RUN] git add -A && git commit -m '{message}'",
                files_changed=[],
            )

        # Check if workspace is a git repo
        git_dir = self.workspace.root / ".git"
        if not git_dir.exists():
            return ToolResult(
                ok=False,
                output="Error: No workspace git repository found.",
                files_changed=[],
            )

        # Check current branch
        try:
            branch_proc = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=str(self.workspace.root),
                capture_output=True,
                text=True,
                check=True,
            )
            current_branch = branch_proc.stdout.strip()
            if current_branch in {"main", "master"}:
                refuse_msg = (
                    f"Refusing to commit on branch '{current_branch}'. "
                    "Please create and use a feature branch."
                )
                return ToolResult(
                    ok=False,
                    output=refuse_msg,
                    files_changed=[],
                )
        except Exception as e:
            return ToolResult(
                ok=False,
                output=f"Error checking git branch: {str(e)}",
                files_changed=[],
            )

        stage_res = run_command_in_workspace("git add -A", self.workspace)
        if not stage_res.ok:
            return stage_res

        cmd_str = f"git commit -m {shlex.quote(message)}"
        commit_res = run_command_in_workspace(cmd_str, self.workspace)
        return commit_res
