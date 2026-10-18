# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime, timezone
from typing import Any, Dict, List

from pydantic import BaseModel

_audit_log_events: List[Dict[str, Any]] = []


class WebAuditEvent(BaseModel):
    timestamp: str
    tool_name: str
    target: str
    status: str
    bytes_read: int
    cache_hit: bool
    truncated: bool


def record_web_audit_event(
    tool_name: str,
    target: str,
    status: str,
    bytes_read: int = 0,
    cache_hit: bool = False,
    truncated: bool = False,
) -> None:
    """Record a web access audit event in memory."""
    event = WebAuditEvent(
        timestamp=datetime.now(timezone.utc).isoformat(),
        tool_name=tool_name,
        target=target,
        status=status,
        bytes_read=bytes_read,
        cache_hit=cache_hit,
        truncated=truncated,
    )
    _audit_log_events.append(event.model_dump())


def get_latest_audit_log() -> List[Dict[str, Any]]:
    """Return in-memory recorded web audit log events."""
    return list(_audit_log_events)


def clear_audit_log() -> None:
    """Clear memory audit log."""
    _audit_log_events.clear()
