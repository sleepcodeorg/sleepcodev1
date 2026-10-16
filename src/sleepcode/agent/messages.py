# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict, List, Optional


class Conversation:
    """Manages system and user messages, tool calls, and tool responses."""

    def __init__(self, system_prompt: str) -> None:
        self.messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]

    def add_user_message(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(
        self,
        content: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        msg: Dict[str, Any] = {"role": "assistant"}
        if content is not None:
            msg["content"] = content
        if tool_calls:
            msg["tool_calls"] = tool_calls
        self.messages.append(msg)

    def add_tool_result(self, tool_call_id: str, output: str) -> None:
        self.messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": output,
            }
        )

    def get_messages(self) -> List[Dict[str, Any]]:
        return list(self.messages)
