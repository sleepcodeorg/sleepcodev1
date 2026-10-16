# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from sleepcode.agent.loop import AgentLimits
from sleepcode.agent.repair import run_repair_loop
from sleepcode.providers.base import ProviderResponse, ToolCall
from sleepcode.providers.fake_provider import FakeProvider
from sleepcode.tools.files import EditFileTool, ReadFileTool, WriteFileTool
from sleepcode.tools.registry import ToolRegistry
from sleepcode.workspace import Workspace


def test_repair_loop_fail_then_pass(tmp_path):
    ws = Workspace(tmp_path)

    # Initial buggy implementation
    (tmp_path / "calc.py").write_text("def add(a, b): return a - b\n")
    test_code = "from calc import add\ndef test_add(): assert add(2, 3) == 5\n"
    (tmp_path / "test_calc.py").write_text(test_code)

    registry = ToolRegistry()
    registry.register(ReadFileTool(ws))
    registry.register(WriteFileTool(ws))
    registry.register(EditFileTool(ws))

    # Turn 1: Agent initially responds done
    resp1 = ProviderResponse(text="Implemented calc", tool_calls=[])

    # Repair attempt:
    # Turn 2: Agent responds with edit tool call
    edit_call = ToolCall(
        id="tc_edit",
        name="edit_file",
        arguments={
            "path": "calc.py",
            "old_string": "return a - b",
            "new_string": "return a + b",
        },
    )
    resp2 = ProviderResponse(text="Fixing add function", tool_calls=[edit_call])
    # Turn 3: Agent responds to tool result (edit success) with final text
    resp3 = ProviderResponse(text="Fixed addition logic", tool_calls=[])

    provider = FakeProvider([resp1, resp2, resp3])

    res = run_repair_loop(
        task="Fix calculator",
        workspace=ws,
        model="openai/gpt-4o-mini",
        provider=provider,
        tools=registry,
        test_cmd="pytest -q -o rootdir=. test_calc.py",
        repair_attempts=2,
    )

    assert res.status == "tests_passed"
    assert res.attempts_used == 1
    assert "1 passed" in res.test_output

    # Verify model received failure message in its calls
    sent_msgs = provider.calls[1]["messages"]
    repair_prompt_sent = False
    for m in sent_msgs:
        if (
            m["role"] == "user"
            and "test command `pytest -q -o rootdir=. test_calc.py` failed" in m["content"]
        ):
            repair_prompt_sent = True
            break
    assert repair_prompt_sent, "Test failure output was not sent to provider"


def test_repair_loop_exhaustion(tmp_path):
    ws = Workspace(tmp_path)
    (tmp_path / "test_calc.py").write_text("def test_fail(): assert False\n")

    registry = ToolRegistry()
    registry.register(ReadFileTool(ws))

    # Agent always says done without fixing
    resp = ProviderResponse(text="Done", tool_calls=[])
    provider = FakeProvider([resp, resp, resp])

    res = run_repair_loop(
        task="Fix broken test",
        workspace=ws,
        model="openai/gpt-4o-mini",
        provider=provider,
        tools=registry,
        test_cmd="pytest -q -o rootdir=. test_calc.py",
        repair_attempts=2,
    )

    assert res.status == "tests_failed"
    assert res.attempts_used == 2


def test_repair_loop_respects_limits(tmp_path):
    ws = Workspace(tmp_path)
    (tmp_path / "test_calc.py").write_text("def test_fail(): assert False\n")

    registry = ToolRegistry()

    # Turn 1 uses 1 iteration. Turn 2 repair attempt should exceed max_iterations=1.
    resp1 = ProviderResponse(text="Initial attempt done", tool_calls=[])
    resp2 = ProviderResponse(text="Repair attempt done", tool_calls=[])
    provider = FakeProvider([resp1, resp2])

    limits = AgentLimits(max_iterations=1)

    res = run_repair_loop(
        task="Fix broken test with low limits",
        workspace=ws,
        model="openai/gpt-4o-mini",
        provider=provider,
        tools=registry,
        test_cmd="pytest -q -o rootdir=. test_calc.py",
        repair_attempts=2,
        limits=limits,
    )

    assert res.status == "tests_failed"
    assert res.agent_result.stop_reason == "max_iterations"
