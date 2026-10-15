# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict, List, Optional

from sleepcode.tools.base import Tool, ToolResult


class ToolRegistry:
    """Registers and executes tools, and exports OpenAI tool schemas."""

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def execute(self, name: str, arguments: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        tool = self.get(name)
        if not tool:
            return ToolResult(
                ok=False,
                output=f"Error: Unknown tool '{name}'",
                files_changed=[],
            )
        try:
            return tool.run(arguments, dry_run=dry_run)
        except Exception as e:
            return ToolResult(
                ok=False,
                output=f"Error executing tool '{name}': {str(e)}",
                files_changed=[],
            )

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Format registered tools as OpenAI JSON schemas."""
        schemas = []
        for tool in self._tools.values():
            schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters_schema,
                    },
                }
            )
        return schemas
