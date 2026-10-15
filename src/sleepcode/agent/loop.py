# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import json
import secrets
import time
from typing import Any, List, Optional, Set

from pydantic import BaseModel, Field

from sleepcode.agent.messages import Conversation
from sleepcode.agent.prompts import SYSTEM_PROMPT
from sleepcode.costs import calculate_cost
from sleepcode.logs import EventLogger
from sleepcode.providers.base import Provider, ProviderResponse
from sleepcode.tools.registry import ToolRegistry
from sleepcode.workspace import Workspace


class AgentLimits(BaseModel):
    max_iterations: int = 40
    max_total_tokens: int = 500_000
    max_cost_usd: float = 2.00
    max_wall_seconds: float = 1800.0


class AgentResult(BaseModel):
    final_text: str
    run_id: str
    stop_reason: str
    iterations: int
    total_tokens: int
    total_cost: float
    files_changed: List[str] = Field(default_factory=list)


class AgentLoop:
    """Core autonomous loop managing model interaction, tool calls, and limit enforcement."""

    def __init__(
        self,
        task: str,
        workspace: Workspace,
        model: str,
        provider: Provider,
        tools: ToolRegistry,
        limits: Optional[AgentLimits] = None,
        dry_run: bool = False,
        extra_secrets: Optional[Set[str]] = None,
        clock: Optional[Any] = None,
    ) -> None:
        self.task = task
        self.workspace = workspace
        self.model = model
        self.provider = provider
        self.tools = tools
        self.limits = limits or AgentLimits()
        self.dry_run = dry_run
        self.extra_secrets = extra_secrets or set()
        self.clock = clock or time.time

        self.run_id = f"run-{int(self.clock())}-{secrets.token_hex(4)}"
        self.logger = EventLogger(self.run_id, extra_secrets=self.extra_secrets)
        self.conversation = Conversation(SYSTEM_PROMPT)

    def run(self) -> AgentResult:
        self.conversation.add_user_message(self.task)

        iterations = 0
        total_tokens = 0
        total_cost = 0.0
        changed_files_set: Set[str] = set()
        start_time = self.clock()

        warned_unknown_cost = False

        while True:
            iterations += 1

            if iterations > self.limits.max_iterations:
                return self._build_result(
                    final_text="Agent stopped: Exceeded maximum iterations limit.",
                    stop_reason="max_iterations",
                    iterations=iterations - 1,
                    total_tokens=total_tokens,
                    total_cost=total_cost,
                    files_changed=sorted(changed_files_set),
                )

            elapsed = self.clock() - start_time
            if elapsed > self.limits.max_wall_seconds:
                return self._build_result(
                    final_text="Agent stopped: Exceeded maximum wall time limit.",
                    stop_reason="max_wall_seconds",
                    iterations=iterations - 1,
                    total_tokens=total_tokens,
                    total_cost=total_cost,
                    files_changed=sorted(changed_files_set),
                )

            tool_schemas = self.tools.get_schemas()
            try:
                response: ProviderResponse = self.provider.complete(
                    messages=self.conversation.get_messages(),
                    tools=tool_schemas if tool_schemas else None,
                    model=self.model,
                )
            except Exception as e:
                return self._build_result(
                    final_text=f"Agent error during model completion: {str(e)}",
                    stop_reason="error",
                    iterations=iterations,
                    total_tokens=total_tokens,
                    total_cost=total_cost,
                    files_changed=sorted(changed_files_set),
                )

            step_tokens = response.input_tokens + response.output_tokens
            total_tokens += step_tokens

            step_cost = calculate_cost(
                model=self.model,
                prompt_tokens=response.input_tokens,
                completion_tokens=response.output_tokens,
                litellm_cost=response.cost_usd,
            )

            if step_cost is not None:
                total_cost += step_cost
            else:
                if not warned_unknown_cost:
                    msg = (
                        f"Warning: Cost limits cannot be enforced for unknown model '{self.model}'."
                    )
                    print(msg)
                    warned_unknown_cost = True

            if total_tokens > self.limits.max_total_tokens:
                return self._build_result(
                    final_text="Agent stopped: Exceeded maximum total tokens limit.",
                    stop_reason="max_total_tokens",
                    iterations=iterations,
                    total_tokens=total_tokens,
                    total_cost=total_cost,
                    files_changed=sorted(changed_files_set),
                )

            if total_cost > self.limits.max_cost_usd:
                return self._build_result(
                    final_text="Agent stopped: Exceeded maximum cost limit.",
                    stop_reason="max_cost_usd",
                    iterations=iterations,
                    total_tokens=total_tokens,
                    total_cost=total_cost,
                    files_changed=sorted(changed_files_set),
                )

            self.logger.log_event(
                step=iterations,
                role="assistant",
                result_summary=response.text[:200] if response.text else None,
                tokens=step_tokens,
                cost=step_cost,
            )

            if not response.tool_calls:
                final_text = response.text or ""
                if self.dry_run:
                    final_text = f"[DRY RUN] {final_text}"
                self.conversation.add_assistant_message(content=response.text)

                return self._build_result(
                    final_text=final_text,
                    stop_reason="completed",
                    iterations=iterations,
                    total_tokens=total_tokens,
                    total_cost=total_cost,
                    files_changed=sorted(changed_files_set),
                )

            raw_tool_calls_msg = []
            for tc in response.tool_calls:
                raw_tool_calls_msg.append(
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                )
            self.conversation.add_assistant_message(
                content=response.text, tool_calls=raw_tool_calls_msg
            )

            for tc in response.tool_calls:
                res = self.tools.execute(tc.name, tc.arguments, dry_run=self.dry_run)
                for fc in res.files_changed:
                    changed_files_set.add(fc)

                self.conversation.add_tool_result(tool_call_id=tc.id, output=res.output)

                self.logger.log_event(
                    step=iterations,
                    role="tool",
                    tool_name=tc.name,
                    arguments=tc.arguments,
                    result_summary=res.output[:200],
                )

    def _build_result(
        self,
        final_text: str,
        stop_reason: str,
        iterations: int,
        total_tokens: int,
        total_cost: float,
        files_changed: List[str],
    ) -> AgentResult:
        return AgentResult(
            final_text=final_text,
            run_id=self.run_id,
            stop_reason=stop_reason,
            iterations=iterations,
            total_tokens=total_tokens,
            total_cost=total_cost,
            files_changed=files_changed,
        )
