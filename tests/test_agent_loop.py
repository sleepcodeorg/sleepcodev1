# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from sleepcode.agent.loop import AgentLoop
from sleepcode.providers.base import ProviderResponse, ToolCall
from sleepcode.providers.fake_provider import FakeProvider
from sleepcode.tools.files import ReadFileTool, WriteFileTool
from sleepcode.tools.registry import ToolRegistry
from sleepcode.workspace import Workspace


def test_agent_loop_scripted_success(temp_workspace: Workspace, sleepcode_home: Path) -> None:
    registry = ToolRegistry()
    registry.register(WriteFileTool(temp_workspace))
    registry.register(ReadFileTool(temp_workspace))

    fake_responses = [
        ProviderResponse(
            text="Writing file",
            tool_calls=[
                ToolCall(
                    id="tc1",
                    name="write_file",
                    arguments={"path": "hello.py", "content": "print('hi')"},
                )
            ],
            input_tokens=50,
            output_tokens=20,
            cost_usd=0.001,
        ),
        ProviderResponse(
            text="Done creating hello.py",
            tool_calls=[],
            input_tokens=100,
            output_tokens=10,
            cost_usd=0.001,
        ),
    ]

    provider = FakeProvider(fake_responses)

    loop = AgentLoop(
        task="Create hello.py",
        workspace=temp_workspace,
        model="openai/gpt-4o-mini",
        provider=provider,
        tools=registry,
    )

    result = loop.run()

    assert result.stop_reason == "completed"
    assert "hello.py" in result.files_changed
    assert (temp_workspace.root / "hello.py").read_text() == "print('hi')"


def test_agent_loop_unknown_tool_recovery(temp_workspace: Workspace, sleepcode_home: Path) -> None:
    registry = ToolRegistry()

    fake_responses = [
        ProviderResponse(
            text="Attempting bad tool",
            tool_calls=[ToolCall(id="tc1", name="nonexistent_tool", arguments={})],
            input_tokens=20,
            output_tokens=10,
        ),
        ProviderResponse(
            text="Recovered from unknown tool",
            tool_calls=[],
            input_tokens=30,
            output_tokens=10,
        ),
    ]

    provider = FakeProvider(fake_responses)

    loop = AgentLoop(
        task="Test unknown tool",
        workspace=temp_workspace,
        model="openai/gpt-4o-mini",
        provider=provider,
        tools=registry,
    )

    result = loop.run()
    assert result.stop_reason == "completed"
    assert "Recovered" in result.final_text


def test_agent_loop_dry_run(temp_workspace: Workspace, sleepcode_home: Path) -> None:
    registry = ToolRegistry()
    registry.register(WriteFileTool(temp_workspace))

    fake_responses = [
        ProviderResponse(
            text="Writing file",
            tool_calls=[
                ToolCall(
                    id="tc1",
                    name="write_file",
                    arguments={"path": "dry.py", "content": "print('dry')"},
                )
            ],
            input_tokens=50,
            output_tokens=20,
        ),
        ProviderResponse(
            text="Finished dry run task.",
            tool_calls=[],
            input_tokens=50,
            output_tokens=10,
        ),
    ]

    provider = FakeProvider(fake_responses)

    loop = AgentLoop(
        task="Dry run write",
        workspace=temp_workspace,
        model="openai/gpt-4o-mini",
        provider=provider,
        tools=registry,
        dry_run=True,
    )

    result = loop.run()

    assert result.stop_reason == "completed"
    assert "[DRY RUN]" in result.final_text
    assert not (temp_workspace.root / "dry.py").exists()
