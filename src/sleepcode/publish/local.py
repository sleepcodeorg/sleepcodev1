# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0
"""Local-only publisher: records intent and never touches a remote."""

from pathlib import Path

from sleepcode.publish.base import Publisher, PublishResult, check_branch_allowed


class LocalPublisher(Publisher):
    """No-op publisher. It validates the branch and reports that nothing was sent."""

    def publish(
        self,
        repo_path: Path,
        branch_name: str,
        title: str,
        body: str,
    ) -> PublishResult:
        """Validate the branch name and return a local-only result. Never runs git push."""
        refusal = check_branch_allowed(branch_name)
        if refusal is not None:
            return PublishResult(ok=False, message=refusal)
        return PublishResult(
            ok=True,
            message="Not published (local only). The branch stays in your repo.",
            url=None,
        )
