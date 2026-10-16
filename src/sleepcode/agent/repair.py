# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from typing import Any, Optional, Set

from pydantic import BaseModel

from sleepcode.agent.loop import AgentLimits, AgentLoop, AgentResult
from sleepcode.config import load_config
from sleepcode.providers.base import Provider
from sleepcode.safety.commands import validate_command
from sleepcode.tools.registry import ToolRegistry
from sleepcode.tools.shell import run_command_in_workspace
from sleepcode.workspace import Workspace


class RepairLoopResult(BaseModel):
    status: str  # "tests_passed" or "tests_failed"
    attempts_used: int
    agent_result: AgentResult
    test_output: str


def run_repair_loop(
    task: str,
    workspace: Workspace,
    model: str,
    provider: Provider,
    tools: ToolRegistry,
    test_cmd: str,
    repair_attempts: int = 2,
    limits: Optional[AgentLimits] = None,
    dry_run: bool = False,
    extra_secrets: Optional[Set[str]] = None,
    clock: Optional[Any] = None,
) -> RepairLoopResult:
    """Run agent task followed by test execution and iterative repair loop."""
    if repair_attempts < 0:
        repair_attempts = 0
    if repair_attempts > 5:
        repair_attempts = 5

    cfg = load_config()
    allowlist = set(cfg.allowed_commands) if cfg.allowed_commands else None

    # Pre-validate test command using safety checks before starting agent loop
    validate_command(test_cmd, workspace, allowed_commands=allowlist)

    agent_limits = limits or AgentLimits()

    loop = AgentLoop(
        task=task,
        workspace=workspace,
        model=model,
        provider=provider,
        tools=tools,
        limits=agent_limits,
        dry_run=dry_run,
        extra_secrets=extra_secrets,
        clock=clock,
    )

    agent_res = loop.run()

    if agent_res.stop_reason not in {"completed"}:
        # Initial run failed due to limits or error
        return RepairLoopResult(
            status="tests_failed",
            attempts_used=0,
            agent_result=agent_res,
            test_output=f"Agent loop stopped early: {agent_res.stop_reason}",
        )

    # First test run
    test_res = run_command_in_workspace(
        test_cmd, workspace, allowed_commands=allowlist, extra_secrets=extra_secrets
    )
    if test_res.ok:
        return RepairLoopResult(
            status="tests_passed",
            attempts_used=0,
            agent_result=agent_res,
            test_output=test_res.output,
        )

    attempts = 0
    while attempts < repair_attempts:
        attempts += 1

        repair_prompt = (
            f"The task implementation was run, but the test command `{test_cmd}` failed.\n"
            f"Test command output:\n{test_res.output}\n\n"
            "Please analyze the error output and fix workspace files so test command passes."
        )

        loop.conversation.add_user_message(repair_prompt)

        # Resume agent loop with cumulative limits
        agent_res = loop.run()

        if agent_res.stop_reason not in {"completed"}:
            msg = f"Agent stopped during repair: {agent_res.stop_reason}\n\n{test_res.output}"
            return RepairLoopResult(
                status="tests_failed",
                attempts_used=attempts,
                agent_result=agent_res,
                test_output=msg,
            )

        test_res = run_command_in_workspace(
            test_cmd, workspace, allowed_commands=allowlist, extra_secrets=extra_secrets
        )
        if test_res.ok:
            return RepairLoopResult(
                status="tests_passed",
                attempts_used=attempts,
                agent_result=agent_res,
                test_output=test_res.output,
            )

    return RepairLoopResult(
        status="tests_failed",
        attempts_used=attempts,
        agent_result=agent_res,
        test_output=test_res.output,
    )
