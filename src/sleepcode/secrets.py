# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import os
import re
from typing import Dict, Optional, Set

# Known secret patterns: sk-..., gsk_..., AIza...
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"gsk_[A-Za-z0-9_-]{20,}"),
    re.compile(r"AIza[A-Za-z0-9_-]{20,}"),
]

PROVIDER_ENV_VARS = [
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GROQ_API_KEY",
    "GEMINI_API_KEY",
    "OPENROUTER_API_KEY",
    "MISTRAL_API_KEY",
]


def get_secret(provider: str, config_keys: Optional[Dict[str, str]] = None) -> Optional[str]:
    """Retrieve API key for provider from env var or config dict."""
    env_var_name = f"{provider.upper()}_API_KEY"
    env_val = os.getenv(env_var_name)
    if env_val:
        return env_val

    if config_keys:
        return config_keys.get(provider.lower()) or config_keys.get(env_var_name)
    return None


def redact_secrets(text: str, extra_secrets: Optional[Set[str]] = None) -> str:
    """Mask any known secret values or pattern matches in text."""
    if not text:
        return text

    redacted = text

    # Redact explicit exact strings if non-empty
    if extra_secrets:
        for secret in extra_secrets:
            if secret and len(secret.strip()) > 0:
                redacted = redacted.replace(secret, "[REDACTED]")

    # Also check env vars for active keys
    for env_var in PROVIDER_ENV_VARS:
        val = os.getenv(env_var)
        if val and len(val.strip()) > 0:
            redacted = redacted.replace(val, "[REDACTED]")

    # Apply regex patterns
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)

    return redacted
