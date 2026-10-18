# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for the local publisher and branch rules."""

from pathlib import Path

import pytest

from sleepcode.publish import PublishResult
from sleepcode.publish.base import check_branch_allowed
from sleepcode.publish.local import LocalPublisher


@pytest.mark.parametrize("branch", ["main", "master"])
def test_protected_branches_refused(branch: str, tmp_path: Path) -> None:
    result = LocalPublisher().publish(tmp_path, branch, "t", "b")
    assert isinstance(result, PublishResult)
    assert result.ok is False
    assert "protected" in result.message


@pytest.mark.parametrize(
    "branch", ["feature/x", "sleepcode", "sleepcode/", "Sleepcode/Abc", "sleepcode/a b"]
)
def test_non_task_branches_refused(branch: str, tmp_path: Path) -> None:
    result = LocalPublisher().publish(tmp_path, branch, "t", "b")
    assert result.ok is False
    assert "not a SleepCode task branch" in result.message


def test_task_branch_allowed_and_nothing_sent(tmp_path: Path) -> None:
    result = LocalPublisher().publish(tmp_path, "sleepcode/fix-tests-20260101-000000", "t", "b")
    assert result.ok is True
    assert "local only" in result.message
    assert result.url is None


def test_check_branch_allowed_returns_none_for_task_branch() -> None:
    assert check_branch_allowed("sleepcode/add-parser-20260101-120000") is None
