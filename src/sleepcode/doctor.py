# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import os
import shutil
import sqlite3
import sys
from typing import Tuple

from rich.console import Console

from sleepcode.config import get_config_dir, get_config_path, load_config
from sleepcode.secrets import redact_secrets

console = Console()


def check_python_version() -> Tuple[bool, str, str]:
    v = sys.version_info
    v_str = f"{v.major}.{v.minor}.{v.micro}"
    if (v.major, v.minor) >= (3, 11):
        return True, f"Python version is {v_str}", "None"
    return False, f"Python version is {v_str} (requires >= 3.11)", "Install Python 3.11 or newer."


def check_git_availability() -> Tuple[bool, str, str]:
    git_path = shutil.which("git")
    if git_path:
        return True, f"Git executable found at {git_path}", "None"
    return False, "Git command not found in PATH", "Install Git or add it to system PATH."


def check_config_file() -> Tuple[bool, str, str]:
    config_path = get_config_path()
    if not config_path.exists():
        return (
            False,
            f"Config file missing at {config_path}",
            "Run 'sleepcode setup' to create initial configuration.",
        )

    mode = os.stat(config_path).st_mode & 0o777
    if mode != 0o600:
        return (
            False,
            f"Config file permissions are {oct(mode)} (expected 0o600)",
            f"Run 'chmod 600 {config_path}' to secure config permissions.",
        )

    return True, f"Config file exists at {config_path} with 0600 permissions", "None"


def check_provider_keys() -> Tuple[bool, str, str]:
    config = load_config()
    if not config.keys:
        return (
            False,
            "No API keys configured",
            "Run 'sleepcode setup' or 'sleepcode config set-key <provider>'.",
        )

    configured = [p for p, k in config.keys.items() if k and k.strip()]
    if not configured:
        return (
            False,
            "No valid API keys configured",
            "Run 'sleepcode setup' to configure provider API keys.",
        )

    p_list = ", ".join(configured)
    return True, f"Configured API keys for: {p_list}", "None"


def check_queue_db_writable() -> Tuple[bool, str, str]:
    config_dir = get_config_dir()
    db_path = config_dir / "sleepcode.db"
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.close()
        return True, f"Queue database at {db_path} is writable", "None"
    except Exception as e:
        return (
            False,
            f"Queue database not writable: {str(e)}",
            f"Check write permissions on directory {config_dir}.",
        )


def run_doctor() -> bool:
    """Run SleepCode diagnostic checks and print plain-language summary."""
    console.print("[bold cyan]SleepCode Doctor Diagnostics[/bold cyan]\n")

    checks = [
        ("Python Version", check_python_version),
        ("Git Availability", check_git_availability),
        ("Config File Security", check_config_file),
        ("Provider Keys", check_provider_keys),
        ("Queue Database Access", check_queue_db_writable),
    ]

    all_passed = True
    for name, check_fn in checks:
        passed, detail, fix_suggestion = check_fn()
        safe_detail = redact_secrets(detail)
        safe_fix = redact_secrets(fix_suggestion)

        if passed:
            console.print(f"[bold green]PASS[/bold green] [{name}] - {safe_detail}")
        else:
            all_passed = False
            console.print(f"[bold red]FAIL[/bold red] [{name}] - {safe_detail}")
            console.print(f"       [yellow]Fix:[/yellow] {safe_fix}")

    return all_passed
