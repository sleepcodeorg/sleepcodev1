# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from sleepcode.agent.loop import AgentLimits, AgentLoop
from sleepcode.providers.base import ProviderResponse, ToolCall
from sleepcode.providers.fake_provider import FakeProvider
from sleepcode.tools.registry import ToolRegistry
from sleepcode.workspace import Workspace


def test_limit_max_iterations(temp_workspace: Workspace, sleepcode_home: Path) -> None:
    registry = ToolRegistry()
    fake_responses = [
        ProviderResponse(
            text="Looping",
            tool_calls=[ToolCall(id=f"tc{i}", name="dummy", arguments={})],
        )
        for i in range(10)
    ]
    provider = FakeProvider(fake_responses)

    loop = AgentLoop(
        task="Infinite loop",
        workspace=temp_workspace,
        model="openai/gpt-4o-mini",
        provider=provider,
        tools=registry,
        limits=AgentLimits(max_iterations=2),
    )

    result = loop.run()
    assert result.stop_reason == "max_iterations"


def test_limit_max_total_tokens(temp_workspace: Workspace, sleepcode_home: Path) -> None:
    registry = ToolRegistry()
    fake_responses = [
        ProviderResponse(text="Big response", tool_calls=[], input_tokens=1000, output_tokens=1000)
    ]
    provider = FakeProvider(fake_responses)

    loop = AgentLoop(
        task="Token limit test",
        workspace=temp_workspace,
        model="openai/gpt-4o-mini",
        provider=provider,
        tools=registry,
        limits=AgentLimits(max_total_tokens=500),
    )

    result = loop.run()
    assert result.stop_reason == "max_total_tokens"


def test_limit_max_cost_usd(temp_workspace: Workspace, sleepcode_home: Path) -> None:
    registry = ToolRegistry()
    fake_responses = [ProviderResponse(text="Expensive response", tool_calls=[], cost_usd=5.00)]
    provider = FakeProvider(fake_responses)

    loop = AgentLoop(
        task="Cost limit test",
        workspace=temp_workspace,
        model="openai/gpt-4o-mini",
        provider=provider,
        tools=registry,
        limits=AgentLimits(max_cost_usd=1.00),
    )

    result = loop.run()
    assert result.stop_reason == "max_cost_usd"


def test_limit_max_wall_seconds(temp_workspace: Workspace, sleepcode_home: Path) -> None:
    registry = ToolRegistry()
    fake_responses = [
        ProviderResponse(text="Step 1", tool_calls=[ToolCall(id="1", name="d", arguments={})]),
        ProviderResponse(text="Step 2", tool_calls=[]),
    ]
    provider = FakeProvider(fake_responses)

    time_counter = [1000.0]

    def fake_clock() -> float:
        time_counter[0] += 100.0
        return time_counter[0]

    loop = AgentLoop(
        task="Wall time limit test",
        workspace=temp_workspace,
        model="openai/gpt-4o-mini",
        provider=provider,
        tools=registry,
        limits=AgentLimits(max_wall_seconds=50.0),
        clock=fake_clock,
    )

    result = loop.run()
    assert result.stop_reason == "max_wall_seconds"
