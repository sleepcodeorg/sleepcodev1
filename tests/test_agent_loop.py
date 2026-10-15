# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path
from unittest.mock import patch

import litellm
import pytest

from sleepcode.agent.loop import AgentLoop
from sleepcode.providers.base import ProviderResponse, ToolCall
from sleepcode.providers.fake_provider import FakeProvider
from sleepcode.providers.litellm_provider import LiteLLMProvider
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


def test_agent_loop_multiturn_valid_json_arguments(
    temp_workspace: Workspace, sleepcode_home: Path
) -> None:
    registry = ToolRegistry()
    registry.register(WriteFileTool(temp_workspace))

    original_args = {"path": "step1.txt", "content": "data1"}

    fake_responses = [
        ProviderResponse(
            text="First step",
            tool_calls=[
                ToolCall(
                    id="tc_step1",
                    name="write_file",
                    arguments=original_args,
                )
            ],
        ),
        ProviderResponse(
            text="Second step",
            tool_calls=[],
        ),
    ]

    provider = FakeProvider(fake_responses)

    loop = AgentLoop(
        task="Multi turn task",
        workspace=temp_workspace,
        model="openai/gpt-4o-mini",
        provider=provider,
        tools=registry,
    )

    loop.run()

    assert len(provider.calls) == 2
    second_call_messages = provider.calls[1]["messages"]

    assistant_msg = next(m for m in second_call_messages if m.get("role") == "assistant")
    tool_calls = assistant_msg.get("tool_calls", [])
    assert len(tool_calls) == 1

    args_str = tool_calls[0]["function"]["arguments"]
    parsed = json.loads(args_str)
    assert parsed == original_args


def test_str_vs_json_dumps_tool_arguments() -> None:
    arguments = {"path": "test.txt", "content": "hello 'quotes'"}

    str_repr = str(arguments)
    with pytest.raises(json.JSONDecodeError):
        json.loads(str_repr)

    json_repr = json.dumps(arguments)
    assert json.loads(json_repr) == arguments


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


def test_litellm_provider_bad_request_no_retry() -> None:
    provider = LiteLLMProvider(api_key="sk-test-key")

    with patch("litellm.completion") as mock_comp:
        mock_comp.side_effect = litellm.BadRequestError(
            message="Invalid prompt", model="gpt-4o", llm_provider="openai"
        )

        with pytest.raises(RuntimeError, match="Invalid prompt"):
            provider.complete(messages=[], model="openai/gpt-4o")

        assert mock_comp.call_count == 1


def test_litellm_provider_authentication_error_redacted() -> None:
    secret_key = "sk-secret-key-123456"
    provider = LiteLLMProvider(api_key=secret_key)

    with patch("litellm.completion") as mock_comp:
        mock_comp.side_effect = litellm.AuthenticationError(
            message=f"Invalid API Key: {secret_key}", model="gpt-4o", llm_provider="openai"
        )

        with pytest.raises(RuntimeError) as exc_info:
            provider.complete(messages=[], model="openai/gpt-4o")

        assert mock_comp.call_count == 1
        err_msg = str(exc_info.value)
        assert secret_key not in err_msg
        assert "[REDACTED]" in err_msg


def test_litellm_provider_rate_limit_retry_until_fail() -> None:
    provider = LiteLLMProvider(api_key="sk-test-key")

    with patch("litellm.completion") as mock_comp, patch("time.sleep") as mock_sleep:
        mock_comp.side_effect = litellm.RateLimitError(
            message="Rate limit hit", model="gpt-4o", llm_provider="openai"
        )

        with pytest.raises(RuntimeError, match="Rate limit hit"):
            provider.complete(messages=[], model="openai/gpt-4o")

        assert mock_comp.call_count == 3
        assert mock_sleep.call_count == 2


def test_litellm_provider_rate_limit_retry_then_success() -> None:
    provider = LiteLLMProvider(api_key="sk-test-key")

    mock_choice = type(
        "Choice", (), {"message": type("Message", (), {"content": "Success", "tool_calls": []})()}
    )()
    mock_response = type("Response", (), {"choices": [mock_choice], "usage": None})()

    with patch("litellm.completion") as mock_comp, patch("time.sleep") as mock_sleep:
        mock_comp.side_effect = [
            litellm.RateLimitError(message="Rate limit hit", model="gpt-4o", llm_provider="openai"),
            mock_response,
        ]

        res = provider.complete(messages=[], model="openai/gpt-4o")

        assert mock_comp.call_count == 2
        assert mock_sleep.call_count == 1
        assert res.text == "Success"
