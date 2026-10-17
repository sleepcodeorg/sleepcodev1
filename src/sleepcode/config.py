# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, Field


class SleepCodeConfig(BaseModel):
    keys: Dict[str, str] = Field(default_factory=dict)
    default_model: Optional[str] = None
    allowed_commands: Optional[List[str]] = None


def get_config_dir() -> Path:
    """Return the config directory path, respecting SLEEPCODE_HOME."""
    home_override = os.getenv("SLEEPCODE_HOME")
    if home_override:
        return Path(home_override).expanduser().resolve()
    return Path.home() / ".sleepcode"


def get_config_path() -> Path:
    """Return the path to config.yaml."""
    return get_config_dir() / "config.yaml"


def load_config() -> SleepCodeConfig:
    """Load configuration from config.yaml."""
    config_path = get_config_path()
    if not config_path.exists():
        return SleepCodeConfig()

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return SleepCodeConfig(**data)
    except Exception:
        return SleepCodeConfig()


def save_config(config: SleepCodeConfig) -> None:
    """Save configuration to config.yaml with 0600 file permissions from creation."""
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = get_config_path()

    if config_path.exists():
        os.chmod(config_path, 0o600)

    fd = os.open(config_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        yaml.safe_dump(config.model_dump(), f)


def set_provider_key(provider: str, key: str) -> None:
    """Store provider key in config."""
    config = load_config()
    config.keys[provider.lower()] = key
    save_config(config)
