# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import pytest

from sleepcode.safety.commands import PROHIBITED_OPERATORS, validate_command
from sleepcode.workspace import Workspace


def test_prohibited_operators(tmp_path):
    ws = Workspace(tmp_path)
    for op in PROHIBITED_OPERATORS:
        cmd = f"ls {op} echo test" if op not in {"\n", "\r"} else f"ls{op}echo test"
        with pytest.raises(ValueError, match="Prohibited shell control operator"):
            validate_command(cmd, ws)


def test_allowlist_enforcement(tmp_path):
    ws = Workspace(tmp_path)

    # Allowed command (script in workspace)
    (tmp_path / "script.py").write_text("print('hello')")
    tokens = validate_command("python script.py", ws)
    assert tokens[0] == "python"

    # Non-allowlisted executable
    with pytest.raises(ValueError, match="not in the allowlist"):
        validate_command("bash -c 'echo hi'", ws)


def test_pip_not_in_default_allowlist(tmp_path):
    ws = Workspace(tmp_path)

    with pytest.raises(ValueError, match="not in the allowlist"):
        validate_command("pip install evilpkg", ws)


def test_path_qualified_executables_rejected(tmp_path):
    ws = Workspace(tmp_path)

    with pytest.raises(ValueError, match="Path-qualified executables are not allowed"):
        validate_command("/bin/rm file.txt", ws)

    with pytest.raises(ValueError, match="Path-qualified executables are not allowed"):
        validate_command("./my_script.sh", ws)


def test_git_subcommand_allowlist_and_global_flag_rejection(tmp_path):
    ws = Workspace(tmp_path)

    bypass_cmds = [
        "git -c core.x=1 push origin main",
        "git --no-pager push origin main",
        "git -c alias.evil=!id evil",
    ]

    for cmd in bypass_cmds:
        with pytest.raises(ValueError) as excinfo:
            validate_command(cmd, ws)
        assert any(
            msg in str(excinfo.value)
            for msg in [
                "Git global options/flags are prohibited",
                "Prohibited or unsupported git subcommand",
                "Prohibited git command",
            ]
        )


def test_python_command_restrictions(tmp_path):
    ws = Workspace(tmp_path)

    # python -c rejected
    with pytest.raises(ValueError, match="Python '-c' and '-' options are prohibited"):
        validate_command("python -c 'import os'", ws)

    # python - stdin rejected
    with pytest.raises(ValueError, match="Python '-c' and '-' options are prohibited"):
        validate_command("python -", ws)


def test_deny_patterns(tmp_path):
    ws = Workspace(tmp_path)

    deny_cmds = [
        "sudo ls",
        "chmod 777 file",
        "chown root file",
        "dd if=/dev/zero of=file",
        "mkfs.ext4 /dev/sdb",
        "curl http://example.com",
        "wget http://example.com",
        "git push origin main",
        "git remote add origin https://github.com/repo",
        "git config --global user.name 'Attacker'",
        "rm -r dir",
        "rm -rf dir",
        "rm -f file",
        "rm --recursive dir",
        "rm --force file",
    ]

    for cmd in deny_cmds:
        with pytest.raises(ValueError) as excinfo:
            validate_command(cmd, ws)
        assert any(
            msg in str(excinfo.value)
            for msg in [
                "Prohibited command",
                "Prohibited 'rm' flag",
                "Prohibited git command",
                "not in the allowlist",
                "Git global options/flags are prohibited",
                "Prohibited or unsupported git subcommand",
            ]
        )


def test_workspace_path_escape_rejected(tmp_path):
    ws = Workspace(tmp_path)

    with pytest.raises(ValueError, match="Argument path outside workspace"):
        validate_command("cat /etc/passwd", ws)

    with pytest.raises(ValueError, match="Argument path outside workspace"):
        validate_command("ls ../secret.txt", ws)
