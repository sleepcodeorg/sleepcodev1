# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from pydantic import BaseModel, Field

MAX_OUTPUT_BYTES = 20_480  # 20 KB truncation threshold


class ToolResult(BaseModel):
    ok: bool
    output: str
    files_changed: List[str] = Field(default_factory=list)


def truncate_output(text: str, max_bytes: int = MAX_OUTPUT_BYTES) -> str:
    """Truncate output if string exceeds byte limit."""
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text

    truncated = encoded[:max_bytes].decode("utf-8", errors="ignore")
    return f"{truncated}\n[truncated: {max_bytes} of {len(encoded)} bytes shown]"


class Tool(ABC):
    """Abstract base class for all tools."""

    name: str
    description: str
    parameters_schema: Dict[str, Any]

    @abstractmethod
    def run(self, arguments: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        """Execute tool logic within workspace context."""
        pass
