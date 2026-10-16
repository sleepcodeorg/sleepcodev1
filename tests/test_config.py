# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from sleepcode.config import SleepCodeConfig, load_config, save_config, set_provider_key


def test_config_load_save(sleepcode_home: Path) -> None:
    config = SleepCodeConfig(keys={"openai": "test-key"}, default_model="openai/gpt-4o")
    save_config(config)

    loaded = load_config()
    assert loaded.keys["openai"] == "test-key"
    assert loaded.default_model == "openai/gpt-4o"


def test_set_provider_key(sleepcode_home: Path) -> None:
    set_provider_key("anthropic", "sk-ant-testkey")
    loaded = load_config()
    assert loaded.keys["anthropic"] == "sk-ant-testkey"

    config_file = sleepcode_home / "config.yaml"
    assert config_file.exists()
    assert (config_file.stat().st_mode & 0o777) == 0o600
