# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import sys
from enum import IntEnum
from typing import Optional


class WebTier(IntEnum):
    OFF = 0
    SEARCH = 1
    READ_ONLY_BROWSER = 2
    INTERACTIVE_BROWSER = 3


def parse_web_tier(tier_str: str) -> WebTier:
    """Parse web tier name to WebTier enum."""
    cleaned = tier_str.strip().lower()
    if cleaned in ("off", "0"):
        return WebTier.OFF
    elif cleaned in ("search", "1"):
        return WebTier.SEARCH
    elif cleaned in ("read-only browser", "read_only_browser", "readonly", "2"):
        return WebTier.READ_ONLY_BROWSER
    elif cleaned in ("interactive browser", "interactive_browser", "interactive", "3"):
        return WebTier.INTERACTIVE_BROWSER
    else:
        raise ValueError(f"Unknown web tier: '{tier_str}'")


def resolve_effective_web_tier(config_tier_str: str, per_run_tier_str: Optional[str]) -> WebTier:
    """Resolve effective web tier given configured tier and optional per-run flag."""
    config_tier = parse_web_tier(config_tier_str)

    if config_tier in (WebTier.READ_ONLY_BROWSER, WebTier.INTERACTIVE_BROWSER):
        sys.stderr.write("Browser access is not available yet\n")
        sys.exit(2)

    if per_run_tier_str is None:
        return config_tier

    per_run_tier = parse_web_tier(per_run_tier_str)
    if per_run_tier in (WebTier.READ_ONLY_BROWSER, WebTier.INTERACTIVE_BROWSER):
        sys.stderr.write("Browser access is not available yet\n")
        sys.exit(2)

    if config_tier == WebTier.OFF and per_run_tier == WebTier.SEARCH:
        return WebTier.SEARCH

    return min(config_tier, per_run_tier)
