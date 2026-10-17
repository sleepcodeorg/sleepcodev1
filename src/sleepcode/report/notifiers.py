# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import json
import shutil
import subprocess
import urllib.request
from abc import ABC, abstractmethod
from typing import Optional

from sleepcode.config import load_config
from sleepcode.secrets import redact_secrets


class Notifier(ABC):
    """Abstract interface for morning report notifications."""

    @abstractmethod
    def send_summary(self, summary_line: str) -> bool:
        """Send a one-line summary notification."""
        pass


class DesktopNotifier(Notifier):
    """Desktop notification provider using notify-send if available."""

    def send_summary(self, summary_line: str) -> bool:
        safe_line = redact_secrets(summary_line)
        notify_path = shutil.which("notify-send")
        if not notify_path:
            return False

        try:
            subprocess.run(
                [notify_path, "SleepCode Morning Report", safe_line],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            return True
        except Exception:
            return False


class WebhookNotifier(Notifier):
    """Webhook notification provider sending summary line to configured URL."""

    def __init__(self, webhook_url: Optional[str] = None) -> None:
        self.webhook_url = webhook_url

    def send_summary(self, summary_line: str) -> bool:
        safe_line = redact_secrets(summary_line)
        url = self.webhook_url
        if not url:
            config = load_config()
            url = getattr(config, "webhook_url", None)

        if not url:
            return False

        payload = json.dumps({"text": safe_line, "summary": safe_line}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                status_code: int = getattr(resp, "status", 0)
                return bool(200 <= status_code < 300)
        except Exception:
            return False


def notify_all(summary_line: str, webhook_url: Optional[str] = None) -> None:
    """Send summary line via all available notifiers."""
    desktop = DesktopNotifier()
    desktop.send_summary(summary_line)

    webhook = WebhookNotifier(webhook_url=webhook_url)
    webhook.send_summary(summary_line)
