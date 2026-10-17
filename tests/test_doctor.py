# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path

import pytest

from sleepcode.doctor import (
    check_config_file,
    check_git_availability,
    check_provider_keys,
    check_python_version,
    check_queue_db_writable,
    run_doctor,
)


def test_doctor_python_version() -> None:
    passed, detail, fix = check_python_version()
    assert passed is True
    assert "Python version is" in detail
    assert fix == "None"


def test_doctor_git_availability() -> None:
    passed, detail, fix = check_git_availability()
    assert passed is True
    assert "Git executable found at" in detail
    assert fix == "None"


def test_doctor_config_file_missing_and_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SLEEPCODE_HOME", str(tmp_path))

    # FAIL case - config missing
    passed, detail, fix = check_config_file()
    assert passed is False
    assert "Config file missing" in detail
    assert "sleepcode setup" in fix

    # Create file with 0600
    config_path = tmp_path / "config.yaml"
    config_path.write_text("keys: {}", encoding="utf-8")
    os.chmod(config_path, 0o600)

    # PASS case
    passed, detail, fix = check_config_file()
    assert passed is True
    assert "0600 permissions" in detail


def test_doctor_provider_keys_missing_and_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SLEEPCODE_HOME", str(tmp_path))
    config_path = tmp_path / "config.yaml"

    # FAIL case - no keys
    config_path.write_text("keys: {}", encoding="utf-8")
    os.chmod(config_path, 0o600)
    passed, detail, fix = check_provider_keys()
    assert passed is False
    assert "No API keys configured" in detail

    # PASS case
    fake_key = "fake-groq-key-123456789"
    config_path.write_text(f"keys:\n  groq: {fake_key}", encoding="utf-8")
    passed, detail, fix = check_provider_keys()
    assert passed is True
    assert "groq" in detail
    # Verify fake key itself is never output in detail or fix
    assert fake_key not in detail
    assert fake_key not in fix


def test_doctor_queue_db_writable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLEEPCODE_HOME", str(tmp_path))
    passed, detail, fix = check_queue_db_writable()
    assert passed is True
    assert "writable" in detail


def test_run_doctor_redacts_fake_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("SLEEPCODE_HOME", str(tmp_path))
    fake_key = "fake-key-for-tests-123456789"
    config_path = tmp_path / "config.yaml"
    config_path.write_text(f"keys:\n  groq: {fake_key}", encoding="utf-8")
    os.chmod(config_path, 0o600)

    all_passed = run_doctor()
    assert all_passed is True

    # Verify fake key is never logged or output
    assert fake_key not in capsys.readouterr().out
