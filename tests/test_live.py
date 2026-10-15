# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path

import pytest

from sleepcode.agent.loop import AgentLoop
from sleepcode.providers.litellm_provider import LiteLLMProvider
from sleepcode.tools.files import ReadFileTool, WriteFileTool
from sleepcode.tools.registry import ToolRegistry
from sleepcode.workspace import Workspace


@pytest.mark.skipif(
    os.getenv("SLEEPCODE_LIVE_TEST") != "1",
    reason="Live tests require SLEEPCODE_LIVE_TEST=1 and real API key",
)
def test_live_agent_run(tmp_path: Path) -> None:
    model = os.getenv("SLEEPCODE_LIVE_MODEL", "openai/gpt-4o-mini")
    ws_dir = tmp_path / "live_ws"
    ws_dir.mkdir()
    ws = Workspace(ws_dir)

    registry = ToolRegistry()
    registry.register(WriteFileTool(ws))
    registry.register(ReadFileTool(ws))

    provider = LiteLLMProvider()

    loop = AgentLoop(
        task="Create a file named live_test.txt with content 'LIVE SUCCESS'",
        workspace=ws,
        model=model,
        provider=provider,
        tools=registry,
    )

    result = loop.run()
    assert result.stop_reason == "completed"

    created_file = ws_dir / "live_test.txt"
    assert created_file.exists()
    assert "LIVE SUCCESS" in created_file.read_text()
