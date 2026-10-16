# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import os
from typing import Dict


def build_minimal_env() -> Dict[str, str]:
    """Build a sanitized minimal environment dictionary for child process execution.

    Filters out any environment variables whose names end with _API_KEY, _TOKEN,
    _SECRET, or contain PASSWORD (case-insensitive).
    """
    clean_env: Dict[str, str] = {}

    for key, val in os.environ.items():
        key_upper = key.upper()
        if (
            key_upper.endswith("_API_KEY")
            or key_upper.endswith("_TOKEN")
            or key_upper.endswith("_SECRET")
            or "PASSWORD" in key_upper
        ):
            continue
        clean_env[key] = val

    # Disable python bytecode caching in child workspace subprocesses
    clean_env["PYTHONDONTWRITEBYTECODE"] = "1"

    return clean_env
