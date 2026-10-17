# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import fnmatch
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import List

FORBIDDEN_SECRET_PATTERNS = [
    ".env",
    "*.pem",
    "*.key",
    "*secret*",
]


def check_working_tree_clean(repo_path: Path) -> tuple[bool, str]:
    """Check if git working tree is clean."""
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        if res.stdout.strip():
            return False, "Working tree is dirty."
        return True, "Clean working tree."
    except Exception as e:
        return False, f"Git error checking working tree: {str(e)}"


def get_current_branch(repo_path: Path) -> str:
    """Get current active git branch name."""
    res = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=repo_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    branch = res.stdout.strip()
    return branch or "HEAD"


def slugify_task(task_text: str) -> str:
    """Create URL/branch friendly slug from task text."""
    clean = re.sub(r"[^a-zA-Z0-9\s-]", "", task_text).lower()
    words = clean.split()[:4]
    slug = "-".join(words) or "task"
    return slug[:30].strip("-")


def create_task_branch(repo_path: Path, task_text: str) -> str:
    """Create and checkout task branch sleepcode/<slug>-<YYYYMMDD-HHMMSS>."""
    slug = slugify_task(task_text)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    base_branch = f"sleepcode/{slug}-{timestamp}"

    branch_name = base_branch
    suffix = 1
    while True:
        check = subprocess.run(
            ["git", "rev-parse", "--verify", branch_name],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if check.returncode != 0:
            break
        branch_name = f"{base_branch}-{suffix}"
        suffix += 1

    subprocess.run(
        ["git", "checkout", "-b", branch_name],
        cwd=repo_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    return branch_name


def restore_branch(repo_path: Path, original_branch: str) -> None:
    """Checkout original branch back."""
    subprocess.run(
        ["git", "checkout", original_branch],
        cwd=repo_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )


def find_staged_secret_files(repo_path: Path) -> List[str]:
    """Check staged or modified files against secret path patterns."""
    res = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    detected: List[str] = []
    for line in res.stdout.splitlines():
        if not line.strip():
            continue
        filepath_str = line[3:].strip()
        filename = Path(filepath_str).name
        for pattern in FORBIDDEN_SECRET_PATTERNS:
            if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(filepath_str, pattern):
                detected.append(filepath_str)
                break

    return detected


def commit_task_changes(
    repo_path: Path,
    task_text: str,
    secret_check: bool = True,
) -> tuple[bool, str]:
    """Stage and commit changes on task branch after passing secret path checks."""
    current_branch = get_current_branch(repo_path)
    if current_branch in ("main", "master"):
        return False, "Refused to commit: current branch is main/master."

    if secret_check:
        forbidden = find_staged_secret_files(repo_path)
        if forbidden:
            f_list = ", ".join(forbidden)
            return (
                False,
                f"Refused commit due to secret path check. Found matching file(s): {f_list}",
            )

    status_res = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    if not status_res.stdout.strip():
        return True, "No changes to commit."

    subprocess.run(
        ["git", "add", "-A"],
        cwd=repo_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )

    commit_msg = f"sleepcode: {task_text[:60]}"
    res = subprocess.run(
        ["git", "commit", "-m", commit_msg],
        cwd=repo_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if res.returncode == 0:
        return True, f"Committed changes on branch '{current_branch}'."
    return False, f"Git commit failed: {res.stderr.strip()}"
