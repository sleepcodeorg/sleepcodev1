# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

from sleepcode.config import get_config_dir
from sleepcode.secrets import redact_secrets


class EventLogger:
    """Logs structured run events as JSON lines with secret redaction."""

    def __init__(self, run_id: str, extra_secrets: Optional[Set[str]] = None) -> None:
        self.run_id = run_id
        self.extra_secrets = extra_secrets or set()
        self.log_dir = get_config_dir() / "runs" / run_id
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "events.jsonl"

    def log_event(
        self,
        step: int,
        role: str,
        tool_name: Optional[str] = None,
        arguments: Optional[Dict[str, Any]] = None,
        result_summary: Optional[str] = None,
        tokens: Optional[int] = None,
        cost: Optional[float] = None,
    ) -> None:
        """Append one JSON line event to events.jsonl."""
        timestamp = datetime.now(timezone.utc).isoformat()

        # Prepare payload
        event = {
            "timestamp": timestamp,
            "run_id": self.run_id,
            "step": step,
            "role": role,
            "tool_name": tool_name,
            "arguments": arguments,
            "result_summary": result_summary,
            "tokens": tokens,
            "cost": cost,
        }

        # Convert to string and redact secrets
        raw_json = json.dumps(event)
        redacted_json = redact_secrets(raw_json, extra_secrets=self.extra_secrets)

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(redacted_json + "\n")
