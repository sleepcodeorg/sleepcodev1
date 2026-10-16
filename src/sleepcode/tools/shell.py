# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import subprocess
from typing import Any, Dict, Optional, Set

from sleepcode.config import load_config
from sleepcode.safety.commands import validate_command
from sleepcode.safety.env import build_minimal_env
from sleepcode.secrets import redact_secrets
from sleepcode.tools.base import MAX_OUTPUT_BYTES, Tool, ToolResult, truncate_output
from sleepcode.workspace import Workspace


def run_command_in_workspace(
    command: str,
    workspace: Workspace,
    timeout: int = 60,
    allowed_commands: Optional[Set[str]] = None,
    extra_secrets: Optional[Set[str]] = None,
) -> ToolResult:
    """Validate and execute a shell command in the workspace directory with safety checks."""
    if timeout > 300:
        timeout = 300
    if timeout < 1:
        timeout = 1

    cfg = load_config()
    allowlist = allowed_commands
    if allowlist is None and cfg.allowed_commands:
        allowlist = set(cfg.allowed_commands)

    try:
        tokens = validate_command(
            command=command,
            workspace=workspace,
            allowed_commands=allowlist,
        )
    except Exception as e:
        return ToolResult(
            ok=False,
            output=f"Command validation error: {str(e)}",
            files_changed=[],
        )

    env = build_minimal_env()

    try:
        proc = subprocess.run(
            tokens,
            cwd=str(workspace.root),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        stdout = redact_secrets(proc.stdout or "", extra_secrets)
        stderr = redact_secrets(proc.stderr or "", extra_secrets)

        output_lines = []
        if stdout:
            output_lines.append(f"STDOUT:\n{stdout}")
        if stderr:
            output_lines.append(f"STDERR:\n{stderr}")
        if not output_lines:
            output_lines.append("(No output)")

        output_str = "\n\n".join(output_lines)
        output_str = truncate_output(output_str, max_bytes=MAX_OUTPUT_BYTES)

        ok = proc.returncode == 0
        if not ok:
            output_str = f"Command failed with exit code {proc.returncode}.\n{output_str}"

        return ToolResult(
            ok=ok,
            output=output_str,
            files_changed=[],
        )
    except subprocess.TimeoutExpired:
        return ToolResult(
            ok=False,
            output=f"Error: Command timed out after {timeout} seconds.",
            files_changed=[],
        )
    except Exception as e:
        return ToolResult(
            ok=False,
            output=f"Execution error: {str(e)}",
            files_changed=[],
        )


class RunShellTool(Tool):
    """Tool to execute safe shell commands within the workspace."""

    name = "run_shell"
    description = (
        "Execute a shell command safely inside the workspace root. "
        "The executable must be on the allowlist, and shell control operators are rejected."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Command string to execute (e.g. 'pytest -q').",
            },
            "timeout": {
                "type": "integer",
                "description": "Optional timeout in seconds (default 60, max 300).",
                "default": 60,
            },
        },
        "required": ["command"],
    }

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def run(self, arguments: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        command = arguments.get("command", "")
        timeout = int(arguments.get("timeout", 60))

        if dry_run:
            return ToolResult(
                ok=True,
                output=f"[DRY RUN] Would execute command: {command}",
                files_changed=[],
            )

        return run_command_in_workspace(command, self.workspace, timeout=timeout)
