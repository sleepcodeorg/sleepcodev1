# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from sleepcode.cli import app
from sleepcode.providers.base import ProviderResponse
from sleepcode.providers.fake_provider import FakeProvider
from sleepcode.setup_wizard import set_test_wizard_provider_override

runner = CliRunner()


def test_setup_wizard_flow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLEEPCODE_HOME", str(tmp_path))

    fake_resp = ProviderResponse(text="Hello from test provider", tool_calls=[])
    set_test_wizard_provider_override(FakeProvider([fake_resp]))

    fake_key = "fake-key-for-tests-1234567890"

    user_inputs = "1\n\n\n\n"

    with patch("getpass.getpass", return_value=fake_key):
        result = runner.invoke(app, ["setup"], input=user_inputs)

    assert result.exit_code == 0, result.output
    assert "Welcome to SleepCode Setup Wizard" in result.output
    assert "Key works!" in result.output
    assert "saved securely" in result.output

    config_path = tmp_path / "config.yaml"
    assert config_path.exists()

    mode = os.stat(config_path).st_mode & 0o777
    assert mode == 0o600, f"Expected 0600 mode, got {oct(mode)}"

    assert fake_key not in result.output


def test_setup_wizard_no_overwrite_without_confirm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SLEEPCODE_HOME", str(tmp_path))
    config_path = tmp_path / "config.yaml"

    import yaml

    config_data = {
        "keys": {"groq": "existing-fake-key"},
        "default_model": "groq/llama-3.3-70b-versatile",
    }
    config_path.write_text(yaml.dump(config_data), encoding="utf-8")
    os.chmod(config_path, 0o600)

    user_inputs = "1\nn\n"
    result = runner.invoke(app, ["setup"], input=user_inputs)

    assert result.exit_code == 0
    assert "Setup cancelled. Existing config kept." in result.output


def test_doctor_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLEEPCODE_HOME", str(tmp_path))

    fake_key = "fake-key-for-doctor-test-999"
    config_path = tmp_path / "config.yaml"
    import yaml

    config_data = {"keys": {"openai": fake_key}}
    config_path.write_text(yaml.dump(config_data), encoding="utf-8")
    os.chmod(config_path, 0o600)

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "SleepCode Doctor Diagnostics" in result.output
    assert fake_key not in result.output
