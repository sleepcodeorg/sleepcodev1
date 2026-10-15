# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import fnmatch
import re
from pathlib import Path
from typing import Any, Dict, List, Set

from sleepcode.tools.base import Tool, ToolResult, truncate_output
from sleepcode.workspace import Workspace, WorkspaceError

EXCLUDED_DIRS: Set[str] = {".git", "node_modules", "__pycache__", ".venv"}
MAX_MATCHES = 200


class SearchTool(Tool):
    name = "search"
    description = "Search for plain-text or regex patterns across workspace files."
    parameters_schema = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Text pattern or regex to search for"},
            "path": {"type": "string", "description": "Relative path to search inside"},
            "glob": {"type": "string", "description": "Optional file pattern glob (e.g., '*.py')"},
            "regex": {"type": "boolean", "description": "Set to true to use regex matching"},
        },
        "required": ["pattern"],
    }

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def run(self, arguments: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        pattern = arguments.get("pattern")
        if not pattern:
            return ToolResult(ok=False, output="Error: pattern parameter is required.")

        path_str = arguments.get("path") or "."
        glob_pattern = arguments.get("glob")
        use_regex = bool(arguments.get("regex", False))

        try:
            start_path = self.workspace.resolve_path(path_str)
        except WorkspaceError as e:
            return ToolResult(ok=False, output=str(e))

        if not start_path.exists():
            return ToolResult(ok=False, output=f"Error: Path '{path_str}' does not exist.")

        regex_obj = None
        if use_regex:
            try:
                regex_obj = re.compile(pattern)
            except re.error as e:
                return ToolResult(ok=False, output=f"Invalid regex pattern: {str(e)}")

        results: List[str] = []
        match_count = 0

        files_to_check: List[Path] = []
        if start_path.is_file():
            files_to_check.append(start_path)
        else:
            for item in start_path.rglob("*"):
                if any(part in EXCLUDED_DIRS for part in item.parts):
                    continue
                if item.is_file():
                    if glob_pattern and not fnmatch.fnmatch(item.name, glob_pattern):
                        continue
                    files_to_check.append(item)

        for file_path in sorted(files_to_check):
            if match_count >= MAX_MATCHES:
                break
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            rel_file = file_path.relative_to(self.workspace.root)
            for line_no, line in enumerate(content.splitlines(), start=1):
                is_match = False
                if use_regex and regex_obj:
                    if regex_obj.search(line):
                        is_match = True
                else:
                    if pattern in line:
                        is_match = True

                if is_match:
                    match_count += 1
                    results.append(f"{rel_file}:{line_no}:{line}")
                    if match_count >= MAX_MATCHES:
                        break

        if not results:
            return ToolResult(ok=True, output="No matches found.", files_changed=[])

        summary = "\n".join(results)
        if match_count >= MAX_MATCHES:
            summary += f"\n[capped at {MAX_MATCHES} matches]"

        return ToolResult(ok=True, output=truncate_output(summary), files_changed=[])
