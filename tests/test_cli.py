# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from typer.testing import CliRunner

from sleepcode.cli import app, set_test_provider_override
from sleepcode.providers.base import ProviderResponse
from sleepcode.providers.fake_provider import FakeProvider

runner = CliRunner()


def test_cli_version() -> None:
    res = runner.invoke(app, ["version"])
    assert res.exit_code == 0
    assert "0.1.0" in res.output


def test_cli_config_list(sleepcode_home: Path) -> None:
    res = runner.invoke(app, ["config", "list"])
    assert res.exit_code == 0
    assert "openai:" in res.output
    assert "sk-" not in res.output


def test_cli_run_missing_workspace() -> None:
    args = ["run", "test task", "--workspace", "/nonexistent_dir_123", "--model", "openai/gpt-4o"]
    res = runner.invoke(app, args)
    assert res.exit_code == 1
    assert "does not exist" in res.output


def test_cli_run_fake_provider(temp_workspace: Path, sleepcode_home: Path) -> None:
    fake_resp = ProviderResponse(text="CLI Success", tool_calls=[])
    set_test_provider_override(FakeProvider([fake_resp]))

    ws_dir = sleepcode_home / "ws"
    ws_dir.mkdir()

    try:
        res = runner.invoke(
            app,
            [
                "run",
                "CLI test task",
                "--workspace",
                str(ws_dir),
                "--model",
                "openai/gpt-4o-mini",
                "--dry-run",
            ],
        )
        assert res.exit_code == 0
        assert "SleepCode Agent Summary" in res.output
    finally:
        set_test_provider_override(None)
