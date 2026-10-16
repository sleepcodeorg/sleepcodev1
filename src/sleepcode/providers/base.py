# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: Dict[str, Any]


class ProviderResponse(BaseModel):
    text: Optional[str] = None
    tool_calls: List[ToolCall] = []
    input_tokens: int = 0
    output_tokens: int = 0
    finish_reason: Optional[str] = None
    cost_usd: Optional[float] = None


class Provider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: str = "",
        max_tokens: int = 4096,
    ) -> ProviderResponse:
        """Send completion request to LLM provider."""
        pass
