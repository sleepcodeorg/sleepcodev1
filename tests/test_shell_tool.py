# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from sleepcode.safety.env import build_minimal_env
from sleepcode.tools.registry import ToolRegistry
from sleepcode.tools.shell import RunShellTool, run_command_in_workspace
from sleepcode.workspace import Workspace


def test_shell_tool_execution(tmp_path):
    ws = Workspace(tmp_path)
    res = run_command_in_workspace("python3 -c \"print('hello from shell')\"", ws)
    assert res.ok
    assert "hello from shell" in res.output


def test_shell_tool_timeout(tmp_path):
    ws = Workspace(tmp_path)
    res = run_command_in_workspace('python3 -c "import time; time.sleep(10)"', ws, timeout=1)
    assert not res.ok
    assert "timed out after 1 seconds" in res.output


def test_env_scrubbing(monkeypatch, tmp_path):
    ws = Workspace(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "mock_key_val")
    monkeypatch.setenv("MY_SECRET_TOKEN", "secret123")
    monkeypatch.setenv("DB_PASSWORD", "pass123")
    monkeypatch.setenv("NORMAL_VAR", "visible")

    env = build_minimal_env()
    assert "OPENAI_API_KEY" not in env
    assert "MY_SECRET_TOKEN" not in env
    assert "DB_PASSWORD" not in env
    assert env.get("NORMAL_VAR") == "visible"

    res = run_command_in_workspace(
        "python3 -c \"import os; print(os.environ.get('OPENAI_API_KEY'))\"", ws
    )
    assert res.ok
    assert "None" in res.output


def test_run_shell_absent_without_allow_shell(tmp_path):
    registry = ToolRegistry()
    schemas = registry.get_schemas()
    tool_names = [s["function"]["name"] for s in schemas]
    assert "run_shell" not in tool_names


def test_run_shell_present_with_allow_shell(tmp_path):
    ws = Workspace(tmp_path)
    registry = ToolRegistry()
    registry.register(RunShellTool(ws))
    schemas = registry.get_schemas()
    tool_names = [s["function"]["name"] for s in schemas]
    assert "run_shell" in tool_names
