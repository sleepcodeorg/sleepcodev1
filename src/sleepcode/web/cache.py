# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional


def get_cache_dir() -> Path:
    """Return cache directory respecting SLEEPCODE_HOME."""
    home_override = os.getenv("SLEEPCODE_HOME")
    if home_override:
        base = Path(home_override).expanduser().resolve()
    else:
        base = Path.home() / ".sleepcode"
    cache_dir = base / "web_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _url_to_cache_key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


class WebCache:
    """Disk cache for fetch results keyed by URL SHA-256 with 0600 file permissions."""

    def __init__(self, ttl_hours: int = 24) -> None:
        self.ttl_seconds = ttl_hours * 3600

    def get(self, url: str) -> Optional[Dict[str, Any]]:
        cache_dir = get_cache_dir()
        key = _url_to_cache_key(url)
        cache_file = cache_dir / f"{key}.json"

        if not cache_file.exists():
            return None

        try:
            mtime = cache_file.stat().st_mtime
            if time.time() - mtime > self.ttl_seconds:
                return None

            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
                return None
        except Exception:
            return None

    def set(self, url: str, data: Dict[str, Any]) -> None:
        cache_dir = get_cache_dir()
        key = _url_to_cache_key(url)
        cache_file = cache_dir / f"{key}.json"

        if cache_file.exists():
            os.chmod(cache_file, 0o600)

        fd = os.open(cache_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
