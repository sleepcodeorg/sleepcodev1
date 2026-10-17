# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path

import pytest

from sleepcode.config import SleepCodeConfig, load_config, save_config, set_provider_key


def test_config_load_save(sleepcode_home: Path) -> None:
    config = SleepCodeConfig(keys={"openai": "fake-test-key"}, default_model="openai/gpt-4o")
    save_config(config)

    loaded = load_config()
    assert loaded.keys["openai"] == "fake-test-key"
    assert loaded.default_model == "openai/gpt-4o"


def test_set_provider_key(sleepcode_home: Path) -> None:
    set_provider_key("anthropic", "fake-ant-testkey")
    loaded = load_config()
    assert loaded.keys["anthropic"] == "fake-ant-testkey"

    config_file = sleepcode_home / "config.yaml"
    assert config_file.exists()
    assert (config_file.stat().st_mode & 0o777) == 0o600


def test_save_config_initial_creation_mode_0600(
    sleepcode_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_file = sleepcode_home / "config.yaml"
    assert not config_file.exists()

    open_calls = []
    real_os_open = os.open

    def mock_os_open(path, flags, mode=0o777, *args, **kwargs):
        open_calls.append((path, flags, mode))
        return real_os_open(path, flags, mode, *args, **kwargs)

    monkeypatch.setattr(os, "open", mock_os_open)

    config = SleepCodeConfig(keys={"groq": "fake-groq-key-123"})
    save_config(config)

    assert config_file.exists()
    assert (config_file.stat().st_mode & 0o777) == 0o600

    # Verify os.open was called with mode 0o600
    assert len(open_calls) > 0
    config_path_str = str(config_file)
    relevant_calls = [c for c in open_calls if str(c[0]) == config_path_str]
    assert len(relevant_calls) == 1
    path_arg, flags_arg, mode_arg = relevant_calls[0]
    assert mode_arg == 0o600
    assert (flags_arg & os.O_CREAT) != 0

    # Also test existing file with looser permissions (0o644) gets set to 0o600 before writing
    config_file.chmod(0o644)
    assert (config_file.stat().st_mode & 0o777) == 0o644

    set_provider_key("groq", "fake-groq-key-456")
    assert (config_file.stat().st_mode & 0o777) == 0o600
