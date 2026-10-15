# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import pytest

from sleepcode.secrets import get_secret, redact_secrets


def test_get_secret_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-test12345678901234567890")
    secret = get_secret("openai")
    assert secret == "sk-proj-test12345678901234567890"


def test_get_secret_config() -> None:
    config_keys = {"openai": "sk-configkey123456789012345678"}
    secret = get_secret("openai", config_keys)
    assert secret == "sk-configkey123456789012345678"


def test_redact_secrets_patterns() -> None:
    fake_openai = "sk-proj-1234567890abcdef123456"
    fake_groq = "gsk_1234567890abcdef123456"
    fake_gemini = "AIzaSy1234567890abcdef123456"

    text = f"Errors: {fake_openai}, {fake_groq}, and {fake_gemini}"
    redacted = redact_secrets(text)

    assert fake_openai not in redacted
    assert fake_groq not in redacted
    assert fake_gemini not in redacted
    assert redacted.count("[REDACTED]") == 3


def test_redact_secrets_explicit() -> None:
    custom_secret = "my_super_secret_password"
    text = f"Failed connecting with {custom_secret}"
    redacted = redact_secrets(text, extra_secrets={custom_secret})

    assert custom_secret not in redacted
    assert "[REDACTED]" in redacted
