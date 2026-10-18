# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0
"""Base interface for publishing a task branch.

Publishers are the only place where SleepCode may ever send a branch to a
remote. Phase 3.5 provides only a local no-op publisher. A GitHub publisher
will be added in a later phase and must follow the same branch rules.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

PROTECTED_BRANCHES = frozenset({"main", "master"})
TASK_BRANCH_PATTERN = re.compile(r"^sleepcode/[a-z0-9][a-z0-9-]*$")


@dataclass(frozen=True)
class PublishResult:
    """Outcome of a publish attempt."""

    ok: bool
    message: str
    url: str | None = None


def check_branch_allowed(branch_name: str) -> str | None:
    """Return a plain-English refusal reason, or None if the branch may be published."""
    if branch_name in PROTECTED_BRANCHES:
        return (
            f"Refused: '{branch_name}' is a protected branch. Only task branches can be published."
        )
    if not TASK_BRANCH_PATTERN.match(branch_name):
        return (
            f"Refused: '{branch_name}' is not a SleepCode task branch (expected sleepcode/<name>)."
        )
    return None


class Publisher(ABC):
    """Abstract publisher for a finished task branch."""

    @abstractmethod
    def publish(
        self,
        repo_path: Path,
        branch_name: str,
        title: str,
        body: str,
    ) -> PublishResult:
        """Publish the branch. Implementations must call check_branch_allowed first."""
