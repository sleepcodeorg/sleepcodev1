# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import shlex
from typing import List, Optional, Set

from sleepcode.workspace import Workspace, WorkspaceError

DEFAULT_ALLOWLIST: Set[str] = {
    "git",
    "python",
    "python3",
    "pytest",
    "ruff",
    "mypy",
    "ls",
    "cat",
    "grep",
}

ALLOWED_GIT_SUBCOMMANDS: Set[str] = {
    "status",
    "diff",
    "add",
    "commit",
    "branch",
    "checkout",
    "log",
    "rev-parse",
}

ALLOWED_PYTHON_MODULES: Set[str] = {
    "pytest",
    "ruff",
    "mypy",
}

PROHIBITED_OPERATORS: List[str] = [
    ";",
    "&&",
    "||",
    "|",
    "`",
    "$(",
    ">",
    "<",
    "\n",
    "\r",
]


def check_shell_operators(command: str) -> None:
    """Check command string for prohibited shell control operators."""
    for op in PROHIBITED_OPERATORS:
        if op in command:
            raise ValueError(f"Prohibited shell control operator '{op}' found in command.")


def validate_command(
    command: str,
    workspace: Workspace,
    allowed_commands: Optional[Set[str]] = None,
) -> List[str]:
    """Parse and validate command for execution safety.

    Returns the parsed command tokens as a list of strings if valid.
    Raises ValueError if validation fails.
    """
    if not command or not command.strip():
        raise ValueError("Empty command.")

    check_shell_operators(command)

    try:
        tokens = shlex.split(command)
    except Exception as e:
        raise ValueError(f"Failed to parse command string: {str(e)}") from e

    if not tokens:
        raise ValueError("Empty command tokens.")

    allowlist = allowed_commands if allowed_commands is not None else DEFAULT_ALLOWLIST

    executable = tokens[0]
    if "/" in executable or "\\" in executable:
        raise ValueError(f"Path-qualified executables are not allowed: '{executable}'")

    if executable.lower() not in {cmd.lower() for cmd in allowlist}:
        raise ValueError(f"Executable '{executable}' is not in the allowlist.")

    tokens_lower = [t.lower() for t in tokens]

    # Blocked keywords check
    blocked_commands = {"sudo", "chmod", "chown", "dd", "mkfs", "curl", "wget"}
    for t in tokens_lower:
        if t in blocked_commands:
            raise ValueError(f"Prohibited command or argument '{t}' in command.")

    # Check rm with -r / -f
    if tokens_lower[0] == "rm":
        for arg in tokens[1:]:
            if arg.startswith("-"):
                arg_clean = arg.lstrip("-").lower()
                if (
                    "r" in arg_clean
                    or "f" in arg_clean
                    or arg_clean == "recursive"
                    or arg_clean == "force"
                ):
                    raise ValueError("Prohibited 'rm' flag (-r/-f) detected.")

    # Git command validation
    if tokens_lower[0] == "git":
        # Reject any git global option/flag (starts with -) before or instead of subcommand
        subcommand: Optional[str] = None
        for token in tokens[1:]:
            if token.startswith("-"):
                raise ValueError(f"Git global options/flags are prohibited: '{token}' in command.")
            else:
                subcommand = token.lower()
                break

        if not subcommand or subcommand not in ALLOWED_GIT_SUBCOMMANDS:
            sub_str = f"'{subcommand}'" if subcommand else "none"
            raise ValueError(
                f"Prohibited or unsupported git subcommand {sub_str}. "
                f"Allowed git subcommands: {sorted(ALLOWED_GIT_SUBCOMMANDS)}"
            )

    # Python command validation
    if tokens_lower[0] in {"python", "python3"}:
        for i, token in enumerate(tokens[1:], start=1):
            if token == "-c" or token == "-":
                raise ValueError("Python '-c' and '-' options are prohibited.")
            if token == "-m":
                if i + 1 >= len(tokens):
                    raise ValueError("Missing module after '-m'.")
                mod_name = tokens[i + 1].lower()
                if mod_name not in ALLOWED_PYTHON_MODULES:
                    raise ValueError(
                        f"Module '{mod_name}' not allowed with 'python -m'. "
                        f"Allowed modules: {sorted(ALLOWED_PYTHON_MODULES)}"
                    )

    # Path escape check on arguments
    for arg in tokens[1:]:
        val_to_check = arg
        if arg.startswith("--") and "=" in arg:
            val_to_check = arg.split("=", 1)[1]

        if val_to_check.startswith("-") and not (
            val_to_check.startswith("/")
            or val_to_check.startswith("~")
            or val_to_check.startswith("..")
        ):
            continue

        # If it looks like a path argument (contains slashes or relative parent traversal)
        if (
            val_to_check.startswith("/")
            or val_to_check.startswith("~")
            or ".." in val_to_check
            or "/" in val_to_check
            or "\\" in val_to_check
        ):
            # Skip checking if it's a git branch name argument in git command or flags
            if tokens_lower[0] == "git":
                continue
            try:
                workspace.resolve_path(val_to_check)
            except WorkspaceError as e:
                raise ValueError(f"Argument path outside workspace: '{arg}'") from e

    return tokens
