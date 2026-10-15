# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict, List, Optional

from sleepcode.providers.base import Provider, ProviderResponse


class FakeProvider(Provider):
    """Deterministic scripted provider for offline testing and deterministic loops."""

    def __init__(self, responses: List[ProviderResponse]) -> None:
        self.responses = list(responses)
        self.calls: List[Dict[str, Any]] = []

    def complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: str = "",
        max_tokens: int = 4096,
    ) -> ProviderResponse:
        self.calls.append(
            {
                "messages": messages,
                "tools": tools,
                "model": model,
                "max_tokens": max_tokens,
            }
        )

        if not self.responses:
            raise RuntimeError("FakeProvider ran out of scripted responses.")

        return self.responses.pop(0)
