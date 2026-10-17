# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sleepcode.queue.db import get_db_connection
from sleepcode.queue.repository import TaskRepository
from sleepcode.report.markdown import generate_morning_report, truncate_excerpt
from sleepcode.report.notifiers import WebhookNotifier


def test_truncate_excerpt_and_redact() -> None:
    fake_secret = "dummy_secret_key_12345"
    long_text = f"Some error log with {fake_secret} and " + "a" * 600

    excerpt = truncate_excerpt(long_text, max_len=100)
    assert fake_secret in long_text
    assert "(truncated)" in excerpt


def test_generate_morning_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLEEPCODE_HOME", str(tmp_path))

    conn = get_db_connection()
    repo = TaskRepository(conn)

    t1 = repo.add_task("Task 1 text", "/path/1", "groq/llama-3.3-70b-versatile")
    repo.update_task_status(t1.id, "succeeded", branch_name="sleepcode/task-1-branch")
    run1 = repo.add_run(
        t1.id,
        status="succeeded",
        cost_usd=0.0012,
        tokens=150,
        files_changed=["a.py"],
        tests_passed=True,
        notes="All good",
    )
    repo.update_run(
        run1.id,
        status="succeeded",
        cost_usd=0.0012,
        tokens=150,
        files_changed=["a.py"],
        tests_passed=True,
        notes="All good",
    )

    report_path, summary = generate_morning_report(date_str="2026-03-30")

    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")

    assert "# SleepCode Morning Report (2026-03-30)" in content
    assert "Task 1 text" in content
    assert "Done" in content
    assert "sleepcode/task-1-branch" in content
    assert "$0.0012" in content


def test_webhook_notifier() -> None:
    notifier = WebhookNotifier(webhook_url="http://example.com/webhook")

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        success = notifier.send_summary("SleepCode Morning Report: 1 task processed")
        assert success is True
        assert mock_urlopen.called
